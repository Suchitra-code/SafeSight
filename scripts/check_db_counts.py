"""Quick DB count verification for violation summary math."""
import sqlite3, pathlib, sys

db_path = pathlib.Path(__file__).resolve().parent.parent / "database" / "safesight_fallback.db"
if not db_path.exists():
    print("DB not found at", db_path)
    sys.exit(1)

con = sqlite3.connect(str(db_path))
t   = con.execute("SELECT COUNT(*) FROM violations").fetchone()[0]
p   = con.execute("SELECT COUNT(*) FROM violations WHERE status IN ('detected','pending review')").fetchone()[0]
rev = con.execute("SELECT COUNT(*) FROM violations WHERE status IN ('confirmed','dismissed')").fetchone()[0]
res = con.execute("SELECT COUNT(*) FROM violations WHERE status = 'resolved'").fetchone()[0]
hist= con.execute("SELECT COUNT(*) FROM violation_status_history").fetchone()[0]
print(f"total={t}  pending={p}  reviewed={rev}  resolved={res}  sum={p+rev+res}  match={p+rev+res==t}")
print(f"violation_status_history rows={hist}")
if p + rev + res != t:
    print("MISMATCH — counts do not add up!")
    sys.exit(1)
else:
    print("OK — pending + reviewed + resolved == total")
