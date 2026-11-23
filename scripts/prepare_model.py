"""
SafeSight AI - Model Weights Preparation Script for Render & Production
Ensures that models/best.pt exists before application startup:
1. Checks if models/best.pt is already present and valid.
2. If MODEL_URL is set in environment, downloads custom weights from MODEL_URL.
3. If not present and MODEL_URL not set, downloads official YOLOv8 model weights
   and saves as models/best.pt so real PyTorch YOLO inference is active.
"""
import os
import sys
import logging
import tempfile
import urllib.request

# Ensure cache directories are writable in container/cloud environments
os.environ.setdefault("YOLO_CONFIG_DIR", os.path.join(tempfile.gettempdir(), "ultralytics"))
os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("prepare_model")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "best.pt")

def ensure_model():
    os.makedirs(MODEL_DIR, exist_ok=True)

    # 1. Check if best.pt already exists and is non-empty
    if os.path.exists(MODEL_PATH) and os.path.getsize(MODEL_PATH) > 1000:
        logger.info(f"Model weights already present at {MODEL_PATH} ({os.path.getsize(MODEL_PATH)} bytes).")
        return True

    # 2. Check if a custom model URL is provided via environment variable
    model_url = os.getenv("MODEL_URL")
    if model_url:
        logger.info(f"Downloading custom model weights from MODEL_URL: {model_url}...")
        try:
            # Custom User-Agent to prevent 403 blocks from CDNs
            req = urllib.request.Request(
                model_url,
                headers={"User-Agent": "Mozilla/5.0 SafeSight-Model-Downloader"}
            )
            with urllib.request.urlopen(req, timeout=120) as response, open(MODEL_PATH, "wb") as out_file:
                out_file.write(response.read())
            logger.info(f"Successfully downloaded custom model weights to {MODEL_PATH} ({os.path.getsize(MODEL_PATH)} bytes).")
            return True
        except Exception as e:
            logger.error(f"Failed to download custom model weights from MODEL_URL ({model_url}): {e}")

    # 3. Fallback: Download official Ultralytics YOLOv8 weights to initialize models/best.pt
    logger.info("Initializing models/best.pt with YOLOv8 safety base weights...")
    try:
        from ultralytics import YOLO
        import shutil
        model = YOLO("yolov8n.pt")
        weights_file = getattr(model, "weights", None)
        if weights_file and os.path.exists(str(weights_file)):
            shutil.copy(str(weights_file), MODEL_PATH)
            logger.info(f"Successfully initialized {MODEL_PATH} from local ultralytics weights ({weights_file}).")
            return True
    except Exception as e:
        logger.warning(f"Ultralytics load failed or restricted ({e}). Attempting direct asset download...")

    # 4. Direct download fallback from official Ultralytics releases
    direct_urls = [
        "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt",
        "https://github.com/ultralytics/assets/releases/download/v8.1.0/yolov8n.pt"
    ]
    for url in direct_urls:
        try:
            logger.info(f"Attempting download from {url}...")
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 SafeSight-Model-Downloader"}
            )
            with urllib.request.urlopen(req, timeout=120) as response, open(MODEL_PATH, "wb") as out_file:
                out_file.write(response.read())
            if os.path.exists(MODEL_PATH) and os.path.getsize(MODEL_PATH) > 1000:
                logger.info(f"Successfully downloaded weights from {url} to {MODEL_PATH} ({os.path.getsize(MODEL_PATH)} bytes).")
                return True
        except Exception as ex:
            logger.warning(f"Download from {url} failed: {ex}")

    logger.error("Could not download or initialize YOLO model weights.")
    return False

if __name__ == "__main__":
    success = ensure_model()
    if not success:
        logger.warning("Could not auto-download model weights at build time. Model will be checked again at runtime.")
    sys.exit(0)
