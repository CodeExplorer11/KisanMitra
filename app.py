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

# ========== LANDING PAGE ==========
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
      <text x='42' y='84' font-family='Inter, sans-serif' font-size='44' fill='#3f321f'>Bhoomi Bandhu</text>
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
        <div class="landing-title">🌾 KisanMitra</div>
        <div class="landing-subtitle">Voice‑First Farming Companion with a classic earthy feel</div>
        <img src="data:image/svg+xml;utf8,{quote(landing_svg)}" class="landing-image" alt="KisanMitra Farm Banner">
        <p style="margin-top:1rem;">Tap below to begin your smart farming journey</p>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("Start Now", use_container_width=True):
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
if not GEMINI_API_KEY:
    st.error("❌ Gemini API key missing.")
    st.stop()

GEMINI_API_KEY = GEMINI_API_KEY.strip().strip('"').strip("'")
available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
if not available_models:
    st.error("No models available.")
    st.stop()
MODEL_NAME = available_models[0]
st.info(f"Using model: {MODEL_NAME}")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(MODEL_NAME)
vision_model = genai.GenerativeModel(MODEL_NAME)

# ---------- Embedded Data ----------
SCHEMES_DATA = {
    "schemes": [
        {"category": "Crop Insurance", "name": "Pradhan Mantri Fasal Bima Yojana", "description": "Low premium crop insurance (2% for Kharif, 1.5% for Rabi).", "link": "https://pmfby.gov.in/"},
        {"category": "Women Farmers", "name": "Mahila Kisan Sashaktikaran Pariyojana", "description": "Skill development and livelihood support for women farmers.", "link": "https://nrlm.gov.in/"},
        {"category": "Direct Income Support", "name": "PM-Kisan Samman Nidhi", "description": "₹6,000 per year income support.", "link": "https://pmkisan.gov.in/"},
        {"category": "Pension & Social Security", "name": "PM Kisan Maan Dhan Yojana", "description": "₹3,000 monthly pension after age 60.", "link": "https://maandhan.in/"},
        {"category": "Soil Health", "name": "Soil Health Card Scheme", "description": "Free soil testing and nutrient recommendations.", "link": "https://soilhealth.dac.gov.in/"}
    ]
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

# ---------- Earthy CSS ----------
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

# ---------- Helper Functions (Original, full) ----------
def transcribe_audio(audio_bytes):
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio_data = recognizer.record(source)
        return recognizer.recognize_google(audio_data)
    except: return None

def detect_language(text):
    return "Hindi" if any('\u0900' <= c <= '\u097f' for c in text) else "English"

def get_ai_response(question, lang):
    detected = detect_language(question)
    force_lang = "Hindi. You MUST answer in Hindi using Devanagari script. No English words." if detected == "Hindi" else "English"
    prompt = f"""You are KisanMitra, a friendly expert farming assistant.
Response language: {force_lang}
Farmer asked: "{question}"
Give a short, practical, actionable answer (max 3 sentences). CRITICAL: Answer in the same language as the question."""
    try: return model.generate_content(prompt).text
    except Exception as e: return f"⚠️ AI error: {str(e)}"

def get_weather_forecast(city):
    # Simulated forecast (replace with real API if you have key)
    return {
        "today": {"temp": 32, "humidity": 65, "condition": "Sunny", "advice": "Good for sowing."},
        "tomorrow": {"temp": 28, "humidity": 85, "condition": "Heavy rain expected", "advice": "Avoid spraying pesticides."}
    }

def get_weather_alert(forecast):
    cond = forecast["tomorrow"]["condition"].lower()
    hum = forecast["tomorrow"]["humidity"]
    if "heavy rain" in cond:
        return "red", ["⚠️ Heavy rain expected tomorrow! Harvest ripe crops immediately.", "🌾 Cover harvested crops with tarpaulin.", "🛑 Postpone fertiliser and pesticide spraying."]
    elif hum > 80:
        return "orange", ["💧 High humidity – risk of fungal diseases. Inspect crops.", "🔍 Apply organic fungicide if dry interval appears."]
    return "normal", ["✅ Weather suitable for normal farming activities."]

def get_mandi_price(commodity, state="Uttar Pradesh"):
    mock = {"wheat":2250,"rice":2180,"mustard":5650,"tomato":1800,"potato":1200,"onion":2500,"corn":2120,"chana":5200}
    price = mock.get(commodity.lower(), 2000)
    return {"commodity": commodity, "price": price, "market": "Sample Mandi (Live API ready)", "state": state, "source": "Mock data"}

def analyze_soil_image(image):
    prompt = """You are a soil expert. Analyze this soil image and provide:
    1. Estimated soil type (sandy, clay, loamy, etc.)
    2. General health indication (good, moderate, poor)
    3. Simple recommendation for improvement. Keep answer short."""
    try: return vision_model.generate_content([prompt, image]).text
    except: return "Error analyzing image."

def analyze_soil_pdf(pdf_bytes):
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        text = "".join([page.extract_text() for page in reader.pages])
        if not text.strip(): return "Could not read text from PDF."
        return model.generate_content(f"Analyze this soil report and give recommendations: {text[:1500]}").text
    except: return "Error processing PDF."

def get_soil_advice(soil_data):
    try: return model.generate_content(f"Analyze soil: {soil_data}. Give short advice on fertilizer and pH correction.").text
    except: return "Unable to analyze soil data."

def get_personalized_advice(profile, question):
    try: return model.generate_content(f"Farmer profile: {profile}\nQuestion: {question}\nGive personalized, practical advice.").text
    except: return "AI temporarily unavailable."

def get_crop_damage_advice(crop, damage_type, lang):
    prompt = f"{crop} field damaged by {damage_type}. Give short recovery steps in {lang}: 1) Drain water 2) Fertiliser to apply 3) Disease prevention 4) When to replant. Keep under 100 words."
    try: return model.generate_content(prompt).text
    except: return "Unable to generate advice. Please consult local agriculture officer."

CROP_ROTATION = {
    "sugarcane": {"next_crops": ["wheat","mustard","potato"], "advice": "Sugarcane depletes nitrogen. Grow wheat or mustard with extra nitrogen.", "soil_condition": "Add 20% more nitrogen."},
    "wheat": {"next_crops": ["rice","maize","pulses"], "advice": "Wheat leaves residual phosphorus. Good for legumes.", "soil_condition": "Reduce DAP by 25%."},
    "rice": {"next_crops": ["wheat","mustard","vegetables"], "advice": "Rice depletes zinc. Apply zinc sulfate before next crop.", "soil_condition": "Zinc deficiency likely. Add organic matter."},
    "potato": {"next_crops": ["maize","onion","cabbage"], "advice": "Potato depletes potassium. Add potash for next crop.", "soil_condition": "Potassium low. Use NPK 20:20:20."},
    "tomato": {"next_crops": ["beans","peas","cucumber"], "advice": "Tomato susceptible to same pests. Rotate with legumes.", "soil_condition": "Good for nitrogen-fixing crops."}
}

def get_crop_rotation_advice(prev, next_c):
    p = prev.lower(); n = next_c.lower()
    if p in CROP_ROTATION:
        if n in CROP_ROTATION[p]["next_crops"]:
            return {"suitable": True, "advice": CROP_ROTATION[p]["advice"], "soil": CROP_ROTATION[p]["soil_condition"]}
        else:
            return {"suitable": False, "advice": f"{prev} to {next_c} not ideal. Recommended: {', '.join(CROP_ROTATION[p]['next_crops'])}", "soil": "Consider soil testing."}
    return {"suitable": True, "advice": "Crop rotation is good for soil health.", "soil": "Add compost before sowing."}

def chatbot_response(user_input, lang="English"):
    detected = detect_language(user_input)
    force_lang = "Hindi. You MUST answer in Hindi using Devanagari script. No English words." if detected == "Hindi" else "English"
    prompt = f"""You are a helpful farming assistant chatbot for KisanMitra.
Response language: {force_lang}
User says: "{user_input}"
Give a short, friendly, helpful answer (max 2 sentences). Keep it warm and encouraging.
CRITICAL: Answer in the same language as the user."""
    try: return model.generate_content(prompt).text
    except Exception as e: return f"⚠️ Error: {str(e)[:100]}"

def get_kvk_by_district(district):
    for center in KVK_DATA["kvk_centers"]:
        if center["district"].lower() == district.lower():
            return center
    return None

GPS_HTML = """
<div style="margin: 10px 0;">
    <button id="gps-btn" style="background:#7a5c2e; color:white; padding:8px 16px; border:none; border-radius:30px; cursor:pointer;">📍 Use My Location</button>
    <p id="gps-status" style="margin-top:8px; font-size:0.85rem;"></p>
</div>
<script>
    const btn = document.getElementById('gps-btn');
    const status = document.getElementById('gps-status');
    btn.onclick = function() {
        if (!navigator.geolocation) {
            status.innerText = "GPS not supported.";
            return;
        }
        status.innerText = "Getting location...";
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const lat = pos.coords.latitude;
                const lon = pos.coords.longitude;
                status.innerText = "Location captured! Loading weather...";
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = '';
                const latInp = document.createElement('input');
                latInp.name = 'gps_lat';
                latInp.value = lat;
                const lonInp = document.createElement('input');
                lonInp.name = 'gps_lon';
                lonInp.value = lon;
                form.appendChild(latInp);
                form.appendChild(lonInp);
                document.body.appendChild(form);
                form.submit();
            },
            (err) => {
                status.innerText = "Location permission denied. Please enable GPS.";
                console.error(err);
            }
        );
    };
</script>
"""

def get_city_from_coords(lat, lon):
    try:
        r = requests.get(f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json", headers={'User-Agent':'KisanMitra'})
        return r.json().get('address', {}).get('city') or r.json().get('address', {}).get('town') or "Your Location"
    except: return "Your Location"

# ---------- TABS (original full content) ----------
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([t("tab1"), t("tab2"), t("tab3"), t("tab4"), t("tab5"), t("tab6"), t("tab7"), t("tab8"), t("tab9")])

# ----- TAB 1: VOICE (with stop button) -----
with tab1:
    st.header("Ask by Voice")
    if st.button("⏹️ Stop Recording", key="stop_voice_btn"):
        st.session_state.stop_voice = True
        st.rerun()
    if st.session_state.stop_voice:
        st.info("Recording stopped. Click 'Enable Recording' to ask again.")
        if st.button("🎤 Enable Recording", key="enable_voice"):
            st.session_state.stop_voice = False
            st.rerun()
    else:
        audio_val = st.audio_input("Tap to record your question", key="main_audio")
        if audio_val:
            with st.spinner("Transcribing..."):
                text = transcribe_audio(audio_val.getvalue())
            if text:
                st.markdown(f'<div class="user-msg">🗣️ <strong>You:</strong> {text}</div>', unsafe_allow_html=True)
                with st.spinner("Getting advice..."):
                    ans = get_ai_response(text, st.session_state.lang_pref)
                st.markdown(f'<div class="bot-msg">🤖 <strong>KisanMitra:</strong> {ans}</div>', unsafe_allow_html=True)
                st.session_state.history.append({"q": text, "a": ans})
                detected_lang = detect_language(ans)
                tts_lang = "hi-IN" if detected_lang == "Hindi" else "en-US"
                st.components.v1.html(f'<script>var u=new SpeechSynthesisUtterance({json.dumps(ans)}); u.lang="{tts_lang}"; window.speechSynthesis.speak(u);</script>', height=0)
            else:
                st.error("Could not understand. Please speak clearly.")
    st.divider()
    st.subheader("Or type your question")
    txt_q = st.text_input("Type here")
    if st.button("Ask", key="ask_text"):
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

# ----- TAB 4: SOIL HEALTH (full options) -----
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

# ----- TAB 5: PERSONALIZED ADVICE + Crop Damage Recovery -----
with tab5:
    st.header("Personalized Farming Advice")
    st.subheader("🌾 Crop Damage Recovery (Heavy Rain / Waterlogging)")
    damage_crop = st.selectbox("Affected crop", ["Wheat", "Rice", "Pulses"])
    damage_type = st.selectbox("Type of damage", ["Waterlogging", "Hailstorm", "Strong wind"])
    if st.button("Get Recovery Advice", key="recovery_btn"):
        advice = get_crop_damage_advice(damage_crop, damage_type, st.session_state.lang_pref)
        st.markdown(f'<div class="bot-msg">🌿 {advice}</div>', unsafe_allow_html=True)
    st.divider()
    if not st.session_state.farmer_profile:
        st.warning("Please fill your Farmer Profile in the sidebar first.")
    else:
        question = st.text_area("What specific advice do you need? (e.g., sowing time, pest control, fertilizer)")
        if st.button("Get Personalized Advice"):
            if question:
                advice = get_personalized_advice(st.session_state.farmer_profile, question)
                st.markdown(f'<div class="bot-msg">🎯 {advice}</div>', unsafe_allow_html=True)

# ----- TAB 6: CROP ROTATION (with Gemini) -----
with tab6:
    st.header("Crop Rotation Advisor")
    col1, col2 = st.columns(2)
    with col1: previous_crop = st.selectbox("Previous crop grown", ["Sugarcane","Wheat","Rice","Potato","Tomato","Maize"])
    with col2: next_crop = st.selectbox("Crop you want to grow next", ["Wheat","Mustard","Rice","Potato","Tomato","Maize","Pulses","Onion"])
    if st.button("Get Rotation Advice"):
        adv = get_crop_rotation_advice(previous_crop, next_crop)
        if adv["suitable"]: st.success(f"✅ Good rotation choice!")
        else: st.warning(f"⚠️ {adv['advice']}")
        st.info(f"🌱 **Soil advice:** {adv['soil']}")
        with st.spinner("Getting detailed AI advice..."):
            prompt = f"Farmer grew {previous_crop} and wants to grow {next_crop}. Give soil management and fertilizer advice."
            detailed = model.generate_content(prompt)
            st.markdown(f'<div class="bot-msg">🤖 <strong>AI Suggestion:</strong><br>{detailed.text}</div>', unsafe_allow_html=True)

# ----- TAB 7: WOMEN EMPOWERMENT (full) -----
with tab7:
    st.header("Women Farmer Empowerment")
    safety_tips = ["🌾 Always inform a family member before going to the field alone.", "📞 Save local police and women’s helpline numbers on speed dial.", "👭 Form a group of women farmers in your village for mutual support.", "🌿 Keep a basic first‑aid kit in your farming bag.", "🚜 Learn about government schemes for women farmers – ask KisanMitra!"]
    tip_idx = datetime.datetime.now().day % len(safety_tips)
    st.info(f"💡 **Safety Tip of the Day:** {safety_tips[tip_idx]}")
    if st.button("🔊 Read Tip Aloud"):
        st.components.v1.html(f'<script>var u=new SpeechSynthesisUtterance("{safety_tips[tip_idx]}"); u.lang="hi-IN"; window.speechSynthesis.speak(u);</script>', height=0)
    st.divider()
    st.subheader("Emergency & Helpline Numbers")
    contacts = {"Women Helpline (India)": "1091", "National Commission for Women": "7827170170", "Local Police": "100", "Women Farmer Support (MKSP)": "1800‑180‑1551"}
    for name, num in contacts.items():
        st.write(f"**{name}:** `{num}`")
    st.divider()
    st.subheader("Small‑Scale Farming for Women")
    ideas = {"🥬 Kitchen Garden": "Grow vegetables in small space. Low investment.", "🐔 Poultry": "Start with 10‑20 chicks. Eggs and meat provide income.", "🍄 Mushroom Cultivation": "Grows in dark sheds. High return in 30 days.", "🐄 Dairy (1‑2 cows)": "Daily milk income. Government subsidy available."}
    for idea, desc in ideas.items():
        with st.expander(idea):
            st.write(desc)
            if st.button(f"Ask KisanMitra about {idea}", key=f"ask_{idea}"):
                ans = get_ai_response(f"How to start {idea} as a woman farmer?", st.session_state.lang_pref)
                st.markdown(f'<div class="bot-msg">🤖 {ans}</div>', unsafe_allow_html=True)
    st.divider()
    st.subheader("Government Schemes for Women")
    women_schemes = [s for s in SCHEMES_DATA["schemes"] if s["category"] == "Women Farmers"]
    for s in women_schemes:
        with st.expander(s["name"]):
            st.write(s["description"])
            st.markdown(f"[🔗 Know More]({s['link']})")

# ----- TAB 8: GOVERNMENT SCHEMES (categorized) -----
with tab8:
    st.header("Government Schemes for Farmers")
    categories = sorted(list(set([s['category'] for s in SCHEMES_DATA['schemes']])))
    selected_cat = st.radio("Filter by Category:", ["All"] + categories, horizontal=True)
    filtered = SCHEMES_DATA['schemes']
    if selected_cat != "All": filtered = [s for s in filtered if s['category'] == selected_cat]
    cols = st.columns(2)
    for idx, scheme in enumerate(filtered):
        with cols[idx % 2]:
            with st.container(border=True):
                st.markdown(f"**{scheme['name']}**")
                st.caption(f"*Category: {scheme['category']}*")
                st.write(scheme['description'])
                st.markdown(f"[🔗 Know More]({scheme['link']})")

# ----- TAB 9: KVK SUPPORT -----
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

# ----- FOOTER & FLOATING CHATBOT (greeting on button) -----
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