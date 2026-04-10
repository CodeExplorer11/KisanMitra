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

# ========== INITIALIZE SESSION STATE ==========
if "entered_app" not in st.session_state:
    st.session_state.entered_app = False
if "selected_feature" not in st.session_state:
    st.session_state.selected_feature = None

# ========== LANDING PAGE ==========
if not st.session_state.entered_app:
    st.markdown("""
    <style>
        .main > div { padding: 0rem; }
        .stApp { background: linear-gradient(145deg, #2d6a4f, #1b4332) !important; }
        .landing-wrapper {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background-image: url("https://seedballs.in/cdn/shop/articles/farmers_day.jpg?v%3D1766078534%26width%3D500&tbnid=RlsNKxP2FS9MqM&vet=1&imgrefurl=https://seedballs.in/blogs/blog/farmers-day-a-powerful-tribute-to-the-heroes-who-feed-the-world?srsltid%3DAfmBOopnwkDKXlplhKwnEADvnfam6_i_f2Sn9o2cIoE2-xl-FURpeHvw&docid=76GBYt0Qf-3NPM&w=500&h=750&hl=en-IN&source=sh/x/im/m1/4&kgs=075546ed03e1bd58&utm_source=sh/x/im/m1/4");
            background-size: cover; background-position: center;
            display: flex; flex-direction: column; justify-content: center; align-items: center;
            text-align: center; color: white; font-family: 'Inter', sans-serif; z-index: 999;
        }
        .landing-wrapper::before {
            content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.4); z-index: -1;
        }
        .landing-title { font-size: 3rem; font-weight: 700; margin-bottom: 0.5rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); }
        .landing-tagline { font-size: 1.5rem; font-weight: 500; margin-bottom: 3rem; text-shadow: 1px 1px 2px rgba(0,0,0,0.5); }
        .stButton { position: fixed; bottom: 80px; left: 0; right: 0; text-align: center; z-index: 1000; }
        .stButton > button {
            background-color: #f4a261; color: #1b4332; border: none; border-radius: 60px;
            padding: 12px 32px; font-size: 1.2rem; font-weight: bold; width: auto; min-width: 200px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2); transition: 0.2s;
        }
        .stButton > button:hover { background-color: #e76f51; transform: scale(1.02); }
    </style>
    <div class="landing-wrapper">
        <div class="landing-title">🌾 KisanMitra</div>
        <div class="landing-tagline">Har Kisan ka Digital Saathi</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Start Now", use_container_width=False):
        st.session_state.entered_app = True
        st.rerun()
    st.stop()

# ========== MAIN APP BACKGROUND (greenish theme) ==========
st.markdown("""
<style>
    .stApp { background: linear-gradient(180deg, #e8f5e9 0%, #c8e6c9 100%) !important; font-family: 'Inter', sans-serif; overflow: auto; }
    [data-testid="stSidebar"] { background: #d9c8a5 !important; }
    [data-testid="stSidebar"] * { color: #2f2516 !important; }
    .main > div { padding: 0rem 1rem; }
    /* Feature card styling – greenish */
    .feature-card {
        background: white; border-radius: 20px; padding: 1.2rem 0.5rem; text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); transition: 0.2s; cursor: pointer;
        border: 1px solid #a5d6a7; margin-bottom: 1rem;
        background-color: #f1f8e9;
    }
    .feature-card:hover { transform: translateY(-4px); box-shadow: 0 8px 20px rgba(0,0,0,0.1); background-color: #e8f5e9; }
    .feature-icon { font-size: 2.5rem; margin-bottom: 0.5rem; }
    .feature-title { font-weight: 600; font-size: 1rem; margin-bottom: 0.3rem; color: #2e7d32; }
    .feature-desc { font-size: 0.75rem; color: #558b2f; }
    /* Make buttons look like cards */
    div[data-testid="column"] > div > div > button {
        background: #f1f8e9 !important;
        border: 1px solid #a5d6a7 !important;
        border-radius: 20px !important;
        padding: 1rem 0.5rem !important;
        height: auto !important;
        white-space: normal !important;
        font-family: inherit !important;
        transition: 0.2s;
    }
    div[data-testid="column"] > div > div > button:hover {
        background: #e8f5e9 !important;
        transform: translateY(-4px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

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
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(MODEL_NAME)
vision_model = genai.GenerativeModel(MODEL_NAME)

# ---------- Multilingual ----------
SUPPORTED_LANGS = {"en": "English", "hi": "हिंदी"}
DEFAULT_LANGUAGE = "en"
if "language" not in st.session_state:
    st.session_state.language = DEFAULT_LANGUAGE

def t(key):
    translations = {
        "en": {
            "sidebar_title": "KisanMitra", "sidebar_lang": "Language", "sidebar_profile": "Farmer Profile",
            "sidebar_profile_placeholder": "Your details (crops, land, location)", "sidebar_history": "Conversation History",
            "sidebar_clear": "Clear History",
        },
        "hi": {
            "sidebar_title": "किसान मित्र", "sidebar_lang": "भाषा", "sidebar_profile": "किसान प्रोफ़ाइल",
            "sidebar_profile_placeholder": "आपका विवरण (फसलें, ज़मीन, स्थान)", "sidebar_history": "बातचीत इतिहास",
            "sidebar_clear": "इतिहास साफ़ करें",
        }
    }
    return translations[st.session_state.get("language", DEFAULT_LANGUAGE)].get(key, key)

if "history" not in st.session_state: st.session_state.history = []
if "lang_pref" not in st.session_state: st.session_state.lang_pref = "English"
if "farmer_profile" not in st.session_state: st.session_state.farmer_profile = ""
if "stop_voice" not in st.session_state: st.session_state.stop_voice = False
if "weather_city_from_gps" not in st.session_state: st.session_state.weather_city_from_gps = None
if "last_weather_data" not in st.session_state: st.session_state.last_weather_data = None

# ---------- Sidebar ----------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1998/1998626.png", width=70)
    st.title(t("sidebar_title"))
    selected_lang = st.selectbox(t("sidebar_lang"), options=["en","hi"], format_func=lambda x: "English" if x=="en" else "हिंदी", index=0 if st.session_state.language=="en" else 1)
    if selected_lang != st.session_state.language:
        st.session_state.language = selected_lang
        st.session_state.lang_pref = "English" if selected_lang=="en" else "Hindi"
        st.rerun()
    st.caption(f"Current UI language: {'English' if st.session_state.language=='en' else 'हिंदी'}")
    st.markdown("---")
    st.subheader(t("sidebar_profile"))
    st.session_state.farmer_profile = st.text_area("", value=st.session_state.farmer_profile, placeholder=t("sidebar_profile_placeholder"), height=100)
    st.markdown("---")
    st.subheader(t("sidebar_history"))
    if st.button(t("sidebar_clear")):
        st.session_state.history = []
        st.rerun()
    for chat in reversed(st.session_state.history[-5:]):
        with st.expander(f"🗣️ {chat['q'][:40]}..."):
            st.write(f"**You:** {chat['q']}")
            st.write(f"**KisanMitra:** {chat['a'][:150]}...")

# ---------- Helper Functions (unchanged) ----------
def transcribe_audio(audio_bytes):
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio_data = recognizer.record(source)
        return recognizer.recognize_google(audio_data)
    except: return None

def detect_language(text):
    return "Hindi" if any('\u0900' <= c <= '\u097f' for c in text) else "English"

def speak_text(text, lang):
    if lang == "Hindi":
        js = f"""
        <script>
            var utterance = new SpeechSynthesisUtterance({json.dumps(text)});
            utterance.lang = 'hi-IN';
            var voices = window.speechSynthesis.getVoices();
            var hindiVoice = voices.find(voice => voice.lang === 'hi-IN');
            if (hindiVoice) utterance.voice = hindiVoice;
            window.speechSynthesis.speak(utterance);
        </script>
        """
    else:
        js = f'<script>var u=new SpeechSynthesisUtterance({json.dumps(text)}); u.lang="en-US"; window.speechSynthesis.speak(u);</script>'
    st.components.v1.html(js, height=0)

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
    kvk_data = [
        {"district": "Lucknow", "center_name": "KVK, Lucknow", "head": "Dr. A. K. Singh", "contact": "+91-522-1234567", "email": "kvk.lucknow@icar.gov.in", "services": "Soil testing, seed production, organic farming training."},
        {"district": "Prayagraj", "center_name": "KVK, Naini", "head": "Dr. S. K. Sharma", "contact": "+91-532-1234567", "email": "kvk.naini@icar.gov.in", "services": "Integrated farming, vermicomposting, fruit preservation."},
        {"district": "Varanasi", "center_name": "KVK, Varanasi", "head": "Dr. R. K. Pandey", "contact": "+91-542-1234567", "email": "kvk.varanasi@icar.gov.in", "services": "Dairy management, aquaculture, mushroom."},
        {"district": "Bareilly", "center_name": "KVK, Bareilly", "head": "Dr. M. K. Sharma", "contact": "+91-581-1234567", "email": "kvk.bareilly@icar.gov.in", "services": "Wheat research, soil health cards, farm machinery."}
    ]
    for center in kvk_data:
        if center["district"].lower() == district.lower():
            return center
    return None

GPS_HTML = """
<div style="margin: 10px 0;">
    <button id="gps-btn" style="background:#7a5c2e; color:white; padding:10px 20px; border:none; border-radius:30px; cursor:pointer; font-size:16px;">📍 Use My Location</button>
    <p id="gps-status" style="margin-top:8px; font-size:0.85rem; color:#5c4b2f;"></p>
</div>
<form id="gps-form" method="post" action="">
    <input type="hidden" name="gps_lat" id="gps_lat">
    <input type="hidden" name="gps_lon" id="gps_lon">
</form>
<script>
    const btn = document.getElementById('gps-btn');
    const status = document.getElementById('gps-status');
    btn.onclick = function() {
        if (!navigator.geolocation) {
            status.innerText = "❌ GPS not supported by your browser.";
            return;
        }
        status.innerText = "📍 Requesting location... Please allow permission when the browser asks.";
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                document.getElementById('gps_lat').value = lat;
                document.getElementById('gps_lon').value = lon;
                document.getElementById('gps-form').submit();
                status.innerText = "✅ Location captured! Refreshing...";
            },
            (error) => {
                let msg = "❌ Location permission denied. ";
                if (error.code === 1) msg += "Tap the lock icon in address bar and allow location.";
                else if (error.code === 2) msg += "Location unavailable. Ensure GPS is on.";
                else msg += "Unknown error. Try again.";
                status.innerText = msg;
                console.error(error);
            },
            { enableHighAccuracy: true, timeout: 10000 }
        );
    };
</script>
"""

def get_city_from_coords(lat, lon):
    try:
        r = requests.get(f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json", headers={'User-Agent':'KisanMitra'})
        return r.json().get('address', {}).get('city') or r.json().get('address', {}).get('town') or "Your Location"
    except: return "Your Location"

# ---------- SCHEMES DATA ----------
SCHEMES_DATA = {
    "schemes": [
        {"category": "Crop Insurance", "name": "Pradhan Mantri Fasal Bima Yojana", "description": "Low premium crop insurance (2% for Kharif, 1.5% for Rabi).", "link": "https://pmfby.gov.in/"},
        {"category": "Women Farmers", "name": "Mahila Kisan Sashaktikaran Pariyojana", "description": "Skill development and livelihood support for women farmers.", "link": "https://nrlm.gov.in/"},
        {"category": "Direct Income Support", "name": "PM-Kisan Samman Nidhi", "description": "₹6,000 per year income support.", "link": "https://pmkisan.gov.in/"},
        {"category": "Pension & Social Security", "name": "PM Kisan Maan Dhan Yojana", "description": "₹3,000 monthly pension after age 60.", "link": "https://maandhan.in/"},
        {"category": "Soil Health", "name": "Soil Health Card Scheme", "description": "Free soil testing and nutrient recommendations.", "link": "https://soilhealth.dac.gov.in/"}
    ]
}

# ========== FEATURE FUNCTIONS (unchanged, but for brevity I keep them here – they are identical to previous version) ==========
def feature_voice_assistant():
    st.header("Ask by Voice")
    if st.button("Stop Recording", key="stop_voice_btn"):
        st.session_state.stop_voice = True
        st.rerun()
    if st.session_state.stop_voice:
        st.info("Recording stopped. Click 'Enable Recording' to ask again.")
        if st.button("Enable Recording", key="enable_voice"):
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
                speak_text(ans, "Hindi" if detect_language(ans) == "Hindi" else "English")
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
            speak_text(ans, "Hindi" if detect_language(ans) == "Hindi" else "English")

def feature_market_prices():
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

def feature_weather():
    st.header("Weather & Alerts")
    st.markdown(f'<div class="km-earth-card">📍 Use "Use My Location" and allow browser GPS.</div>', unsafe_allow_html=True)
    st.markdown(GPS_HTML, unsafe_allow_html=True)
    st.caption("— OR —")
    if "gps_lat" in st.query_params and "gps_lon" in st.query_params:
        lat = st.query_params.get("gps_lat"); lon = st.query_params.get("gps_lon")
        try:
            lat = float(lat); lon = float(lon)
            city = get_city_from_coords(lat, lon)
            st.session_state.weather_city_from_gps = city
            st.success(f"📍 Location detected: {city}")
            st.query_params.clear()
            st.rerun()
        except: pass
    manual_city = st.text_input("Enter district/city name", "Lucknow")
    city = manual_city
    weather_source = st.radio("Select weather source", ["Manual City", "Current Location"], horizontal=True)
    if weather_source == "Current Location":
        if st.session_state.weather_city_from_gps:
            city = st.session_state.weather_city_from_gps
            st.info(f"Using GPS location: {city}")
        else:
            st.warning("Current location unavailable. Please click 'Use My Location' and allow GPS permission.")
    if st.button("Get Weather", key="get_weather"):
        if weather_source == "Current Location" and not st.session_state.weather_city_from_gps:
            st.error("❌ GPS location not available.")
        else:
            forecast = get_weather_forecast(city)
            st.session_state.last_weather_data = {"city": city, "forecast": forecast}
            st.rerun()
    if st.button("Refresh Weather", key="refresh_weather"):
        if weather_source == "Current Location" and not st.session_state.weather_city_from_gps:
            st.error("❌ GPS location not available.")
        else:
            forecast = get_weather_forecast(city)
            st.session_state.last_weather_data = {"city": city, "forecast": forecast}
            st.rerun()
    if st.session_state.last_weather_data:
        data = st.session_state.last_weather_data
        forecast = data["forecast"]
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Today**")
            st.markdown(f"🌡️ {forecast['today']['temp']}°C, {forecast['today']['condition']}<br>💡 {forecast['today']['advice']}", unsafe_allow_html=True)
        with col2:
            st.write("**Tomorrow**")
            st.markdown(f"🌡️ {forecast['tomorrow']['temp']}°C, {forecast['tomorrow']['condition']}<br>💡 {forecast['tomorrow']['advice']}", unsafe_allow_html=True)
        alert_level, advice_list = get_weather_alert(forecast)
        if alert_level == "red":
            st.error("🚨 Severe Weather Alert!")
        elif alert_level == "orange":
            st.warning("⚠️ Weather Advisory")
        for adv in advice_list:
            st.write(f"- {adv}")

def feature_soil_health():
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

def feature_personalized_advice():
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

def feature_crop_rotation():
    st.header("Crop Rotation Advisor")
    col1, col2 = st.columns(2)
    with col1: previous_crop = st.selectbox("Previous crop grown", ["Sugarcane","Wheat","Rice","Potato","Tomato","Maize"])
    with col2: next_crop = st.selectbox("Crop you want to grow next", ["Wheat","Mustard","Rice","Potato","Tomato","Maize","Pulses","Onion"])
    if st.button("Get Rotation Advice"):
        adv = get_crop_rotation_advice(previous_crop, next_crop)
        if adv["suitable"]: st.success(f"✅ Good rotation choice!")
        else: st.warning(f"⚠️ {adv['advice']}")
        st.info(f"🌱 Soil advice: {adv['soil']}")
        with st.spinner("Getting detailed AI advice..."):
            prompt = f"Farmer grew {previous_crop} and wants to grow {next_crop}. Give soil management and fertilizer advice."
            detailed = model.generate_content(prompt)
            st.markdown(f'<div class="bot-msg">🤖 AI Suggestion:<br>{detailed.text}</div>', unsafe_allow_html=True)

def feature_women_empowerment():
    st.header("Women Farmer Empowerment")
    safety_tips = [
        "🌾 Always inform a family member before going to the field alone.",
        "📞 Save local police and women’s helpline numbers on speed dial.",
        "👭 Form a group of women farmers in your village for mutual support.",
        "🌿 Keep a basic first‑aid kit in your farming bag.",
        "🚜 Learn about government schemes for women farmers – ask KisanMitra!"
    ]
    tip_idx = datetime.datetime.now().day % len(safety_tips)
    st.info(f"💡 Safety Tip of the Day: {safety_tips[tip_idx]}")
    if st.button("Read Tip Aloud"):
        speak_text(safety_tips[tip_idx], "Hindi")
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

def feature_government_schemes():
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

def feature_kvk():
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
    st.info("KVK centres provide free soil testing, seed distribution, training, and crop‑specific advice.")

def feature_nabard():
    st.header("🏦 NABARD & Regional Rural Banks (RRB)")
    st.caption("Empowering rural India with credit, schemes, and local banking support.")
    with st.expander("🤖 Find Schemes for You (AI-Powered)", expanded=False):
        st.markdown("Tell us about your farm – we'll recommend relevant NABARD schemes and RRB services.")
        with st.form("nabard_form"):
            col1, col2 = st.columns(2)
            with col1: crop_adv = st.text_input("Main crop(s)", placeholder="e.g., Wheat, Rice")
            with col2: land_adv = st.text_input("Land size (acres)", placeholder="e.g., 2, 5")
            location_adv = st.text_input("State/District", placeholder="e.g., Uttar Pradesh")
            submitted = st.form_submit_button("Get Personalized Advice")
            if submitted:
                with st.spinner("Analyzing schemes..."):
                    prompt = f"""Based on farmer profile: crops={crop_adv}, land={land_adv}, location={location_adv}. Recommend relevant NABARD schemes (KCC, Interest Subvention, MKSP, AMI, FPO) and RRB services. Keep short."""
                    try:
                        response = model.generate_content(prompt)
                        st.success("**AI Recommendation:**")
                        st.markdown(f'<div class="bot-msg">🤖 {response.text}</div>', unsafe_allow_html=True)
                    except: st.error("AI error.")
    with st.expander("📚 NABARD Schemes (Categorised)", expanded=False):
        nabard_schemes = {
            "Credit & Loans": [{"name": "Kisan Credit Card (KCC)", "desc": "Flexible credit for cultivation.", "link": "https://www.nabard.org/content.aspx?id=566"}],
            "Interest Subvention": [{"name": "Interest Subvention Scheme", "desc": "Short‑term loans at 7% interest.", "link": "https://www.nabard.org/auth/writereaddata/File/Interest%20Subvention%20Scheme.pdf"}],
            "Women Farmers": [{"name": "Mahila Kisan Sashaktikaran Pariyojana (MKSP)", "desc": "Skill development for women.", "link": "https://nrlm.gov.in/"}]
        }
        for cat, schemes in nabard_schemes.items():
            st.subheader(cat)
            for sch in schemes:
                st.markdown(f"**{sch['name']}** – {sch['desc']} [🔗]({sch['link']})")
    with st.expander("💰 Kisan Credit Card & Loan Benefits", expanded=False):
        st.subheader("Kisan Credit Card (KCC)")
        st.markdown("Covers all cultivation expenses. Visit any bank or RRB.")
        loan_amt = st.number_input("Loan amount (₹)", min_value=10000, max_value=300000, step=10000, value=100000)
        yearly_saving = (loan_amt * 2) / 100
        st.metric("Yearly Saving (approx)", f"₹{yearly_saving:,.2f}")
    with st.expander("🏦 Regional Rural Banks (RRBs)", expanded=False):
        st.markdown("Find RRB contacts by state (example data).")
        state_rrb = st.selectbox("Select state", ["Uttar Pradesh", "Bihar", "Madhya Pradesh"])
        if st.button("Show Example RRB"):
            if state_rrb == "Uttar Pradesh":
                st.success("Prathama UP Gramin Bank – 1800‑180‑1234")
            elif state_rrb == "Bihar":
                st.success("Dakshin Bihar Gramin Bank – 0612-2221234")
            else:
                st.success("Madhyanchal Gramin Bank – 0755-2551234")
    with st.expander("🔔 Live Updates & Grievance", expanded=False):
        st.markdown("[NABARD WhatsApp Channel](https://wa.me/91XXXXXXXXXX?text=Join) | [NIVARAN Portal](https://www.nabard.org/content.aspx?id=607)")

# ========== DASHBOARD (2 rows × 5 columns, greenish) ==========
def show_dashboard():
    st.markdown("""
    <div style='background:#e8f5e9;padding:0.8rem 1.2rem;border-radius:20px;
    border:1px solid #a5d6a7;margin-bottom:1rem'>
        <h3 style='margin:0;color:#2e7d32;'>🌾 KisanMitra</h3>
        <p style='margin:0;color:#558b2f;font-size:0.85rem;'>AI-powered smart farming assistant</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("### 🌟 Choose a Service")
    features = [
        ("voice", "Voice Assistant", "🎤", "Ask farming questions by voice", feature_voice_assistant),
        ("market", "Market Prices", "💰", "Live mandi rates", feature_market_prices),
        ("weather", "Weather Intelligence", "🌤️", "Forecast & alerts", feature_weather),
        ("soil", "Soil Analysis", "🧪", "Upload photo or PDF", feature_soil_health),
        ("advice", "AI Advice", "📝", "Personalized recommendations", feature_personalized_advice),
        ("rotation", "Crop Rotation", "🔄", "Plan your next crop", feature_crop_rotation),
        ("women", "Women Empowerment", "🚺", "Schemes & safety", feature_women_empowerment),
        ("schemes", "Govt Schemes", "📜", "All government schemes", feature_government_schemes),
        ("kvk", "KVK Support", "🌾", "Find nearest KVK", feature_kvk),
        ("nabard", "NABARD & RRB", "🏦", "Loans & banking", feature_nabard),
    ]
    # Split into two rows of 5 columns each
    row1 = features[:5]
    row2 = features[5:]
    # Display first row (5 columns)
    cols = st.columns(5)
    for idx, (key, title, icon, desc, func) in enumerate(row1):
        with cols[idx]:
            if st.button(f"{icon}\n\n**{title}**\n\n{desc}", use_container_width=True):
                st.session_state.selected_feature = key
                st.rerun()
    # Display second row (5 columns)
    cols = st.columns(5)
    for idx, (key, title, icon, desc, func) in enumerate(row2):
        with cols[idx]:
            if st.button(f"{icon}\n\n**{title}**\n\n{desc}", use_container_width=True):
                st.session_state.selected_feature = key
                st.rerun()
    st.markdown("---")
    st.caption("🌾 KisanMitra – Your Voice Farming Companion")

# ========== MAIN FLOW ==========
if st.session_state.selected_feature is None:
    show_dashboard()
else:
    feature_map = {
        "voice": feature_voice_assistant,
        "market": feature_market_prices,
        "weather": feature_weather,
        "soil": feature_soil_health,
        "advice": feature_personalized_advice,
        "rotation": feature_crop_rotation,
        "women": feature_women_empowerment,
        "schemes": feature_government_schemes,
        "kvk": feature_kvk,
        "nabard": feature_nabard,
    }
    if st.button("← Back to Dashboard", use_container_width=False):
        st.session_state.selected_feature = None
        st.rerun()
    feature_map[st.session_state.selected_feature]()

# ========== FLOATING CHATBOT ==========
with st.popover("💬 Help", use_container_width=False, help="Ask me about farming or using the app"):
    st.markdown("### KisanMitra Assistant")
    st.info("Ask me anything about farming or using the app.")
    if st.button("🔊 Play Welcome", key="play_help_greeting"):
        greeting = "नमस्ते! मैं आपकी क्या मदद कर सकता हूँ?"
        speak_text(greeting, "Hindi")
    audio_val = st.audio_input("Speak your question", key="chat_audio_popover")
    if audio_val:
        with st.spinner("Transcribing..."):
            text = transcribe_audio(audio_val.getvalue())
        if text:
            st.markdown(f"🗣️ **You:** {text}")
            with st.spinner("Thinking..."):
                ans = chatbot_response(text, st.session_state.lang_pref)
            st.success(f"🤖 **Answer:** {ans}")
            speak_text(ans, "Hindi" if detect_language(ans) == "Hindi" else "English")
        else:
            st.error("Could not understand audio.")
    text_q = st.text_input("Or type your question", key="chat_text_popover")
    if text_q:
        st.markdown(f"🗣️ **You:** {text_q}")
        with st.spinner("Thinking..."):
            ans = chatbot_response(text_q, st.session_state.lang_pref)
        st.success(f"🤖 **Answer:** {ans}")
        speak_text(ans, "Hindi" if detect_language(ans) == "Hindi" else "English")

with st.expander("🚀 Future Scope"):
    st.write("""
- 📱 Mobile app for rural accessibility  
- 🌐 Regional language expansion (10+ languages)  
- 📡 Live satellite + weather integration  
- 🛒 Direct farmer-to-market marketplace  
""")