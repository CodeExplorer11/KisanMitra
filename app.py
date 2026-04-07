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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        .landing-card {
            background: linear-gradient(145deg, #e8f5e9, #c8e6c9);
            padding: 2rem;
            border-radius: 30px;
            text-align: center;
            margin: 2rem auto;
            max-width: 800px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.05);
            font-family: 'Inter', sans-serif;
            color: #2e5e2e;
        }
        .landing-title {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        .landing-subtitle {
            font-size: 1.2rem;
            margin-bottom: 1.5rem;
            opacity: 0.8;
        }
        .landing-image {
            width: 100%;
            max-width: 280px;
            border-radius: 20px;
            margin: 1rem auto;
            border: 2px solid #fff;
        }
        .feature-list {
            text-align: left;
            display: inline-block;
            margin: 1rem auto;
            font-size: 0.95rem;
        }
        .feature-list li { margin: 6px 0; }
    </style>
    <div class="landing-card">
        <div class="landing-title">🌾 KisanMitra</div>
        <div class="landing-subtitle">Your Voice Farming Companion</div>
        <img src="https://cdn.pixabay.com/photo/2016/11/14/04/08/farmer-1822530_640.jpg" class="landing-image">
        <div class="feature-list"><ul>
            <li>🎤 Voice queries in Hindi / English</li>
            <li>🌱 Crop advisory & disease detection</li>
            <li>💰 Market prices & weather alerts</li>
            <li>📄 Soil health analysis (photo/PDF)</li>
            <li>🔄 Crop rotation & recovery tips</li>
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

# ---------- Embedded Data ----------
SCHEMES_DATA = {
    "schemes": [
        {"category": "Crop Insurance", "name": "Pradhan Mantri Fasal Bima Yojana", "description": "Low premium crop insurance.", "link": "https://pmfby.gov.in/"},
        {"category": "Women Farmers", "name": "Mahila Kisan Sashaktikaran Pariyojana", "description": "Skill development for women farmers.", "link": "https://nrlm.gov.in/"},
        {"category": "Direct Income Support", "name": "PM-Kisan Samman Nidhi", "description": "₹6,000/year income support.", "link": "https://pmkisan.gov.in/"},
        {"category": "Pension & Social Security", "name": "PM Kisan Maan Dhan Yojana", "description": "₹3,000 monthly pension.", "link": "https://maandhan.in/"},
        {"category": "Soil Health", "name": "Soil Health Card Scheme", "description": "Free soil testing.", "link": "https://soilhealth.dac.gov.in/"}
    ]
}

KVK_DATA = {
    "kvk_centers": [
        {"district": "Lucknow", "center_name": "KVK, Lucknow", "head": "Dr. A. K. Singh", "contact": "+91-522-1234567", "email": "kvk.lucknow@icar.gov.in", "services": "Soil testing, seed production, organic farming."},
        {"district": "Prayagraj", "center_name": "KVK, Naini", "head": "Dr. S. K. Sharma", "contact": "+91-532-1234567", "email": "kvk.naini@icar.gov.in", "services": "Integrated farming, vermicomposting."},
        {"district": "Varanasi", "center_name": "KVK, Varanasi", "head": "Dr. R. K. Pandey", "contact": "+91-542-1234567", "email": "kvk.varanasi@icar.gov.in", "services": "Dairy, aquaculture, mushroom."},
        {"district": "Bareilly", "center_name": "KVK, Bareilly", "head": "Dr. M. K. Sharma", "contact": "+91-581-1234567", "email": "kvk.bareilly@icar.gov.in", "services": "Wheat research, soil health cards."}
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

# ---------- Light Green CSS ----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    * { margin: 0; padding: 0; box-sizing: border-box; }
    .stApp { background: #f4faf4 !important; font-family: 'Inter', sans-serif; }
    h1, h2, h3 { color: #2b5e2b !important; font-weight: 600; }
    [data-testid="stSidebar"] { background: #d9f0d9 !important; }
    [data-testid="stSidebar"] * { color: #1e3a1e !important; }
    .stButton>button { background: #3c9e3c; color: white; border-radius: 30px; font-weight: 500; transition: 0.2s; }
    .stButton>button:hover { background: #2e7d32; transform: scale(1.02); }
    .user-msg, .bot-msg { background: white; border-radius: 20px; padding: 0.8rem; margin: 0.8rem 0; border-left: 5px solid #3c9e3c; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .stTabs [data-baseweb="tab-list"] { gap: 5px; background: #e6f0e6; padding: 5px; border-radius: 40px; }
    .stTabs [data-baseweb="tab"] { border-radius: 30px; padding: 6px 18px; font-weight: 500; color: #2b5e2b; }
    .stTabs [aria-selected="true"] { background: #3c9e3c; color: white; }
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
    st.subheader("History")
    if st.button("Clear"):
        st.session_state.history = []
        st.rerun()
    for chat in reversed(st.session_state.history[-5:]):
        with st.expander(f"🗣️ {chat['q'][:30]}..."):
            st.write(f"**You:** {chat['q']}")
            st.write(f"**KisanMitra:** {chat['a'][:100]}...")

# ---------- Helper Functions ----------
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
    force_lang = "Hindi. Answer in Hindi Devanagari script. No English words." if detected == "Hindi" else "English"
    prompt = f"You are KisanMitra. Response language: {force_lang}\nFarmer: {question}\nGive short, practical answer (max 3 sentences)."
    try: return model.generate_content(prompt).text
    except: return "⚠️ AI error."

def get_weather_forecast(city):
    # Simulated forecast (replace with real API if key available)
    return {
        "today": {"temp": 32, "humidity": 65, "condition": "Sunny", "advice": "Good for sowing."},
        "tomorrow": {"temp": 28, "humidity": 85, "condition": "Heavy rain", "advice": "Avoid spraying."}
    }

def get_weather_alert(forecast):
    cond = forecast["tomorrow"]["condition"].lower()
    hum = forecast["tomorrow"]["humidity"]
    if "heavy rain" in cond:
        return "red", ["⚠️ Heavy rain tomorrow! Harvest crops.", "🌾 Clear drainage.", "🛑 No pesticides."]
    elif hum > 80:
        return "orange", ["💧 High humidity risk – fungal diseases.", "🔍 Inspect crops."]
    return "normal", ["✅ Weather suitable."]

def get_mandi_price(commodity, state):
    mock = {"wheat":2250,"rice":2180,"mustard":5650,"tomato":1800}
    price = mock.get(commodity.lower(), 2000)
    return {"commodity": commodity, "price": price, "market": "Sample Mandi"}

def analyze_soil_image(image):
    try: return vision_model.generate_content(["Analyze soil: type, health, recommendation. Keep short.", image]).text
    except: return "Error."

def analyze_soil_pdf(pdf_bytes):
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        text = "".join([p.extract_text() for p in reader.pages])
        return model.generate_content(f"Analyze soil report: {text[:1500]}").text if text.strip() else "No text found."
    except: return "Error."

def get_soil_advice(data):
    try: return model.generate_content(f"Soil: {data}. Give fertilizer and pH advice.").text
    except: return "Unable."

def get_personalized_advice(profile, question):
    try: return model.generate_content(f"Profile: {profile}\nQuestion: {question}\nShort practical advice.").text
    except: return "Try again."

def get_crop_damage_advice(crop, damage, lang):
    prompt = f"{crop} damaged by {damage}. Recovery steps in {lang}: drain water, fertiliser, disease control, replanting."
    try: return model.generate_content(prompt).text
    except: return "Consult local officer."

def get_kvk_by_district(district):
    for c in KVK_DATA["kvk_centers"]:
        if c["district"].lower() == district.lower():
            return c
    return None

def chatbot_response(user_input):
    detected = detect_language(user_input)
    force_lang = "Hindi. Answer in Hindi." if detected == "Hindi" else "English"
    prompt = f"Farming assistant. Response language: {force_lang}\nUser: {user_input}\nShort friendly answer (max 2 sentences)."
    try: return model.generate_content(prompt).text
    except: return "Please try again."

GPS_HTML = """<div><button id="get-location" style="background:#4CAF50; color:white; padding:8px 16px; border:none; border-radius:30px; cursor:pointer;">📍 Use My Location</button><p id="status" style="margin-top:8px;"></p></div><script>const btn=document.getElementById('get-location'),status=document.getElementById('status');btn.onclick=function(){if('geolocation' in navigator){status.innerHTML="Getting location...";navigator.geolocation.getCurrentPosition(function(p){status.innerHTML="Location captured!";const form=document.createElement('form');form.method='POST';form.action='';const lat=document.createElement('input');lat.name='latitude';lat.value=p.coords.latitude;const lon=document.createElement('input');lon.name='longitude';lon.value=p.coords.longitude;form.appendChild(lat);form.appendChild(lon);document.body.appendChild(form);form.submit();},function(){status.innerHTML="Permission denied.";});}else{status.innerHTML="GPS not supported.";}};</script>"""
def get_city_from_coords(lat, lon):
    try: return requests.get(f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json", headers={'User-Agent':'KisanMitra'}).json().get('address',{}).get('city','Your Location')
    except: return "Your Location"

# ---------- TABS ----------
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([t("tab1"), t("tab2"), t("tab3"), t("tab4"), t("tab5"), t("tab6"), t("tab7"), t("tab8"), t("tab9")])

# Tab1: Voice
with tab1:
    st.header("Ask by Voice")
    if st.button("⏹️ Stop Recording"):
        st.session_state.stop_voice = True
        st.rerun()
    if st.session_state.stop_voice:
        st.info("Recording stopped. Click 'Enable' to resume.")
        if st.button("🎤 Enable Recording"):
            st.session_state.stop_voice = False
            st.rerun()
    else:
        audio = st.audio_input("Tap to record")
        if audio:
            with st.spinner("Transcribing..."):
                text = transcribe_audio(audio.getvalue())
            if text:
                st.markdown(f'<div class="user-msg">🗣️ You: {text}</div>', unsafe_allow_html=True)
                with st.spinner("Thinking..."):
                    ans = get_ai_response(text, st.session_state.lang_pref)
                st.markdown(f'<div class="bot-msg">🤖 KisanMitra: {ans}</div>', unsafe_allow_html=True)
                st.session_state.history.append({"q": text, "a": ans})
                detected = detect_language(ans)
                tts = "hi-IN" if detected=="Hindi" else "en-US"
                st.components.v1.html(f'<script>var u=new SpeechSynthesisUtterance({json.dumps(ans)}); u.lang="{tts}"; window.speechSynthesis.speak(u);</script>', height=0)
            else:
                st.error("Could not understand.")
    st.divider()
    st.subheader("Or type your question")
    txt = st.text_input("")
    if st.button("Ask"):
        if txt:
            ans = get_ai_response(txt, st.session_state.lang_pref)
            st.markdown(f'<div class="user-msg">🗣️ You: {txt}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="bot-msg">🤖 KisanMitra: {ans}</div>', unsafe_allow_html=True)
            st.session_state.history.append({"q": txt, "a": ans})
            detected = detect_language(ans)
            tts = "hi-IN" if detected=="Hindi" else "en-US"
            st.components.v1.html(f'<script>var u=new SpeechSynthesisUtterance({json.dumps(ans)}); u.lang="{tts}"; window.speechSynthesis.speak(u);</script>', height=0)

# Tab2: Market
with tab2:
    st.header("Market Prices")
    col1, col2 = st.columns(2)
    with col1: commodity = st.text_input("Commodity", placeholder="Wheat, Rice...")
    with col2: state = st.text_input("State", "Uttar Pradesh")
    if st.button("Get Price"):
        if commodity:
            p = get_mandi_price(commodity, state)
            st.success(f"{p['commodity']}: ₹{p['price']} per quintal")
            st.caption("Source: Sample data (API ready)")

# Tab3: Weather with forecast & alerts
with tab3:
    st.header("Weather & Alerts")
    st.markdown(GPS_HTML, unsafe_allow_html=True)
    st.caption("or enter city manually")
    city = st.text_input("City", "Lucknow")
    if st.button("Get Weather") or ("latitude" in st.query_params):
        if "latitude" in st.query_params:
            lat, lon = st.query_params["latitude"], st.query_params["longitude"]
            city = get_city_from_coords(lat, lon)
            st.success(f"📍 Location: {city}")
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
        alert_level, alerts = get_weather_alert(forecast)
        if alert_level == "red":
            st.error("🚨 Severe Weather Alert")
        elif alert_level == "orange":
            st.warning("⚠️ Weather Advisory")
        for a in alerts:
            st.write(f"- {a}")

# Tab4: Soil Health
with tab4:
    st.header("Soil Health")
    opt = st.radio("Choose option", ["Upload photo", "Upload PDF", "Enter manually"])
    if opt == "Upload photo":
        img = st.file_uploader("", type=["jpg","png"])
        if img:
            image = Image.open(img)
            st.image(image, width=200)
            if st.button("Analyze"):
                with st.spinner("Analyzing..."):
                    advice = analyze_soil_image(image)
                st.markdown(f'<div class="bot-msg">{advice}</div>', unsafe_allow_html=True)
    elif opt == "Upload PDF":
        pdf = st.file_uploader("", type=["pdf"])
        if pdf and st.button("Analyze PDF"):
            with st.spinner("Reading..."):
                advice = analyze_soil_pdf(pdf.read())
            st.markdown(f'<div class="bot-msg">{advice}</div>', unsafe_allow_html=True)
    else:
        data = st.text_area("Enter soil test results (pH, NPK)")
        if st.button("Get Advice"):
            advice = get_soil_advice(data)
            st.markdown(f'<div class="bot-msg">{advice}</div>', unsafe_allow_html=True)

# Tab5: Personalized Advice + Crop Damage Recovery
with tab5:
    st.header("Personalized Advice")
    st.subheader("Crop Damage Recovery (Heavy Rain)")
    crop = st.selectbox("Crop", ["Wheat", "Rice"])
    damage = st.selectbox("Damage type", ["Waterlogging", "Hailstorm"])
    if st.button("Get Recovery Advice"):
        adv = get_crop_damage_advice(crop, damage, st.session_state.lang_pref)
        st.markdown(f'<div class="bot-msg">{adv}</div>', unsafe_allow_html=True)
    st.divider()
    if not st.session_state.farmer_profile:
        st.warning("Please fill farmer profile in sidebar.")
    else:
        question = st.text_area("Your question")
        if st.button("Get Advice"):
            adv = get_personalized_advice(st.session_state.farmer_profile, question)
            st.markdown(f'<div class="bot-msg">{adv}</div>', unsafe_allow_html=True)

# Tab6: Crop Rotation
with tab6:
    st.header("Crop Rotation Advisor")
    col1, col2 = st.columns(2)
    with col1: prev = st.selectbox("Previous crop", ["Sugarcane","Wheat","Rice","Potato"])
    with col2: nxt = st.selectbox("Next crop", ["Wheat","Mustard","Rice","Pulses"])
    if st.button("Check Rotation"):
        # Simple rule based
        if prev=="Sugarcane" and nxt=="Wheat":
            st.success("Good rotation. Sugarcane depletes nitrogen; wheat benefits from added fertilizer.")
        else:
            st.info("Crop rotation improves soil health. Consider adding legumes.")

# Tab7: Women Empowerment
with tab7:
    st.header("Women Farmer Support")
    st.image("https://cdn.pixabay.com/photo/2017/12/09/08/18/women-3009632_640.jpg", width=250)
    st.info("💡 Safety Tip: Always inform family before going to the field.")
    st.write("**Emergency Numbers:** Women Helpline 1091, Police 100")
    st.write("**Small-scale ideas:** Kitchen garden, poultry, mushroom")
    st.write("**Schemes:** MKSP, NRLM for women farmers")

# Tab8: Government Schemes
with tab8:
    st.header("Government Schemes")
    cats = sorted(set([s['category'] for s in SCHEMES_DATA['schemes']]))
    sel_cat = st.radio("Filter", ["All"]+cats, horizontal=True)
    filtered = SCHEMES_DATA['schemes'] if sel_cat=="All" else [s for s in SCHEMES_DATA['schemes'] if s['category']==sel_cat]
    for s in filtered:
        with st.expander(s['name']):
            st.write(s['description'])
            st.markdown(f"[Know More]({s['link']})")

# Tab9: KVK Support
with tab9:
    st.header("Krishi Vigyan Kendra (KVK)")
    district = st.text_input("Enter your district")
    if st.button("Find KVK"):
        kvk = get_kvk_by_district(district)
        if kvk:
            st.success(kvk['center_name'])
            st.write(f"**Head:** {kvk['head']}")
            st.write(f"**Contact:** {kvk['contact']}")
            st.write(f"**Email:** {kvk['email']}")
            st.write(f"**Services:** {kvk['services']}")
        else:
            st.warning("Data not available. Visit kvk.icar.gov.in")

# ---------- Floating Chatbot (no auto-speak) ----------
with st.popover("💬 Help", use_container_width=False):
    st.markdown("### KisanMitra Assistant")
    st.info("Ask me anything about farming or using the app.")
    # No automatic greeting speech
    audio = st.audio_input("Speak your question")
    if audio:
        with st.spinner("Transcribing..."):
            text = transcribe_audio(audio.getvalue())
        if text:
            st.write(f"🗣️ You: {text}")
            with st.spinner("Thinking..."):
                ans = chatbot_response(text)
            st.success(f"🤖 {ans}")
            detected = detect_language(ans)
            tts = "hi-IN" if detected=="Hindi" else "en-US"
            st.components.v1.html(f'<script>var u=new SpeechSynthesisUtterance({json.dumps(ans)}); u.lang="{tts}"; window.speechSynthesis.speak(u);</script>', height=0)
        else:
            st.error("Could not understand.")
    txt_q = st.text_input("Or type your question")
    if txt_q:
        with st.spinner("Thinking..."):
            ans = chatbot_response(txt_q)
        st.success(f"🤖 {ans}")
        detected = detect_language(ans)
        tts = "hi-IN" if detected=="Hindi" else "en-US"
        st.components.v1.html(f'<script>var u=new SpeechSynthesisUtterance({json.dumps(ans)}); u.lang="{tts}"; window.speechSynthesis.speak(u);</script>', height=0)

# Footer
st.markdown("---")
st.caption("🌾 KisanMitra – Voice-First Farming Companion")