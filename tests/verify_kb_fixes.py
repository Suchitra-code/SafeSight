"""
Verification script for Knowledge Base fixes and test queries.
"""
import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db import execute_query
from app.services import embedder, search_service, qa_service

print('======================================================================')
print('SYSTEM AND DATABASE VERIFICATION')
print('======================================================================')

# 1. Document ID 31 Status
doc31 = execute_query('SELECT id, title, original_name, stored_name, doc_type, status, page_count FROM documents WHERE id=31')
print('1. Document ID 31 Record:')
print('  ', doc31[0] if doc31 else 'NOT FOUND')

chunks31 = execute_query('SELECT id, document_id, page_no, chunk_index, length(text) as char_len, substr(text, 1, 80) as snippet FROM doc_chunks WHERE document_id=31')
print('   Document ID 31 Chunks in DB:')
for c in (chunks31 or []):
    print('    -', c)

findings31 = execute_query('SELECT id, description, category, severity, corrective_action, due_date, status FROM report_findings WHERE document_id=31')
print('   Document ID 31 Extracted Findings in DB:')
for f in (findings31 or []):
    print('    -', f)

# 2. Total indexed chunks & Document list
all_docs = execute_query('SELECT id, title, original_name FROM documents ORDER BY id')
print(f'\n2. All Canonical Documents in DB ({len(all_docs or [])} docs):')
for d in (all_docs or []):
    print(f'   ID {d["id"]}: {d["title"]} ({d["original_name"]})')

all_chunks = execute_query('SELECT count(*) as cnt FROM doc_chunks')
print(f'   Total doc_chunks in SQLite DB: {all_chunks[0]["cnt"]}')

status = embedder.get_embedder_status()
print(f'   Total chunks in memory/meta: {status["chunk_count"]}')

# 3. Active Search Engine
print('\n3. Active Search Engine:')
print(f'   Backend Mode: {status["backend"]}')
print(f'   Is Neural (sentence-transformers + FAISS): {status["is_neural"]}')

# 4. Duplicate Filtering Status
dup_docs = execute_query('SELECT original_name, count(*) as cnt FROM documents GROUP BY original_name HAVING cnt > 1')
print('\n4. Duplicate Filtering Status:')
print(f'   Duplicate documents count in documents table: {len(dup_docs or [])}')

dup_chunks = execute_query('SELECT substr(text, 1, 80) as snip, count(*) as cnt FROM doc_chunks GROUP BY snip HAVING cnt > 1')
print(f'   Duplicate chunks count in doc_chunks table: {len(dup_chunks or [])}')

print('\n======================================================================')
print('EXECUTION OF ALL 4 TEST QUERIES (A, B, C, D)')
print('======================================================================')

queries = [
    ('A', 'workers without safety goggles'),
    ('B', 'What PPE is required for welding?'),
    ('C', 'What violations and corrective actions are listed in sample_site_inspection_report.pdf?'),
    ('D', 'What hazards were found in the crane zone audit?')
]

for label, q in queries:
    print(f'\n>>> QUERY {label}: "{q}"')
    search_res = search_service.search_knowledge(q, mode='hybrid', limit=5)
    print('--- Retrieved Document Chunks ---')
    for idx, r in enumerate(search_res.get('results', [])):
        print(f' [{idx+1}] Doc ID {r.get("document_id")}: "{r.get("doc_title")}" (p.{r.get("page_no")})')
        print(f'     Relevance Score: {r.get("score")}')
        print(f'     Snippet: {r.get("snippet")[:160]}...')

    ans = qa_service.answer_question(q)
    print('\n--- Final Synthesized Answer ---')
    print(ans.get('answer'))

    print('\n--- Exact Citations ---')
    for c in ans.get('citations', []):
        print(f' * [{c.get("doc_title")}, p.{c.get("page_no")}] (Doc ID: {c.get("document_id")})')
        print(f'   Snippet: {c.get("snippet")[:120]}...')

    # Grounded check
    retrieved_titles = [r.get('doc_title') for r in search_res.get('results', [])]
    cited_titles = [c.get('doc_title') for c in ans.get('citations', [])]
    is_grounded = all(t in retrieved_titles for t in cited_titles) if cited_titles else False
    print(f'--- Grounded in Retrieved Sources: {is_grounded} ---')
