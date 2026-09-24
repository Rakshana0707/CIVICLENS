import os
from dotenv import load_dotenv

# Try loading from standard environment file
load_dotenv()

class Settings:
    # URL configurations allowing separation between UI and Backend
    BACKEND_ROOT_URL: str = os.getenv("BACKEND_ROOT_URL", "http://localhost:5000")
    # For future module API calls (e.g. /api/budget)
    BACKEND_API_URL: str = os.getenv("BACKEND_API_URL", f"{BACKEND_ROOT_URL}/api")

settings = Settings()
