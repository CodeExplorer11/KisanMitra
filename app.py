"""
KisanMitra - Voice-Based Digital Field Companion
Complete working version with Gemini AI
"""

import streamlit as st
import os
import google.generativeai as genai
from dotenv import load_dotenv
import speech_recognition as sr
import pyttsx3
import tempfile
import pygame

# Load API keys
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
else:
    st.error("⚠️ Gemini API key not found! Please add it to .env file")
    model = None

# Page config
st.set_page_config(page_title="KisanMitra", page_icon="🌾", layout="centered")

# Custom CSS for mobile feel
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        font-size: 20px;
        padding: 15px;
        border-radius: 50px;
    }
    .response-box {
        background-color: #e8f5e9;
        padding: 20px;
        border-radius: 15px;
        margin: 10px 0;
        border-left: 5px solid #2e7d32;
    }
    h1 {
        text-align: center;
        color: #2e7d32;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("🌾 KisanMitra")
st.caption("आपका वॉइस डिजिटल साथी | Your Voice Farming Companion")

# Language selector
lang = st.radio("भाषा / Language", ["हिंदी", "English"], horizontal=True)
is_hindi = lang == "हिंदी"

# Initialize speech components
@st.cache_resource
def init_tts():
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    return engine

def speak(text):
    try:
        engine = init_tts()
        engine.say(text)
        engine.runAndWait()
    except:
        st.warning("🔊 Audio not available, but text is shown below.")

def listen():
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            st.info("🎤 सुन रहा हूँ... Speak now...")
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=5, phrase_time_limit=10)
        
        if is_hindi:
            text = r.recognize_google(audio, language="hi-IN")
        else:
            text = r.recognize_google(audio, language="en-IN")
        return text
    except sr.WaitTimeoutError:
        st.warning("⏰ समय समाप्त। कृपया फिर से बोलें।")
        return None
    except sr.UnknownValueError:
        st.warning("🤔 सुनाई नहीं दिया। कृपया स्पष्ट बोलें।")
        return None
    except Exception as e:
        st.error(f"❌ त्रुटि: {str(e)}")
        return None

def get_ai_response(question):
    if not model:
        return "⚠️ AI model not configured. Please check API key."
    
    prompt = f"""You are KisanMitra, a helpful farming assistant for Indian farmers.
    Language: {'Hindi' if is_hindi else 'English'}
    Farmer's question: {question}
    
    Give a short, practical, actionable answer (max 3 sentences). Include specific advice.
    If in Hindi, use simple Hindi or Hinglish."""
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Error: {str(e)[:100]}. Please try again."

# Voice input button
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🎙️ बोलें / Speak", use_container_width=True):
        user_query = listen()
        
        if user_query:
            st.markdown(f"""
            <div style="background-color:#e3f2fd; padding:12px; border-radius:12px; margin:10px 0;">
                <strong>🗣️ आपने पूछा:</strong> {user_query}
            </div>
            """, unsafe_allow_html=True)
            
            with st.spinner("🤔 सोच रहा हूँ..."):
                response = get_ai_response(user_query)
            
            st.markdown(f"""
            <div class="response-box">
                <strong>🤖 KisanMitra:</strong><br>
                {response}
            </div>
            """, unsafe_allow_html=True)
            
            speak(response)

# Quick questions
st.markdown("---")
st.subheader("⚡ त्वरित प्रश्न")

quick_qs = [
    "गेहूं में कितना पानी दें?",
    "सरसों का भाव क्या है?",
    "टमाटर में रोग कैसे ठीक करें?",
    "आज मौसम कैसा रहेगा?"
]

cols = st.columns(2)
for i, q in enumerate(quick_qs):
    with cols[i % 2]:
        if st.button(q, use_container_width=True):
            with st.spinner("🤔..."):
                response = get_ai_response(q)
            st.markdown(f"""
            <div class="response-box">
                <strong>🤖 उत्तर:</strong><br>
                {response}
            </div>
            """, unsafe_allow_html=True)
            speak(response)

# Footer
st.markdown("---")
st.caption("🌾 KisanMitra - आपका विश्वसनीय साथी | जय किसान!")