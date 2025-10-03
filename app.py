import streamlit as st
import os
import tempfile
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.rag_service import RAGStudyAssistant
from utils.file_processor import FileProcessor
from utils.speech_service import SpeechService

# Page configuration
st.set_page_config(
    page_title="StudyMate AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #4B0082;
        text-align: center;
        margin-bottom: 2rem;
    }
    .feature-card {
        padding: 1.5rem;
        border-radius: 10px;
        background-color: #f0f2f6;
        margin: 1rem 0;
        border-left: 4px solid #4B0082;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .user-message {
        background-color: #e6f3ff;
        border-left: 4px solid #0066cc;
    }
    .ai-message {
        background-color: #f0f8f0;
        border-left: 4px solid #00cc66;
    }
    .streak-counter {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

class StudyMateApp:
    def __init__(self):
        self.initialize_session_state()
        self.rag_assistant = RAGStudyAssistant()
        self.doc_processor = FileProcessor()
        self.speech_service = SpeechService()
    
    def initialize_session_state(self):
        """Initialize all session state variables"""
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        if 'documents' not in st.session_state:
            st.session_state.documents = []
        if 'study_sessions' not in st.session_state:
            st.session_state.study_sessions = []
        if 'flashcards' not in st.session_state:
            st.session_state.flashcards = []
        if 'current_streak' not in st.session_state:
            st.session_state.current_streak = 0
        if 'last_study_date' not in st.session_state:
            st.session_state.last_study_date = None
        if 'focus_timer' not in st.session_state:
            st.session_state.focus_timer = None
    
    def render_sidebar(self):
        """Render the sidebar with navigation and user info"""
        with st.sidebar:
            st.markdown('<h2 style="text-align: center;">🎓 StudyMate AI</h2>', 
                       unsafe_allow_html=True)
            
            # Navigation
            page = st.radio(
                "Navigate to:",
                ["🏠 Dashboard", "💬 Study Chat", "📚 Documents", "🎤 Voice Notes", 
                 "📊 Progress", "🎯 Focus Mode", "🃏 Flashcards"]
            )
            
            # Streak counter
            self.render_streak_counter()
            
            # Quick stats
            st.markdown("---")
            st.subheader("Quick Stats")
            total_study = sum(session['duration'] for session in st.session_state.study_sessions)
            st.metric("Total Study Time", f"{total_study} min")
            st.metric("Documents", len(st.session_state.documents))
            st.metric("Chat Sessions", len([m for m in st.session_state.messages if m['role'] == 'user']))
            
            # Study reminder
            self.render_study_reminder()
            
        return page
    
    def render_streak_counter(self):
        """Render the study streak counter"""
        today = datetime.now().date()
        last_study = st.session_state.last_study_date
        
        if last_study and last_study == today:
            # Already studied today
            pass
        elif last_study and last_study == today - timedelta(days=1):
            # Continuing streak
            st.session_state.current_streak += 1
            st.session_state.last_study_date = today
        elif last_study and last_study < today - timedelta(days=1):
            # Broken streak
            st.session_state.current_streak = 1
            st.session_state.last_study_date = today
        else:
            # First time
            st.session_state.current_streak = 1
            st.session_state.last_study_date = today
        
        st.markdown(f"""
        <div class="streak-counter">
            <h3>🔥 Study Streak</h3>
            <h1>{st.session_state.current_streak} days</h1>
            <p>Keep going!</p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_study_reminder(self):
        """Render study reminders based on progress"""
        if st.session_state.study_sessions:
            recent_sessions = [s for s in st.session_state.study_sessions 
                             if s['timestamp'].date() >= datetime.now().date() - timedelta(days=7)]
            if len(recent_sessions) < 3:
                st.warning("💡 Try to study at least 3 times this week!")
    
    def render_dashboard(self):
        """Render the main dashboard"""
        st.markdown('<h1 class="main-header">🎓 StudyMate AI Dashboard</h1>', 
                   unsafe_allow_html=True)
        
        # Quick actions
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🚀 Start Study Session", use_container_width=True):
                st.session_state.current_page = "🎯 Focus Mode"
                st.rerun()
        
        with col2:
            if st.button("💬 Ask Study Question", use_container_width=True):
                st.session_state.current_page = "💬 Study Chat"
                st.rerun()
        
        with col3:
            if st.button("📚 Upload Materials", use_container_width=True):
                st.session_state.current_page = "📚 Documents"
                st.rerun()
        
        with col4:
            if st.button("📊 View Progress", use_container_width=True):
                st.session_state.current_page = "📊 Progress"
                st.rerun()
        
        # Recent activity
        st.markdown("---")
        col1, col2 = st.columns([2, 1])
        
        with col1:
            self.render_recent_activity()
        
        with col2:
            self.render_quick_tips()
    
    def render_recent_activity(self):
        """Render recent study activity"""
        st.subheader("📈 Recent Activity")
        
        if st.session_state.study_sessions:
            # Create activity chart
            df = pd.DataFrame(st.session_state.study_sessions)
            df['date'] = df['timestamp'].dt.date
            daily_study = df.groupby('date')['duration'].sum().reset_index()
            
            fig = px.bar(daily_study, x='date', y='duration', 
                        title="Daily Study Time (minutes)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No study sessions recorded yet. Start studying to see your progress!")
    
    def render_quick_tips(self):
        """Render AI-powered study tips"""
        st.subheader("💡 Study Tips")
        
        tips = [
            "Break study sessions into 25-minute chunks with 5-minute breaks",
            "Teach what you've learned to someone else (or the AI!)",
            "Create flashcards for key concepts",
            "Review material within 24 hours of learning",
            "Connect new information to what you already know"
        ]
        
        for i, tip in enumerate(tips):
            st.markdown(f"**{i+1}.** {tip}")
    
    def render_study_chat(self):
        """Render the AI study chat interface"""
        st.header("💬 AI Study Assistant")

        # New Chat button
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("Chat with StudyMate")
        with col2:
            if st.button("🆕 New Chat", use_container_width=True):
                st.session_state.messages = []
                st.rerun()

        # Document context selector
        if st.session_state.documents:
            selected_docs = st.multiselect(
                "Select documents for context:",
                options=[doc['name'] for doc in st.session_state.documents],
                default=[doc['name'] for doc in st.session_state.documents[:3]]
            )
            # Get the content of selected documents for context
            context_texts = [doc['content'] for doc in st.session_state.documents if doc['name'] in selected_docs]
        else:
            st.info("📚 Upload documents first to get contextual answers!")
            context_texts = []

        # Chat messages
        chat_container = st.container()

        with chat_container:
            for message in st.session_state.messages:
                message_class = "user-message" if message["role"] == "user" else "ai-message"
                st.markdown(f"""
                <div class="chat-message {message_class}">
                    <strong>{'You' if message['role'] == 'user' else 'StudyMate'}:</strong><br>
                    {message['content']}
                </div>
                """, unsafe_allow_html=True)

        # Chat input
        with st.form("chat_input", clear_on_submit=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                user_input = st.text_input("Ask a study question:", placeholder="e.g., Explain quantum physics...")
            with col2:
                submitted = st.form_submit_button("Send 🚀")

            # Add answer format selector
            answer_format = st.selectbox(
                "Select answer format:",
                options=[
                    ("Full sentences (detailed)", "full"),
                    ("Short summary", "short_summary"),
                    ("Bullet points", "bullet_points"),
                    ("Long answer", "long_answer"),
                    ("One word answer", "one_word"),
                    ("Short answer", "short_answer")
                ],
                format_func=lambda x: x[0],
                index=0
            )[1]

            if submitted and user_input:
                # Add user message
                st.session_state.messages.append({"role": "user", "content": user_input})

                # Get AI response with context and format
                with st.spinner("🤔 Thinking..."):
                    try:
                        response = self.rag_assistant.query(user_input, context_texts, answer_format=answer_format)
                        st.session_state.messages.append({"role": "assistant", "content": response})

                        # Record study session
                        self.record_study_session("Chat Interaction", 5)

                    except Exception as e:
                        st.error(f"Error getting response: {str(e)}")

                st.rerun()
    
    def render_documents_page(self):
        """Render document upload and management"""
        st.header("📚 Study Materials")
        
        # File upload
        uploaded_files = st.file_uploader(
            "Upload study materials",
            type=['pdf', 'txt', 'docx', 'png', 'jpg', 'jpeg'],
            accept_multiple_files=True,
            help="Supported formats: PDF, TXT, DOCX, Images"
        )
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                with st.spinner(f"Processing {uploaded_file.name}..."):
                    try:
                        # Save and process file
                        with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            text_content = self.doc_processor.process_file(tmp_file.name)
                        
                        # Add to knowledge base
                        self.rag_assistant.add_documents([text_content])

                        # Store document info
                        st.session_state.documents.append({
                            'name': uploaded_file.name,
                            'content': text_content,
                            'upload_time': datetime.now()
                        })

                        # Automatically generate flashcards from the new document
                        try:
                            st.write(f"Debug: Content length passed to generate_flashcards: {len(text_content)}")
                            new_flashcards = self.rag_assistant.generate_flashcards(content=text_content)
                            st.session_state.flashcards.extend(new_flashcards)
                            st.info(f"🃏 Generated {len(new_flashcards)} flashcards from {uploaded_file.name}")
                            if new_flashcards:
                                st.subheader(f"🃏 Generated Flashcards from {uploaded_file.name}")
                                for i, card in enumerate(new_flashcards, 1):
                                    with st.expander(f"Flashcard {i}"):
                                        st.write(f"**Question:** {card['question']}")
                                        st.write(f"**Answer:** {card['answer']}")
                        except Exception as e:
                            st.warning(f"Could not generate flashcards from {uploaded_file.name}: {str(e)}")

                        st.success(f"✅ {uploaded_file.name} processed successfully!")
                        
                    except Exception as e:
                        st.error(f"❌ Error processing {uploaded_file.name}: {str(e)}")
        
        # Document list
        if st.session_state.documents:
            st.subheader("Your Documents")
            for doc in st.session_state.documents:
                with st.expander(f"📄 {doc['name']}"):
                    preview = doc['content'][:500] + "..." if len(doc['content']) > 500 else doc['content']
                    st.write(f"**Preview:** {preview}")
                    st.write(f"**Uploaded:** {doc['upload_time'].strftime('%Y-%m-%d %H:%M')}")
                    
                    # Use unique key by appending upload time timestamp to avoid duplicates
                    unique_key = f"remove_{doc['name']}_{doc['upload_time'].timestamp()}"
                    if st.button(f"Remove {doc['name']}", key=unique_key):
                        st.session_state.documents.remove(doc)
                        st.rerun()
    
    def render_voice_notes(self):
        """Render voice note functionality"""
        st.header("🎤 Voice Notes")

        # Tabs for different input methods
        tab1, tab2 = st.tabs(["🎙️ Record Voice Note", "📤 Upload Voice File"])

        with tab1:
            st.subheader("Record Voice Note")
            audio_data = st.audio_input("Record your study notes:")

            if audio_data:
                with st.spinner("Processing audio..."):
                    try:
                        text = self.speech_service.speech_to_text(audio_data)
                        st.text_area("Transcribed Text:", text, height=150, key="record_text")

                        if st.button("Save to Notes", key="save_record"):
                            st.session_state.messages.append({
                                "role": "user",
                                "content": f"Voice Note: {text}"
                            })
                            st.success("Note saved!")

                    except Exception as e:
                        st.error(f"Error processing audio: {str(e)}")

        with tab2:
            st.subheader("Upload Voice Note")
            uploaded_audio = st.file_uploader(
                "Upload an audio file",
                type=['wav', 'mp3', 'flac', 'ogg'],
                help="Supported formats: WAV, MP3, FLAC, OGG"
            )

            if uploaded_audio:
                with st.spinner("Processing uploaded audio..."):
                    try:
                        # Save uploaded file temporarily
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_audio.name.split('.')[-1]}") as tmp_file:
                            tmp_file.write(uploaded_audio.getvalue())
                            tmp_file_path = tmp_file.name

                        # Transcribe
                        text = self.speech_service.speech_to_text(tmp_file_path)
                        st.text_area("Transcribed Text:", text, height=150, key="upload_text")

                        if st.button("Save to Notes", key="save_upload"):
                            st.session_state.messages.append({
                                "role": "user",
                                "content": f"Voice Note: {text}"
                            })
                            st.success("Note saved!")

                        # Clean up temp file
                        os.unlink(tmp_file_path)

                    except Exception as e:
                        st.error(f"Error processing audio: {str(e)}")

        # Voice Commands section
        st.markdown("---")
        st.subheader("Voice Commands")
        st.markdown("""
        Try saying:
        - **"Explain machine learning"**
        - **"Create flashcards from my documents"**
        - **"What did I study yesterday?"**
        - **"Set a 25 minute timer"**
        """)
    
    def render_focus_mode(self):
        """Render focus/pomodoro timer"""
        st.header("🎯 Focus Mode")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Pomodoro Timer")
            study_time = st.slider("Study Time (minutes)", 15, 60, 25)
            break_time = st.slider("Break Time (minutes)", 5, 30, 5)
            
            if st.button("Start Focus Session"):
                st.session_state.focus_timer = {
                    'start_time': datetime.now(),
                    'study_duration': study_time,
                    'break_duration': break_time,
                    'phase': 'study'
                }
                st.success(f"🎯 Focus session started! Study for {study_time} minutes.")
        
        with col2:
            if st.session_state.focus_timer:
                timer = st.session_state.focus_timer
                elapsed = (datetime.now() - timer['start_time']).total_seconds() / 60
                remaining = timer['study_duration'] - elapsed
                
                if remaining > 0:
                    st.subheader(f"⏰ {int(remaining)} minutes remaining")
                    st.progress(elapsed / timer['study_duration'])
                else:
                    st.balloons()
                    st.success("🎉 Study session complete! Time for a break.")
                    
                    # Record session
                    self.record_study_session("Focus Mode", timer['study_duration'])
                    
                    # Reset timer
                    st.session_state.focus_timer = None
    
    def render_flashcards(self):
        """Render flashcard system"""
        st.header("🃏 Smart Flashcards")
        
        # Generate flashcards from documents
        if st.session_state.documents and st.button("Generate Flashcards from Documents"):
            with st.spinner("Creating flashcards..."):
                try:
                    flashcards = self.rag_assistant.generate_flashcards()
                    st.session_state.flashcards.extend(flashcards)
                    st.success(f"Generated {len(flashcards)} new flashcards!")
                except Exception as e:
                    st.error(f"Error generating flashcards: {str(e)}")
        
        # Manual flashcard creation
        with st.form("add_flashcard"):
            col1, col2 = st.columns(2)
            with col1:
                question = st.text_input("Question:")
            with col2:
                answer = st.text_input("Answer:")
            
            if st.form_submit_button("Add Flashcard"):
                if question and answer:
                    st.session_state.flashcards.append({
                        'question': question,
                        'answer': answer,
                        'review_count': 0,
                        'last_reviewed': None
                    })
                    st.success("Flashcard added!")
        
        # Flashcard review
        if st.session_state.flashcards:
            st.subheader("Review Flashcards")
            current_card = st.session_state.flashcards[0]  # Simple implementation
            
            st.markdown(f"**Q:** {current_card['question']}")
            
            if st.button("Show Answer"):
                st.markdown(f"**A:** {current_card['answer']}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("👍 Easy"):
                        st.session_state.flashcards.remove(current_card)
                        st.rerun()
                with col2:
                    if st.button("😐 Medium"):
                        # Move to later in deck
                        st.session_state.flashcards.append(st.session_state.flashcards.pop(0))
                        st.rerun()
                with col3:
                    if st.button("👎 Hard"):
                        # Keep at front
                        st.rerun()
        

    
    def render_progress(self):
        """Render progress analytics"""
        st.header("📊 Study Progress")
        
        if not st.session_state.study_sessions:
            st.info("No study data yet. Start studying to see your progress!")
            return
        
        # Create analytics
        df = pd.DataFrame(st.session_state.study_sessions)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_time = df['duration'].sum()
            st.metric("Total Study Time", f"{total_time} min")
        
        with col2:
            session_count = len(df)
            st.metric("Study Sessions", session_count)
        
        with col3:
            avg_session = total_time / session_count
            st.metric("Avg Session", f"{avg_session:.1f} min")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Daily study time
            df['date'] = df['timestamp'].dt.date
            daily_study = df.groupby('date')['duration'].sum().reset_index()
            fig1 = px.line(daily_study, x='date', y='duration', 
                          title="Daily Study Time Trend")
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Topic distribution
            topic_counts = df['topic'].value_counts()
            fig2 = px.pie(values=topic_counts.values, names=topic_counts.index,
                         title="Study Topic Distribution")
            st.plotly_chart(fig2, use_container_width=True)
    
    def record_study_session(self, topic, duration):
        """Record a study session"""
        session = {
            'topic': topic,
            'duration': duration,
            'timestamp': datetime.now()
        }
        st.session_state.study_sessions.append(session)
    
    def run(self):
        """Main app runner"""
        page = self.render_sidebar()
        
        # Route to appropriate page
        if page == "🏠 Dashboard":
            self.render_dashboard()
        elif page == "💬 Study Chat":
            self.render_study_chat()
        elif page == "📚 Documents":
            self.render_documents_page()
        elif page == "🎤 Voice Notes":
            self.render_voice_notes()
        elif page == "📊 Progress":
            self.render_progress()
        elif page == "🎯 Focus Mode":
            self.render_focus_mode()
        elif page == "🃏 Flashcards":
            self.render_flashcards()

# Run the app
if __name__ == "__main__":
    app = StudyMateApp()
    app.run()
