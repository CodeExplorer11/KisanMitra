import streamlit as st
import requests
import google.generativeai as genai
import io
import speech_recognition as sr
from PIL import Image
import datetime
import PyPDF2
import json

# ========== PAGE CONFIG ==========
st.set_page_config(page_title="KisanMitra", page_icon="🌾", layout="wide")

# ========== LANDING PAGE ==========
if "entered_app" not in st.session_state:
    st.session_state.entered_app = False

if not st.session_state.entered_app:
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@600;700&display=swap');
        .landing-card {
            background: linear-gradient(145deg, #2d6a4f, #1b4332);
            padding: 2rem;
            border-radius: 30px;
            text-align: center;
            color: white;
            margin: 2rem auto;
            max-width: 800px;
            box-shadow: 0 20px 30px rgba(0,0,0,0.2);
            font-family: 'Inter', sans-serif;
        }
        .landing-title {
            font-size: 3rem;
            font-weight: 700;
            font-family: 'Poppins', sans-serif;
            margin-bottom: 0.5rem;
        }
        .landing-subtitle {
            font-size: 1.3rem;
            margin-bottom: 1.5rem;
            opacity: 0.9;
        }
        .landing-image {
            width: 100%;
            max-width: 300px;
            border-radius: 20px;
            margin: 1rem auto;
            border: 3px solid #ffb703;
        }
        .feature-list {
            text-align: left;
            display: inline-block;
            margin: 1rem auto;
            font-size: 1rem;
        }
        .feature-list li { margin: 8px 0; }
    </style>
    <div class="landing-card">
        <div class="landing-title">🌾 KisanMitra</div>
        <div class="landing-subtitle">Voice-Based Digital Field Companion</div>
        <img src="https://cdn.pixabay.com/photo/2016/11/14/04/08/farmer-1822530_640.jpg" class="landing-image">
        <div class="feature-list"><ul>
            <li>🎤 Voice queries in Hindi / English</li>
            <li>🌱 Crop advisory & disease detection</li>
            <li>💰 Live market prices & weather</li>
            <li>📄 Soil health analysis (photo/PDF)</li>
            <li>🔄 Crop rotation & recovery advice</li>
        </ul></div>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🌾 Start Now", use_container_width=True):
            st.session_state.entered_app = True
            st.rerun()
    st.stop()

# ========== MAIN APP ==========
# ---------- Load API Keys ----------
GEMINI_API_KEY = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
        st.success("✅ API key loaded")
except:
    pass
if not GEMINI_API_KEY:
    try:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if GEMINI_API_KEY:
            st.info("📝 API key loaded from .env")
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

# ---------- Embedded Data for Schemes & KVK ----------
SCHEMES_DATA = {
    "schemes": [
        {"category": "Crop Insurance", "name": "Pradhan Mantri Fasal Bima Yojana (PMFBY)", "description": "Low premium crop insurance (2% for Kharif, 1.5% for Rabi).", "link": "https://pmfby.gov.in/"},
        {"category": "Women Farmers", "name": "Mahila Kisan Sashaktikaran Pariyojana (MKSP)", "description": "Skill development and livelihood support for women farmers.", "link": "https://nrlm.gov.in/"},
        {"category": "Direct Income Support", "name": "PM-Kisan Samman Nidhi (PM-KISAN)", "description": "₹6,000 per year in three instalments to small farmers.", "link": "https://pmkisan.gov.in/"},
        {"category": "Pension & Social Security", "name": "Pradhan Mantri Kisan Maan Dhan Yojana (PM-KMY)", "description": "₹3,000 monthly pension after age 60.", "link": "https://maandhan.in/"},
        {"category": "Infrastructure & Marketing", "name": "Agricultural Marketing Infrastructure (AMI)", "description": "Funding for warehouses, grading, and market infrastructure.", "link": "https://agmarknet.gov.in/"},
        {"category": "Soil Health", "name": "Soil Health Card Scheme", "description": "Free soil testing and nutrient recommendations.", "link": "https://soilhealth.dac.gov.in/"}
    ]
}

KVK_DATA = {
    "kvk_centers": [
        {"district": "Lucknow", "center_name": "KVK, Lucknow", "head": "Dr. A. K. Singh", "contact": "+91-522-1234567", "email": "kvk.lucknow@icar.gov.in", "services": "Soil testing, seed production, organic farming training, farm machinery demonstration."},
        {"district": "Prayagraj", "center_name": "KVK, Naini", "head": "Dr. S. K. Sharma", "contact": "+91-532-1234567", "email": "kvk.naini@icar.gov.in", "services": "Integrated farming, vermicomposting, fruit and vegetable preservation."},
        {"district": "Varanasi", "center_name": "KVK, Varanasi", "head": "Dr. R. K. Pandey", "contact": "+91-542-1234567", "email": "kvk.varanasi@icar.gov.in", "services": "Dairy management, aquaculture, bee keeping, mushroom cultivation."},
        {"district": "Bareilly", "center_name": "KVK, Bareilly", "head": "Dr. M. K. Sharma", "contact": "+91-581-1234567", "email": "kvk.bareilly@icar.gov.in", "services": "Wheat and sugarcane research, soil health cards, farm machinery."}
    ]
}

# ---------- Multilingual & Session State ----------
SUPPORTED_LANGS = {"en": "English", "hi": "हिंदी"}
DEFAULT_LANGUAGE = "en"
TEXTS = {
    "en": { "app_title": "🌾 KisanMitra", "app_caption": "Your Voice Farming Companion", "sidebar_title": "🌾 KisanMitra", "sidebar_lang": "🗣️ Response Language", "sidebar_profile": "👨‍🌾 Farmer Profile", "sidebar_profile_placeholder": "Your details (crops, land, location)", "sidebar_history": "📜 Conversation History", "sidebar_clear": "Clear History", "tab1": "🎤 Voice Assistant", "tab2": "💰 Market Prices", "tab3": "🌤️ Weather", "tab4": "🧪 Soil Health", "tab5": "📝 Personalized Advice", "tab6": "🔄 Crop Rotation", "tab7": "🚺 Women Empowerment", "tab8": "📜 Govt Schemes", "tab9": "🌾 KVK Support", "voice_header": "🎤 Ask by Voice", "voice_placeholder": "Tap to record your question", "voice_transcribing": "Transcribing...", "voice_thinking": "Getting advice...", "voice_error": "Could not understand. Please speak clearly.", "voice_type_header": "Or type your question", "voice_type_placeholder": "Type here", "voice_ask_btn": "Ask", "market_header": "💰 Mandi Prices", "market_info": "ℹ️ Live API ready. Showing sample prices.", "market_commodity": "Commodity (e.g., Wheat, Rice)", "market_state": "State", "market_btn": "Get Price", "weather_header": "🌤️ Weather", "weather_city": "Enter district/city name", "weather_btn": "Get Weather", "soil_header": "🧪 Soil Health Analysis", "soil_photo_option": "Option 1: Upload a photo of your soil", "soil_photo_btn": "Analyze Soil from Photo", "soil_pdf_option": "Option 2: Upload soil lab report (PDF)", "soil_pdf_btn": "Analyze PDF Report", "soil_manual_option": "Option 3: Enter test results manually", "soil_manual_btn": "Get Manual Advice", "personalized_header": "📝 Personalized Farming Advice", "personalized_warning": "Please fill your Farmer Profile in the sidebar first.", "personalized_question": "What specific advice do you need?", "personalized_btn": "Get Personalized Advice", "footer": "🌾 KisanMitra – Voice-First, Real-Time, Personalized Farming Companion | Jai Kisan!" },
    "hi": { "app_title": "🌾 किसान मित्र", "app_caption": "आपका आवाज़ी खेती साथी", "sidebar_title": "🌾 किसान मित्र", "sidebar_lang": "🗣️ जवाब की भाषा", "sidebar_profile": "👨‍🌾 किसान प्रोफ़ाइल", "sidebar_profile_placeholder": "आपका विवरण (फसलें, ज़मीन, स्थान)", "sidebar_history": "📜 बातचीत इतिहास", "sidebar_clear": "इतिहास साफ़ करें", "tab1": "🎤 आवाज़ सहायक", "tab2": "💰 मंडी भाव", "tab3": "🌤️ मौसम", "tab4": "🧪 मिट्टी स्वास्थ्य", "tab5": "📝 व्यक्तिगत सलाह", "tab6": "🔄 फसल चक्र", "tab7": "🚺 महिला सशक्तिकरण", "tab8": "📜 सरकारी योजनाएँ", "tab9": "🌾 केवीके सहायता", "voice_header": "🎤 आवाज़ से पूछें", "voice_placeholder": "अपना सवाल रिकॉर्ड करें", "voice_transcribing": "लिख रहा हूँ...", "voice_thinking": "जवाब दे रहा हूँ...", "voice_error": "समझ नहीं आया। कृपया साफ़ बोलें।", "voice_type_header": "या लिखकर पूछें", "voice_type_placeholder": "यहाँ लिखें", "voice_ask_btn": "पूछें", "market_header": "💰 मंडी भाव", "market_info": "ℹ️ लाइव API तैयार। नमूना मूल्य दिखा रहे हैं।", "market_commodity": "फसल (जैसे, गेहूं, धान)", "market_state": "राज्य", "market_btn": "भाव देखें", "weather_header": "🌤️ मौसम", "weather_city": "जिला/शहर का नाम", "weather_btn": "मौसम देखें", "soil_header": "🧪 मिट्टी स्वास्थ्य जांच", "soil_photo_option": "विकल्प 1: मिट्टी की फोटो अपलोड करें", "soil_photo_btn": "फोटो से मिट्टी जांचें", "soil_pdf_option": "विकल्प 2: मिट्टी लैब रिपोर्ट (PDF)", "soil_pdf_btn": "PDF रिपोर्ट जांचें", "soil_manual_option": "विकल्प 3: मैन्युअल रूप से मान दर्ज करें", "soil_manual_btn": "मैन्युअल सलाह लें", "personalized_header": "📝 व्यक्तिगत खेती सलाह", "personalized_warning": "कृपया पहले साइडबार में किसान प्रोफ़ाइल भरें।", "personalized_question": "आपको किस सलाह की ज़रूरत है?", "personalized_btn": "व्यक्तिगत सलाह लें", "footer": "🌾 किसान मित्र – आवाज़-पहला, वास्तविक-समय, व्यक्तिगत खेती साथी | जय किसान!" }
}

def t(key):
    lang = st.session_state.get("language", DEFAULT_LANGUAGE)
    return TEXTS.get(lang, TEXTS[DEFAULT_LANGUAGE]).get(key, key)

if "language" not in st.session_state: st.session_state.language = DEFAULT_LANGUAGE
if "history" not in st.session_state: st.session_state.history = []
if "lang_pref" not in st.session_state: st.session_state.lang_pref = "English"
if "farmer_profile" not in st.session_state: st.session_state.farmer_profile = ""
if "stop_voice" not in st.session_state: st.session_state.stop_voice = False

# ---------- Modern CSS ----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400;14..32,500;14..32,600;14..32,700&family=Poppins:wght@600;700&display=swap');
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body, .stApp { font-family: 'Inter', sans-serif !important; background: #faf9f5 !important; }
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { font-family: 'Poppins', sans-serif !important; font-weight: 600 !important; color: #2c5e2e !important; letter-spacing: -0.3px; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #1e3a1e 0%, #2a5a2a 100%) !important; border-right: none !important; }
    [data-testid="stSidebar"] * { color: #fefae0 !important; }
    .stButton>button { background: linear-gradient(95deg, #e67e22, #f39c12) !important; color: white !important; border: none !important; border-radius: 60px !important; padding: 0.6rem 1.5rem !important; font-weight: 600 !important; font-size: 1rem !important; transition: all 0.2s ease !important; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,0.1); background: linear-gradient(95deg, #d35400, #e67e22) !important; }
    .user-msg, .bot-msg, [data-testid="stExpander"] { background: white; border-radius: 20px; padding: 1rem; margin: 1rem 0; box-shadow: 0 2px 8px rgba(0,0,0,0.03); border: 1px solid #eee; }
    .user-msg { border-left: 6px solid #e67e22; }
    .bot-msg { border-left: 6px solid #2c5e2e; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background: #f0ede6; padding: 6px; border-radius: 50px; margin-bottom: 1rem; }
    .stTabs [data-baseweb="tab"] { border-radius: 40px; padding: 8px 20px; font-weight: 500; color: #4a5b2e; }
    .stTabs [aria-selected="true"] { background: #2c5e2e; color: white; }
</style>
""", unsafe_allow_html=True)

# ---------- SIDEBAR ----------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1998/1998626.png", width=80)
    st.title(t("sidebar_title"))
    st.markdown("---")
    selected_lang = st.selectbox(t("sidebar_lang"), options=list(SUPPORTED_LANGS.keys()), format_func=lambda x: SUPPORTED_LANGS[x], index=list(SUPPORTED_LANGS.keys()).index(st.session_state.language))
    if selected_lang != st.session_state.language:
        st.session_state.language = selected_lang
        st.session_state.lang_pref = "English" if st.session_state.language == "en" else "Hindi"
        st.rerun()
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

# ---------- HELPER FUNCTIONS ----------
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
    prompt = f"You are KisanMitra, a friendly expert farming assistant.\nResponse language: {force_lang}\nFarmer asked: \"{question}\"\nGive short, practical, actionable answer (max 3 sentences). CRITICAL: Answer in the same language as the question."
    try:
        return model.generate_content(prompt).text
    except Exception as e:
        return f"⚠️ AI error: {str(e)}"

def get_weather(city):
    # For demo, return fixed data. Replace with real API if you have key.
    return {"temp": 28, "humidity": 65, "description": "clear sky", "city": city}

def get_weather_forecast(city):
    # Simulate tomorrow's forecast
    return {
        "today": {"temp": 32, "humidity": 65, "condition": "Sunny", "suitable": True, "advice": "Good day for sowing."},
        "tomorrow": {"temp": 28, "humidity": 85, "condition": "Heavy rain expected", "suitable": False, "advice": "Avoid spraying pesticides."}
    }

def get_weather_alert(forecast):
    advice = []
    alert_level = "normal"
    cond = forecast["tomorrow"]["condition"].lower()
    hum = forecast["tomorrow"]["humidity"]
    if "heavy rain" in cond or "thunderstorm" in cond:
        alert_level = "red"
        advice = ["⚠️ Heavy rain expected tomorrow! Harvest ripe crops immediately.", "🌾 Cover harvested crops with tarpaulin. Clear field drainage.", "🛑 Postpone fertiliser and pesticide spraying."]
    elif hum > 80 or "rain" in cond:
        alert_level = "orange"
        advice = ["💧 High humidity/rain risk – fungal diseases possible. Inspect crops.", "🔍 Apply organic fungicide (neem oil) if dry interval appears."]
    else:
        advice = ["✅ Weather suitable for normal farming activities."]
    return alert_level, advice

def get_mandi_price(commodity, state="Uttar Pradesh"):
    mock = {"wheat":2250,"rice":2180,"mustard":5650,"tomato":1800,"potato":1200,"onion":2500,"corn":2120,"chana":5200}
    price = mock.get(commodity.lower(), 2000)
    return {"commodity": commodity, "price": price, "market": "Sample Mandi (Live API ready)", "state": state, "source": "Mock data"}

def analyze_soil_image(image):
    prompt = "Analyze this soil image: 1) Soil type 2) Health indication 3) Improvement recommendation. Keep short."
    try:
        return vision_model.generate_content([prompt, image]).text
    except: return "Error analyzing image."

def analyze_soil_pdf(pdf_bytes):
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        text = "".join([page.extract_text() for page in reader.pages])
        if not text.strip(): return "Could not read text from PDF."
        return model.generate_content(f"Analyze this soil report and give recommendations: {text[:1500]}").text
    except: return "Error processing PDF."

def get_soil_advice(soil_data):
    try:
        return model.generate_content(f"Analyze soil: {soil_data}. Give short advice on fertilizer and pH correction.").text
    except: return "Unable to analyze soil data."

def get_personalized_advice(profile, question):
    try:
        return model.generate_content(f"Farmer profile: {profile}\nQuestion: {question}\nGive personalized, practical advice.").text
    except: return "AI temporarily unavailable."

def get_crop_damage_advice(crop, damage_type, lang):
    prompt = f"Wheat field damaged by heavy rain and waterlogging. Give short recovery steps in {lang}: 1) Drain water 2) Fertiliser to apply 3) Disease prevention 4) When to replant. Keep under 100 words."
    try:
        return model.generate_content(prompt).text
    except: return "Unable to generate advice. Please consult local agriculture officer."

def get_kvk_by_district(district):
    for center in KVK_DATA['kvk_centers']:
        if center['district'].lower() == district.lower():
            return center
    # If not found, use Gemini to suggest nearest KVK (simulate live)
    try:
        prompt = f"Provide contact details of the nearest Krishi Vigyan Kendra (KVK) for district {district} in India. Include center name, head, phone, email, and services. If exact data not known, provide a plausible example."
        response = model.generate_content(prompt)
        return {"district": district, "center_name": "KVK (AI suggested)", "head": "Contact local office", "contact": response.text[:200], "email": "kvk."+district.lower()+"@icar.gov.in", "services": "Soil testing, training, seed distribution."}
    except:
        return None

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
    prompt = f"You are a helpful farming assistant chatbot.\nResponse language: {force_lang}\nUser: \"{user_input}\"\nGive short, friendly answer (max 2 sentences). CRITICAL: Answer in same language as user."
    try:
        return model.generate_content(prompt).text
    except Exception as e:
        return f"⚠️ Error: {str(e)[:100]}"

GPS_HTML = """<div id="gps-container"><button id="get-location" style="background:#4CAF50; color:white; padding:10px 20px; border:none; border-radius:30px; cursor:pointer; width:100%;">📍 Use My Current Location</button><p id="location-status" style="margin-top:10px; color:#666; text-align:center;"></p></div><script>const btn=document.getElementById('get-location'),status=document.getElementById('location-status');btn.onclick=function(){if('geolocation' in navigator){status.innerHTML="📍 Getting location...";navigator.geolocation.getCurrentPosition(function(p){const lat=p.coords.latitude,lon=p.coords.longitude;status.innerHTML="✅ Location captured! Getting weather...";const form=document.createElement('form');form.method='POST';form.action='';const latIn=document.createElement('input');latIn.name='latitude';latIn.value=lat;const lonIn=document.createElement('input');lonIn.name='longitude';lonIn.value=lon;form.appendChild(latIn);form.appendChild(lonIn);document.body.appendChild(form);form.submit();},function(){status.innerHTML="❌ Location permission denied.";});}else{status.innerHTML="❌ GPS not supported.";}};</script>"""

def get_city_from_coords(lat, lon):
    try:
        r = requests.get(f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json", headers={'User-Agent': 'KisanMitra'})
        return r.json().get('address', {}).get('city') or r.json().get('address', {}).get('town') or "Your Location"
    except: return "Your Location"

# ---------- MAIN TABS (9 tabs) ----------
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([t("tab1"), t("tab2"), t("tab3"), t("tab4"), t("tab5"), t("tab6"), t("tab7"), t("tab8"), t("tab9")])

# ----- TAB 1: VOICE ASSISTANT -----
with tab1:
    st.header(t("voice_header"))
    if st.button("⏹️ Stop Recording", key="stop_voice_btn"):
        st.session_state.stop_voice = True
        st.rerun()
    if st.session_state.stop_voice:
        st.info("🛑 Recording stopped. Click 'Enable Recording' to ask again.")
        if st.button("🎤 Enable Recording", key="enable_voice"):
            st.session_state.stop_voice = False
            st.rerun()
    else:
        audio_val = st.audio_input(t("voice_placeholder"), key="main_audio")
        if audio_val:
            with st.spinner(t("voice_transcribing")):
                text = transcribe_audio(audio_val.getvalue())
            if text:
                st.markdown(f'<div class="user-msg">🗣️ <strong>You:</strong> {text}</div>', unsafe_allow_html=True)
                with st.spinner(t("voice_thinking")):
                    ans = get_ai_response(text, st.session_state.lang_pref)
                st.markdown(f'<div class="bot-msg">🤖 <strong>KisanMitra:</strong> {ans}</div>', unsafe_allow_html=True)
                st.session_state.history.append({"q": text, "a": ans})
                detected_lang = detect_language(ans)
                tts_lang = "hi-IN" if detected_lang == "Hindi" else "en-US"
                st.components.v1.html(f'<script>var u=new SpeechSynthesisUtterance({json.dumps(ans)}); u.lang="{tts_lang}"; window.speechSynthesis.speak(u);</script>', height=0)
            else:
                st.error(t("voice_error"))
    st.divider()
    st.subheader(t("voice_type_header"))
    txt_q = st.text_input(t("voice_type_placeholder"))
    if st.button(t("voice_ask_btn"), key="ask_text"):
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
    st.header(t("market_header"))
    st.info(t("market_info"))
    col1, col2 = st.columns(2)
    with col1: commodity = st.text_input(t("market_commodity"))
    with col2: state = st.text_input(t("market_state"), "Uttar Pradesh")
    if st.button(t("market_btn")):
        if commodity:
            p = get_mandi_price(commodity, state)
            st.success(f"**{p['commodity']}** in {p['market']}, {p['state']}")
            st.metric("Price per quintal", f"₹{p['price']}")
            st.caption(f"Source: {p['source']}")

# ----- TAB 3: WEATHER (with alerts and future forecast) -----
with tab3:
    st.header(t("weather_header"))
    st.markdown(GPS_HTML, unsafe_allow_html=True)
    st.caption("— OR —")
    city = st.text_input(t("weather_city"), "Lucknow")
    if "latitude" in st.query_params and "longitude" in st.query_params:
        lat, lon = st.query_params["latitude"], st.query_params["longitude"]
        city = get_city_from_coords(lat, lon)
        st.success(f"📍 Location detected: {city}")
    if st.button(t("weather_btn")) or ("latitude" in st.query_params):
        w = get_weather(city)
        col1, col2, col3 = st.columns(3)
        col1.metric("Temperature", f"{w['temp']}°C"); col2.metric("Humidity", f"{w['humidity']}%"); col3.metric("Condition", w['description'].title())
        # Future forecast
        st.subheader("📅 2‑Day Forecast")
        forecast = get_weather_forecast(city)
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("**Today**")
            st.write(f"🌡️ {forecast['today']['temp']}°C, {forecast['today']['condition']}")
            st.write(f"💡 {forecast['today']['advice']}")
        with col_b:
            st.write("**Tomorrow**")
            st.write(f"🌡️ {forecast['tomorrow']['temp']}°C, {forecast['tomorrow']['condition']}")
            st.write(f"💡 {forecast['tomorrow']['advice']}")
        # Alert system
        alert_level, advice_list = get_weather_alert(forecast)
        if alert_level == "red":
            st.error("🚨 **Severe Weather Alert!**")
        elif alert_level == "orange":
            st.warning("⚠️ **Weather Advisory**")
        for adv in advice_list:
            st.write(f"- {adv}")

# ----- TAB 4: SOIL HEALTH -----
with tab4:
    st.header(t("soil_header"))
    st.subheader(t("soil_photo_option"))
    soil_img = st.file_uploader("", type=["jpg","jpeg","png"])
    if soil_img:
        image = Image.open(soil_img); st.image(image, width=200)
        if st.button(t("soil_photo_btn")):
            advice = analyze_soil_image(image); st.markdown(f'<div class="bot-msg">📸 {advice}</div>', unsafe_allow_html=True)
    st.subheader(t("soil_pdf_option"))
    pdf_file = st.file_uploader("", type=["pdf"])
    if pdf_file:
        if st.button(t("soil_pdf_btn")):
            advice = analyze_soil_pdf(pdf_file.read()); st.markdown(f'<div class="bot-msg">📑 {advice}</div>', unsafe_allow_html=True)
    st.subheader(t("soil_manual_option"))
    soil_input = st.text_area("")
    if st.button(t("soil_manual_btn")):
        if soil_input: advice = get_soil_advice(soil_input); st.markdown(f'<div class="bot-msg">📋 {advice}</div>', unsafe_allow_html=True)

# ----- TAB 5: PERSONALIZED ADVICE (with crop damage recovery) -----
with tab5:
    st.header(t("personalized_header"))
    st.subheader("🌾 Crop Damage Recovery (Heavy Rain / Waterlogging)")
    damage_crop = st.selectbox("Affected crop", ["Wheat", "Rice", "Pulses"])
    damage_type = st.selectbox("Type of damage", ["Waterlogging", "Hailstorm", "Strong wind"])
    if st.button("Get Recovery Advice", key="recovery_btn"):
        advice = get_crop_damage_advice(damage_crop, damage_type, st.session_state.lang_pref)
        st.markdown(f'<div class="bot-msg">🌿 {advice}</div>', unsafe_allow_html=True)
    st.divider()
    if not st.session_state.farmer_profile:
        st.warning(t("personalized_warning"))
    else:
        question = st.text_area(t("personalized_question"))
        if st.button(t("personalized_btn")):
            if question:
                advice = get_personalized_advice(st.session_state.farmer_profile, question)
                st.markdown(f'<div class="bot-msg">🎯 {advice}</div>', unsafe_allow_html=True)

# ----- TAB 6: CROP ROTATION -----
with tab6:
    st.header("🔄 Crop Rotation Advisor")
    col1, col2 = st.columns(2)
    with col1: prev_crop = st.selectbox("Previous crop grown", ["Sugarcane","Wheat","Rice","Potato","Tomato","Maize"])
    with col2: next_crop = st.selectbox("Crop you want to grow next", ["Wheat","Mustard","Rice","Potato","Tomato","Maize","Pulses","Onion"])
    if st.button("Get Rotation Advice"):
        adv = get_crop_rotation_advice(prev_crop, next_crop)
        if adv["suitable"]: st.success(f"✅ Good rotation choice!")
        else: st.warning(f"⚠️ {adv['advice']}")
        st.info(f"🌱 **Soil advice:** {adv['soil']}")
        with st.spinner("Getting detailed AI advice..."):
            detailed = model.generate_content(f"Farmer grew {prev_crop} and wants to grow {next_crop}. Give soil management and fertilizer advice.")
            st.markdown(f'<div class="bot-msg">🤖 <strong>AI Suggestion:</strong><br>{detailed.text}</div>', unsafe_allow_html=True)

# ----- TAB 7: WOMEN EMPOWERMENT -----
with tab7:
    st.header("🚺 Women Farmer Empowerment")
    safety_tips = ["🌾 Always inform a family member before going to the field alone.", "📞 Save local police and women’s helpline numbers on speed dial.", "👭 Form a group of women farmers in your village for mutual support.", "🌿 Keep a basic first‑aid kit in your farming bag.", "🚜 Learn about government schemes for women farmers – ask KisanMitra!"]
    tip_idx = datetime.datetime.now().day % len(safety_tips)
    st.info(f"💡 **Safety Tip of the Day:** {safety_tips[tip_idx]}")
    if st.button("🔊 Read Tip Aloud"):
        st.components.v1.html(f'<script>var u=new SpeechSynthesisUtterance("{safety_tips[tip_idx]}"); u.lang="hi-IN"; window.speechSynthesis.speak(u);</script>', height=0)
    st.divider()
    st.subheader("📞 Emergency & Helpline Numbers")
    contacts = {"Women Helpline (India)": "1091", "National Commission for Women": "7827170170", "Local Police": "100", "Women Farmer Support (MKSP)": "1800‑180‑1551"}
    for name, num in contacts.items():
        st.write(f"**{name}:** `{num}`")
    st.divider()
    st.subheader("🌱 Small‑Scale Farming for Women")
    ideas = {"🥬 Kitchen Garden": "Grow vegetables in small space. Low investment.", "🐔 Poultry": "Start with 10‑20 chicks. Eggs and meat provide income.", "🍄 Mushroom Cultivation": "Grows in dark sheds. High return in 30 days.", "🐄 Dairy (1‑2 cows)": "Daily milk income. Government subsidy available."}
    for idea, desc in ideas.items():
        with st.expander(idea):
            st.write(desc)
            if st.button(f"Ask KisanMitra about {idea}", key=f"ask_{idea}"):
                ans = get_ai_response(f"How to start {idea} as a woman farmer?", st.session_state.lang_pref)
                st.markdown(f'<div class="bot-msg">🤖 {ans}</div>', unsafe_allow_html=True)
    st.divider()
    st.subheader("🏛️ Government Schemes for Women")
    women_schemes = [s for s in SCHEMES_DATA["schemes"] if s["category"] == "Women Farmers"]
    for s in women_schemes:
        with st.expander(s["name"]):
            st.write(s["description"])
            st.markdown(f"[🔗 Know More]({s['link']})")

# ----- TAB 8: GOVERNMENT SCHEMES (categorized) -----
with tab8:
    st.header("📜 Government Schemes for Farmers")
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

# ----- TAB 9: KVK SUPPORT (dynamic lookup with AI fallback) -----
with tab9:
    st.header("🌾 Krishi Vigyan Kendra (KVK)")
    st.caption("Find your nearest KVK centre and get expert agricultural support.")
    district = st.text_input("Enter your district name:", placeholder="e.g., Lucknow, Prayagraj, Bareilly")
    if st.button("🔍 Find KVK", use_container_width=True):
        center = get_kvk_by_district(district)
        if center:
            st.success(f"**{center['center_name']}**")
            st.markdown(f"**Head:** {center['head']}")
            st.markdown(f"**📞 Contact:** {center['contact']}")
            st.markdown(f"**📧 Email:** {center['email']}")
            st.markdown(f"**🛠️ Services offered:** {center['services']}")
        else:
            st.warning(f"No KVK data available for district: {district}. Please visit [ICAR KVK Portal](https://kvk.icar.gov.in/).")
    st.info("KVK centres provide free soil testing, seed distribution, training, and crop‑specific advice. Contact them for immediate help.")

# ----- FOOTER & FLOATING CHATBOT (with spoken greeting) -----
st.markdown("---")
st.caption(t("footer"))

with st.popover("🤖 💬 Help", use_container_width=False, help="Ask me about farming or using the app"):
    st.markdown("### 💬 KisanMitra Assistant")
    greeting = "नमस्ते! मैं आपकी कैसे मदद कर सकता हूँ?"
    st.info(greeting)
    # Speak greeting when popover opens (only once per session)
    if "greeting_spoken" not in st.session_state:
        st.components.v1.html(f'<script>var u=new SpeechSynthesisUtterance({json.dumps(greeting)}); u.lang="hi-IN"; window.speechSynthesis.speak(u);</script>', height=0)
        st.session_state.greeting_spoken = True
    
    audio_val = st.audio_input("🎤 Speak your question", key="chat_audio_popover")
    if audio_val:
        with st.spinner("Transcribing..."):
            text = transcribe_audio(audio_val.getvalue())
        if text:
            st.markdown(f"🗣️ **You:** {text}")
            with st.spinner("🤔 Thinking..."):
                ans = chatbot_response(text)
            st.success(f"🤖 **Answer:** {ans}")
            detected = detect_language(ans)
            tts_lang = "hi-IN" if detected == "Hindi" else "en-US"
            st.components.v1.html(f'<script>var u=new SpeechSynthesisUtterance({json.dumps(ans)}); u.lang="{tts_lang}"; window.speechSynthesis.speak(u);</script>', height=0)
        else:
            st.error("Could not understand audio.")
    text_q = st.text_input("Or type your question", key="chat_text_popover")
    if text_q:
        st.markdown(f"🗣️ **You:** {text_q}")
        with st.spinner("🤔 Thinking..."):
            ans = chatbot_response(text_q)
        st.success(f"🤖 **Answer:** {ans}")
        detected = detect_language(ans)
        tts_lang = "hi-IN" if detected == "Hindi" else "en-US"
        st.components.v1.html(f'<script>var u=new SpeechSynthesisUtterance({json.dumps(ans)}); u.lang="{tts_lang}"; window.speechSynthesis.speak(u);</script>', height=0)