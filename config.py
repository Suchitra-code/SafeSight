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

# Milestone 2 Storage Paths
DOC_UPLOAD_FOLDER = os.path.join(UPLOAD_FOLDER, "documents")
DOC_OUTPUT_FOLDER = os.path.join(OUTPUT_FOLDER, "documents")
KNOWLEDGE_FOLDER = os.path.join(BASE_DIR, "knowledge")
FAISS_INDEX_PATH = os.path.join(KNOWLEDGE_FOLDER, "faiss.index")
CHUNKS_META_PATH = os.path.join(KNOWLEDGE_FOLDER, "chunks_meta.json")

# Milestone 3 Storage Paths
FAISS_VISUAL_INDEX_PATH = os.path.join(KNOWLEDGE_FOLDER, "faiss_visual.index")
VISUAL_CHUNKS_META_PATH = os.path.join(KNOWLEDGE_FOLDER, "visual_chunks_meta.json")
AGENT_CHECKPOINT_DB_PATH = os.path.join(KNOWLEDGE_FOLDER, "agent_checkpoints.sqlite")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
APP_LOG_PATH = os.path.join(LOGS_DIR, "app.log")

# Create required directories automatically
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, REPORT_FOLDER, MODEL_DIR, DOC_UPLOAD_FOLDER, DOC_OUTPUT_FOLDER, KNOWLEDGE_FOLDER, LOGS_DIR]:
    os.makedirs(folder, exist_ok=True)

# Upload constraints
MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "avi", "mov"}
ALLOWED_DOC_EXTENSIONS = {"pdf", "docx", "txt", "png", "jpg", "jpeg"}

# Milestone 2 NLP & Search Configuration
TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").strip().lower()
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-1.5-flash")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
VISION_LLM_ENABLED = os.getenv("VISION_LLM_ENABLED", "false").lower() in ("true", "1", "yes")
AUTO_INVESTIGATE_HIGH = os.getenv("AUTO_INVESTIGATE_HIGH", "false").lower() in ("true", "1", "yes")

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
COMPLIANCE_TARGET = float(os.getenv("COMPLIANCE_TARGET", "95.0"))

# Milestone 4 Copilot & Mission Control Configuration
COPILOT_MAX_RETRIES = int(os.getenv("COPILOT_MAX_RETRIES", "2"))
COPILOT_MIN_EVIDENCE_SCORE = float(os.getenv("COPILOT_MIN_EVIDENCE_SCORE", "0.25"))
VALIDATION_PASS_SCORE = int(os.getenv("VALIDATION_PASS_SCORE", "80"))
VALIDATION_REVISE_SCORE = int(os.getenv("VALIDATION_REVISE_SCORE", "50"))
COPILOT_RATE_LIMIT_PER_MIN = int(os.getenv("COPILOT_RATE_LIMIT_PER_MIN", "20"))
LANGGRAPH_VERSION = "1.2.20"

# Demo mode flag (True if weights file doesn't exist)
DEMO_MODE = not os.path.isfile(MODEL_PATH)
