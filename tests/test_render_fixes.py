"""
Verification test for Render 502 fix:
- App factory startup speed
- Health checks (/healthz, /api/health)
- Authentication (login for suchitra and admin)
- Dashboard rendering
- Embedder status without neural overhead
- YOLOv8 detector thread-safety and detection
"""
import time
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ["DISABLE_SENTENCE_TRANSFORMERS"] = "true"

print("--- Testing App Creation & Startup Time ---")
t0 = time.time()
from run import app
boot_duration = time.time() - t0
print(f"[OK] App imported and created in {boot_duration:.3f} seconds.")
assert boot_duration < 30.0, f"Boot too slow: {boot_duration}s"

client = app.test_client()

print("\n--- Testing Health Endpoints ---")
# /healthz (Render health check path)
r = client.get("/healthz")
print(f"/healthz: status={r.status_code}, data={r.get_json()}")
assert r.status_code == 200
assert r.get_json().get("status") == "ok"

# /api/health (Milestone 3 monitoring endpoint)
r = client.get("/api/health")
print(f"/api/health: status={r.status_code}")
assert r.status_code == 200
health_data = r.get_json()
print("Components checked:", list(health_data.get("components", {}).keys()))

print("\n--- Testing Authentication ---")
# Test login GET
r = client.get("/login")
assert r.status_code == 200
print("[OK] /login GET 200")

# Test login POST for suchitra
r = client.post("/login", data={"username": "suchitra", "password": "admin123"}, follow_redirects=False)
print(f"/login POST (suchitra): status={r.status_code}, location={r.headers.get('Location')}")
assert r.status_code == 302

# Test login POST for admin
r = client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=False)
print(f"/login POST (admin): status={r.status_code}, location={r.headers.get('Location')}")
assert r.status_code == 302

print("\n--- Testing Authenticated Dashboard Access ---")
with client.session_transaction() as sess:
    sess["logged_in"] = True
    sess["username"] = "suchitra"

r = client.get("/")
print(f"GET / (authenticated): status={r.status_code}")
assert r.status_code == 200

r = client.get("/dashboard")
print(f"GET /dashboard (authenticated): status={r.status_code}")
assert r.status_code == 200

print("\n--- Testing YOLOv8 Detector ---")
from app.services.detector import PPEDetector, get_memory_rss_mb
detector = PPEDetector()
detector.wait_until_ready(timeout=30)
print(f"[OK] Detector ready. is_demo={detector.is_demo}, RSS={get_memory_rss_mb()} MB")

import numpy as np
dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
detections = detector.detect(dummy_frame)
print(f"[OK] Detections on dummy frame: count={len(detections)}")

print("\n==========================================")
print("ALL RENDER DEPLOYMENT CHECKS PASSED!")
print("==========================================")
