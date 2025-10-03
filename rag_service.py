import os
import torch
from transformers import pipeline
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pickle
from dotenv import load_dotenv
from huggingface_hub import login
from utils.note_generator import NoteGenerator

load_dotenv()

class RAGStudyAssistant:
    def __init__(self):
        # Use CPU to avoid PyTorch CUDA compatibility issues
        device = 'cpu'
        try:
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2', device=device)
            self.device = device
        except Exception as e:
            print(f"Warning: Failed to initialize embedder: {e}")
            print("Embedder will be None - some features may not work.")
            self.embedder = None
            self.device = 'cpu'
        # Login to Hugging Face using API key from environment variable
        hf_api_key = os.getenv('HUGGINGFACE_API_KEY')
        if hf_api_key:
            login(token=hf_api_key)
        # Try to load a powerful public model for educational QA
        try:
            self.qa_pipeline = pipeline(
                "text2text-generation",
                model="google/flan-t5-base",
                device_map="auto" if torch.cuda.is_available() else "cpu"
            )
        except Exception as e:
            print(f"Warning: Failed to load model google/flan-t5-base: {e}")
            print("Falling back to public model 'gpt2'")
            try:
                self.qa_pipeline = pipeline(
                    "text-generation",
                    model="gpt2",
                    device_map="auto" if torch.cuda.is_available() else "cpu"
                )
            except Exception as e2:
                print(f"Warning: Failed to load fallback model gpt2: {e2}")
                self.qa_pipeline = None
        self.vector_index = None
        self.documents = []
        self.note_generator = NoteGenerator()
        self.chunk_size = 2000  # words
        self.chunk_overlap = 200  # words
    
    def _chunk_text(self, text):
        """Split text into chunks with overlap"""
        words = text.split()
        chunks = []
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk = words[i:i + self.chunk_size]
            if chunk:
                chunks.append(' '.join(chunk))
        return chunks
    
    def add_documents(self, documents):
        """Add documents to knowledge base with chunking and batch embedding"""
        if not documents:
            return
        all_chunks = []
        for doc in documents:
            chunks = self._chunk_text(doc)
            all_chunks.extend(chunks)
        self.documents.extend(all_chunks)

        batch_size = 100
        embeddings_list = []
        for i in range(0, len(all_chunks), batch_size):
            batch_chunks = all_chunks[i:i+batch_size]
            try:
                batch_embeddings = self.embedder.encode(batch_chunks)
                embeddings_list.append(batch_embeddings)
            except Exception as e:
                print(f"Error embedding batch starting at index {i}: {e}")
                # Optionally skip or break here

        if not embeddings_list:
            print("No embeddings generated due to errors.")
            return

        embeddings = np.vstack(embeddings_list)

        if self.vector_index is None:
            self.vector_index = faiss.IndexFlatL2(embeddings.shape[1])
        self.vector_index.add(embeddings.astype('float32'))
    
    def query(self, question, context_texts=None, answer_format="full"):
        """Query the knowledge base with answer format options"""
        if context_texts:
            # Use provided context texts, chunk them if necessary
            all_chunks = []
            for text in context_texts:
                chunks = self._chunk_text(text)
                all_chunks.extend(chunks)
            context = "\n".join(all_chunks)  # Use all chunks
        else:
            if self.vector_index is None or len(self.documents) == 0:
                return "Please upload some study materials first!"
            if self.qa_pipeline is None:
                return "QA model is not loaded properly."
            
            # Semantic search
            question_embedding = self.embedder.encode([question])
            D, I = self.vector_index.search(question_embedding.astype('float32'), 30)  # Retrieve top 30 chunks

            if len(I[0]) == 0:
                return "No relevant documents found."

            # Build context
            context = "\n".join([self.documents[i] for i in I[0]])

        # Adjust prompt based on answer_format
        format_instructions = {
            "full": "You are a helpful AI study assistant. Answer the question in a friendly, conversational tone, providing detailed information from the context as if explaining to a curious student.",
            "short_summary": "You are a helpful AI study assistant. Provide a concise summary of the key points from the context in 2-3 sentences, in a friendly and engaging way.",
            "bullet_points": "You are a helpful AI study assistant. Extract and present the main information from the context in clear bullet points, making it easy and fun to read.",
            "long_answer": "You are a helpful AI study assistant. Provide a long and detailed answer, elaborating on all relevant aspects from the context in a conversational manner, like chatting with a student.",
            "one_word": "You are a helpful AI study assistant. Provide a single word answer based on the context, keeping it straightforward.",
            "short_answer": "You are a helpful AI study assistant. Provide a brief answer in one or two sentences based on the context, in a friendly tone."
        }
        instruction = format_instructions.get(answer_format, "Answer in full sentences and in detail.")

        prompt = f"{instruction} Based on the provided context, answer the following educational question accurately. Context: {context} Question: {question}"

        # Adjust max length based on format
        max_len = {
            "full": 2048,
            "short_summary": 1024,
            "bullet_points": 1024,
            "long_answer": 2048,
            "one_word": 20,
            "short_answer": 1024
        }.get(answer_format, 2048)

        try:
            if self.qa_pipeline.task == "text2text-generation":
                response = self.qa_pipeline(
                    prompt,
                    max_length=max_len,
                    do_sample=True,
                    temperature=0.7
                )
                generated_text = response[0].get('generated_text', '')
                return generated_text
            else:
                response = self.qa_pipeline(
                    prompt,
                    max_new_tokens=max_len,
                    temperature=0.7,
                    do_sample=True
                )
                generated_text = response[0].get('generated_text', '')
                return generated_text.replace(prompt, "")
        except Exception as e:
            return f"Error during generation: {e}"

    def generate_notes(self, topic):
        """Generate notes for a given topic"""
        if self.vector_index is None or len(self.documents) == 0:
            return "Please upload some study materials first!"
        if self.qa_pipeline is None:
            return "QA model is not loaded properly."

        question_embedding = self.embedder.encode([topic])
        D, I = self.vector_index.search(question_embedding.astype('float32'), 30)  # More chunks for notes

        if len(I[0]) == 0:
            return "No relevant documents found for notes generation."

        context = "\n".join([self.documents[i] for i in I[0]])
        prompt = f"Generate detailed study notes on the following topic based on the context:\n\nContext: {context}\n\nTopic: {topic}\n\nNotes:"
        try:
            if self.qa_pipeline.task == "text2text-generation":
                response = self.qa_pipeline(
                    prompt,
                    max_length=2048,
                    do_sample=True,
                    temperature=0.7
                )
                generated_text = response[0].get('generated_text', '')
                return generated_text
            else:
                response = self.qa_pipeline(
                    prompt,
                    max_new_tokens=2048,
                    temperature=0.7,
                    do_sample=True
                )
                generated_text = response[0].get('generated_text', '')
                return generated_text.replace(prompt, "")
        except Exception as e:
            return f"Error during notes generation: {e}"

    def export_notes(self, notes, filename, format):
        """Export notes to specified format"""
        format = format.lower()
        if format == 'txt':
            self.note_generator.export_txt(notes, filename)
        elif format == 'pdf':
            self.note_generator.export_pdf(notes, filename)
        elif format == 'word':
            self.note_generator.export_word(notes, filename)
        elif format == 'json':
            self.note_generator.export_json(notes, filename)
        elif format == 'excel':
            self.note_generator.export_excel(notes, filename)
        elif format == 'chart':
            self.note_generator.export_chart(notes, filename)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def generate_flashcards(self, content=None):
        """Generate flashcards from documents or specific content"""
        if self.qa_pipeline is None:
            return []

        if content is not None:
            # Generate from specific content
            chunks = self._chunk_text(content)
            context = "\n".join(chunks[:30])  # Use first 30 chunks instead of 10
        else:
            # Generate from all documents
            if self.vector_index is None or len(self.documents) == 0:
                return []
            context = "\n".join(self.documents[:30])  # Use first 30 chunks instead of 10

        # Limit context length by tokens approximately (assuming 1 token ~ 4 chars)
        max_context_chars = 2048 * 4  # 2048 tokens approx
        if len(context) > max_context_chars:
            context = context[:max_context_chars] + "..."

        print(f"Flashcard generation context length: {len(context)}")  # Debug print

        prompt = f"Generate 5 flashcards from the following study material. Each flashcard must have a question and answer. Format your response exactly like this example:\n\nFlashcard 1:\nQuestion: What is the capital of France?\nAnswer: Paris\n\nFlashcard 2:\nQuestion: What is 2+2?\nAnswer: 4\n\nFlashcard 3:\nQuestion: What is the color of the sky?\nAnswer: Blue\n\nFlashcard 4:\nQuestion: What is the largest planet?\nAnswer: Jupiter\n\nFlashcard 5:\nQuestion: What is water made of?\nAnswer: Hydrogen and oxygen\n\nContext: {context}\n\nFlashcards:"

        try:
            if self.qa_pipeline.task == "text2text-generation":
                response = self.qa_pipeline(
                    prompt,
                    max_length=2048,
                    do_sample=True,
                    temperature=0.7
                )
                generated_text = response[0].get('generated_text', '')
            else:
                response = self.qa_pipeline(
                    prompt,
                    max_new_tokens=2048,
                    temperature=0.7,
                    do_sample=True
                )
                generated_text = response[0].get('generated_text', '')
                generated_text = generated_text.replace(prompt, "")

            print(f"Generated text for flashcards: {generated_text}")  # Debug print

            # Parse the generated text
            flashcards = []
            # Normalize line endings
            normalized_text = generated_text.replace('\r\n', '\n').replace('\r', '\n')
            print(f"Normalized generated text: {normalized_text}")  # Debug print

            # Try parsing as Flashcard format first
            parts = normalized_text.split("Flashcard ")
            print(f"Number of parts after splitting on 'Flashcard ': {len(parts)}")  # Debug print

            if len(parts) > 1:
                # Use Flashcard format parsing
                for part in parts[1:]:  # Skip the first empty part
                    lines = part.split('\n')
                    print(f"Lines in part: {lines}")  # Debug print
                    if len(lines) >= 3:
                        question_line = [line for line in lines if line.lower().startswith("question:")]
                        answer_line = [line for line in lines if line.lower().startswith("answer:")]
                        if question_line and answer_line:
                            question = question_line[0][len("question:"):].strip()
                            answer = answer_line[0][len("answer:"):].strip()
                            print(f"Extracted question: '{question}', answer: '{answer}'")  # Debug print
                            if question and answer:
                                flashcards.append({
                                    'question': question,
                                    'answer': answer,
                                    'review_count': 0,
                                    'last_reviewed': None
                                })
            else:
                # Fallback: parse as direct Question/Answer format
                print("Falling back to direct Question/Answer parsing")  # Debug print
                # Split by "Question:" to find multiple questions
                question_parts = normalized_text.split("Question:")
                for part in question_parts[1:]:  # Skip first part before first "Question:"
                    # Find the end of this question-answer pair
                    answer_start = part.lower().find("answer:")
                    if answer_start != -1:
                        question = part[:answer_start].strip()
                        remaining = part[answer_start + len("answer:"):].strip()
                        # Find the end of this answer (next "Question:" or end)
                        next_question = remaining.lower().find("question:")
                        if next_question != -1:
                            answer = remaining[:next_question].strip()
                        else:
                            answer = remaining.strip()
                        print(f"Fallback extracted question: '{question}', answer: '{answer}'")  # Debug print
                        if question and answer:
                            flashcards.append({
                                'question': question,
                                'answer': answer,
                                'review_count': 0,
                                'last_reviewed': None
                            })

            print(f"Total flashcards parsed: {len(flashcards)}")  # Debug print
            return flashcards[:5]  # Limit to 5 flashcards
        except Exception as e:
            print(f"Error generating flashcards: {e}")
            return []
