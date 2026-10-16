"""
Demo Data Seeder for SafeSight AI.
Generates realistic historical data across 21 days with:
- 14 workers baseline
- Exactly 53 violations: 25 helmet, 15 vest, 8 goggles, 5 other
- Distributed across 3 cameras
- Distributed across all 5 statuses: detected, pending review, confirmed, dismissed, resolved
- Compliance rate ~94.5%
- 8 generated sample snapshot images with OpenCV
"""
import os
import sys
import random
from datetime import datetime, timedelta

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import cv2
import numpy as np

import config
from app.db import execute_query, execute_insert, init_db


def generate_sample_snapshots():
    """Generates 8 realistic synthetic snapshot crops for demo cards."""
    os.makedirs(config.OUTPUT_FOLDER, exist_ok=True)
    snapshot_filenames = []

    labels = [
        ("NO HELMET", (68, 68, 239)),
        ("SAFE WORKER", (94, 197, 34)),
        ("MISSING VEST", (11, 158, 245)),
        ("NO GOGGLES", (11, 158, 245)),
        ("RESTRICTED AREA", (180, 50, 220)),
        ("NO HELMET", (68, 68, 239)),
        ("SAFE WORKER", (94, 197, 34)),
        ("NO HELMET", (68, 68, 239))
    ]

    for i, (tag, color) in enumerate(labels):
        fname = f"snap_demo_{i+1}.jpg"
        fpath = os.path.join(config.OUTPUT_FOLDER, fname)

        # Generate a worker silhouette placeholder with badge
        img = np.zeros((260, 200, 3), dtype=np.uint8)
        img[:] = (35, 25, 20)  # dark background

        # Worker body outline
        cv2.circle(img, (100, 70), 38, (120, 110, 100), -1)  # head
        cv2.ellipse(img, (100, 200), (65, 90), 0, 0, 360, (70, 60, 50), -1)  # torso

        # Draw PPE simulation
        if "SAFE" in tag:
            # Draw green hardhat
            cv2.ellipse(img, (100, 55), (42, 24), 0, 180, 360, (94, 197, 34), -1)
            # Draw green vest
            cv2.rectangle(img, (60, 130), (140, 220), (94, 197, 34), 3)
        elif "NO HELMET" in tag:
            # Draw red exclamation mark on head
            cv2.putText(img, "!", (92, 75), cv2.FONT_HERSHEY_DUPLEX, 1.2, (68, 68, 239), 2)
        elif "VEST" in tag:
            # Draw yellow hardhat
            cv2.ellipse(img, (100, 55), (42, 24), 0, 180, 360, (11, 158, 245), -1)

        # Tag banner at bottom
        cv2.rectangle(img, (0, 225), (200, 260), (15, 10, 5), -1)
        cv2.rectangle(img, (8, 232), (192, 253), color, 1)
        cv2.putText(img, tag, (16, 248), cv2.FONT_HERSHEY_DUPLEX, 0.42, color, 1)

        cv2.imwrite(fpath, img)
        snapshot_filenames.append(fname)

    return snapshot_filenames


