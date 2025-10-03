import unittest
from utils.rag_service import RAGStudyAssistant
from utils.file_processor import FileProcessor

class TestRAGStudyAssistant(unittest.TestCase):
    def setUp(self):
        self.assistant = RAGStudyAssistant()
        self.file_processor = FileProcessor()
        self.documents = self.file_processor.load_documents()
        self.assistant.add_documents(self.documents)

    def test_instantiation(self):
        self.assertIsNotNone(self.assistant)
        self.assertIsNotNone(self.assistant.embedder)
        self.assertIsNotNone(self.assistant.qa_pipeline)

    def test_add_documents(self):
        initial_count = len(self.assistant.documents)
        self.assistant.add_documents(["Sample document for testing."])
        self.assertEqual(len(self.assistant.documents), initial_count + 1)

    def test_query(self):
        question = "What is mathematics?"
        response = self.assistant.query(question)
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)

if __name__ == "__main__":
    unittest.main()
