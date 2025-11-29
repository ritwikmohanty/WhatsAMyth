"""
Application configuration using Pydantic Settings.
Reads environment variables and provides typed configuration.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All settings have sensible defaults for local development.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/whatsamyth"
    
    # Security
    secret_key: str = "changeme-in-production"
    internal_token: str = "internal-secret-token"
    
    # Bot Tokens
    telegram_bot_token: Optional[str] = None
    discord_bot_token: Optional[str] = None
    
    # LLM Configuration
    llm_backend: str = "openai"  # ollama, local_transformers, or openai
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"
    transformers_model: str = "google/flan-t5-base"

    # OpenAI/OpenRouter Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "deepseek/deepseek-r1-0528-qwen3-8b"
    openai_base_url: str = "https://openrouter.ai/api/v1"  # OpenRouter endpoint
    
    # Storage Paths
    faiss_index_path: str = "/data/faiss.index"
    memory_graph_path: str = "/data/memory_graph.json"
    media_path: str = "media/replies"
    
    # TTS Configuration
    tts_provider: str = "pyttsx3"  # coqui or pyttsx3
    coqui_model: str = "tts_models/en/ljspeech/tacotron2-DDC"
    
    # Server
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    
    # CORS
    frontend_origin: str = "http://localhost:3000"
    
    # Redis
    redis_url: Optional[str] = None
    
    # Feature Flags
    enable_bots: bool = False
    enable_background_verification: bool = True
    verification_interval_seconds: int = 60
    
    # Embedding Model
    embedding_model: str = "sentence-transformers/paraphrase-mpnet-base-v2"
    
    # Clustering
    similarity_threshold: float = 0.75
    
    # Authoritative domains for verification
    authoritative_domains: list[str] = [
        "who.int",
        "cdc.gov",
        "gov.in",
        "pib.gov.in",
        "ndma.gov.in",
        "imd.gov.in",
        "factcheck.org",
        "snopes.com",
        "politifact.com",
        "reuters.com",
        "apnews.com",
        "bbc.com",
        "altnews.in",
        "boomlive.in",
        "thequint.com/news/webqoof"
    ]


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to avoid re-reading environment on every call.
    """
    return Settings()
