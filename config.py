import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

load_dotenv(BASE_DIR / ".env", override=False)

# 공공데이터포털
BASE_URL = os.getenv("BASE_URL")
SERVICE_KEY = os.getenv("SERVICE_KEY")

# Cohere
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
MODEL_NAME = "rerank-v4.0-fast"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
PORT = int(os.getenv("PORT", "8080"))
