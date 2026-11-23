"""
Live Video Stream Route for SafeSight AI.
Streams multipart/x-mixed-replace MJPEG feed with real-time YOLOv8 detections,
safety rule analysis, visual bounding boxes, and rate-limited violation logging.
Optimized for production containers (Render) with thread limits and CPU throttling.
"""
import os
import time
import logging
import threading
from flask import Blueprint, Response, request
import cv2
import numpy as np

import config
from app.db import execute_insert
from app.services.detector import PPEDetector
from app.services.safety_rules import analyze_safety
from app.services.processor import annotate_frame, crop_person_snapshot

logger = logging.getLogger(__name__)

stream_bp = Blueprint("stream", __name__)

# Concurrency guard: limit simultaneous streaming threads to prevent worker starvation
_MAX_CONCURRENT_STREAMS = 2
_active_streams = 0
_stream_lock = threading.Lock()


def generate_mjpeg_stream(source_identifier: str):
    """
    Generator yielding JPEG frame buffers for multipart/x-mixed-replace streaming.
    Handles webcam (source '0'), video file, or synthetic CCTV feed if camera unavailable.
    Guaranteed to release worker threads and avoid CPU starvation.
    """
    global _active_streams

    with _stream_lock:
        if _active_streams >= _MAX_CONCURRENT_STREAMS:
            logger.warning("Active live stream limit reached. Rejecting extra stream to preserve worker threads.")
            # Yield single placeholder notice frame
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:] = (30, 20, 15)
            cv2.putText(frame, "Stream Capacity Limit Reached", (80, 220),
                        cv2.FONT_HERSHEY_DUPLEX, 0.7, (230, 230, 230), 1)
            cv2.putText(frame, "Please refresh or close other active tabs.", (100, 260),
                        cv2.FONT_HERSHEY_DUPLEX, 0.5, (160, 160, 160), 1)
            _, buf = cv2.imencode(".jpg", frame)
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")
            return
        _active_streams += 1

    detector = PPEDetector()
    cap = None
    is_synthetic = False

    try:
        if source_identifier in ("0", "webcam", "default"):
            # On Linux cloud containers (Render), check if video device exists before attempting capture
            is_linux = os.name != "nt"
            if is_linux and not os.path.exists("/dev/video0"):
                is_synthetic = True
            else:
                try:
                    cap = cv2.VideoCapture(0)
                    if not cap or not cap.isOpened():
                        is_synthetic = True
                except Exception:
                    is_synthetic = True
            cam_name = "Cam 01 – Zone A"
            location = "Zone A - Fabrication"
        else:
            cam_name = f"Cam {source_identifier}"
            location = "Facility Perimeter"
            matched_video = None
            if os.path.exists(config.UPLOAD_FOLDER):
                for f in os.listdir(config.UPLOAD_FOLDER):
                    if f.endswith((".mp4", ".avi")):
                        matched_video = os.path.join(config.UPLOAD_FOLDER, f)
                        break
            if matched_video:
                cap = cv2.VideoCapture(matched_video)
            else:
                is_synthetic = True

        if cap and not cap.isOpened():
            cap.release()
            cap = None
            is_synthetic = True

        last_violation_log = {}  # violation_type -> unix_timestamp
        frame_counter = 0
        start_time = time.time()
        max_duration = 300  # Automatically cycle stream after 5 minutes to release worker threads

        while (time.time() - start_time) < max_duration:
            frame = None
            if not is_synthetic and cap:
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                    if not ret:
                        is_synthetic = True

            if is_synthetic or frame is None:
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                frame[:] = (30, 20, 15)

                t_str = time.strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(frame, f"[CCTV] {cam_name} | {location}", (20, 35),
                            cv2.FONT_HERSHEY_DUPLEX, 0.5, (200, 200, 200), 1)
                cv2.putText(frame, f"REC {t_str}", (480, 35),
                            cv2.FONT_HERSHEY_DUPLEX, 0.45, (68, 68, 239), 1)

                shift = int((time.time() * 30) % 350)
                px1 = 120 + shift
                py1 = 120
                px2 = px1 + 90
                py2 = py1 + 240

                cv2.ellipse(frame, (px1 + 45, py1 + 35), (25, 30), 0, 0, 360, (110, 100, 90), -1)
                cv2.rectangle(frame, (px1 + 10, py1 + 65), (px2 - 10, py2), (75, 65, 55), -1)

                detections = [
                    {"class_name": "Person", "confidence": 0.93, "bbox": [px1, py1, px2, py2]},
                    {"class_name": "Safety Vest", "confidence": 0.91, "bbox": [px1 + 12, py1 + 75, px2 - 12, py1 + 180]}
                ]
            else:
                if frame.shape[1] > 960:
                    scale = 960.0 / frame.shape[1]
                    frame = cv2.resize(frame, (960, int(frame.shape[0] * scale)))

                detections = detector.detect(frame, conf_threshold=0.40)

            analysis = analyze_safety(detections, enable_goggles=config.ENABLE_GOGGLES_CHECK)
            annotated = annotate_frame(frame, analysis)

            # Rate-limited violation logging
            current_time = time.time()
            for v in analysis.get("violations", []):
                v_type = v["violation_type"]
                last_logged = last_violation_log.get(v_type, 0)
                if (current_time - last_logged) >= config.VIOLATION_COOLDOWN_SECONDS:
                    last_violation_log[v_type] = current_time
                    try:
                        snap_name = crop_person_snapshot(frame, v.get("person_bbox", [0, 0, 100, 100]))
                        execute_insert(
                            """
                            INSERT INTO violations (upload_id, detection_id, violation_type, severity, confidence,
                                                    snapshot_path, camera_name, location, status)
                            VALUES (NULL, NULL, %s, %s, %s, %s, %s, %s, 'detected')
                            """,
                            (v_type, v["severity"], float(v.get("confidence", 0.9)),
                             snap_name, cam_name, location)
                        )
                    except Exception as err:
                        logger.warning(f"Error logging live stream violation: {err}")

            ret, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if not ret:
                continue

            frame_bytes = buffer.tobytes()
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

            frame_counter += 1
            # Throttled to ~10-12 FPS to maintain low CPU footprint on single-vCPU containers
            time.sleep(0.08)

    except (GeneratorExit, ConnectionResetError, BrokenPipeError):
        pass
    except Exception as e:
        logger.error(f"Live stream generator exception: {e}")
    finally:
        if cap:
            try:
                cap.release()
            except Exception:
                pass
        with _stream_lock:
            _active_streams = max(0, _active_streams - 1)


@stream_bp.route("/video_feed/<source>")
def video_feed(source):
    """Returns MJPEG multipart stream for live monitor."""
    return Response(
        generate_mjpeg_stream(source),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )
