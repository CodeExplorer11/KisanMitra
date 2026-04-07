import streamlit as st
import requests
import google.generativeai as genai
import io
import speech_recognition as sr
from PIL import Image
import datetime
import PyPDF2
import json
from urllib.parse import quote

# ========== PAGE CONFIG ==========
st.set_page_config(page_title="KisanMitra", page_icon="🌾", layout="wide")

# ========== LANDING PAGE (image fixed) ==========
if "entered_app" not in st.session_state:
    st.session_state.entered_app = False

if not st.session_state.entered_app:
    landing_svg = """
    <svg xmlns='http://www.w3.org/2000/svg' width='720' height='380' viewBox='0 0 720 380'>
      <defs>
        <linearGradient id='sky' x1='0' y1='0' x2='0' y2='1'>
          <stop offset='0%' stop-color='#f8ecd0'/>
          <stop offset='100%' stop-color='#efe2c1'/>
        </linearGradient>
      </defs>
      <rect width='720' height='380' fill='url(#sky)'/>
      <path d='M0 285 Q140 250 280 285 T560 280 T720 292 L720 380 L0 380 Z' fill='#7c9a48'/>
      <path d='M0 315 Q150 280 300 320 T620 312 T720 320 L720 380 L0 380 Z' fill='#5f7f35' opacity='0.9'/>
      <circle cx='610' cy='86' r='32' fill='#f7c95e'/>
      <text x='42' y='84' font-family='Inter, sans-serif' font-size='44' fill='#3f321f'>🌾 KisanMitra</text>
      <text x='42' y='130' font-family='Inter, sans-serif' font-size='24' fill='#5d4c2b'>A trusted farming companion for every field.</text>
      <text x='42' y='180' font-family='Inter, sans-serif' font-size='18' fill='#5d4c2b'>Get weather, mandi rates, and voice support in one place.</text>
    </svg>
    """
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
        .landing-card {{
            background: #fff8ea;
            padding: 2rem;
            border-radius: 30px;
            text-align: center;
            margin: 2rem auto;
            max-width: 760px;
            font-family: 'Inter', sans-serif;
            color: #4a3f2b;
            border: 1px solid #dfcda8;
            box-shadow: 0 6px 16px rgba(74,63,43,0.15);
        }}
        .landing-title {{
            font-size: 2.2rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }}
        .landing-subtitle {{
            font-size: 1.1rem;
            margin-bottom: 1rem;
            opacity: 0.8;
        }}
        .landing-image {{
            width: 100%;
            max-width: 660px;
            border-radius: 20px;
            margin: 0.5rem auto;
            border: 2px solid #e2d3b4;
        }}
    </style>
    <div class="landing-card">
        <div class="landing-title">FRIEND</div>
        <div class="landing-subtitle">Voice‑First Farming Companion with a classic earthy feel</div>
        <img src="data:image/svg+xml;utf8,{quote(landing_svg)}" class="landing-image" alt="KisanMitra Farm Banner">
        <p style="margin-top:1rem;">Tap below to begin your smart farming journey</p>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button(" Start Now", use_container_width=True):
            st.session_state.entered_app = True
            st.rerun()
    st.stop()

# ========== MAIN APP ==========
# ---------- Load API Keys ----------
GEMINI_API_KEY = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    pass
if not GEMINI_API_KEY:
    try:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    except:
        pass

# ---------- Sample Data (replace with real API) ----------
SCHEMES_DATA = {
    # ... (keep your existing schemes data)
}

KVK_DATA = {
    "kvk_centers": [
        {"district": "Lucknow", "center_name": "KVK, Lucknow", "head": "Dr. A. K. Singh", "contact": "+91-522-1234567", "email": "kvk.lucknow@icar.gov.in", "services": "Soil testing, seed production, organic farming training."},
        {"district": "Prayagraj", "center_name": "KVK, Naini", "head": "Dr. S. K. Sharma", "contact": "+91-532-1234567", "email": "kvk.naini@icar.gov.in", "services": "Integrated farming, vermicomposting, fruit preservation."},
        {"district": "Varanasi", "center_name": "KVK, Varanasi", "head": "Dr. R. K. Pandey", "contact": "+91-542-1234567", "email": "kvk.varanasi@icar.gov.in", "services": "Dairy management, aquaculture, mushroom."},
        {"district": "Bareilly", "center_name": "KVK, Bareilly", "head": "Dr. M. K. Sharma", "contact": "+91-581-1234567", "email": "kvk.bareilly@icar.gov.in", "services": "Wheat research, soil health cards, farm machinery."}
    ]
}

