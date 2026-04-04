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
    st.error("⚠️ API key missing. Add GEMINI_API_KEY in Secrets.")
    st.stop()

st.set_page_config(page_title="KisanMitra", page_icon="🌾", layout="wide")

# ========== HIGH CONTRAST CSS (All text visible) ==========
st.markdown("""
<style>
    /* Main background - light, not white */
    .stApp {
        background: linear-gradient(135deg, #f0f7f0 0%, #e8f0e8 100%);
    }
    /* Card style with dark text */
    .card {
        background: white;
        border-radius: 24px;
        padding: 1.8rem;
        box-shadow: 0 8px 20px rgba(0,0,0,0.1);
        margin-bottom: 1.5rem;
        border: 1px solid #d0e0c0;
    }
    /* Voice button - bright orange */
    .voice-btn {
        background: linear-gradient(95deg, #ff8c00, #ffb347);
        color: white !important;
        font-size: 24px;
        padding: 16px 30px;
        border: none;
        border-radius: 60px;
        cursor: pointer;
        width: 100%;
        font-weight: bold;
        transition: all 0.2s;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    .voice-btn:hover {
        transform: scale(1.02);
        background: linear-gradient(95deg, #ffa033, #ffcc66);
    }
    /* Chat bubbles - clear text */
    .user-msg {
        background: #e3f2fd;
        padding: 12px 18px;
        border-radius: 24px 24px 8px 24px;
        margin: 12px 0;
        font-size: 16px;
        color: #1a1a1a;
        border-left: 5px solid #ff8c00;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .bot-msg {
        background: #e8f5e9;
        padding: 12px 18px;
        border-radius: 24px 24px 24px 8px;
        margin: 12px 0;
        font-size: 16px;
        color: #1a1a1a;
        border-right: 5px solid #2e7d32;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    /* Sidebar - dark green with white text */
    [data-testid="stSidebar"] {
        background: #1e3a1e;
        background-image: linear-gradient(145deg, #1e3a1e, #0e2a0e);
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    /* Headers */
    h1, h2, h3, .stMarkdown {
        color: #1e3a1e !important;
    }
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: #ffffffcc;
        border-radius: 40px;
        padding: 6px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 40px;
        padding: 8px 24px;
        background-color: #f0e6d0;
        font-weight: bold;
        color: #1e3a1e;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ff8c00;
        color: white;
    }
    /* Status message */
    #statusMsg {
        color: #b45309 !important;
        font-weight: bold;
    }
    /* Buttons */
    .stButton button {
        background-color: #2e7d32;
        color: white;
        border-radius: 30px;
        padding: 10px 20px;
        font-weight: bold;
    }
    .stButton button:hover {
        background-color: #1e5e22;
    }
</style>
""", unsafe_allow_html=True)

# ========== SESSION STATE ==========
if "history" not in st.session_state:
    st.session_state.history = []
if "lang" not in st.session_state:
    st.session_state.lang = "auto"

# ========== SIDEBAR ==========
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1998/1998626.png", width=80)
    st.title("🌾 KisanMitra")
    st.markdown("---")
    st.subheader("🗣️ Response Language")
    lang_choice = st.radio(
        "Choose language for answers",
        ["Auto (match your speech)", "Hindi", "Hinglish", "English"],
        index=0
    )
    if lang_choice == "Auto (match your speech)":
        st.session_state.lang = "auto"
    elif lang_choice == "Hindi":
        st.session_state.lang = "hi"
    elif lang_choice == "Hinglish":
        st.session_state.lang = "hinglish"
    else:
        st.session_state.lang = "en"
    
    st.markdown("---")
    st.subheader("📜 Conversation History")
    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.history = []
        st.rerun()
    for idx, chat in enumerate(reversed(st.session_state.history[-8:])):
        with st.expander(f"🗣️ {chat['q'][:35]}..."):
            st.write(f"**Question:** {chat['q']}")
            st.write(f"**Answer:** {chat['a'][:150]}...")

# ========== MAIN TABS ==========
tab1, tab2, tab3 = st.tabs(["🎤 Voice Assistant", "🔬 Disease Detection", "🌤️ Weather & Market"])

