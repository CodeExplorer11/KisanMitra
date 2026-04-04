import streamlit as st
import os
import google.generativeai as genai
from dotenv import load_dotenv
import requests
from PIL import Image
import io

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    vision_model = genai.GenerativeModel('gemini-pro-vision')
else:
    st.error("⚠️ Gemini API key missing. Add it in Secrets.")
    model = None
    vision_model = None

st.set_page_config(page_title="KisanMitra", page_icon="🌾", layout="centered")

# Custom CSS for mobile
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        font-size: 18px;
        padding: 12px;
        border-radius: 50px;
    }
    .response-box {
        background-color: #e8f5e9;
        padding: 20px;
        border-radius: 15px;
        margin: 10px 0;
        border-left: 5px solid #2e7d32;
    }
    .query-box {
        background-color: #e3f2fd;
        padding: 12px;
        border-radius: 12px;
        margin: 10px 0;
    }
    h1 { text-align: center; color: #2e7d32; }
    .stRadio > div { justify-content: center; }
</style>
""", unsafe_allow_html=True)

# Language selection
lang = st.radio("भाषा / Language", ["हिंदी", "English"], horizontal=True)
is_hindi = lang == "हिंदी"

# ---------- Helper: Get AI response ----------
def get_ai_response(question):
    if not model:
        return "⚠️ AI not configured. Please check API key."
    prompt = f"""You are KisanMitra, a helpful farming assistant for Indian farmers.
Language: {'Hindi' if is_hindi else 'English'}.
Farmer's question: {question}
Give a short, practical, actionable answer (max 3 sentences). Include specific advice if possible."""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Error: {str(e)[:100]}"

# ---------- Voice Input (JavaScript) ----------
voice_html = f"""
<div id="voice-container" style="text-align:center; margin-bottom:20px;">
    <button id="mic-btn" style="background-color:#4CAF50; color:white; font-size:24px; padding:15px 30px; border:none; border-radius:50px; cursor:pointer;">🎤 बोलें / Speak</button>
    <p id="status" style="margin-top:10px; color:#555;">Tap and speak</p>
</div>
<script>
    const micBtn = document.getElementById('mic-btn');
    const statusDiv = document.getElementById('status');
    let recognition = null;
    function startRecognition() {{
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {{
            statusDiv.innerText = "Your browser does not support voice input.";
            return;
        }}
        recognition = new SpeechRecognition();
        recognition.lang = '{'hi-IN' if is_hindi else 'en-US'}';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;
        recognition.onstart = function() {{
            statusDiv.innerText = "🎙️ Listening... सुन रहा हूँ...";
            micBtn.style.backgroundColor = "#ff5722";
        }};
        recognition.onresult = function(event) {{
            const text = event.results[0][0].transcript;
            statusDiv.innerText = "✅ Recognized: " + text;
            // Send to Streamlit via form
            const form = document.createElement('form');
            form.method = 'post';
            form.action = '';
            const input = document.createElement('input');
            input.name = 'voice_query';
            input.value = text;
            form.appendChild(input);
            document.body.appendChild(form);
            form.submit();
        }};
        recognition.onerror = function(event) {{
            statusDiv.innerText = "❌ Error: " + event.error;
            micBtn.style.backgroundColor = "#4CAF50";
        }};
        recognition.onend = function() {{
            micBtn.style.backgroundColor = "#4CAF50";
            if (statusDiv.innerText !== "✅ Recognized") {{
                statusDiv.innerText = "Tap and speak again";
            }}
        }};
        recognition.start();
    }}
    micBtn.addEventListener('click', startRecognition);
</script>
"""

# Display voice component
st.components.v1.html(voice_html, height=120)

# Handle voice query submitted via form
if "voice_query" in st.query_params:
    user_query = st.query_params["voice_query"]
    if user_query:
        st.markdown(f'<div class="query-box">🗣️ <strong>{"आपने पूछा" if is_hindi else "You asked"}:</strong> {user_query}</div>', unsafe_allow_html=True)
        with st.spinner("🤔 सोच रहा हूँ..."):
            answer = get_ai_response(user_query)
        st.markdown(f'<div class="response-box">🤖 <strong>KisanMitra:</strong><br>{answer}</div>', unsafe_allow_html=True)
        # Speak answer via browser TTS
        speak_js = f"""
        <script>
            var utterance = new SpeechSynthesisUtterance({answer});
            utterance.lang = '{'hi-IN' if is_hindi else 'en-US'}';
            window.speechSynthesis.speak(utterance);
        </script>
        """
        st.components.v1.html(speak_js, height=0)

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
    with cols[i%2]:
        if st.button(q, use_container_width=True):
            answer = get_ai_response(q)
            st.markdown(f'<div class="response-box">🤖 <strong>उत्तर:</strong><br>{answer}</div>', unsafe_allow_html=True)
            st.components.v1.html(f'<script>var u = new SpeechSynthesisUtterance("{answer}"); u.lang = "{'hi-IN' if is_hindi else 'en-US'}"; window.speechSynthesis.speak(u);</script>', height=0)

# ---------- Disease Detection Page (simple inline) ----------
st.markdown("---")
st.subheader("🔬 फसल रोग पहचान | Crop Disease Detection")
uploaded_file = st.file_uploader("तस्वीर लें / Upload photo", type=["jpg", "jpeg", "png"])
if uploaded_file and vision_model:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded", width=200)
    if st.button("रोग की पहचान करें"):
        with st.spinner("विश्लेषण..."):
            prompt = "Analyze this crop image. Tell disease (if any), treatment, organic solution. Keep short."
            response = vision_model.generate_content([prompt, image])
            st.markdown(f'<div class="response-box">🔍 <strong>निदान / Diagnosis:</strong><br>{response.text}</div>', unsafe_allow_html=True)

# ---------- Weather (simple mock, can add API later) ----------
st.markdown("---")
st.subheader("🌤️ मौसम जानकारी | Weather")
if st.button("आज का मौसम / Today's Weather"):
    # Use OpenWeatherMap if you have key, else mock
    weather_text = "आज तापमान 28°C, हल्की धूप। खेत में काम कर सकते हैं।" if is_hindi else "Today 28°C, partly sunny. Suitable for farming."
    st.info(weather_text)

# Footer
st.markdown("---")
st.caption("🌾 KisanMitra - आपका विश्वसनीय साथी | जय किसान!")