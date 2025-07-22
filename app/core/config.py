import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://postgres:postgres@localhost:5432/healthcare_navigator"
    )
    
    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = "gpt-3.5-turbo"
    
    # API
    api_title: str = "Healthcare Cost Navigator"
    api_version: str = "0.1.0"
    api_description: str = "Search hospitals by MS-DRG procedures with AI assistant"
    
    # CORS
    allowed_origins: list[str] = ["*"]
    
    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100
    
    class Config:
        env_file = ".env"


settings = Settings()
