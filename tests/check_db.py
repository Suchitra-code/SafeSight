"""Quick DB inspection script."""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

conn = sqlite3.connect('database/safesight_fallback.db')
conn.row_factory = sqlite3.Row

cur = conn.cursor()

# Chunks
cur.execute('SELECT id, document_id, page_no, substr(text, 1, 150) as txt FROM doc_chunks ORDER BY id')
rows = cur.fetchall()
print(f'=== doc_chunks: {len(rows)} total ===')
for r in rows:
    print(f'  id={r["id"]} doc_id={r["document_id"]} page={r["page_no"]}')
    print(f'    text: {repr(r["txt"])}')

# Documents
cur.execute('SELECT id, title, original_name, doc_type, processing_status FROM documents ORDER BY id')
docs = cur.fetchall()
print(f'\n=== documents: {len(docs)} total ===')
for d in docs:
    print(f'  id={d["id"]} type={d["doc_type"]} status={d["processing_status"]} name={d["original_name"]}')

# Report findings
cur.execute('SELECT id, document_id, finding_id, description, severity, corrective_action FROM report_findings ORDER BY document_id, id')
findings = cur.fetchall()
print(f'\n=== report_findings: {len(findings)} total ===')
for f in findings:
    print(f'  id={f["id"]} doc_id={f["document_id"]} fid={f["finding_id"]} sev={f["severity"]} desc={repr(f["description"][:80])}')

conn.close()
print('\nDone.')
