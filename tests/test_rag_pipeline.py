"""
Unit tests for RAG pipeline, unified retriever, guardrails, and visual indexer.
"""
import unittest
from app.llm.provider import LLMClient, set_llm_client
from app.rag.retriever import retrieve, Source
from app.rag.guardrails import sanitize_input, sanitize_output, verify_and_ground_answer, REFUSAL_MESSAGE
from app.rag.rag_pipeline import answer_rag_question
from app.rag.visual_indexer import search_visual_events


class TestRAGComponents(unittest.TestCase):

    def setUp(self):
        # Configure fake LLM for deterministic RAG tests
        set_llm_client(LLMClient(provider="fake"))

    def test_sanitize_input(self):
        raw = "What is the \x00 rule for \x1f welding?   "
        clean = sanitize_input(raw)
        self.assertEqual(clean, "What is the rule for welding?")

    def test_sanitize_output_removes_scripts(self):
        malicious = "Rule says wear helmet <script>alert('xss')</script> immediately."
        safe = sanitize_output(malicious)
        self.assertNotIn("<script>", safe)
        self.assertIn("wear helmet", safe)

    def test_guardrails_refusal_on_empty_sources(self):
        ans, cites, conf = verify_and_ground_answer("You should wear boots [S1]", [])
        self.assertEqual(ans, REFUSAL_MESSAGE)
        self.assertEqual(cites, [])
        self.assertEqual(conf, "Low")

    def test_guardrails_strips_invalid_citations(self):
        s1 = Source("S1", "document", "Safety Manual", "Wear safety helmet", 0.9, "doc:1")
        ans, cites, conf = verify_and_ground_answer("Wear helmet [S1] and gloves [S99]", [s1])
        self.assertIn("[S1]", ans)
        self.assertNotIn("[S99]", ans)
        self.assertEqual(len(cites), 1)

    def test_unified_retrieval(self):
        sources = retrieve("helmet", top_k=3)
        self.assertTrue(len(sources) > 0)
        self.assertEqual(sources[0].source_id, "S1")

    def test_answer_rag_question_end_to_end(self):
        res = answer_rag_question("What PPE is required for welding?", session_id="test_sess")
        self.assertIn("answer", res)
        self.assertTrue(len(res["citations"]) > 0 or res["answer"] == REFUSAL_MESSAGE)


if __name__ == "__main__":
    unittest.main()
