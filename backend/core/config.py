import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Base directory of the project (3 levels up from this file)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Config:
    def __init__(self):
        # Application Info
        self.APP_NAME: str = os.getenv("APP_NAME", "CivicLens TN")
        self.ENV: str = os.getenv("ENV", "development")
        self.DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t", "yes")

        # API Settings
        self.API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
        self.API_PORT: int = int(os.getenv("API_PORT", "5000"))
        self.FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

        # Database Settings
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/data/processed/civiclens.db")

        # Directory Settings
        self.DATA_DIR: Path = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
        self.RAW_DATA_DIR: Path = Path(os.getenv("RAW_DATA_DIR", self.DATA_DIR / "raw"))
        self.PROCESSED_DATA_DIR: Path = Path(os.getenv("PROCESSED_DATA_DIR", self.DATA_DIR / "processed"))
        self.MODEL_DIR: Path = Path(os.getenv("MODEL_DIR", BASE_DIR / "ml" / "models"))

        # Logging Settings
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# Global configuration instance to be imported across the backend
config = Config()
