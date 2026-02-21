from functools import lru_cache
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file= BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    cors_origins: List[str] = ["*"]
    
    app_name: str = "AI Gmail Intelligence"
    app_version: str = "1.0.0"

    GROQ_API_KEY: str = Field(..., description="Groq API key for LLM inference")
    GROQ_MODEL: str = "llama3-70b-8192"
    GROQ_TEMPERATURE: float = 0.7
    GROQ_MAX_TOKENS: int = 2048
    
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384 
    embedding_batch_size: int = 32
    
    PINECONE_API_KEY: str = Field(..., description="Pinecone API key")
    PINECONE_ENVIRONMENT: str = Field(..., description="Pinecone environment (e.g., us-east-1-aws)")
    pinecone_index_name: str = "rag-platform"
    pinecone_namespace: str = "default"
  
    chunk_size: int = 500
    chunk_overlap: int = 100
    retrieval_top_k: int = 10
    similarity_threshold: float = 0.7

    log_level: str = 'INFO'
    log_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    emails_processed_file: str = 'data/emails-processed/processed.json'

    days_to_keep: int = 7

@lru_cache()
def get_settings():
    return Settings() # type: ignore

settings = get_settings()