import os
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

# 공공데이터포털
BASE_URL = os.getenv("BASE_URL")
SERVICE_KEY = os.getenv("SERVICE_KEY")

# Cohere
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
MODEL_NAME = "rerank-v5.0-fast"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
PORT = int(os.getenv("PORT", "8080"))
