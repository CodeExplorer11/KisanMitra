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

# ========== VIBRANT CSS ==========
st.markdown("""
<style>
    /* Main background gradient */
    .stApp {
        background: linear-gradient(135deg, #f9f3e6 0%, #fff3e0 100%);
    }
    /* Card style */
    .card {
        background: rgba(255,255,255,0.95);
        border-radius: 28px;
        padding: 1.8rem;
        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        margin-bottom: 1.5rem;
        backdrop-filter: blur(2px);
        border: 1px solid rgba(255,215,150,0.5);
    }
    /* Voice button */
    .voice-btn {
        background: linear-gradient(95deg, #ff8c00, #ffb347);
        color: white;
        font-size: 28px;
        padding: 18px 30px;
        border: none;
        border-radius: 60px;
        cursor: pointer;
        width: 100%;
        font-weight: bold;
        transition: all 0.2s;
        box-shadow: 0 8px 20px rgba(255,140,0,0.3);
    }
    .voice-btn:hover {
        transform: scale(1.02);
        background: linear-gradient(95deg, #ffa033, #ffcc66);
    }
    /* Chat bubbles */
    .user-msg {
        background: #fff0db;
        padding: 12px 18px;
        border-radius: 24px 24px 8px 24px;
        margin: 12px 0;
        font-size: 16px;
        border-left: 5px solid #ff8c00;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .bot-msg {
        background: #e8f0fe;
        padding: 12px 18px;
        border-radius: 24px 24px 24px 8px;
        margin: 12px 0;
        font-size: 16px;
        border-right: 5px solid #2e7d32;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #2e5e2e;
        background-image: linear-gradient(145deg, #2e5e2e, #1e3a1e);
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    h1, h2, h3 {
        color: #b45309;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: #fff7e8;
        border-radius: 40px;
        padding: 6px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 40px;
        padding: 8px 24px;
        background-color: #ffe6cc;
        font-weight: bold;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ff8c00;
        color: white;
    }
    /* Language selector */
    .lang-select {
        background: #fff0db;
        padding: 10px;
        border-radius: 40px;
        margin-bottom: 15px;
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
    st.title("🌾 किसान मित्र")
    st.markdown("---")
    st.subheader("🗣️ भाषा चुनें")
    lang_choice = st.radio(
        "बोलने और जवाब की भाषा",
        ["Auto (जैसे बोलें वैसे)", "हिंदी", "हिंग्लिश", "English"],
        index=0
    )
    if lang_choice == "Auto (जैसे बोलें वैसे)":
        st.session_state.lang = "auto"
    elif lang_choice == "हिंदी":
        st.session_state.lang = "hi"
    elif lang_choice == "हिंग्लिश":
        st.session_state.lang = "hinglish"
    else:
        st.session_state.lang = "en"
    
    st.markdown("---")
    st.subheader("📜 बातचीत इतिहास")
    if st.button("🗑️ साफ करें", use_container_width=True):
        st.session_state.history = []
        st.rerun()
    for idx, chat in enumerate(reversed(st.session_state.history[-8:])):
        with st.expander(f"🗣️ {chat['q'][:35]}..."):
            st.write(f"**प्रश्न:** {chat['q']}")
            st.write(f"**जवाब:** {chat['a'][:150]}...")

# ========== MAIN TABS ==========
tab1, tab2, tab3 = st.tabs(["🎤 वॉइस सहायक", "🔬 रोग पहचान", "🌤️ मौसम / भाव"])

# ----- TAB 1: VOICE ASSISTANT -----
with tab1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.title("🌾 आवाज़ से पूछें")
    st.caption("अपनी भाषा में बोलें – AI तुरंत जवाब देगा और बोलेगा")
    
    # Voice button (JavaScript with Web Speech API)
    voice_html = """
    <div style="text-align:center; margin:20px 0;">
        <button id="micBtn" class="voice-btn">🎤 बोलें / Speak Now</button>
        <p id="statusMsg" style="margin-top:15px; font-size:16px; color:#b45309;">👉 Tap, allow mic, speak naturally</p>
    </div>
    <script>
        const mic = document.getElementById('micBtn');
        const statusSpan = document.getElementById('statusMsg');
        let recognition;
        mic.onclick = function() {
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                statusSpan.innerText = "❌ Your browser doesn't support voice input. Try Chrome.";
                return;
            }
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.lang = '';  // auto-detect language
            recognition.interimResults = false;
            recognition.maxAlternatives = 1;
            recognition.onstart = function() {
                statusSpan.innerHTML = "🎙️ सुन रहा हूँ... बोलिए...";
                mic.style.background = "#e65c00";
            };
            recognition.onresult = function(event) {
                const spoken = event.results[0][0].transcript;
                statusSpan.innerHTML = "✅ सुना: " + spoken;
                // send to Streamlit backend
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
                statusSpan.innerHTML = "❌ Error: " + e.error + ". Please try again.";
                mic.style.background = "linear-gradient(95deg, #ff8c00, #ffb347)";
            };
            recognition.onend = function() {
                mic.style.background = "linear-gradient(95deg, #ff8c00, #ffb347)";
            };
            recognition.start();
        };
    </script>
    """
    st.components.v1.html(voice_html, height=200)
    
    # Process voice input
    if "voice_text" in st.query_params:
        user_q = st.query_params["voice_text"]
        if user_q:
            # Display user message
            st.markdown(f'<div class="user-msg">🗣️ <strong>आप:</strong> {user_q}</div>', unsafe_allow_html=True)
            
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
            with st.spinner("🤔 सोच रहा हूँ..."):
                prompt = f"""You are KisanMitra, a friendly expert farmer assistant.
