"""
Unit tests for Milestone 2 Chunker (chunker.py).
"""
import unittest
from app.services.chunker import chunk_document


class TestChunker(unittest.TestCase):
    def setUp(self):
        paras = [
            f"Paragraph {i}: Safety regulations mandate all personnel wear PPE. "
            f"Hard hats, high-visibility vests, and safety boots are required at all times. "
            f"Failure to comply will result in immediate removal from the active work site. "
            for i in range(1, 15)
        ]
        self.long_text = "\n\n".join(paras)
        self.pages = [
            {"page_no": 1, "text": self.long_text[:len(self.long_text)//2]},
            {"page_no": 2, "text": self.long_text[len(self.long_text)//2:]}
        ]

    def test_chunking_creates_chunks(self):
        chunks = chunk_document(1, 1, self.pages, target_words=100, overlap_words=20)
        self.assertGreater(len(chunks), 1)

    def test_chunk_fields(self):
        chunks = chunk_document(1, 1, self.pages, target_words=100, overlap_words=20)
        first = chunks[0]
        self.assertIn("chunk_index", first)
        self.assertIn("text", first)
        self.assertIn("page_no", first)
        self.assertEqual(first["chunk_index"], 0)

    def test_chunk_page_attribution(self):
        chunks = chunk_document(1, 1, self.pages, target_words=80, overlap_words=15)
        pages_found = {c["page_no"] for c in chunks}
        self.assertIn(1, pages_found)
        self.assertIn(2, pages_found)

    def test_overlap_between_adjacent_chunks(self):
        chunks = chunk_document(1, 1, self.pages, target_words=80, overlap_words=20)
        if len(chunks) >= 2:
            chunk1_words = set(chunks[0]["text"].split()[-10:])
            chunk2_words = set(chunks[1]["text"].split()[:15])
            self.assertTrue(len(chunk1_words.intersection(chunk2_words)) > 0)

    def test_empty_or_tiny_page(self):
        tiny_pages = [{"page_no": 1, "text": "Short notice."}]
        chunks = chunk_document(1, 1, tiny_pages)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["text"], "Short notice.")


if __name__ == "__main__":
    unittest.main()
