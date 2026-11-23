"""
YOLOv8 Detection Service for SafeSight AI.
Loads the YOLOv8 model as a singleton, handles CPU/CUDA selection,
normalizes class names, and gracefully handles demo/missing model mode.
"""
import os
import logging
import config

logger = logging.getLogger(__name__)

class PPEDetector:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(PPEDetector, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_path=None):
        if self._initialized:
            return
        self.model_path = model_path or config.MODEL_PATH
        self.model = None
        self.is_demo = True
        self.device = config.DEVICE
        self._load_model()
        self._initialized = True

    def _load_model(self):
        """Loads YOLO model once if the weights file exists."""
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
            return

        try:
            import torch

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
            logger.info("YOLOv8 model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load YOLOv8 model ({e}). Falling back to DEMO mode.")
            self.is_demo = True
            self.model = None

    def _normalize_class_name(self, raw_name: str) -> str:
        """Map model class name to canonical SafeSight name via config.CLASS_MAP."""
        cleaned = raw_name.strip().lower()
        return config.CLASS_MAP.get(cleaned, raw_name.strip().title())

    def detect(self, image, conf_threshold=None):
        """
        Runs inference on an OpenCV BGR image or numpy array.
        Returns:
            list of dicts: [
                {"class_name": "Person", "confidence": 0.92, "bbox": [x1, y1, x2, y2]},
                ...
            ]
        """
        if conf_threshold is None:
            conf_threshold = config.CONFIDENCE_THRESHOLD

        # If in demo mode without real weights, return synthetic detections if it's a test/demo image
        if self.is_demo or self.model is None:
            return self._generate_demo_detections(image, conf_threshold)

        try:
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
        # Return 1 or 2 simulated workers with realistic bounding boxes
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
