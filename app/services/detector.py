"""
YOLOv8 Detection Service for SafeSight AI.
Loads the YOLOv8 model as a thread-safe singleton, handles CPU/CUDA selection,
normalizes class names, and supports non-blocking background initialization
so Gunicorn workers bind port instantly without timeout.
"""
import os
import logging
import threading
import time
import config

logger = logging.getLogger(__name__)


def get_memory_rss_mb() -> float:
    """Returns the current process RSS memory in MB (Linux/Render & fallback)."""
    try:
        with open("/proc/self/status", "r") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return round(float(line.split()[1]) / 1024.0, 1)
    except Exception:
        pass
    try:
        import resource
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)
    except Exception:
        return 0.0


class PPEDetector:
    _instance = None
    _init_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = super(PPEDetector, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_path=None):
        if self._initialized:
            return

        with self._init_lock:
            if self._initialized:
                return
            self.model_path = model_path or config.MODEL_PATH
            self.model = None
            self.is_demo = True
            self.device = config.DEVICE
            self._inference_lock = threading.Lock()
            self._ready_event = threading.Event()
            self._loading = False

            # Start loading model in background thread
            # This ensures Gunicorn boots and binds Render port in <1 second
            self._start_async_load()
            self._initialized = True

    def _start_async_load(self):
        """Launches model loading on a daemon thread to unblock server boot."""
        if self._loading:
            return
        self._loading = True
        t = threading.Thread(target=self._load_model, daemon=True, name="YOLOModelLoader")
        t.start()

    def _load_model(self):
        """Loads YOLO model once if the weights file exists."""
        start_t = time.time()
        logger.info(f"YOLO loader started in background thread. Initial RSS: {get_memory_rss_mb()} MB")

        if not os.path.exists(self.model_path):
            try:
                from scripts.prepare_model import ensure_model
                ensure_model()
            except Exception as prep_err:
                logger.warning(f"Auto-prepare weights encountered: {prep_err}")

        if not os.path.exists(self.model_path):
            logger.warning(
                f"Weights file not found at '{self.model_path}'. Running detector in DEMO mode."
            )
            self.is_demo = True
            self._loading = False
            self._ready_event.set()
            return

        try:
            import torch

            # Optimize PyTorch CPU settings for cloud containers
            try:
                torch.set_grad_enabled(False)
                torch.set_num_threads(2)
            except Exception:
                pass

            # Compatibility patch for PyTorch 2.6+ default weights_only=True
            try:
                _orig_torch_load = torch.load
                def _safe_torch_load(*args, **kwargs):
                    if "weights_only" not in kwargs:
                        kwargs["weights_only"] = False
                    return _orig_torch_load(*args, **kwargs)
                torch.load = _safe_torch_load
            except Exception:
                pass

            try:
                if hasattr(torch.serialization, "add_safe_globals"):
                    import ultralytics.nn.tasks
                    torch.serialization.add_safe_globals([ultralytics.nn.tasks.DetectionModel])
            except Exception:
                pass

            from ultralytics import YOLO

            # Determine device: use cuda if available and requested, else cpu
            target_device = "cpu"
            if torch.cuda.is_available() and self.device.lower() in ("cuda", "gpu", "0"):
                target_device = "cuda"

            logger.info(f"Loading YOLOv8 model from {self.model_path} onto {target_device}...")
            self.model = YOLO(self.model_path)
            self.device = target_device
            self.is_demo = False

            duration = round(time.time() - start_t, 2)
            logger.info(f"YOLOv8 model loaded successfully in {duration}s. Post-load RSS: {get_memory_rss_mb()} MB")
        except Exception as e:
            logger.error(f"Failed to load YOLOv8 model ({e}). Falling back to DEMO mode.")
            self.is_demo = True
            self.model = None
        finally:
            self._loading = False
            self._ready_event.set()

    def wait_until_ready(self, timeout=30):
        """Wait up to `timeout` seconds for background model loading to complete."""
        return self._ready_event.wait(timeout=timeout)

    def _normalize_class_name(self, raw_name: str) -> str:
        """Map model class name to canonical SafeSight name via config.CLASS_MAP."""
        cleaned = raw_name.strip().lower()
        return config.CLASS_MAP.get(cleaned, raw_name.strip().title())

    def detect(self, image, conf_threshold=None):
        """
        Runs thread-safe inference on an OpenCV BGR image or numpy array.
        Returns:
            list of dicts: [
                {"class_name": "Person", "confidence": 0.92, "bbox": [x1, y1, x2, y2]},
                ...
            ]
        """
        if conf_threshold is None:
            conf_threshold = config.CONFIDENCE_THRESHOLD

        # If model is still loading in background, wait up to 30s
        if not self._ready_event.is_set():
            logger.info("Detector still loading in background, waiting for completion...")
            self._ready_event.wait(timeout=30)

        # If in demo mode without real weights, return synthetic detections
        if self.is_demo or self.model is None:
            return self._generate_demo_detections(image, conf_threshold)

        # Thread-safe prediction lock for gthread workers
        with self._inference_lock:
            try:
                import torch
                with torch.inference_mode():
                    results = self.model.predict(
                        source=image,
                        conf=conf_threshold,
                        device=self.device,
                        verbose=False
                    )
                detections = []
                if not results:
                    return detections

                result = results[0]
                boxes = result.boxes
                if boxes is None or len(boxes) == 0:
                    return detections

                names = result.names  # mapping {class_id: name}
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    raw_name = names.get(cls_id, f"Class_{cls_id}")
                    canonical_name = self._normalize_class_name(raw_name)
                    conf = float(box.conf[0].item())
                    coords = [int(v) for v in box.xyxy[0].tolist()]

                    detections.append({
                        "class_name": canonical_name,
                        "confidence": round(conf, 3),
                        "bbox": coords
                    })

                return detections
            except Exception as e:
                logger.error(f"Error during YOLO inference: {e}")
                return []

    def _generate_demo_detections(self, image, conf_threshold):
        """
        Produces realistic simulated detections when running in demo mode
        so the user can immediately test uploads and see annotations.
        """
        if image is None:
            return []
        h, w = image.shape[:2]
        return [
            {
                "class_name": "Person",
                "confidence": 0.94,
                "bbox": [int(w * 0.2), int(h * 0.2), int(w * 0.45), int(h * 0.9)]
            },
            {
                "class_name": "Hardhat",
                "confidence": 0.92,
                "bbox": [int(w * 0.26), int(h * 0.21), int(w * 0.39), int(h * 0.35)]
            },
            {
                "class_name": "Safety Vest",
                "confidence": 0.89,
                "bbox": [int(w * 0.23), int(h * 0.38), int(w * 0.42), int(h * 0.68)]
            },
            {
                "class_name": "Person",
                "confidence": 0.91,
                "bbox": [int(w * 0.55), int(h * 0.25), int(w * 0.80), int(h * 0.92)]
            },
            {
                "class_name": "NO-Hardhat",
                "confidence": 0.88,
                "bbox": [int(w * 0.62), int(h * 0.26), int(w * 0.73), int(h * 0.40)]
            }
        ]