def seed_demo_data(reset: bool = True):
    """Populates database with the required demo records."""
    init_db()

    if reset:
        print("Clearing existing records...")
        execute_query("DELETE FROM violations", commit=True, fetch=False)
        execute_query("DELETE FROM detections", commit=True, fetch=False)
        execute_query("DELETE FROM uploads", commit=True, fetch=False)
        print("Existing data cleared.")

    snapshots = generate_sample_snapshots()

    cameras = [
        {"name": "Cam 01 – Zone A", "zone": "Zone A - Fabrication"},
        {"name": "Cam 02 – Zone B", "zone": "Zone B - Assembly Line"},
        {"name": "Cam 03 – Exit", "zone": "Zone C - Exit Gate"}
    ]

    statuses = ["detected", "pending review", "confirmed", "dismissed", "resolved"]
    status_weights = [0.25, 0.20, 0.30, 0.10, 0.15]

    # Create dummy uploads over the last 21 days
    now = datetime.now()
    upload_ids = []

    print("Seeding uploads and detections across 21 days...")
    for day_offset in range(21, -1, -1):
        event_date = now - timedelta(days=day_offset, hours=random.randint(1, 8))
        cam = random.choice(cameras)

        u_id = execute_insert(
            """
            INSERT INTO uploads (filename, original_name, file_type, file_path, output_path,
                                camera_name, location, uploaded_at, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'done')
            """,
            (
                f"demo_feed_d{day_offset}.jpg",
                f"site_inspection_day_{21-day_offset}.jpg",
                "image",
                f"/uploads/demo_feed_d{day_offset}.jpg",
                f"annotated_demo_d{day_offset}.jpg",
                cam["name"],
                cam["zone"],
                event_date.strftime("%Y-%m-%d %H:%M:%S")
            )
        )
        upload_ids.append((u_id, cam, event_date))

        # Detections: ~14 workers baseline, ~94.5% safe
        total_workers = 14
        safe_workers = 13 if random.random() < 0.65 else 14
        unsafe_workers = total_workers - safe_workers
        comp_rate = round((safe_workers / total_workers) * 100.0, 1)

        execute_insert(
            """
            INSERT INTO detections (upload_id, frame_no, timestamp_sec, total_people,
                                    safe_count, unsafe_count, compliance_percent, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (u_id, 0, 0.0, total_workers, safe_workers, unsafe_workers, comp_rate,
             event_date.strftime("%Y-%m-%d %H:%M:%S"))
        )

    # Required violation counts: exactly 53 violations
    # Helmet: 25, Vest: 15, Goggles: 8, Other: 5
    violation_specs = (
        [("helmet", "HIGH")] * 25 +
        [("vest", "MEDIUM")] * 15 +
        [("goggles", "MEDIUM")] * 8 +
        [("other", "LOW")] * 5
    )
    random.seed(42)  # reproducible distribution
    random.shuffle(violation_specs)

    print("Inserting exactly 53 violations (25 Helmet, 15 Vest, 8 Goggles, 5 Other)...")
    for i, (v_type, severity) in enumerate(violation_specs):
        u_id, cam, base_dt = random.choice(upload_ids)
        # Jitter the timestamp
        v_dt = base_dt + timedelta(minutes=random.randint(10, 360))
        snap = random.choice(snapshots)
        stat = random.choices(statuses, weights=status_weights)[0]
        conf = round(random.uniform(0.85, 0.98), 2)

        notes_map = {
            "helmet": "Worker identified without mandatory hardhat near scaffolding.",
            "vest": "High-visibility vest missing in active machinery zone.",
            "goggles": "Safety eyewear absent during welding/grinding area transit.",
            "other": "Personnel detected crossing marked restricted hazardous perimeter."
        }
        note = notes_map.get(v_type, "Standard safety compliance inspection note.")
        reviewer = random.choice(["Inspector Dave", "Safety Officer Miller", "AI Auditor", None])

        execute_insert(
            """
            INSERT INTO violations (upload_id, detection_id, violation_type, severity, confidence,
                                    snapshot_path, camera_name, location, status, reviewed_by,
                                    notes, detected_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                u_id,
                1,
                v_type,
                severity,
                conf,
                snap,
                cam["name"],
                cam["zone"],
                stat,
                reviewer,
                note,
                v_dt.strftime("%Y-%m-%d %H:%M:%S"),
                v_dt.strftime("%Y-%m-%d %H:%M:%S")
            )
        )

    print("Demo data seeded successfully:")
    print("  - Total violations: 53 (25 Helmet, 15 Vest, 8 Goggles, 5 Other)")
    print("  - Cameras: 3")
    print("  - Statuses: 5")
    print("  - Days covered: 21")
    print("  - Sample snapshots: 8 created")


if __name__ == "__main__":
    reset_flag = "--reset" in sys.argv
    seed_demo_data(reset=reset_flag)
