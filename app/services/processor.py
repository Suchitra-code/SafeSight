"""
Image and Video Processing Pipeline for SafeSight AI.
Handles resizing, detection, safety rule execution, OpenCV drawing,
snapshot cropping, MySQL storage, and video rendering with progress tracking.
"""
import os
import uuid
import time
import shutil
import subprocess
import threading
import logging
from typing import Dict, Any, Optional

import cv2
import numpy as np

import config
from app.db import execute_insert, execute_query
from app.services.detector import PPEDetector
from app.services.safety_rules import analyze_safety

logger = logging.getLogger(__name__)

# In-memory progress tracking for asynchronous video processing jobs
video_progress_store: Dict[int, Dict[str, Any]] = {}

# BGR color palette (Sunrise Garden — Strictly NO blue, NO black)
COLOR_SAFE = (115, 181, 34)       # #22B573 Mint
COLOR_DANGER = (80, 57, 229)      # #E53950 Red
COLOR_WARNING = (60, 201, 255)    # #FFC93C Sun
COLOR_PANEL_BG = (47, 29, 74)     # #4A1D2F Warm Plum Container
COLOR_WHITE = (255, 255, 255)
COLOR_TEXT_DIM = (126, 107, 154)  # #9A6B7E Warm Soft Text


def draw_rounded_rectangle(img, pt1, pt2, color, thickness=2, radius=8):
    """Draws a rectangle with smooth corners."""
    x1, y1 = pt1
    x2, y2 = pt2
    # Ensure radius fits in box
    r = min(radius, abs(x2 - x1) // 2, abs(y2 - y1) // 2)

    # Top/Bottom lines
    cv2.line(img, (x1 + r, y1), (x2 - r, y1), color, thickness)
    cv2.line(img, (x1 + r, y2), (x2 - r, y2), color, thickness)
    # Left/Right lines
    cv2.line(img, (x1, y1 + r), (x1, y2 - r), color, thickness)
    cv2.line(img, (x2, y1 + r), (x2, y2 - r), color, thickness)

    # 4 Corner arcs
    cv2.ellipse(img, (x1 + r, y1 + r), (r, r), 180, 0, 90, color, thickness)
    cv2.ellipse(img, (x2 - r, y1 + r), (r, r), 270, 0, 90, color, thickness)
    cv2.ellipse(img, (x1 + r, y2 - r), (r, r), 90, 0, 90, color, thickness)
    cv2.ellipse(img, (x2 - r, y2 - r), (r, r), 0, 0, 90, color, thickness)


def draw_label(img, text, origin, bg_color, text_color=COLOR_WHITE, font_scale=0.5, thickness=1):
    """Draws a filled rounded badge above or next to a detection box."""
    font = cv2.FONT_HERSHEY_DUPLEX
    (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    x, y = origin
    pad = 4

    # Background rect
    bx1 = max(0, x)
    by1 = max(0, y - text_h - (pad * 2))
    bx2 = min(img.shape[1] - 1, x + text_w + (pad * 2))
    by2 = max(0, y)

    cv2.rectangle(img, (bx1, by1), (bx2, by2), bg_color, -1)
    cv2.putText(img, text, (bx1 + pad, by2 - pad - 1), font, font_scale, text_color, thickness, cv2.LINE_AA)


def draw_stats_overlay(img, total, safe, unsafe, compliance):
    """
    Renders top-left floating telemetry banner:
    Workers: N | Safe: X | Unsafe: Y | Compliance: Z%
    """
    h, w = img.shape[:2]
    banner_text = f" Workers: {total}  |  Safe: {safe}  |  Unsafe: {unsafe}  |  Compliance: {compliance:.1f}% "
    font = cv2.FONT_HERSHEY_DUPLEX
    font_scale = 0.55
    thickness = 1
    (tw, th), baseline = cv2.getTextSize(banner_text, font, font_scale, thickness)

    bx1, by1 = 16, 16
    bx2 = bx1 + tw + 20
    by2 = by1 + th + 16

    # Draw navy rounded container with subtle border
    overlay = img.copy()
    cv2.rectangle(overlay, (bx1, by1), (bx2, by2), COLOR_PANEL_BG, -1)
    cv2.rectangle(overlay, (bx1, by1), (bx2, by2), (207, 217, 243), 1)
    cv2.addWeighted(overlay, 0.88, img, 0.12, 0, img)

    # Determine status color dot
    dot_color = COLOR_SAFE if compliance >= 90.0 else (COLOR_WARNING if compliance >= 70.0 else COLOR_DANGER)
    cv2.circle(img, (bx1 + 10, by1 + ((by2 - by1) // 2)), 5, dot_color, -1)

    cv2.putText(img, banner_text, (bx1 + 16, by1 + th + 7), font, font_scale, COLOR_WHITE, thickness, cv2.LINE_AA)


def annotate_frame(frame, analysis: Dict[str, Any]):
    """
    Draws all person boxes, PPE tags, and telemetry banner on a frame.
    """
    annotated = frame.copy()
    persons = analysis.get("persons", [])

    for person in persons:
        bbox = person["bbox"]
        x1, y1, x2, y2 = bbox
        is_safe = person["is_safe"]
        only_secondary = person.get("only_secondary", False)

        # Color coding: Green for Safe, Red for Unsafe (Helmet violation), Amber for Vest/Goggles-only
        if is_safe:
            color = COLOR_SAFE
            status_text = f"Person – SAFE {int(person['confidence']*100)}%"
        elif only_secondary:
            color = COLOR_WARNING
            v_names = ", ".join([v["violation_type"].upper() for v in person["violations"]])
            status_text = f"WARN ({v_names}) {int(person['confidence']*100)}%"
        else:
            color = COLOR_DANGER
            status_text = f"NO HELMET {int(person['confidence']*100)}%"

        # Draw main person rounded box
        draw_rounded_rectangle(annotated, (x1, y1), (x2, y2), color, thickness=2, radius=6)
        draw_label(annotated, status_text, (x1, y1), color, COLOR_WHITE, font_scale=0.5)

        # Draw matched PPE gear items with smaller indicators
        for item in person.get("matched_ppe", []):
            ix1, iy1, ix2, iy2 = item["bbox"]
            iname = item.get("class_name", "")
            iconf = int(item.get("confidence", 0) * 100)
            icol = COLOR_SAFE if "no-" not in iname.lower() else COLOR_DANGER
            cv2.rectangle(annotated, (ix1, iy1), (ix2, iy2), icol, 1)
            draw_label(annotated, f"{iname} {iconf}%", (ix1, iy1), icol, COLOR_WHITE, font_scale=0.38)

    # Render telemetry banner
    draw_stats_overlay(
        annotated,
        analysis["total_people"],
        analysis["safe_count"],
        analysis["unsafe_count"],
        analysis["compliance_percent"]
    )

    return annotated


def crop_person_snapshot(image, bbox, output_dir=None) -> str:
    """
    Crops person box with 10% padding and saves snapshot to outputs/ folder.
    Returns the relative path for database storage.
    """
    if output_dir is None:
        output_dir = config.OUTPUT_FOLDER

    h, w = image.shape[:2]
    x1, y1, x2, y2 = bbox

    pad_x = int((x2 - x1) * 0.1)
    pad_y = int((y2 - y1) * 0.1)

    cx1 = max(0, x1 - pad_x)
    cy1 = max(0, y1 - pad_y)
    cx2 = min(w, x2 + pad_x)
    cy2 = min(h, y2 + pad_y)

    cropped = image[cy1:cy2, cx1:cx2]
    if cropped.size == 0:
        return ""

    filename = f"snap_{uuid.uuid4().hex[:8]}.jpg"
    full_path = os.path.join(output_dir, filename)
    cv2.imwrite(full_path, cropped)
    return filename


def process_image(file_path: str, upload_id: int, confidence: float = 0.40,
                  camera_name: str = "Manual Upload", location: str = "Zone A") -> Dict[str, Any]:
    """
    Full processing pipeline for a single static image.
    """
    detector = PPEDetector()
    img = cv2.imread(file_path)
    if img is None:
        raise ValueError(f"Unable to read image at {file_path}")

    # Resize to max width 1280 while preserving aspect ratio
    h, w = img.shape[:2]
    if w > 1280:
        scale = 1280.0 / w
        img = cv2.resize(img, (1280, int(h * scale)), interpolation=cv2.INTER_AREA)

    # 1. Detection
    detections = detector.detect(img, conf_threshold=confidence)

    # 2. Safety Rules
    analysis = analyze_safety(detections, enable_goggles=config.ENABLE_GOGGLES_CHECK)

    # 3. Annotation
    annotated = annotate_frame(img, analysis)
    output_filename = f"annotated_{os.path.basename(file_path)}"
    output_path = os.path.join(config.OUTPUT_FOLDER, output_filename)
    cv2.imwrite(output_path, annotated)

    # 4. Save Detections to DB
    det_id = execute_insert(
        """
        INSERT INTO detections (upload_id, frame_no, timestamp_sec, total_people, safe_count, unsafe_count, compliance_percent)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (upload_id, 0, 0.0, analysis["total_people"], analysis["safe_count"],
         analysis["unsafe_count"], analysis["compliance_percent"])
    )

    # 5. Save Violations with Cropped Snapshots to DB
    violations_saved = []
    for person in analysis.get("persons", []):
        if not person["is_safe"]:
            snap_file = crop_person_snapshot(img, person["bbox"])
            for v in person.get("violations", []):
                v_type = v["violation_type"]
                severity = v["severity"]
                conf = float(v.get("confidence", 0.90))

                v_id = execute_insert(
                    """
                    INSERT INTO violations (upload_id, detection_id, violation_type, severity, confidence,
                                            snapshot_path, camera_name, location, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'detected')
                    """,
                    (upload_id, det_id, v_type, severity, conf, snap_file, camera_name, location)
                )
                v_copy = dict(v)
                v_copy["id"] = v_id
                v_copy["snapshot_path"] = snap_file
                violations_saved.append(v_copy)

    # Update upload status to 'done'
    execute_query(
        "UPDATE uploads SET status = 'done', output_path = %s WHERE id = %s",
        (output_filename, upload_id),
        fetch=False,
        commit=True
    )

    return {
        "upload_id": upload_id,
        "output_file": output_filename,
        "total_people": analysis["total_people"],
        "safe_count": analysis["safe_count"],
        "unsafe_count": analysis["unsafe_count"],
        "compliance_percent": analysis["compliance_percent"],
        "violations": violations_saved,
        "is_demo": detector.is_demo
    }


def reencode_to_h264(input_path: str, output_path: str) -> bool:
    """Uses ffmpeg if available to convert video to standard H.264 for HTML5 browser playback."""
    ffmpeg_exe = shutil.which("ffmpeg")
    if not ffmpeg_exe:
        return False
    try:
        cmd = [
            ffmpeg_exe, "-y", "-i", input_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p", output_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception as e:
        logger.warning(f"ffmpeg conversion failed: {e}")
        return False


def process_video_async(file_path: str, upload_id: int, confidence: float = 0.40,
                        camera_name: str = "Manual Upload", location: str = "Zone A",
                        frame_skip: int = 5):
    """
    Background worker thread function for asynchronous video processing.
    """
    def _worker():
        try:
            video_progress_store[upload_id] = {"percent": 5, "status": "Initializing video..."}
            detector = PPEDetector()
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                raise ValueError("Could not open video file.")

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Scale resolution if wider than 1280
            if w > 1280:
                scale = 1280.0 / w
                w = 1280
                h = int(h * scale)

            base_name = os.path.basename(file_path)
            temp_output_name = f"temp_annotated_{base_name}"
            final_output_name = f"annotated_{os.path.splitext(base_name)[0]}.mp4"

            temp_output_path = os.path.join(config.OUTPUT_FOLDER, temp_output_name)
            final_output_path = os.path.join(config.OUTPUT_FOLDER, final_output_name)

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_output_path, fourcc, fps / max(1, frame_skip), (w, h))

            frame_no = 0
            processed_count = 0
            cooldown_tracker = {}  # violation_type -> last_timestamp_sec

            total_workers_sum = 0
            safe_workers_sum = 0

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_no % frame_skip == 0:
                    current_sec = round(frame_no / fps, 2)
                    if frame.shape[1] != w:
                        frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_AREA)

                    # Inference + Rules
                    detections = detector.detect(frame, conf_threshold=confidence)
                    analysis = analyze_safety(detections, enable_goggles=config.ENABLE_GOGGLES_CHECK)

                    annotated = annotate_frame(frame, analysis)
                    out.write(annotated)

                    total_workers_sum += analysis["total_people"]
                    safe_workers_sum += analysis["safe_count"]

                    # Save detection summary
                    det_id = execute_insert(
                        """
                        INSERT INTO detections (upload_id, frame_no, timestamp_sec, total_people, safe_count, unsafe_count, compliance_percent)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (upload_id, frame_no, current_sec, analysis["total_people"],
                         analysis["safe_count"], analysis["unsafe_count"], analysis["compliance_percent"])
                    )

                    # Debounce violations within 3-second window
                    for person in analysis.get("persons", []):
                        if not person["is_safe"]:
                            snap_file = crop_person_snapshot(frame, person["bbox"])
                            for v in person.get("violations", []):
                                vtype = v["violation_type"]
                                last_seen = cooldown_tracker.get(vtype, -999.0)
                                if (current_sec - last_seen) >= 3.0:
                                    cooldown_tracker[vtype] = current_sec
                                    execute_insert(
                                        """
                                        INSERT INTO violations (upload_id, detection_id, violation_type, severity, confidence,
                                                                snapshot_path, camera_name, location, status)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'detected')
                                        """,
                                        (upload_id, det_id, vtype, v["severity"],
                                         float(v.get("confidence", 0.9)), snap_file, camera_name, location)
                                    )

                    processed_count += 1
                    # Progress calculation
                    progress = min(90, int((frame_no / max(1, total_frames)) * 90))
                    video_progress_store[upload_id] = {
                        "percent": progress,
                        "status": f"Processing frame {frame_no}/{total_frames} ({progress}%)"
                    }

                frame_no += 1

            cap.release()
            out.release()

            # Transcode with ffmpeg if available for browser playback, else use mp4v
            video_progress_store[upload_id] = {"percent": 95, "status": "Optimizing video for web..."}
            if reencode_to_h264(temp_output_path, final_output_path):
                try:
                    os.remove(temp_output_path)
                except Exception:
                    pass
                chosen_output = final_output_name
            else:
                chosen_output = temp_output_name

            execute_query(
                "UPDATE uploads SET status = 'done', output_path = %s WHERE id = %s",
                (chosen_output, upload_id),
                fetch=False,
                commit=True
            )

            video_progress_store[upload_id] = {
                "percent": 100,
                "status": "Complete",
                "output_file": chosen_output
            }

        except Exception as e:
            logger.error(f"Error processing video upload {upload_id}: {e}", exc_info=True)
            execute_query(
                "UPDATE uploads SET status = 'failed' WHERE id = %s",
                (upload_id,),
                fetch=False,
                commit=True
            )
            video_progress_store[upload_id] = {
                "percent": 100,
                "status": f"Failed: {str(e)}",
                "error": True
            }

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
