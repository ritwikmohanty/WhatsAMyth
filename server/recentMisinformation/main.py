from typing import Optional, List
from sqlmodel import Field, SQLModel, create_engine, Session, select
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
import os
import requests
import feedparser
from datetime import datetime
import hashlib
import json
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# CONFIG
DB_FILE = os.getenv("WHATSAMYTH_DB", "whatsamyth.db")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # set this in environment if using Google API
USER_AGENT = "WhatsAMyth/1.0 (+https://example.com)"

app = FastAPI(title="WhatsAMyth Backend", version="0.1")

# Database models
class Claim(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    claim_text: str
    claimant: Optional[str] = None
    claim_date: Optional[str] = None
    publisher: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    rating: Optional[str] = None
    review_date: Optional[str] = None
    source: Optional[str] = None  # e.g., google, altnews, pib
    fetched_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    raw_json: Optional[str] = None
    dedupe_hash: Optional[str] = None

# Create DB engine
engine = create_engine(f"sqlite:///{DB_FILE}", echo=False, connect_args={"check_same_thread": False})

def init_db():
    SQLModel.metadata.create_all(engine)

init_db()

# Utility helpers
def make_hash(s: str) -> str:
    h = hashlib.sha256()
    h.update(s.encode('utf-8'))
    return h.hexdigest()

def normalize_text(s: str) -> str:
    if not s:
        return ""
    s2 = s.lower()
    s2 = ' '.join(s2.split())
    return s2

# Ingestion logic
def upsert_claim(session: Session, claim_data: dict, source_label: str = "unknown") -> Claim:
    """Insert or update claim by dedupe_hash or url."""
    url = claim_data.get('url') or claim_data.get('link')
    claim_text = claim_data.get('claim') or claim_data.get('text') or claim_data.get('title') or ''
    norm = normalize_text(claim_text)
    # primary dedupe key: canonical url or normalized text snippet
    dedupe_key = url or norm[:300]
    dedupe_hash = make_hash(dedupe_key)

    # try find existing
    stmt = select(Claim).where(Claim.dedupe_hash == dedupe_hash)
    existing = session.exec(stmt).first()
    if existing:
        # update fetched_at and maybe raw_json
        existing.fetched_at = datetime.utcnow().isoformat()
        try:
            existing.raw_json = json.dumps(claim_data, ensure_ascii=False)
        except Exception:
            existing.raw_json = str(claim_data)
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    c = Claim(
        claim_text=claim_text,
        claimant=claim_data.get('claimant'),
        claim_date=claim_data.get('claimDate') or claim_data.get('published'),
        publisher=claim_data.get('publisher') or claim_data.get('source'),
        title=claim_data.get('title'),
        url=url,
        rating=claim_data.get('rating') or claim_data.get('textualRating') or claim_data.get('verdict'),
        review_date=claim_data.get('reviewDate'),
        source=source_label,
        raw_json=json.dumps(claim_data, ensure_ascii=False),
        dedupe_hash=dedupe_hash
    )
    session.add(c)
    session.commit()
    session.refresh(c)
    return c

# Google Fact Check API integration
def fetch_google_claims(query: str = "india", max_results: int = 20) -> List[dict]:
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY env var not set")
    url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    params = {
        'query': query,
        'languageCode': 'en',
        'pageSize': max_results,
        'key': GOOGLE_API_KEY
    }
    headers = {'User-Agent': USER_AGENT}
    r = requests.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()
    out = []
    for claim in data.get('claims', []):
        base = {
            'claim': claim.get('text'),
            'claimant': claim.get('claimant'),
            'claimDate': claim.get('claimDate')
        }
        for review in claim.get('claimReview', []):
            rec = base.copy()
            rec.update({
                'publisher': review.get('publisher', {}).get('name'),
                'title': review.get('title'),
                'url': review.get('url'),
                'textualRating': review.get('textualRating'),
                'reviewDate': review.get('reviewDate')
            })
            out.append(rec)
    return out

# RSS / site fetchers — simple: list of feeds
DEFAULT_RSS_FEEDS = [
    # Indian fact-check RSS feeds
    "https://www.altnews.in/feed/",
    "https://factly.in/feed/",
    "https://www.boomlive.in/rss.xml",
    "https://pib.gov.in/PressReleasePage.aspx?MenuId=27",  # PIB Fact Check (not a true RSS, but for demo)
    "https://www.indiatoday.in/fact-check/feed",            # India Today Fact Check
    "https://www.thequint.com/news/webqoof/rss.xml",        # The Quint WebQoof
    "https://www.newschecker.in/feed/",                    # Newschecker                   # Vishvas News
    # add more as needed
]

def fetch_feed(url: str, timeout: int = 12) -> List[dict]:
    headers = {'User-Agent': USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except Exception as e:
        print("feed fetch failed", url, e)
        return []
    feed = feedparser.parse(resp.content)
    rows = []
    for e in feed.entries:
        # Only include English entries
        lang = e.get('language') or e.get('lang') or e.get('dc_language') or ''
        # Some feeds may not have a language field, so try to filter by summary/title if possible
        if lang and not lang.lower().startswith('en'):
            continue
        published = e.get('published') or e.get('updated') or ''
        rows.append({
            'title': e.get('title'),
            'link': e.get('link'),
            'published': published,
            'summary': e.get('summary', '')
        })
    return rows

# API models
class FetchResponse(BaseModel):
    ingested: int
    source: str

# Routes
@app.post('/fetch/google', response_model=FetchResponse)
def fetch_google_endpoint(query: str = Query("india"), max: int = Query(50)):
    """Fetch recent claims from Google Fact Check API and store them."""
    claims = fetch_google_claims(query=query, max_results=max)
    cnt = 0
    with Session(engine) as session:
        for c in claims:
            upsert_claim(session, c, source_label='google')
            cnt += 1
    return {'ingested': cnt, 'source': 'google'}

@app.post('/fetch/rss', response_model=FetchResponse)
def fetch_rss_endpoint(feeds: Optional[List[str]] = Query(None)):
    """Fetch a list of RSS feeds (or DEFAULT_RSS_FEEDS) and ingest them."""
    feed_list = feeds or DEFAULT_RSS_FEEDS
    cnt = 0
    with Session(engine) as session:
        for f in feed_list:
            items = fetch_feed(f)
            if not items:
                print(f"No items found for feed: {f}")
            for it in items:
                upsert_claim(session, it, source_label=f)
                cnt += 1
    return {'ingested': cnt, 'source': 'rss'}

from collections import defaultdict

@app.get('/claims')
def list_claims(limit: int = 20, offset: int = 0):
    from datetime import datetime, timedelta
    with Session(engine) as session:
        one_week_ago = datetime.utcnow() - timedelta(days=7)
        stmt = select(Claim).where(Claim.fetched_at >= one_week_ago.isoformat()).order_by(Claim.fetched_at.desc())
        rows = session.exec(stmt).all()
        # Group by source to ensure at least one from each
        source_map = defaultdict(list)
        for row in rows:
            source_map[row.source or 'unknown'].append(row)
        # Collect at least one from each source, then fill up to limit
        selected = []
        for src, items in source_map.items():
            if items:
                selected.append(items[0])
        # Fill up to limit with remaining, sorted by date
        remaining = [r for r in rows if r not in selected]
        selected += remaining[:max(0, limit - len(selected))]
        selected = selected[:limit]
        # Format: misinformation, rebuttal, link, date, source
        formatted = []
        for row in selected:
            misinformation = row.claim_text or row.title or ""
            rebuttal = ""
            if row.rating:
                rebuttal = row.rating
            elif row.review_date:
                rebuttal = row.review_date
            elif row.raw_json:
                try:
                    raw = json.loads(row.raw_json)
                    rebuttal = raw.get('summary', '') or raw.get('textualRating', '')
                except Exception:
                    rebuttal = ""
            link = row.url or row.title or row.publisher or ""
            formatted.append({
                "misinformation": misinformation,
                "rebuttal": rebuttal,
                "link": link,
                "date": row.claim_date or row.fetched_at,
                "source": row.source
            })
        return formatted

@app.get('/claim/{claim_id}')
def get_claim(claim_id: int):
    with Session(engine) as session:
        c = session.get(Claim, claim_id)
        if not c:
            raise HTTPException(status_code=404, detail='not found')
        return c

@app.get('/search')
def search(q: str = Query(..., min_length=1), limit: int = 50):
    qlike = f"%{q}%"
    with Session(engine) as session:
        stmt = select(Claim).where(Claim.claim_text.ilike(qlike)).limit(limit)
        rows = session.exec(stmt).all()
        return rows

# simple health
@app.get('/health')
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "Welcome to WhatsAMyth API. See /docs for API documentation."}

# Optional: background task runner example (not auto-run here) — you can call these from cron or GitHub Actions
@app.post('/run/daily-fetch')
def run_daily_fetch(background_tasks: BackgroundTasks):
    # trigger both Google + RSS in background
    def task():
        try:
            print('starting background fetch')
            claims = []
            try:
                claims = fetch_google_claims(query='india', max_results=100)
            except Exception as e:
                print('google fetch error', e)
            with Session(engine) as session:
                for c in claims:
                    upsert_claim(session, c, source_label='google')
                for f in DEFAULT_RSS_FEEDS:
                    items = fetch_feed(f)
                    for it in items:
                        upsert_claim(session, it, source_label=f)
            print('background fetch complete')
        except Exception as e:
            print('background fetch failed', e)
    background_tasks.add_task(task)
    return {"status": "scheduled"}
