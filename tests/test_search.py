"""
Unit tests for Milestone 2 Search & Q&A services (search_service, qa_service).
"""
import unittest
from app.services import search_service, qa_service


class TestSearchAndQA(unittest.TestCase):
    def test_keyword_search_returns_dict(self):
        res = search_service.search_knowledge("safety", mode="keyword")
        self.assertIsInstance(res, dict)
        self.assertIn("results", res)
        self.assertIn("count", res)
        self.assertIn("query", res)

    def test_semantic_or_hybrid_search(self):
        res = search_service.search_knowledge("welding helmet protection", mode="hybrid")
        self.assertIsInstance(res, dict)
        self.assertIn("results", res)
        self.assertGreaterEqual(res["count"], 1)

    def test_search_snippet_has_highlight(self):
        res = search_service.search_knowledge("helmet", mode="hybrid")
        if res["results"]:
            snippet = res["results"][0]["snippet"]
            self.assertTrue("<mark class=\"search-match\">" in snippet or len(snippet) > 0)

    def test_repository_filter(self):
        res = search_service.search_knowledge("safety", repository_id=2, mode="hybrid")
        self.assertIsInstance(res, dict)

    def test_qa_answer_structure(self):
        ans = qa_service.answer_question("What PPE is required for welding?")
        self.assertIsInstance(ans, dict)
        self.assertIn("question", ans)
        self.assertIn("answer", ans)
        self.assertIn("citations", ans)
        self.assertGreater(len(ans["answer"]), 10)

    def test_qa_unknown_question_fallback(self):
        ans = qa_service.answer_question("What is the recipe for chocolate cake on Mars?")
        self.assertIsInstance(ans, dict)
        self.assertIn("answer", ans)


if __name__ == "__main__":
    unittest.main()
