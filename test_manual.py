from utils.rag_service import RAGStudyAssistant
from utils.file_processor import FileProcessor

# Initialize
assistant = RAGStudyAssistant()
file_processor = FileProcessor()
documents = file_processor.load_documents()
print(f"Loaded {len(documents)} documents")

assistant.add_documents(documents)

# Test queries from different subjects
test_questions = [
    "What is algebra?",
    "What are the branches of science?",
    "What is history?",
    "What is literature?",
    "What is geography?",
    "What is computer science?",
    "What is economics?"
]

for question in test_questions:
    print(f"\nQuestion: {question}")
    response = assistant.query(question)
    print(f"Answer: {response[:200]}...")  # First 200 chars
