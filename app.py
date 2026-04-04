import streamlit as st
import os
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image
import datetime

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    vision_model = genai.GenerativeModel('gemini-pro-vision')
else:
    st.error("⚠️ API key missing")
    model = None

# Page config
st.set_page_config(page_title="KisanMitra", page_icon="🌾", layout="wide")

# Custom CSS for better UI
st.markdown("""
<style>
    /* Gradient background */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e8f0e8 100%);
    }
    /* Main card */
    .main-card {
        background: white;
        border-radius: 20px;
        padding: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    /* Voice button */
    .voice-btn {
        background: linear-gradient(135deg, #2e7d32, #4caf50);
        color: white;
        font-size: 28px;
        padding: 20px 40px;
        border: none;
        border-radius: 60px;
        cursor: pointer;
        width: 100%;
        transition: transform 0.2s;
    }
    .voice-btn:hover {
        transform: scale(1.02);
    }
    /* Chat bubble */
    .user-bubble {
        background: #e3f2fd;
        padding: 12px 18px;
        border-radius: 20px 20px 20px 5px;
        margin: 10px 0;
        font-family: 'Segoe UI', sans-serif;
    }
    .bot-bubble {
        background: #e8f5e9;
        padding: 12px 18px;
        border-radius: 20px 20px 5px 20px;
        margin: 10px 0;
        border-left: 4px solid #2e7d32;
    }
    /* Sidebar */
    .sidebar-history {
        background: #fef9e6;
        padding: 15px;
        border-radius: 15px;
        margin-bottom: 10px;
    }
    h1 {
        color: #2e7d32;
        text-align: center;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background: white;
        border-radius: 30px;
        padding: 8px 20px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "lang_pref" not in st.session_state:
    st.session_state.lang_pref = "auto"

# Sidebar with history
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/india-farmer.png", width=80)
    st.title("📜 बातचीत का इतिहास")
    if st.button("🗑️ Clear History"):
        st.session_state.chat_history = []
        st.rerun()
    for i, chat in enumerate(reversed(st.session_state.chat_history[-10:])):
        with st.expander(f"🗣️ {chat['question'][:40]}..."):
            st.write(f"**प्रश्न:** {chat['question']}")
            st.write(f"**उत्तर:** {chat['answer'][:100]}...")

# Main area with tabs
tab1, tab2, tab3 = st.tabs(["🎤 वॉइस असिस्टेंट", "🔬 रोग पहचान", "🌤️ मौसम और भाव"])

with tab1:
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.title("🌾 KisanMitra")
    st.caption("अपनी भाषा में बोलें – AI देगा जवाब | Speak in your village language")
    
    # Language preference
    col1, col2 = st.columns(2)
    with col1:
        lang_option = st.selectbox("भाषा / Language", ["Auto (from speech)", "Hindi", "Hinglish", "English"])
        if lang_option == "Auto (from speech)":
            st.session_state.lang_pref = "auto"
        elif lang_option == "Hindi":
            st.session_state.lang_pref = "hi"
        elif lang_option == "Hinglish":
            st.session_state.lang_pref = "hinglish"
        else:
            st.session_state.lang_pref = "en"
    
    # Voice input using HTML/JS (supports any language)
    voice_html = """
    <div style="text-align:center; margin:20px 0;">
        <button id="micBtn" class="voice-btn">🎤 बोलें / Speak</button>
        <p id="status" style="margin-top:15px; color:#2e7d32;">Tap and speak in your language</p>
    </div>
    <script>
        const micBtn = document.getElementById('micBtn');
        const statusDiv = document.getElementById('status');
        let recognition = null;
        micBtn.onclick = function() {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRecognition) {
                statusDiv.innerText = "Browser not supported";
                return;
            }
            recognition = new SpeechRecognition();
            recognition.lang = '';  // auto-detect
            recognition.interimResults = false;
            recognition.onstart = function() {
                statusDiv.innerText = "🎙️ Listening... सुन रहा हूँ...";
                micBtn.style.background = "#ff5722";
            };
            recognition.onresult = function(event) {
                const text = event.results[0][0].transcript;
                statusDiv.innerText = "✅ Recognized: " + text;
                const form = document.createElement('form');
                form.method = 'post';
                form.action = '';
                const input = document.createElement('input');
                input.name = 'voice_query';
                input.value = text;
                form.appendChild(input);
                document.body.appendChild(form);
                form.submit();
            };
            recognition.onerror = function() {
                statusDiv.innerText = "❌ Try again";
                micBtn.style.background = "linear-gradient(135deg, #2e7d32, #4caf50)";
            };
            recognition.onend = function() {
                micBtn.style.background = "linear-gradient(135deg, #2e7d32, #4caf50)";
            };
            recognition.start();
        };
    </script>
    """
    st.components.v1.html(voice_html, height=180)
    
    # Process voice query
    if "voice_query" in st.query_params:
        user_q = st.query_params["voice_query"]
        if user_q:
            st.markdown(f'<div class="user-bubble">🗣️ <strong>आप:</strong> {user_q}</div>', unsafe_allow_html=True)
            with st.spinner("🤔 सोच रहा हूँ..."):
                # Auto-detect language from query (simple heuristic)
                detected_lang = "hi" if any(u'\u0900' <= c <= u'\u097f' for c in user_q) else "en"
                if st.session_state.lang_pref == "auto":
                    use_lang = "Hindi" if detected_lang == "hi" else "English"
                elif st.session_state.lang_pref == "hi":
                    use_lang = "Hindi"
                elif st.session_state.lang_pref == "hinglish":
                    use_lang = "Hinglish"
                else:
                    use_lang = "English"
                
                prompt = f"""You are KisanMitra, a helpful farming assistant. 