# ---------- Multilingual ----------
SUPPORTED_LANGS = {"en": "English", "hi": "हिंदी"}
DEFAULT_LANGUAGE = "en"
TEXTS = {
    "en": { "tab1": "🎤 Voice", "tab2": "💰 Market", "tab3": "🌤️ Weather", "tab4": "🧪 Soil", "tab5": "📝 Advice", "tab6": "🔄 Rotation", "tab7": "🚺 Women", "tab8": "📜 Schemes", "tab9": "🌾 KVK" },
    "hi": { "tab1": "🎤 आवाज़", "tab2": "💰 मंडी", "tab3": "🌤️ मौसम", "tab4": "🧪 मिट्टी", "tab5": "📝 सलाह", "tab6": "🔄 फसल चक्र", "tab7": "🚺 महिला", "tab8": "📜 योजनाएँ", "tab9": "🌾 केवीके" }
}
def t(key): return TEXTS.get(st.session_state.get("language", DEFAULT_LANGUAGE), TEXTS[DEFAULT_LANGUAGE]).get(key, key)

if "language" not in st.session_state: st.session_state.language = DEFAULT_LANGUAGE
if "history" not in st.session_state: st.session_state.history = []
if "lang_pref" not in st.session_state: st.session_state.lang_pref = "English"
if "farmer_profile" not in st.session_state: st.session_state.farmer_profile = ""
if "stop_voice" not in st.session_state: st.session_state.stop_voice = False
if "weather_city_from_gps" not in st.session_state: st.session_state.weather_city_from_gps = None

