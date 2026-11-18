"""Test all 4 queries and print detailed outputs."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services import qa_service

test_queries = [
    'workers without safety goggles',
    'What PPE is required for welding?',
    'What violations and corrective actions are listed in sample_site_inspection_report.pdf?',
    'What hazards were found in the crane zone audit?'
]

for q in test_queries:
    print('=' * 60)
    print('QUERY:', q)
    ans = qa_service.answer_question(q)
    print('\n[ANSWER]')
    print(ans['answer'])
    print('\n[CITATIONS]')
    for c in ans['citations']:
        print(f" * [{c['doc_title']}, p.{c['page_no']}] (ID: {c['document_id']})")
        print(f"   Snippet: {c['snippet']}")
    print()
