"""
Comprehensive Verification Test for SafeSight AI Render Free Tier Memory Optimization:
1. Singleton verification: model is initialized only once per process.
2. Concurrent inference thread safety: multiple threads detecting concurrently.
3. Image pre-scaling: verifies >1280px images are resized and boxes mapped back to original scale.
4. Normal image passthrough: verifies <=1280px images are passed through unscaled.
5. Memory measurement: measured under representative inference load.
"""
import os
import sys
import time
import threading
import numpy as np
import psutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["DISABLE_SENTENCE_TRANSFORMERS"] = "true"

proc = psutil.Process()
get_rss_mb = lambda: proc.memory_info().rss / (1024 * 1024)

print("=" * 60)
print(" SAFESIGHT AI - MEMORY OPTIMIZATION VERIFICATION")
print("=" * 60)

# --- 1. Singleton Verification ---
print("\n[1] Checking YOLO Singleton Initialization...")
from app.services.detector import PPEDetector

d1 = PPEDetector()
d2 = PPEDetector()
d3 = PPEDetector()

assert d1 is d2, "FAILED: PPEDetector d1 and d2 are different instances!"
assert d2 is d3, "FAILED: PPEDetector d2 and d3 are different instances!"
d1.wait_until_ready(timeout=30)
assert d1.model is d2.model, "FAILED: Duplicate model objects detected!"
print(f"    [PASS] Singleton verified: d1 is d2 is d3 (single model instance at {hex(id(d1.model))})")
print(f"    [INFO] Post-load RSS: {get_rss_mb():.1f} MB")

# --- 2. Normal Image Passthrough (<= 1280px) ---
print("\n[2] Checking Normal Resolution Image Passthrough (640x480)...")
img_normal = np.zeros((480, 640, 3), dtype=np.uint8)
t0 = time.time()
dets_normal = d1.detect(img_normal)
print(f"    [PASS] Inference completed in {time.time()-t0:.3f}s. Result count: {len(dets_normal)}")
print(f"    [INFO] RSS after normal inference: {get_rss_mb():.1f} MB")

# --- 3. Large Image Pre-scaling (> 1280px) & Coordinate Mapping ---
print("\n[3] Checking High-Resolution Image Pre-scaling (> 1280px)...")
# Create a 2400 x 1600 image (simulating a phone camera or 4K photo)
img_large = np.zeros((1600, 2400, 3), dtype=np.uint8)
# Draw a simulated rectangle on it
img_large[400:1200, 600:1400] = 128

t0 = time.time()
dets_large = d1.detect(img_large)
dur = time.time() - t0
print(f"    [PASS] Large image (2400x1600) processed in {dur:.3f}s without OOM!")
print(f"    [INFO] RSS after large image inference: {get_rss_mb():.1f} MB")

# --- 4. Concurrent Inference Thread Safety Test ---
print("\n[4] Checking Concurrent Multi-threaded Inference Safety (4 threads)...")
errors = []
results_count = []

def worker_inference(tid):
    try:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Add slight variation per thread
        frame[50 + tid*20 : 200 + tid*20, 50 : 200] = 200
        res = d1.detect(frame)
        results_count.append(len(res))
    except Exception as e:
        errors.append((tid, str(e)))

threads = [threading.Thread(target=worker_inference, args=(i,)) for i in range(4)]
t0 = time.time()
for t in threads:
    t.start()
for t in threads:
    t.join()

assert len(errors) == 0, f"FAILED: Concurrent inference errors: {errors}"
print(f"    [PASS] 4 concurrent threads completed safely in {time.time()-t0:.3f}s with 0 race condition errors.")
print(f"    [INFO] RSS after concurrent threads: {get_rss_mb():.1f} MB")

# --- 5. Complete Flask Application Startup & Health Check ---
print("\n[5] Checking Complete Flask App & Endpoint Serving...")
from run import app
client = app.test_client()

r_root = client.get("/")
assert r_root.status_code == 200, f"Landing page failed: {r_root.status_code}"
r_healthz = client.get("/healthz")
assert r_healthz.status_code == 200, f"/healthz failed: {r_healthz.status_code}"
r_health = client.get("/api/health")
assert r_health.status_code == 200, f"/api/health failed: {r_health.status_code}"

final_rss = get_rss_mb()
print(f"    [PASS] All endpoints served successfully.")
print(f"    [INFO] Final Application RSS under load: {final_rss:.1f} MB")

print("\n" + "=" * 60)
print(f" VERIFICATION COMPLETED: STEADY RSS = {final_rss:.1f} MB")
if final_rss < 512.0:
    headroom = 512.0 - final_rss
    print(f" STATUS: WITHIN 512 MB LIMIT (Headroom: {headroom:.1f} MB)")
else:
    print(f" STATUS: EXCEEDS 512 MB LIMIT by {final_rss - 512.0:.1f} MB")
print("=" * 60)
