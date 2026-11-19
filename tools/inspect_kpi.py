import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.db import execute_query

def main():
    inspections = execute_query("SELECT COUNT(*) as c FROM uploads", fetch=True)[0]["c"]
    total_v = execute_query("SELECT COUNT(*) as c FROM violations", fetch=True)[0]["c"]
    resolved_v = execute_query("SELECT COUNT(*) as c FROM violations WHERE LOWER(status) = 'resolved'", fetch=True)[0]["c"]
    statuses = execute_query("SELECT status, COUNT(*) as c FROM violations GROUP BY status", fetch=True)
    det = execute_query("SELECT SUM(total_people) as p, SUM(safe_count) as s, SUM(unsafe_count) as u FROM detections", fetch=True)[0]

    print("Total Inspections (uploads):", inspections)
    print("Total Violations:", total_v)
    print("Resolved Violations:", resolved_v)
    print("Violation Statuses:", statuses)
    print("Detections (people, safe, unsafe):", det)

if __name__ == "__main__":
    main()