Language: {reply_lang}
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
            
            # Speak answer (browser TTS)
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
        st.markdown("### 📝 हाल की बातें")
        for chat in st.session_state.history[-5:]:
            st.markdown(f'<div class="user-msg">🗣️ {chat["q"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bot-msg">🤖 {chat["a"]}</div>', unsafe_allow_html=True)
    else:
        st.info("☝️ ऊपर माइक दबाएं और बोलें। मैं किसानी के सारे सवालों के जवाब दूंगा।")
    st.markdown('</div>', unsafe_allow_html=True)

# ----- TAB 2: DISEASE DETECTION -----
with tab2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🔬 फसल रोग पहचान")
    img_file = st.file_uploader("फसल की तस्वीर लें / Upload image", type=["jpg","jpeg","png"])
    if img_file:
        image = Image.open(img_file)
        st.image(image, width=250)
        if st.button("🔍 रोग पहचानें", use_container_width=True):
            with st.spinner("विश्लेषण हो रहा है..."):
                diag_prompt = "Analyze this crop image. List: 1) Possible disease, 2) Organic treatment, 3) Chemical solution if needed. Keep short."
                response = vision_model.generate_content([diag_prompt, image])
                st.success("✅ निदान परिणाम")
                st.markdown(f'<div class="bot-msg">🌿 {response.text}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ----- TAB 3: MARKET & WEATHER (Simple) -----
with tab3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🌤️ मौसम जानकारी")
    if st.button("आज का मौसम", use_container_width=True):
        st.info("🌡️ तापमान 28-32°C, हल्की धूप। सिंचाई के लिए उपयुक्त।")
    st.subheader("💰 मंडी भाव")
    crop = st.selectbox("फसल चुनें", ["गेहूं", "धान", "सरसों", "टमाटर", "आलू"])
    if st.button("भाव देखें", use_container_width=True):
        prices = {"गेहूं": "₹2,250/क्विंटल", "धान": "₹2,180/क्विंटल", "सरसों": "₹5,650/क्विंटल", "टमाटर": "₹1,800/क्विंटल", "आलू": "₹1,200/क्विंटल"}
        st.success(f"{crop} का आज का भाव: {prices[crop]}")
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("🌾 KisanMitra – आपकी आवाज़ में किसानी की पूरी मदद | जय हिंद, जय किसान!")