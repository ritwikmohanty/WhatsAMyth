
# WhatsAMyth Backend (FastAPI)

This is a minimal backend for WhatsAMyth — it ingests fact-check data from Google Fact Check API and RSS feeds,
stores claims in SQLite, and exposes simple endpoints to list and search claims.

## Files
- `main.py` - FastAPI application
- `requirements.txt` - Python dependencies
- `.env.example` - example environment variables
- `Dockerfile` - optional Dockerfile for container deployment
- `docker-compose.yml` - optional compose file to run the service and sqlite browser (if desired)

## Quickstart (local)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# copy .env.example -> .env and set GOOGLE_API_KEY if you plan to use Google Fact Check API
export GOOGLE_API_KEY=your_key_here
uvicorn main:app --reload --port 8000
```

## Endpoints
- `POST /fetch/google?query=india&max=50` - fetch recent claims from Google Fact Check and store
- `POST /fetch/rss` - fetch configured RSS feeds and store
- `GET  /claims?limit=50&offset=0` - list recent claims
- `GET  /claim/{id}` - get claim details
- `GET  /search?q=...` - simple text search

## Deployment
You can Dockerize this service. Example `Dockerfile` and `docker-compose.yml` are included.
