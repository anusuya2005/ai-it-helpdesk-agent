"""
test_agent.py
-------------
Basic unit tests covering the RAG retriever and the end-to-end agent flow.

Run:
    python -m unittest discover -s tests
"""

import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.rag import TfidfRetriever, tokenize
from agent.knowledge_base import load_knowledge_base, build_document_text
from agent.agent import ITHelpdeskAgent


class TestTokenize(unittest.TestCase):
    def test_tokenize_lowercases_and_strips_stopwords(self):
        tokens = tokenize("My Wi-Fi is NOT Connecting to the router!")
        self.assertIn("wifi", tokens)
        self.assertIn("connecting", tokens)
        self.assertNotIn("is", tokens)
        self.assertNotIn("the", tokens)


class TestRetriever(unittest.TestCase):
    def setUp(self):
        self.kb = load_knowledge_base()
        docs = [build_document_text(e) for e in self.kb]
        ids = [e["id"] for e in self.kb]
        self.retriever = TfidfRetriever(docs, ids)

    def test_returns_top_k_results(self):
        results = self.retriever.query("printer not printing", top_k=3)
        self.assertEqual(len(results), 3)

    def test_relevant_document_ranks_first(self):
        results = self.retriever.query("my wifi wont connect at all", top_k=1)
        top_id = results[0][0]
        self.assertEqual(top_id, "KB001")

    def test_unrelated_query_has_low_score(self):
        results = self.retriever.query("printer not printing", top_k=1)
        wifi_score = None
        for doc_id, score, _ in self.retriever.query("wifi issue", top_k=len(self.kb)):
            if doc_id == "KB005":  # printer entry
                wifi_score = score
        self.assertIsNotNone(wifi_score)
        self.assertLess(wifi_score, 0.3)


class TestAgentEndToEnd(unittest.TestCase):
    def setUp(self):
        self.agent = ITHelpdeskAgent()
        self.session_id = f"test-{uuid.uuid4()}"

    def test_greeting_returns_intro(self):
        result = self.agent.handle_message(self.session_id, "hello")
        self.assertIn("IT Helpdesk", result["response"])

    def test_known_issue_returns_solution_steps(self):
        result = self.agent.handle_message(self.session_id, "my printer is not printing anything")
        self.assertEqual(result["category"], "Hardware")
        self.assertTrue(len(result["sources"]) > 0)
        self.assertIn("1.", result["response"])

    def test_vague_message_asks_clarifying_question(self):
        result = self.agent.handle_message(self.session_id, "zzz qwerty nonsense 12345")
        self.assertIn("more detail", result["response"].lower())

    def test_escalation_after_repeated_unresolved(self):
        session_id = f"test-escalate-{uuid.uuid4()}"
        self.agent.handle_message(session_id, "my wifi is not connecting")
        self.agent.handle_message(session_id, "still not working")
        result = self.agent.handle_message(session_id, "still not working")
        self.assertTrue(result["escalated"])
        self.assertIn("ticket", result["response"].lower())


if __name__ == "__main__":
    unittest.main()
