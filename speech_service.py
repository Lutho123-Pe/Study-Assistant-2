import speech_recognition as sr
import io

class SpeechService:
    def __init__(self):
        self.recognizer = sr.Recognizer()
    
    def speech_to_text(self, audio_data):
        """
        Convert audio data to text using speech recognition.
        
        Args:
            audio_data: Can be bytes (from recording) or file-like object (from upload)
        
        Returns:
            str: Transcribed text
        """
        try:
            if isinstance(audio_data, bytes):
                # Handle recorded audio (bytes)
                audio = sr.AudioData(audio_data, sample_rate=16000, sample_width=2)
            else:
                # Handle uploaded file
                with sr.AudioFile(audio_data) as source:
                    audio = self.recognizer.record(source)
            
            # Recognize speech using Google Speech Recognition
            text = self.recognizer.recognize_google(audio)
            return text
            
        except sr.UnknownValueError:
            return "Speech recognition could not understand the audio."
        except sr.RequestError as e:
            return f"Could not request results from speech recognition service; {e}"
        except Exception as e:
            return f"Error in speech recognition: {str(e)}"
