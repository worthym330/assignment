"""
Configuration management for Formbricks Data Seeder.

Loads settings from environment variables with sensible defaults.
All configuration is centralized here for easy maintenance.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""
    
    # Project paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    
    # Formbricks settings
    FORMBRICKS_URL: str = os.getenv("FORMBRICKS_URL", "https://localhost:3000")
    FORMBRICKS_API_KEY: Optional[str] = os.getenv("FORMBRICKS_API_KEY")
    FORMBRICKS_ENVIRONMENT_ID: Optional[str] = os.getenv("FORMBRICKS_ENVIRONMENT_ID")
    
    # Ollama settings
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama2")
    
    # Docker settings
    COMPOSE_PROJECT_NAME: str = os.getenv("COMPOSE_PROJECT_NAME", "formbricks-seeder")
    
    # Database (used by Docker Compose)
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@postgres:5432/formbricks"
    )
    
    # NextAuth (used by Formbricks)
    NEXTAUTH_SECRET: str = os.getenv("NEXTAUTH_SECRET", "supersecretkey123456")
    NEXTAUTH_URL: str = os.getenv("NEXTAUTH_URL", "https://localhost:3000")
    
    # Data generation settings
    NUM_USERS: int = int(os.getenv("NUM_USERS", "10"))
    NUM_SURVEYS: int = int(os.getenv("NUM_SURVEYS", "5"))
    MIN_RESPONSES_PER_SURVEY: int = int(os.getenv("MIN_RESPONSES_PER_SURVEY", "3"))
    MAX_RESPONSES_PER_SURVEY: int = int(os.getenv("MAX_RESPONSES_PER_SURVEY", "8"))
    
    @classmethod
    def validate(cls) -> None:
        """
        Validate critical configuration values.
        Raises ValueError if required settings are missing.
        """
        errors = []
        
        # Check for seeding requirements
        if not cls.FORMBRICKS_API_KEY:
            errors.append("FORMBRICKS_API_KEY is required for seeding")
        
        if not cls.FORMBRICKS_ENVIRONMENT_ID:
            errors.append("FORMBRICKS_ENVIRONMENT_ID is required for seeding")
        
        if errors:
            raise ValueError(
                "Configuration validation failed:\n" + 
                "\n".join(f"  - {err}" for err in errors) +
                "\n\nPlease update your .env file with the required values."
            )
    
    @classmethod
    def ensure_data_dir(cls) -> None:
        """Ensure the data directory exists."""
        cls.DATA_DIR.mkdir(exist_ok=True)
    
    @classmethod
    def get_data_file(cls, filename: str) -> Path:
        """Get full path to a data file."""
        return cls.DATA_DIR / filename


# Create singleton instance
config = Config()