# ---------- Light Green CSS ----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    .stApp { background: linear-gradient(180deg, #f6f1e5 0%, #efe7d3 100%) !important; font-family: 'Inter', sans-serif; }
    h1, h2, h3 { color: #4a3f2b !important; font-weight: 600; }
    [data-testid="stSidebar"] { background: #d9c8a5 !important; }
    [data-testid="stSidebar"] * { color: #2f2516 !important; }
    .stButton>button { background: #7a5c2e; color: #fff9ec; border-radius: 30px; font-weight: 500; border: 1px solid #654a24; transition: 0.2s; }
    .stButton>button:hover { background: #5f4521; transform: scale(1.02); }
    .user-msg, .bot-msg { background: #fffaf0; border-radius: 20px; padding: 0.8rem; margin: 0.8rem 0; border-left: 5px solid #7a5c2e; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
    .stTabs [data-baseweb="tab-list"] { gap: 5px; background: #e8dbc0; padding: 5px; border-radius: 40px; }
    .stTabs [data-baseweb="tab"] { border-radius: 30px; padding: 6px 18px; font-weight: 500; color: #4a3f2b; }
    .stTabs [aria-selected="true"] { background: #6f8f3d; color: #fffaf0; }
    .km-earth-card { background: #fffaf0; border: 1px solid #dcc9a2; border-radius: 18px; padding: 0.8rem 1rem; }
</style>
""", unsafe_allow_html=True)

# ---------- Sidebar ----------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1998/1998626.png", width=70)
    st.title("KisanMitra")
    selected_lang = st.selectbox("Language", options=["en","hi"], format_func=lambda x: "English" if x=="en" else "हिंदी", index=0)
    if selected_lang != st.session_state.language:
        st.session_state.language = selected_lang
        st.session_state.lang_pref = "English" if selected_lang=="en" else "Hindi"
        st.rerun()
    st.markdown("---")
    st.subheader("Farmer Profile")
    st.session_state.farmer_profile = st.text_area("Your details (crops, land, location)", value=st.session_state.farmer_profile, height=100)
    st.markdown("---")
    st.subheader("Conversation History")
    if st.button("Clear History"):
        st.session_state.history = []
        st.rerun()
    for chat in reversed(st.session_state.history[-5:]):
        with st.expander(f"🗣️ {chat['q'][:40]}..."):
            st.write(f"**You:** {chat['q']}")
            st.write(f"**KisanMitra:** {chat['a'][:150]}...")

# ---------- Helper Functions (placeholders – replace with your actual implementations) ----------
def get_mandi_price(commodity, state):
    return {"commodity": commodity, "market": "Sample Mandi", "state": state, "price": "2000", "source": "Demo"}

def get_weather_forecast(city):
    return {"today": {"temp": 28, "condition": "Sunny", "advice": "Good for sowing"}, "tomorrow": {"temp": 30, "condition": "Partly cloudy", "advice": "Irrigate if needed"}}

def get_weather_alert(forecast):
    return "green", ["No alerts"]

def get_city_from_coords(lat, lon):
    return "Lucknow"

def analyze_soil_image(image):
    return "Soil appears loamy. Recommended: add organic compost."

def analyze_soil_pdf(pdf_bytes):
    return "PDF analysis: pH 6.5, NPK adequate."

def get_soil_advice(input_text):
    return "Based on your inputs, apply DAP and potash."

def get_crop_rotation_advice(crop):
    return f"After {crop}, plant legumes to fix nitrogen."

def get_women_schemes(district):
    return [{"name": "Mahila Kisan Sashaktikaran Pariyojana", "description": "Training and resources for women farmers"}]

def get_ai_response(query, lang_pref):
    return f"This is a demo response to: {query}"

def chatbot_response(query, lang_pref):
    return f"Chatbot demo: {query}"

# FIXED: detect_language without unicode_category
def detect_language(text):
    # Simple Devanagari detection
    if any('\u0900' <= c <= '\u097F' for c in text):
        return "Hindi"
    return "English"

def transcribe_audio(audio_bytes):
    return "Sample transcribed text"

def get_kvk_by_district(district):
    for kvk in KVK_DATA["kvk_centers"]:
        if kvk["district"].lower() == district.lower():
            return kvk
    return None

# GPS HTML component (required for tab3)
GPS_HTML = """
<div id="gps-form" style="display:none;">
    <form id="gpsForm" action="" method="get">
        <input type="hidden" name="gps_lat" id="gps_lat">
        <input type="hidden" name="gps_lon" id="gps_lon">
    </form>
</div>
<script>
function getLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(sendPosition, showError);
    } else {
        alert("Geolocation is not supported by this browser.");
    }
}
function sendPosition(position) {
    document.getElementById('gps_lat').value = position.coords.latitude;
    document.getElementById('gps_lon').value = position.coords.longitude;
    document.getElementById('gpsForm').submit();
}
function showError(error) {
    alert("Unable to get location: " + error.message);
}
</script>
<button onclick="getLocation()">📍 Use My Location</button>
"""

# ---------- Tabs ----------
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([t("tab1"), t("tab2"), t("tab3"), t("tab4"), t("tab5"), t("tab6"), t("tab7"), t("tab8"), t("tab9")])

# ----- TAB 1: VOICE -----
with tab1:
    st.header("Voice Assistant")
    st.caption("Speak your query or type below")
    audio_bytes = st.audio_input("Record your question")
    if audio_bytes:
        with st.spinner("Transcribing..."):
            txt_q = transcribe_audio(audio_bytes.getvalue())
        if txt_q:
            ans = get_ai_response(txt_q, st.session_state.lang_pref)
            st.markdown(f'<div class="user-msg">🗣️ <strong>You:</strong> {txt_q}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bot-msg">🤖 <strong>KisanMitra:</strong> {ans}</div>', unsafe_allow_html=True)
            st.session_state.history.append({"q": txt_q, "a": ans})
            detected_lang = detect_language(ans)
            tts_lang = "hi-IN" if detected_lang == "Hindi" else "en-US"
            st.components.v1.html(f'<script>var u=new SpeechSynthesisUtterance({json.dumps(ans)}); u.lang="{tts_lang}"; window.speechSynthesis.speak(u);</script>', height=0)

# ----- TAB 2: MARKET PRICES -----
with tab2:
    st.header("Mandi Prices")
    st.info("Live API ready – showing sample prices.")
    col1, col2 = st.columns(2)
    with col1: commodity = st.text_input("Commodity (e.g., Wheat, Rice)")
    with col2: state = st.text_input("State", "Uttar Pradesh")
    if st.button("Get Price"):
        if commodity:
            p = get_mandi_price(commodity, state)
            st.success(f"**{p['commodity']}** in {p['market']}, {p['state']}")
            st.metric("Price per quintal", f"₹{p['price']}")
            st.caption(f"Source: {p['source']}")

# ----- TAB 3: WEATHER (GPS fixed) -----
with tab3:
    st.header("Weather & Alerts")
    st.markdown('<div class="km-earth-card">📍 Use <strong>Use My Location</strong> and allow browser GPS. If permission is denied or phone GPS is OFF, weather will <strong>not</strong> load from location.</div>', unsafe_allow_html=True)
    st.markdown(GPS_HTML, unsafe_allow_html=True)
    st.caption("— OR —")
    manual_city = st.text_input("Enter district/city name", "Lucknow")
    city = manual_city
    
    if "gps_lat" in st.query_params and "gps_lon" in st.query_params:
        lat = st.query_params.get("gps_lat")
        lon = st.query_params.get("gps_lon")
        try:
            float(lat); float(lon)
            st.session_state.weather_city_from_gps = get_city_from_coords(lat, lon)
            st.success(f"📍 Location detected: {st.session_state.weather_city_from_gps}")
            st.query_params.clear()
        except (TypeError, ValueError):
            st.session_state.weather_city_from_gps = None

    weather_source = st.radio("Select weather source", ["Manual City", "Current Location"], horizontal=True)
    if weather_source == "Current Location":
        if st.session_state.weather_city_from_gps:
            city = st.session_state.weather_city_from_gps
            st.info(f"Using GPS location: {city}")
        else:
            st.warning("Current location unavailable. Please click 'Use My Location' and allow GPS permission.")
    
    if st.button("Get Weather"):
        if weather_source == "Current Location" and not st.session_state.weather_city_from_gps:
            st.error("❌ GPS location not available. Turn on location and allow permission, then tap 'Use My Location'.")
        else:
            forecast = get_weather_forecast(city)
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Today**")
                st.write(f"🌡️ {forecast['today']['temp']}°C, {forecast['today']['condition']}")
                st.write(f"💡 {forecast['today']['advice']}")
            with col2:
                st.write("**Tomorrow**")
                st.write(f"🌡️ {forecast['tomorrow']['temp']}°C, {forecast['tomorrow']['condition']}")
                st.write(f"💡 {forecast['tomorrow']['advice']}")
            alert_level, advice_list = get_weather_alert(forecast)
            if alert_level == "red":
                st.error("🚨 **Severe Weather Alert!**")
            elif alert_level == "orange":
                st.warning("⚠️ **Weather Advisory**")
            for adv in advice_list:
                st.write(f"- {adv}")

# ----- TAB 4: SOIL HEALTH -----
with tab4:
    st.header("Soil Health Analysis")
    st.subheader("Option 1: Upload a photo of your soil")
    soil_img = st.file_uploader("", type=["jpg","jpeg","png"])
    if soil_img:
        image = Image.open(soil_img); st.image(image, width=200)
        if st.button("Analyze Soil from Photo"):
            with st.spinner("Analyzing..."):
                advice = analyze_soil_image(image)
            st.markdown(f'<div class="bot-msg">📸 {advice}</div>', unsafe_allow_html=True)
    st.subheader("Option 2: Upload soil lab report (PDF)")
    pdf_file = st.file_uploader("", type=["pdf"])
    if pdf_file:
        if st.button("Analyze PDF Report"):
            with st.spinner("Reading PDF..."):
                advice = analyze_soil_pdf(pdf_file.read())
            st.markdown(f'<div class="bot-msg">📑 {advice}</div>', unsafe_allow_html=True)
    st.subheader("Option 3: Enter test results manually")
    soil_input = st.text_area("")
    if st.button("Get Manual Advice"):
        if soil_input:
            advice = get_soil_advice(soil_input)
            st.markdown(f'<div class="bot-msg">📋 {advice}</div>', unsafe_allow_html=True)

# ----- TAB 5: AI ADVICE (original) -----
with tab5:
    st.header("Personalised Farming Advice")
    query = st.text_area("Ask anything about your crops, pests, fertilisers, etc.")
    if st.button("Get Advice"):
        if query:
            with st.spinner("Generating advice..."):
                advice = get_ai_response(query, st.session_state.lang_pref)
            st.markdown(f'<div class="bot-msg">🌿 {advice}</div>', unsafe_allow_html=True)

# ----- TAB 6: CROP ROTATION (original) -----
with tab6:
    st.header("Crop Rotation Advisory")
    crop = st.text_input("Which crop did you grow last season?")
    if st.button("Suggest rotation"):
        if crop:
            advice = get_crop_rotation_advice(crop)
            st.info(advice)

# ----- TAB 7: WOMEN SCHEMES (original) -----
with tab7:
    st.header("Schemes for Women Farmers")
    district = st.text_input("Enter your district")
    if st.button("Show schemes"):
        if district:
            schemes = get_women_schemes(district)
            for scheme in schemes:
                st.markdown(f"**{scheme['name']}**")
                st.write(scheme['description'])
                st.markdown("---")

# ----- TAB 8: SCHEMES (original) -----
with tab8:
    st.header("Government Schemes")
    category_filter = st.selectbox("Filter by category", ["All", "Subsidy", "Loan", "Training", "Equipment"])
    filtered = [s for s in SCHEMES_DATA.get("schemes", []) if category_filter == "All" or s.get("category") == category_filter]
    cols = st.columns(2)
    for idx, scheme in enumerate(filtered):
        with cols[idx % 2]:
            with st.container(border=True):
                st.markdown(f"**{scheme['name']}**")
                st.caption(f"*Category: {scheme['category']}*")
                st.write(scheme['description'])
                st.markdown(f"[🔗 Know More]({scheme['link']})")

# ----- TAB 9: KVK SUPPORT (original) -----
with tab9:
    st.header("Krishi Vigyan Kendra (KVK)")
    st.caption("Find your nearest KVK centre and get expert agricultural support.")
    district = st.text_input("Enter your district name:", placeholder="e.g., Lucknow, Prayagraj, Bareilly")
    if st.button("Find KVK", use_container_width=True):
        kvk = get_kvk_by_district(district)
        if kvk:
            st.success(f"**{kvk['center_name']}**")
            st.markdown(f"**Head:** {kvk['head']}")
            st.markdown(f"**📞 Contact:** {kvk['contact']}")
            st.markdown(f"**📧 Email:** {kvk['email']}")
            st.markdown(f"**🛠️ Services offered:** {kvk['services']}")
        else:
            st.warning(f"No KVK data available for district: {district}. Please visit [ICAR KVK Portal](https://kvk.icar.gov.in/).")
    st.info("KVK centres provide free soil testing, seed distribution, training, and crop‑specific advice. Contact them for immediate help.")

# ----- FOOTER & FLOATING CHATBOT (original) -----
st.markdown("---")
st.caption("🌾 KisanMitra – Voice-First, Real-Time, Personalized Farming Companion | Jai Kisan!")

with st.popover("💬 Help", use_container_width=False, help="Ask me about farming or using the app"):
    st.markdown("### KisanMitra Assistant")
    st.info("Ask me anything about farming or using the app.")
    if st.button("🔊 Play Welcome", key="play_help_greeting"):
        greeting = "नमस्ते! मैं आपकी क्या मदद कर सकता हूँ?"
        st.components.v1.html(f'<script>var u=new SpeechSynthesisUtterance({json.dumps(greeting)}); u.lang="hi-IN"; window.speechSynthesis.speak(u);</script>', height=0)
    
    audio_val = st.audio_input("Speak your question", key="chat_audio_popover")
    if audio_val:
        with st.spinner("Transcribing..."):
            text = transcribe_audio(audio_val.getvalue())
        if text:
            st.markdown(f"🗣️ **You:** {text}")
            with st.spinner("Thinking..."):
                ans = chatbot_response(text, st.session_state.lang_pref)
            st.success(f"🤖 **Answer:** {ans}")
            detected_ans_lang = detect_language(ans)
            tts_lang = "hi-IN" if detected_ans_lang == "Hindi" else "en-US"
            st.components.v1.html(f'<script>var u=new SpeechSynthesisUtterance({json.dumps(ans)}); u.lang="{tts_lang}"; window.speechSynthesis.speak(u);</script>', height=0)
        else:
            st.error("Could not understand audio.")
    text_q = st.text_input("Or type your question", key="chat_text_popover")
    if text_q:
        st.markdown(f"🗣️ **You:** {text_q}")
        with st.spinner("Thinking..."):
            ans = chatbot_response(text_q, st.session_state.lang_pref)
        st.success(f"🤖 **Answer:** {ans}")
        detected_ans_lang = detect_language(ans)
        tts_lang = "hi-IN" if detected_ans_lang == "Hindi" else "en-US"
        st.components.v1.html(f'<script>var u=new SpeechSynthesisUtterance({json.dumps(ans)}); u.lang="{tts_lang}"; window.speechSynthesis.speak(u);</script>', height=0)