Farmer asked in {use_lang}: "{user_q}"
Answer in {use_lang} (use simple words, short sentences, practical advice). Max 3 sentences."""
                response = model.generate_content(prompt)
                answer = response.text
            st.markdown(f'<div class="bot-bubble">🤖 <strong>KisanMitra:</strong> {answer}</div>', unsafe_allow_html=True)
            # Speak answer
            st.components.v1.html(f'<script>var u = new SpeechSynthesisUtterance("{answer}"); u.lang = "{detected_lang}"; window.speechSynthesis.speak(u);</script>', height=0)
            # Save to history
            st.session_state.chat_history.append({
                "question": user_q,
                "answer": answer,
                "time": datetime.datetime.now().strftime("%H:%M")
            })
    
    # Display recent conversation
    if st.session_state.chat_history:
        st.markdown("### 📝 हाल की बातचीत")
        for chat in st.session_state.chat_history[-5:]:
            st.markdown(f'<div class="user-bubble">🗣️ {chat["question"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bot-bubble">🤖 {chat["answer"]}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.subheader("🔬 फसल रोग पहचान")
    uploaded = st.file_uploader("तस्वीर लें / Upload", type=["jpg","jpeg","png"])
    if uploaded and vision_model:
        img = Image.open(uploaded)
        st.image(img, width=200)
        if st.button("रोग पहचानें"):
            with st.spinner("Analyzing..."):
                resp = vision_model.generate_content(["Analyze this crop image. Tell disease, treatment, organic solution. Keep short.", img])
                st.success(resp.text)
    st.markdown('</div>', unsafe_allow_html=True)

with tab3:
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.subheader("🌤️ मौसम और मंडी भाव")
    if st.button("आज का मौसम"):
        st.info("🌡️ 28°C, आंशिक बादल, खेत में काम कर सकते हैं।")
    if st.button("सरसों का भाव"):
        st.success("₹5,650 प्रति क्विंटल (बढ़ रहा)")
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("🌾 KisanMitra - आपकी आवाज, आपकी भाषा, आपका साथी | जय किसान!")