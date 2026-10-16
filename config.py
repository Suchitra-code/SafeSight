"""
Configuration module for SafeSight AI - PPE Safety Analytics Platform.
Loads environment variables from .env with fallback defaults.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory is the project root (safesight-ai)
BASE_DIR = Path(__file__).resolve().parent

# Load .env file from project root or parent
env_path = BASE_DIR / ".env"
if not env_path.exists():
    env_path = BASE_DIR.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # Try loading .env.example if .env does not exist yet
    example_env = BASE_DIR / ".env.example"
    if example_env.exists():
        load_dotenv(dotenv_path=example_env)

# MySQL connection settings
MYSQL_HOST = os.getenv("MYSQL_HOST", os.getenv("DB_HOST", "localhost"))
MYSQL_PORT = int(os.getenv("MYSQL_PORT", os.getenv("DB_PORT", "3306")))
MYSQL_USER = os.getenv("MYSQL_USER", os.getenv("DB_USER", "root"))
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", os.getenv("DB_PASSWORD", ""))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", os.getenv("DB_NAME", "safesight"))

# Flask settings
SECRET_KEY = os.getenv("SECRET_KEY", "safesight-ai-secret-key-2024")
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() in ("true", "1", "yes")

# Storage paths (all relative to project root)
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")
REPORT_FOLDER = os.path.join(BASE_DIR, "reports")
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "best.pt")

# Create required directories automatically
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, REPORT_FOLDER, MODEL_DIR]:
    os.makedirs(folder, exist_ok=True)

# Upload constraints
MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "avi", "mov"}

# Detection & Model Configuration
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.40"))
VIDEO_FRAME_SKIP = int(os.getenv("VIDEO_FRAME_SKIP", "5"))
DEVICE = os.getenv("DEVICE", "cpu")

# Expected classes mapping (case-insensitive key to canonical name)
CLASS_MAP = {
    "person": "Person",
    "hardhat": "Hardhat",
    "helmet": "Hardhat",
    "no-hardhat": "NO-Hardhat",
    "no-helmet": "NO-Hardhat",
    "safety vest": "Safety Vest",
    "vest": "Safety Vest",
    "no-safety vest": "NO-Safety Vest",
    "no-vest": "NO-Safety Vest",
    "goggles": "Goggles",
    "glasses": "Goggles",
    "no-goggles": "NO-Goggles",
    "no-glasses": "NO-Goggles"
}

# Rule toggles
ENABLE_GOGGLES_CHECK = os.getenv("ENABLE_GOGGLES_CHECK", "true").lower() in ("true", "1", "yes")
VIOLATION_COOLDOWN_SECONDS = int(os.getenv("VIOLATION_COOLDOWN_SECONDS", "10"))
DETECTION_ACCURACY = float(os.getenv("DETECTION_ACCURACY", "94.5"))

# Demo mode flag (True if weights file doesn't exist)
DEMO_MODE = not os.path.isfile(MODEL_PATH)