# ----- TAB 1: VOICE ASSISTANT -----
with tab1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("🌾 Ask by Voice")
    st.caption("Speak in your language – AI will answer and speak back")
    
    # Voice button with JavaScript (Web Speech API)
    voice_html = """
    <div style="text-align:center; margin:20px 0;">
        <button id="micBtn" class="voice-btn">🎤 Tap to Speak</button>
        <p id="statusMsg" style="margin-top:15px; font-size:16px;">👉 Tap, allow mic, speak naturally</p>
    </div>
    <script>
        const mic = document.getElementById('micBtn');
        const statusSpan = document.getElementById('statusMsg');
        let recognition;
        mic.onclick = function() {
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                statusSpan.innerText = "❌ Voice not supported. Use Chrome on mobile.";
                return;
            }
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.lang = '';  // auto-detect
            recognition.interimResults = false;
            recognition.maxAlternatives = 1;
            recognition.onstart = function() {
                statusSpan.innerHTML = "🎙️ Listening... Speak now...";
                mic.style.background = "#e65c00";
            };
            recognition.onresult = function(event) {
                const spoken = event.results[0][0].transcript;
                statusSpan.innerHTML = "✅ Recognized: " + spoken;
                // Send to Streamlit backend
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = '';
                const inp = document.createElement('input');
                inp.name = 'voice_text';
                inp.value = spoken;
                form.appendChild(inp);
                document.body.appendChild(form);
                form.submit();
            };
            recognition.onerror = function(e) {
                statusSpan.innerHTML = "❌ Error: " + e.error + ". Try again.";
                mic.style.background = "linear-gradient(95deg, #ff8c00, #ffb347)";
            };
            recognition.onend = function() {
                mic.style.background = "linear-gradient(95deg, #ff8c00, #ffb347)";
            };
            recognition.start();
        };
    </script>
    """
    st.components.v1.html(voice_html, height=180)
    
    # Process voice input
    if "voice_text" in st.query_params:
        user_q = st.query_params["voice_text"]
        if user_q:
            # Display user message
            st.markdown(f'<div class="user-msg">🗣️ <strong>You:</strong> {user_q}</div>', unsafe_allow_html=True)
            
            # Determine response language
            has_hindi = any(u'\u0900' <= c <= u'\u097f' for c in user_q)
            if st.session_state.lang == "auto":
                reply_lang = "Hindi" if has_hindi else "English"
            elif st.session_state.lang == "hi":
                reply_lang = "Hindi"
            elif st.session_state.lang == "hinglish":
                reply_lang = "Hinglish"
            else:
                reply_lang = "English"
            
            # Get AI response from Gemini
            with st.spinner("🤔 Thinking..."):
                prompt = f"""You are KisanMitra, a friendly expert farming assistant.
Response language: {reply_lang}
Farmer asked: "{user_q}"
Give a short, practical, actionable answer (max 3 sentences). Use local terms if helpful.
If in Hindi/Hinglish, keep it simple."""
                try:
                    resp = model.generate_content(prompt)
                    answer = resp.text
                except Exception as e:
                    answer = f"⚠️ Error: {str(e)[:100]}"
            
            # Show bot response
            st.markdown(f'<div class="bot-msg">🤖 <strong>KisanMitra:</strong> {answer}</div>', unsafe_allow_html=True)
            
            # Speak answer using browser TTS
            speak_js = f"""
            <script>
                var utterance = new SpeechSynthesisUtterance(`{answer}`);
                utterance.lang = '{'hi-IN' if has_hindi else 'en-US'}';
                window.speechSynthesis.speak(utterance);
            </script>
            """
            st.components.v1.html(speak_js, height=0)
            
            # Save to history
            st.session_state.history.append({
                "q": user_q,
                "a": answer,
                "time": datetime.datetime.now().strftime("%I:%M %p")
            })
    
    # Show recent conversation
    if st.session_state.history:
        st.markdown("### 📝 Recent Conversations")
        for chat in st.session_state.history[-5:]:
            st.markdown(f'<div class="user-msg">🗣️ {chat["q"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bot-msg">🤖 {chat["a"]}</div>', unsafe_allow_html=True)
    else:
        st.info("☝️ Tap the microphone above and speak. I'll answer all farming questions.")
    st.markdown('</div>', unsafe_allow_html=True)

# ----- TAB 2: DISEASE DETECTION -----
with tab2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🔬 Crop Disease Detection")
    img_file = st.file_uploader("Upload a photo of the crop", type=["jpg","jpeg","png"])
    if img_file:
        image = Image.open(img_file)
        st.image(image, width=250)
        if st.button("🔍 Detect Disease", use_container_width=True):
            with st.spinner("Analyzing..."):
                diag_prompt = "Analyze this crop image. List: 1) Possible disease, 2) Organic treatment, 3) Chemical solution if needed. Keep short."
                response = vision_model.generate_content([diag_prompt, image])
                st.success("✅ Diagnosis Result")
                st.markdown(f'<div class="bot-msg">🌿 {response.text}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ----- TAB 3: MARKET & WEATHER -----
with tab3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🌤️ Weather Information")
    if st.button("Today's Weather", use_container_width=True):
        st.info("🌡️ Temperature: 28-32°C, Partly sunny. Good for farming activities.")
    st.subheader("💰 Market Prices")
    crop = st.selectbox("Select Crop", ["Wheat", "Rice", "Mustard", "Tomato", "Potato"])
    if st.button("Get Price", use_container_width=True):
        prices = {"Wheat": "₹2,250/quintal", "Rice": "₹2,180/quintal", "Mustard": "₹5,650/quintal", "Tomato": "₹1,800/quintal", "Potato": "₹1,200/quintal"}
        st.success(f"Today's price for {crop}: {prices[crop]}")
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("🌾 KisanMitra – Your Voice Farming Companion | Jai Hind, Jai Kisan!")