# WhatsAMyth Backend

A misinformation detection and verification system that analyzes claims from multiple sources (Web, Telegram, Discord) and provides fact-checked verdicts with audio explanations.

## Features

- **Claim Detection**: Automatically identifies verifiable claims in messages using rule-based patterns and semantic analysis
- **Claim Clustering**: Groups similar claims together using sentence embeddings and FAISS
- **Evidence Search**: Searches authoritative sources for evidence
- **LLM Verification**: Uses local LLM to analyze evidence and generate verdicts
- **Multi-Platform**: Integrates with Telegram, Discord, and web forms
- **Audio Responses**: Generates TTS audio for verdicts
- **Memory Graph**: Tracks claim relationships and predicts re-emergence

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd whatsamyth-backend

# Copy environment file
cp .env.example .env

# Edit .env with your settings (bot tokens, etc.)
nano .env

# Build and start
docker-compose up --build
```

The API will be available at `http://localhost:8000`

### Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your database URL and other settings

# Start PostgreSQL (or use SQLite for development)
# For SQLite, set: DATABASE_URL=sqlite:///./whatsamyth.db

# Run migrations (optional, tables auto-create)
# alembic upgrade head

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Configuration

### Environment Variables

Create a `.env` file with:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/whatsamyth

# Security
SECRET_KEY=your-secret-key-here
INTERNAL_TOKEN=token-for-bot-auth

# Bot Tokens (optional)
TELEGRAM_BOT_TOKEN=your-telegram-token
DISCORD_BOT_TOKEN=your-discord-token

# LLM Configuration
LLM_BACKEND=local_transformers  # or "ollama"
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# TTS
TTS_PROVIDER=pyttsx3  # or "coqui"

# Features
ENABLE_BOTS=false
ENABLE_BACKGROUND_VERIFICATION=true
```

### LLM Setup

#### Option 1: Ollama (Recommended for quality)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama2

# Set in .env
LLM_BACKEND=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

#### Option 2: Local Transformers

```bash
# Uses TinyLlama by default (small but functional)
# Set in .env
LLM_BACKEND=local_transformers

# Or specify a different model
TRANSFORMERS_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0
```

#### Option 3: Fallback (No LLM)

If no LLM is available, the system uses rule-based verdicts.

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Key Endpoints

#### POST /api/messages
Submit a message for analysis.

```json
{
  "text": "COVID-19 vaccine contains microchips",
  "source": "web_form",
  "metadata": {"chat_id": "123", "user_id": "456"}
}
```

Response:
```json
{
  "message_id": 1,
  "is_claim": true,
  "cluster_id": 1,
  "cluster_status": "FALSE",
  "short_reply": "This claim is FALSE. COVID-19 vaccines do not contain microchips.",
  "audio_url": "/media/replies/1.mp3",
  "needs_verification": false
}
```

#### GET /api/claims
List all claim clusters with pagination.

#### GET /api/claims/{cluster_id}
Get detailed information about a claim cluster.

#### GET /api/stats/overview
Get dashboard statistics.

## Running Bots

### Telegram Bot

1. Create a bot via [@BotFather](https://t.me/botfather)
2. Get the token and add to `.env`
3. Enable bots: `ENABLE_BOTS=true`
4. Or run separately:

```bash
python run_bots.py --telegram
```

### Discord Bot

1. Create an application at [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a bot and get the token
3. Enable required intents (Message Content)
4. Add to `.env` and run:

```bash
python run_bots.py --discord
```

### Bot Commands

**Telegram:**
- `/start` - Welcome message
- `/help` - Help information
- `/check <claim>` - Check a specific claim
- `/stats` - Show statistics

**Discord:**
- `!myth help` - Help information
- `!myth check <claim>` - Check a claim
- `!myth stats` - Show statistics
- React with 🔍 to check a message

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_endpoints.py -v
```

## Project Structure

```
whatsamyth-backend/
├── app/
│   ├── main.py              # FastAPI app & lifespan
│   ├── config.py            # Pydantic settings
│   ├── db.py                # Database setup
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── crud.py              # Database operations
│   ├── services/
│   │   ├── detection.py     # Claim detection
│   │   ├── embedding.py     # Embeddings & FAISS
│   │   ├── clustering.py    # Cluster management
│   │   ├── verification.py  # Evidence search & LLM
│   │   ├── memory_graph.py  # Relationship graph
│   │   ├── llm_client.py    # LLM adapters
│   │   └── tts.py           # Text-to-speech
│   ├── routers/
│   │   ├── messages.py      # /api/messages
│   │   ├── claims.py        # /api/claims
│   │   └── stats.py         # /api/stats
│   └── bots/
│       ├── telegram_bot.py
│       └── discord_bot.py
├── tests/
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Telegram   │     │   Discord   │     │  Web Form   │
│    Bot      │     │    Bot      │     │   (API)     │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                           ▼
                 ┌─────────────────┐
                 │  FastAPI Server │
                 └────────┬────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
         ▼                ▼                ▼
   ┌──────────┐    ┌───────────┐    ┌──────────┐
   │ Detection│    │ Embedding │    │Clustering│
   │ Service  │    │  + FAISS  │    │ Service  │
   └──────────┘    └───────────┘    └──────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  Verification   │
                 │   (Evidence +   │
                 │      LLM)       │
                 └────────┬────────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
              ▼           ▼           ▼
        ┌──────────┐ ┌─────────┐ ┌─────────┐
        │PostgreSQL│ │  FAISS  │ │   TTS   │
        │    DB    │ │  Index  │ │  Audio  │
        └──────────┘ └─────────┘ └─────────┘
```

## Security Considerations

1. **Internal Token**: Bot-to-API communication uses `X-Internal-Token` header
2. **Rate Limiting**: Bots implement per-chat rate limiting
3. **CORS**: Configured for frontend origin only
4. **No PII Storage**: User IDs can be hashed before storage
5. **Input Validation**: Pydantic validates all inputs

## Production Deployment

### Using Gunicorn

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### Docker Compose Production

```yaml
# Add to docker-compose.yml
services:
  web:
    command: gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
    restart: always
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests
4. Submit a pull request
