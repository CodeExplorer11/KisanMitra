import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import io
import speech_recognition as sr

# --- Configuration ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Page Setup ---
st.set_page_config(page_title="KisanMitra", layout="centered")
st.title("🌾 KisanMitra")
st.caption("Ask any farming question with your voice!")

# --- Sidebar for Language & History ---
with st.sidebar:
    st.header("Settings")
    # Language selector for responses
    language = st.selectbox("Response Language", ["English", "Hindi", "Hinglish"])

    st.divider()
    st.header("Conversation History")
    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state['history'] = []
        st.rerun()

# --- Initialize Session State ---
if "history" not in st.session_state:
    st.session_state['history'] = []

# --- Gemini AI Setup ---
if not GEMINI_API_KEY:
    st.error("Gemini API key not found. Please add it to your environment secrets.")
    st.stop()
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# --- Helper Functions ---
def transcribe_audio(audio_bytes):
    """Convert audio bytes to text using Google Speech Recognition."""
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio_data = recognizer.record(source)
        # Recognize speech (auto-detects language)
        return recognizer.recognize_google(audio_data)
    except sr.UnknownValueError:
        return "Sorry, could not understand the audio."
    except sr.RequestError:
        return "Sorry, the speech recognition service is unavailable."

def get_farming_advice(question, lang):
    """Get farming advice from Gemini AI."""
    prompt = f"""You are KisanMitra, a friendly expert farming assistant.
Response language: {lang}
Farmer asked: "{question}"
Give a short, practical, actionable answer (max 3 sentences). Use local terms if helpful."""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Error getting advice: {str(e)}"

# --- Main App UI ---
st.header("🎤 Record Your Question")

# The magic happens here: a simple audio recorder
audio_value = st.audio_input("Tap to record your question")

if audio_value:
    # 1. Transcribe the audio to text
    with st.spinner("Transcribing your voice..."):
        transcribed_text = transcribe_audio(audio_value.getvalue())
    st.write(f"**You asked:** {transcribed_text}")
    st.audio(audio_value) # Play back the recording

    # 2. Get advice from Gemini
    with st.spinner("Getting advice from KisanMitra..."):
        advice = get_farming_advice(transcribed_text, language)

    # 3. Display and save the result
    st.success("**KisanMitra says:**")
    st.write(advice)
    
    # Save to session state history
    if 'history' not in st.session_state:
        st.session_state['history'] = []
    st.session_state['history'].append({"question": transcribed_text, "answer": advice})

    # Optional: Speak the advice using browser's TTS
    st.markdown(f"""
    <audio autoplay>
        <source src="https://api.streamelements.com/kappa-v2/speech?voice=Google%20UK%20English%20Female&text={advice}" type="audio/mpeg">
    </audio>
    """, unsafe_allow_html=True)

# --- Display Conversation History ---
if st.session_state['history']:
    st.divider()
    st.header("📜 Past Conversations")
    for chat in st.session_state['history'][-5:]: # Show last 5
        with st.expander(f"🗣️ {chat['question'][:50]}..."):
            st.write(f"**You:** {chat['question']}")
            st.write(f"**KisanMitra:** {chat['answer']}")