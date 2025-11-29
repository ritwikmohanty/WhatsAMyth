# WhatsAMyth Backend - Complete Setup Guide

This guide provides step-by-step instructions for setting up, testing, and deploying the WhatsAMyth misinformation detection backend.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Docker)](#quick-start-docker)
3. [Local Development Setup](#local-development-setup)
4. [Database Setup](#database-setup)
5. [LLM Configuration](#llm-configuration)
6. [Bot Setup (Telegram & Discord)](#bot-setup)
7. [Running Tests](#running-tests)
8. [API Testing](#api-testing)
9. [Production Deployment](#production-deployment)
10. [Debugging FAQ](#debugging-faq)

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.11+ | Runtime |
| Docker | 20.10+ | Containerization |
| Docker Compose | 2.0+ | Multi-container orchestration |
| PostgreSQL | 15+ | Database (or use Docker) |
| Git | Any | Version control |

### Optional Software

| Software | Purpose |
|----------|---------|
| Ollama | Local LLM inference |
| ffmpeg | Audio conversion for TTS |
| ngrok | Webhook testing for bots |

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 4GB | 8GB+ |
| Storage | 5GB | 20GB+ |
| CPU | 2 cores | 4+ cores |
| GPU | Not required | NVIDIA GPU for faster embeddings |

---

## Quick Start (Docker)

The fastest way to get started is with Docker Compose.

### Step 1: Clone and Navigate

```bash
git clone <your-repository-url>
cd whatsamyth-backend
```

### Step 2: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your settings
nano .env  # or use any text editor
```

**Minimum required changes in `.env`:**

```bash
# Generate a secure secret key
SECRET_KEY=your-very-long-random-secret-key-here

# Set internal token for bot authentication
INTERNAL_TOKEN=your-internal-secret-token
```

### Step 3: Build and Start

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up --build -d
```

### Step 4: Verify Installation

```bash
# Check service health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","database":true,"faiss_index_loaded":true,"faiss_index_size":0}
```

### Step 5: Access the API

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

---

## Local Development Setup

For development without Docker.

### Step 1: Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate it
# On Linux/macOS:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
# Install all requirements
pip install -r requirements.txt

# If you encounter issues with torch, install it separately first:
pip install torch==2.2.0 --index-url https://download.pytorch.org/whl/cpu

# Then install the rest
pip install -r requirements.txt
```

### Step 3: Configure Environment

```bash
cp .env.example .env
```

**For local development with SQLite:**

```bash
# In .env, set:
DATABASE_URL=sqlite:///./whatsamyth.db
```

**For local PostgreSQL:**

```bash
# In .env, set:
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/whatsamyth
```

### Step 4: Start the Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use the built-in runner
python -m app.main
```

### Step 5: Verify

```bash
curl http://localhost:8000/
# {"name":"WhatsAMyth API","version":"1.0.0","docs":"/docs","health":"/health"}
```

---

## Database Setup

### Option A: PostgreSQL with Docker (Recommended)

```bash
# Start only the database
docker-compose up -d db

# Verify it's running
docker-compose ps
```

### Option B: Local PostgreSQL

```bash
# Install PostgreSQL (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib

# Start service
sudo systemctl start postgresql

# Create database and user
sudo -u postgres psql
```

```sql
-- In PostgreSQL shell:
CREATE DATABASE whatsamyth;
CREATE USER whatsamyth_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE whatsamyth TO whatsamyth_user;
\q
```

Update `.env`:
```bash
DATABASE_URL=postgresql://whatsamyth_user:your_password@localhost:5432/whatsamyth
```

### Option C: SQLite (Development Only)

```bash
# In .env:
DATABASE_URL=sqlite:///./whatsamyth.db
```

### Database Migrations (Optional)

The application auto-creates tables on startup. For manual migrations:

```bash
# Generate a migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## LLM Configuration

The system supports three LLM backends:

### Option A: Ollama (Best Quality)

**Step 1: Install Ollama**

```bash
# Linux/macOS
curl -fsSL https://ollama.com/install.sh | sh

# Windows: Download from https://ollama.com/download
```

**Step 2: Pull a Model**

```bash
# Recommended models (in order of quality/size):
ollama pull llama2        # 7B, good quality
ollama pull mistral       # 7B, fast
ollama pull llama2:13b    # 13B, better quality
ollama pull tinyllama     # 1.1B, fastest
```

**Step 3: Start Ollama**

```bash
# Ollama runs as a service, start it:
ollama serve

# Or it may already be running. Check:
curl http://localhost:11434/api/tags
```

**Step 4: Configure .env**

```bash
LLM_BACKEND=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

### Option B: Local Transformers

Uses HuggingFace transformers with a small local model.

```bash
# In .env:
LLM_BACKEND=local_transformers
TRANSFORMERS_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0
```

**Note**: First run will download the model (~2GB for TinyLlama).

### Option C: Fallback (No LLM)

If no LLM is available, the system uses rule-based verdicts:

```bash
# In .env:
LLM_BACKEND=fallback
```

This provides basic functionality using keyword matching.

---

## Bot Setup

### Telegram Bot Setup

#### Step 1: Create Bot with BotFather

1. Open Telegram and search for `@BotFather`
2. Send `/newbot`
3. Follow prompts to name your bot
4. Copy the **API token** (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### Step 2: Configure Environment

```bash
# In .env:
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
ENABLE_BOTS=true
```

#### Step 3: Test the Bot

```bash
# Run bot standalone
python run_bots.py --telegram

# Or with the main app (if ENABLE_BOTS=true)
uvicorn app.main:app --reload
```

#### Step 4: Chat with Your Bot

1. Find your bot in Telegram by its username
2. Send `/start` to see welcome message
3. Send `/help` for commands
4. Send any claim to check it

**Telegram Bot Commands:**
- `/start` - Welcome message
- `/help` - Help information
- `/check <claim>` - Check a specific claim
- `/stats` - Show statistics

### Discord Bot Setup

#### Step 1: Create Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Name it "WhatsAMyth" (or your preference)
4. Go to "Bot" section → "Add Bot"

#### Step 2: Configure Bot

1. Under "Bot" section:
   - Copy the **Token** (click "Reset Token" if needed)
   - Enable "Message Content Intent" under Privileged Gateway Intents

#### Step 3: Generate Invite Link

1. Go to "OAuth2" → "URL Generator"
2. Select scopes: `bot`, `applications.commands`
3. Select permissions:
   - Read Messages/View Channels
   - Send Messages
   - Attach Files
   - Read Message History
   - Add Reactions
4. Copy the generated URL and open it to invite bot to your server

#### Step 4: Configure Environment

```bash
# In .env:
DISCORD_BOT_TOKEN=your-discord-bot-token
ENABLE_BOTS=true
```

#### Step 5: Test the Bot

```bash
# Run bot standalone
python run_bots.py --discord

# Or both bots
python run_bots.py --all
```

**Discord Bot Commands:**
- `!myth help` - Help information
- `!myth check <claim>` - Check a claim
- `!myth stats` - Show statistics
- React with 🔍 to any message to check it

### Running Both Bots

```bash
# Standalone (recommended for production)
python run_bots.py --all

# With main app
# Set ENABLE_BOTS=true in .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Running Tests

### Run All Tests

```bash
# Basic test run
pytest

# With verbose output
pytest -v

# With coverage report
pytest --cov=app --cov-report=html
```

### Run Specific Test Files

```bash
# Test database models
pytest tests/test_models.py -v

# Test services
pytest tests/test_services.py -v

# Test API endpoints
pytest tests/test_endpoints.py -v
```

### Run Specific Test

```bash
# Run single test
pytest tests/test_endpoints.py::TestMessagesEndpoint::test_ingest_claim_message -v
```

### Test Coverage

```bash
# Generate HTML coverage report
pytest --cov=app --cov-report=html

# Open report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

---

## API Testing

### Using cURL

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Submit a Claim:**
```bash
curl -X POST http://localhost:8000/api/messages/ \
  -H "Content-Type: application/json" \
  -d '{
    "text": "COVID-19 vaccines contain microchips for tracking people",
    "source": "web_form"
  }'
```

**List Claims:**
```bash
curl http://localhost:8000/api/claims/
```

**Get Claim Details:**
```bash
curl http://localhost:8000/api/claims/1
```

**Get Statistics:**
```bash
curl http://localhost:8000/api/stats/overview
```

### Using Postman

1. Import `postman_collection.json` into Postman
2. Set the `baseUrl` variable to `http://localhost:8000`
3. Run requests from the collection

### Using Swagger UI

1. Open http://localhost:8000/docs
2. Click "Try it out" on any endpoint
3. Fill in parameters and execute

---

## Production Deployment

### Docker Production Setup

```bash
# Build production image
docker build -t whatsamyth-backend:latest .

# Run with production settings
docker-compose -f docker-compose.yml up -d
```

### Using Gunicorn

```bash
# Install gunicorn (already in requirements)
pip install gunicorn

# Run with multiple workers
gunicorn app.main:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  -b 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Environment Variables for Production

```bash
# Production .env
DATABASE_URL=postgresql://user:password@db-host:5432/whatsamyth
SECRET_KEY=very-long-random-production-secret-key
INTERNAL_TOKEN=secure-internal-token
ENABLE_BOTS=true
ENABLE_BACKGROUND_VERIFICATION=true
FRONTEND_ORIGIN=https://your-frontend-domain.com
LLM_BACKEND=ollama
TTS_PROVIDER=pyttsx3
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name api.whatsamyth.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /media {
        alias /path/to/whatsamyth-backend/media;
    }
}
```

---

## Debugging FAQ

### Common Issues and Solutions

#### 1. "Database connection failed"

**Symptoms:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solutions:**

```bash
# Check if PostgreSQL is running
docker-compose ps  # for Docker
sudo systemctl status postgresql  # for local

# Check connection string
echo $DATABASE_URL

# Test connection manually
psql $DATABASE_URL

# For Docker, ensure db service is healthy
docker-compose logs db
```

#### 2. "ModuleNotFoundError: No module named 'xxx'"

**Solutions:**

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Check Python version
python --version  # Should be 3.11+
```

#### 3. "FAISS index initialization failed"

**Symptoms:**
```
Failed to initialize embedding service
```

**Solutions:**

```bash
# Ensure FAISS directory exists
mkdir -p /data

# Check disk space
df -h

# Try with a fresh index
rm -f /data/faiss.index*

# Check faiss-cpu installation
pip install faiss-cpu --force-reinstall
```

#### 4. "Telegram bot not responding"

**Solutions:**

```bash
# Verify token
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"

# Check if another instance is running
ps aux | grep telegram

# Check logs
docker-compose logs web | grep telegram

# Test standalone
python run_bots.py --telegram
```

#### 5. "Discord bot offline"

**Solutions:**

```bash
# Verify token and intents
# Go to Discord Developer Portal → Bot → Privileged Gateway Intents
# Enable "Message Content Intent"

# Check logs
python run_bots.py --discord 2>&1

# Verify bot is in server with correct permissions
```

#### 6. "LLM not generating responses"

**Solutions:**

```bash
# For Ollama:
curl http://localhost:11434/api/tags  # Should list models
ollama list  # Check installed models
ollama pull llama2  # Pull if missing

# For local transformers:
# Check model download
ls ~/.cache/huggingface/hub/

# Test manually:
python -c "from transformers import pipeline; print('OK')"

# Fall back to rule-based:
# Set LLM_BACKEND=fallback in .env
```

#### 7. "TTS audio not generating"

**Solutions:**

```bash
# Check ffmpeg installation
ffmpeg -version

# Install if missing (Ubuntu/Debian)
sudo apt install ffmpeg

# Check espeak for pyttsx3
espeak-ng --version

# Install if missing
sudo apt install espeak-ng

# Test pyttsx3
python -c "import pyttsx3; e=pyttsx3.init(); print('OK')"

# Fall back to pyttsx3 if Coqui fails
# Set TTS_PROVIDER=pyttsx3 in .env
```

#### 8. "Tests failing with database errors"

**Solutions:**

```bash
# Tests use SQLite by default
# Ensure test db doesn't conflict
rm -f test.db

# Run tests in isolation
pytest tests/test_models.py -v --tb=short

# Check test environment
pytest --collect-only
```

#### 9. "Memory issues / OOM errors"

**Solutions:**

```bash
# Use smaller embedding model
# In config.py, change embedding_model to:
embedding_model: str = "sentence-transformers/paraphrase-MiniLM-L6-v2"

# Use smaller LLM
# Set TRANSFORMERS_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0

# Reduce batch sizes
# Limit concurrent requests
```

#### 10. "CORS errors from frontend"

**Solutions:**

```bash
# Check FRONTEND_ORIGIN in .env
FRONTEND_ORIGIN=http://localhost:3000

# For development, allow all origins (not for production!)
# In app/main.py, CORS middleware allows "*"

# Check browser console for exact error
```

### Debug Mode

Enable debug logging:

```python
# In app/main.py, add:
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or via environment:

```bash
export LOG_LEVEL=DEBUG
uvicorn app.main:app --reload --log-level debug
```

### Useful Debug Commands

```bash
# Check all services
docker-compose ps

# View logs
docker-compose logs -f web
docker-compose logs -f db

# Enter container
docker-compose exec web bash

# Check database
docker-compose exec db psql -U postgres -d whatsamyth

# Monitor resources
docker stats

# Check network
docker network ls
docker network inspect whatsamyth-backend_default
```

### Getting Help

1. Check the logs first: `docker-compose logs -f`
2. Run tests to verify setup: `pytest -v`
3. Check the health endpoint: `curl localhost:8000/health`
4. Verify environment variables: `env | grep -E "(DATABASE|TOKEN|LLM)"`

---

## Quick Reference

### Common Commands

```bash
# Start everything
docker-compose up -d

# Stop everything
docker-compose down

# Rebuild after code changes
docker-compose up --build

# View logs
docker-compose logs -f web

# Run tests
pytest -v

# Format code
black app/ tests/

# Check types
mypy app/
```

### Environment Variable Quick Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| DATABASE_URL | Yes | - | PostgreSQL connection string |
| SECRET_KEY | Yes | - | Application secret key |
| INTERNAL_TOKEN | Yes | - | Bot authentication token |
| TELEGRAM_BOT_TOKEN | No | - | Telegram bot token |
| DISCORD_BOT_TOKEN | No | - | Discord bot token |
| LLM_BACKEND | No | local_transformers | ollama/local_transformers/fallback |
| TTS_PROVIDER | No | pyttsx3 | coqui/pyttsx3 |
| ENABLE_BOTS | No | false | Enable bot integration |

---

## Support

For issues not covered here:
1. Check existing GitHub issues
2. Search error messages in logs
3. Create a new issue with:
   - Error message
   - Steps to reproduce
   - Environment details (OS, Python version, etc.)
