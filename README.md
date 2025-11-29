# WhatsAMyth

**WhatsAMyth** is an intelligent misinformation detection pipeline that automatically detects, fact-checks, and rebuts false claims in real-time. It listens to messaging platforms (WhatsApp, Telegram, web), verifies claims against authoritative sources, and delivers instant, shareable corrections with a memory system that prevents repeated debunking.

<div align="center">

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19+-blue.svg)](https://react.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

## 📋 Table of Contents

- [What We're Building](#what-were-building)
- [The Pipeline: Step by Step](#the-pipeline-step-by-step)
- [Core Components](#core-components)
- [System Architecture](#system-architecture)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Usage](#api-usage)
- [Project Structure](#project-structure)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)

---

## 🎯 What We're Building

WhatsAMyth consists of **three core ideas**:

### 1. The Listener Agent
Sits on top of chat streams (Telegram, web form, WhatsApp Business bot).
- Every new message triggers the pipeline automatically.
- Captures the source, sender, and message text.

### 2. The Fact-Check Pipeline
A multi-stage verification engine:
- **Detects**: Is this a claim worth checking?
- **Extracts**: What are the core claims?
- **Clusters**: Have we seen this myth before?
- **Verifies**: If new → search authoritative sources
- **Rebuts**: Generate short, shareable counter-claim

### 3. The Misinformation Memory Graph
A persistent knowledge base:
- Each myth stored as a node: text, topic, verdict, first seen, where it spread
- Similar myths linked together in clusters
- Next time a similar forward appears → instant reply (no rework)
- Over time → used to forecast which myths will resurface

---

## 🔄 The Pipeline: Step by Step

### Real-World Example: The WhatsApp Shutdown Hoax

**Message received:**
```
Forwarded
WhatsApp will be off from 11:30 pm to 6:00 am daily …
charge of 499.00 will be added to your monthly bill …
Message from Narendra Modi (PM) …
```

### Step 1️⃣: Message Enters the System

**Listener Agent** receives an event:
- **Source**: `whatsapp:+91xxxxxxxxxx` | `telegram:group-id` | `web:user`
- **Text**: Full forward with metadata
- Action: Hand text to the Fact-Check Pipeline

### Step 2️⃣: Pre-processing & Claim Detection

**Claim Detector** analyzes the message:
- Removes whitespace, normalizes formatting
- Detects language (English, Hindi, etc.)
- Recognizes signals:
  - ✓ Says "Forwarded"
  - ✓ Contains instructions: "forward or lose account"
  - ✓ Invokes authority: "PM Modi", "central govt"
  - ✓ Threatens consequences: deletion, fees, shutdown

**Result**: Marked as a **CLAIM** (not casual chatter)

### Step 3️⃣: Extract Core Claims

**Claim Extractor** breaks down the message into crisp propositions:

| Claim | Text |
|-------|------|
| **A** | "The central government has declared WhatsApp will be off from 11:30 pm to 6:00 am daily." |
| **B** | "If you don't forward this message, your WhatsApp account will be deleted within 48 hours." |
| **C** | "To reactivate your account, you will be charged ₹499 on your monthly bill." |
| **D** | "This message is from Prime Minister Narendra Modi." |

**Canonical claim** (for clustering):
> "Government & WhatsApp will shut WhatsApp nightly, delete accounts if you don't forward this, and charge ₹499 for reactivation, announced by PM Modi."

### Step 4️⃣: Check Memory Graph (Clustering)

**Clustering Agent** embeds the claim and searches for similar past myths:

**Case A — Already seen (80%+ similarity)**
- System finds cluster #17: *"WhatsApp shutdown & account deletion scam"*
- Verdict: ❌ **FALSE**
- Sources: WhatsApp FAQ, PIB fact-checks, media articles
- Pre-written rebuttals in multiple languages
- **Action**: Skip verification, jump to Step 6 (generate reply from stored rebuttal)

**Case B — First time (current scenario)**
- Create new cluster #42
- Link Claims A–D to it
- **Action**: Proceed to Step 5 (verification)

### Step 5️⃣: Verification Against Official Sources

**Verification Agent** determines what sources matter:

| Claim Part | Authority |
|------------|-----------|
| "WhatsApp will be off" | WhatsApp official blog, FAQ, Meta status page |
| "Declared by central govt / PM Modi" | PIB fact-check, PMO, MyGov |
| "Charge 499 on bill" | WhatsApp billing, telecom regulations |

**Search queries generated**:
```
"WhatsApp will be shut down at night" fake
"WhatsApp off from 11:30 pm to 6 am" PIB
"WhatsApp account will be deleted if you don't forward" fact check
"WhatsApp 499 monthly bill reactivation" hoax
```

**Evidence found** (from official sources):
> "WhatsApp is not shutting down. Any message asking users to forward or lose their account is a hoax."

**LLM / Rule-based verdict**:
- Claim A: No official order. No scheduled shutdown. → **FALSE**
- Claim B: WhatsApp explicitly says they don't delete accounts based on forwards. → **FALSE**
- Claim C: No ₹499 fee mentioned anywhere official. → **FALSE**
- Claim D: PM Modi / govt have never issued such a directive. → **FALSE**

**Cluster #42 is now tagged**:
- `status: FALSE`
- `category: WhatsApp hoax / chain message`
- `sources: [official URLs & quotes]`
- `first_seen: Jan 5 2026, 10:23 IST`
- `regions: [based on sender metadata]`

### Step 6️⃣: Generate Short, Shareable Rebuttal

**Response Agent** creates a WhatsApp-style reply:

```
❌ This WhatsApp message is FAKE.

❌ There is NO order from the Government of India or PM Modi 
   to shut WhatsApp from 11:30 pm to 6:00 am.

❌ WhatsApp does NOT delete accounts or charge ₹499 based on forwards.

✅ If any such rule existed, it would be announced on 
   WhatsApp's official website, PIB, or MyGov — NOT via random forwards.

🔁 PLEASE STOP forwarding this and share this clarification instead.
```

**Variants generated**:
- **Short version** (for status/quick forward): "This 'WhatsApp off at night / ₹499' message is a hoax. Govt & WhatsApp have issued no such rule. Don't forward."
- **Hindi/Regional versions**: Auto-translated rebuttals
- **Audio version** (TTS): 20-second spoken clarification

### Step 7️⃣: Send Reply Back to User

**Broadcaster Agent** routes the response:

| Source | Action |
|--------|--------|
| `whatsapp:+91xxxx` | Send via WhatsApp Business API |
| `telegram:group-id` | Post reply in same Telegram group |
| `web:user` | Return JSON to web UI |

**User experience**:
1. They forward the hoax to WhatsAMyth (or paste on website)
2. Within a few seconds, bot replies with myth-vs-fact breakdown
3. User taps "forward" on the reply and blasts it into family/group chats
4. The correction spreads faster than the hoax

### Step 8️⃣: Memory Graph is Updated

**Graph Storage** now contains:

```
Cluster #42
├── Text: canonical claim
├── Topic: "WhatsApp hoax / platform shutdown / billing"
├── Verdict: FALSE
├── Evidence: [links to sources]
├── First_seen: Jan 5 2026, 10:23 IST
├── Regions: [Maharashtra, Delhi, India]
├── Related_myths:
│   ├── "WhatsApp charging fee unless forwarded" (2012)
│   ├── "Facebook privacy settings fee" (2016)
│   └── "Signal shutdown if not forwarded" (2021)
└── Time_series: [weekly appearance count]
```

### Step 9️⃣: Next Time = Instant Reaction

**One month later**, someone forwards a slightly rephrased version:

```
"Govt and WhatsApp have decided to suspend WhatsApp daily 
midnight to 7 am. Non-forwarders' accounts will be blocked 
and they'll need to pay 499…"
```

**Pipeline now**:
1. Listener Agent sees message
2. Claim Detector: CLAIM ✓
3. Claim Extractor: Same core propositions
4. **Clustering: HIGH MATCH with cluster #42** ✓
5. **Skip verification** — directly pull pre-computed verdict: ❌ FALSE
6. **Instant reply** with: "This is the same debunked hoax as before. It is false because…"

**Result**: No wasted compute. Instant, accurate response.

### Step 🔟: Forecasting & Prevention

**Over time**, system learns patterns:

| Pattern | Signal |
|---------|--------|
| WhatsApp hoaxes spike | After policy announcements, election season |
| Peak times | Evening hours, weekends |
| High-spread regions | Urban India, specific demographics |

**Forecaster Agent** can:
- Watch for external triggers: "WhatsApp just announced new privacy terms"
- Check Memory Graph: "After privacy changes, these 3 myths historically spike"
- Pre-generate messages: Push corrections **before** the hoax explodes via official channels

---

## 🏗️ Core Components

### Listener Agent
- Monitors multiple channels: WhatsApp, Telegram, web forms
- Captures metadata: sender, source, timestamp, region
- Triggers pipeline on each message

### Claim Detector
- Pattern matching: "Forwarded", "Don't delete", "Central govt"
- Semantic analysis: distinguishes claims from casual chat
- Tags: `CLAIM`, `OPINION`, `NOISE`

### Claim Extractor
- Breaks multi-claim forwards into individual propositions
- Rewrites into canonical form for consistent processing
- Links extracted claims to original message

### Clustering Agent
- Embeds claims using Sentence-Transformers
- Searches FAISS index for similar past myths
- Returns matching cluster or creates new one
- Enables deduplication and trend tracking

### Verification Agent
- Determines relevant authoritative sources
- Builds and executes search queries
- Extracts evidence snippets from results
- Uses local LLM to analyze evidence & generate verdict

### Response Agent
- Generates short, human-readable rebuttals
- Creates multiple variants: short, long, regional languages
- Produces audio versions (TTS)
- Optimizes for WhatsApp format & tone

### Broadcaster Agent
- Routes response to correct platform
- Maintains conversation context
- Handles rate-limiting and delivery

### Memory Graph
- Stores myth clusters with metadata
- Tracks time-series of reappearances
- Enables pattern analysis and forecasting
- Powers deduplication in subsequent cycles

### LLM Client
- Analyzes evidence against claims
- Generates verdicts with reasoning
- Powers rebuttal generation
- Supports local models (Transformers, Ollama)

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────────┐
│                   Input Channels                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   WhatsApp   │  │   Telegram   │  │  Web Form    │     │
│  │ Business API │  │    Bot       │  │  (React UI)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│               Listener Agent                               │
│   (Capture message, metadata, trigger pipeline)            │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│           ⚙️ Fact-Check Pipeline (Main)                   │
├────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐  │
│  │ 1. Claim Detector → 2. Claim Extractor             │  │
│  │ 3. Clustering Agent (search Memory Graph)          │  │
│  │    ├─ If already seen → jump to Step 6             │  │
│  │    └─ If new → Step 4                              │  │
│  │ 4. Verification Agent (search sources)             │  │
│  │    └─ LLM verdict generation                       │  │
│  │ 5. Response Agent (generate rebuttal)              │  │
│  │ 6. Broadcaster Agent (send to user)                │  │
│  └─────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│               Memory Graph (Storage)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  PostgreSQL  │  │  FAISS Index │  │  Time Series │     │
│  │  (metadata)  │  │  (embeddings)│  │  (analytics) │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│          External Services & Data Sources                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  WhatsApp    │  │  PIB / MyGov │  │ DuckDuckGo   │     │
│  │  Official    │  │  (India Govt)│  │  Web Search  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐                       │
│  │ HuggingFace  │  │  Local LLM   │                       │
│  │  Models      │  │  (Ollama)    │                       │
│  └──────────────┘  └──────────────┘                       │
└────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Tech |
|-------|------|
| **Backend Framework** | FastAPI 0.109+ |
| **Database** | PostgreSQL + SQLAlchemy |
| **Vector Store** | FAISS (embeddings) |
| **ML/Embeddings** | Sentence-Transformers |
| **LLM** | Local (Transformers) or Ollama |
| **Bots** | python-telegram-bot, discord.py |
| **TTS** | pyttsx3, Coqui TTS |
| **Web Search** | DuckDuckGo API, HTTP requests |
| **Frontend** | React 19 + Vite + Tailwind CSS |
| **Task Scheduling** | APScheduler |
| **Containerization** | Docker & Docker Compose |

---

## 🚀 Quick Start

### Using Docker Compose (Recommended)

```bash
git clone https://github.com/ritwikmohanty/WhatsAMyth.git
cd WhatsAMyth

# Backend
cd server/whatsamyth-backend
cp .env.example .env
docker-compose up --build

# Frontend (in another terminal)
cd client
npm install
npm run dev
```

**Access points**:
- Frontend: `http://localhost:5173`
- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

### Local Development

**Backend**:
```bash
cd server/whatsamyth-backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

**Frontend**:
```bash
cd client
npm install
npm run dev
```

---

## 📦 Installation

### Prerequisites

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Backend |
| Node.js | 18+ | Frontend |
| Docker | 20.10+ | Containerization |
| PostgreSQL | 15+ | Database (or use Docker) |

### Option 1: Docker Compose (Full Stack)

```bash
cd server/whatsamyth-backend
docker-compose up --build
```

### Option 2: Local Development

```bash
# Backend
cd server/whatsamyth-backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd client
npm install
```

---

## ⚙️ Configuration

### Environment Variables

Create `.env` in `server/whatsamyth-backend/`:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/whatsamyth
# Or SQLite for development:
# DATABASE_URL=sqlite:///./whatsamyth.db

# Security
SECRET_KEY=your-secret-key
INTERNAL_TOKEN=your-internal-token

# Bot Tokens (optional)
TELEGRAM_BOT_TOKEN=your-telegram-token
DISCORD_BOT_TOKEN=your-discord-token

# LLM (local_transformers or ollama)
LLM_BACKEND=local_transformers
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# TTS (pyttsx3 or coqui)
TTS_PROVIDER=pyttsx3

# Features
ENABLE_BOTS=true
ENABLE_BACKGROUND_VERIFICATION=true
LOG_LEVEL=INFO
```

### LLM Setup

**Option A: Ollama (Recommended)**
```bash
curl https://ollama.ai/install.sh | sh
ollama pull llama2
ollama serve
```

**Option B: Local Transformers**
```bash
# Models auto-download on first run
# For GPU: pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### Database

**PostgreSQL**:
```bash
createdb whatsamyth
```

**SQLite** (development):
```bash
# Just set DATABASE_URL=sqlite:///./whatsamyth.db in .env
# Tables auto-create
```

---

## 💡 API Usage

**Analyze a Message**:
```bash
curl -X POST "http://localhost:8000/api/messages/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "WhatsApp is ending on March 31st",
    "source": "web"
  }'
```

**Get Claim Details**:
```bash
curl "http://localhost:8000/api/claims/123"
```

**Get Statistics**:
```bash
curl "http://localhost:8000/api/stats"
```

**Interactive Docs**: `http://localhost:8000/docs` (Swagger) or `http://localhost:8000/redoc` (ReDoc)

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/messages/analyze` | Analyze a message for claims |
| GET | `/api/messages/{id}` | Get message details |
| GET | `/api/claims` | List all claims |
| GET | `/api/claims/{id}` | Get claim details |
| GET | `/api/stats` | Get statistics |
| GET | `/api/stats/trending` | Get trending myths |

---

## 📁 Project Structure

```
WhatsAMyth/
├── client/                          # React Frontend
│   ├── src/
│   │   ├── components/              # React components
│   │   │   ├── Header, Hero, InputSection
│   │   │   ├── ProcessingView, ResultsView
│   │   │   ├── ClaimCard, ClaimDetailPage
│   │   │   ├── TrendingMyths, RecentMyths
│   │   │   ├── HowItWorks, IntegrationsSection
│   │   │   └── ui/                  # Reusable UI components
│   │   ├── lib/
│   │   │   ├── api.js               # API client
│   │   │   └── utils.js
│   │   └── App.jsx, main.jsx
│   ├── package.json, vite.config.js, index.html
│
├── server/
│   ├── whatsamyth-backend/          # FastAPI Backend
│   │   ├── app/
│   │   │   ├── main.py              # FastAPI app
│   │   │   ├── config.py, db.py, models.py, schemas.py
│   │   │   ├── crud.py
│   │   │   ├── routers/             # API routes
│   │   │   │   ├── messages.py
│   │   │   │   ├── claims.py
│   │   │   │   └── stats.py
│   │   │   ├── services/            # Core pipeline
│   │   │   │   ├── detection.py     # 🔍 Claim Detection
│   │   │   │   ├── clustering.py    # 🔗 Clustering Agent
│   │   │   │   ├── embedding.py     # Vector embeddings
│   │   │   │   ├── verification.py  # 🔎 Verification Agent
│   │   │   │   ├── rebuttal.py      # 📝 Response Agent
│   │   │   │   ├── llm_client.py    # 🤖 LLM integration
│   │   │   │   ├── memory_graph.py  # 💾 Memory Graph
│   │   │   │   ├── keywords.py      # Keyword extraction
│   │   │   │   ├── tts.py           # 🔊 Text-to-speech
│   │   │   │   └── hoax_library.py
│   │   │   └── bots/
│   │   │       ├── telegram_bot.py
│   │   │       └── discord_bot.py
│   │   ├── tests/
│   │   ├── requirements.txt, docker-compose.yml, Dockerfile
│   │
│   └── recentMisinformation/        # Hoax scraper
│
└── README.md (this file)

---

## 🛠️ Development

### Running Locally

```bash
# Terminal 1: Backend
cd server/whatsamyth-backend
source .venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2: Frontend
cd client
npm run dev
```

### Code Style

**Backend**:
```bash
pip install black flake8
black app/
flake8 app/
```

**Frontend**:
```bash
npm run lint
npm run lint -- --fix
```

---

## 🧪 Testing

**Backend**:
```bash
cd server/whatsamyth-backend
pytest tests/ -v
pytest tests/test_endpoints.py -v
pytest --cov=app tests/
```

**Frontend**:
```bash
cd client
npm test
```

---

## 🚢 Deployment

### Docker

```bash
# Build
cd server/whatsamyth-backend
docker build -t whatsamyth-backend:latest .

# Run
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@db:5432/whatsamyth \
  -e SECRET_KEY=your-key \
  whatsamyth-backend:latest
```

### Full Stack with Docker Compose

```bash
cd server/whatsamyth-backend
docker-compose up -d
docker-compose logs -f
```

### Production Environment

```bash
DATABASE_URL=postgresql://prod_user:pass@prod_host/whatsamyth
SECRET_KEY=generate-strong-key
LLM_BACKEND=ollama
ENABLE_BOTS=true
LOG_LEVEL=WARNING
```

---

## 📚 Documentation

For more detailed information, see:

- **Backend Setup**: `/server/whatsamyth-backend/README.md`
- **Backend Guide**: `/server/whatsamyth-backend/SETUP_GUIDE.md`
- **Implementation Details**: `/server/whatsamyth-backend/IMPLEMENTATION_COMPLETE.md`
- **API Docs**: `http://localhost:8000/docs` (when running)

---

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -m 'Add my feature'`
4. Push to branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📄 License

MIT License - see LICENSE file for details

---

## 👥 Contributors

1. **Ritwik Mohanty**
2. **Shashank Satish**
3. **Suryanshu Banerjee**
4. **Vedant Walunj**

---

**Made with ❤️ to combat misinformation**
