import streamlit as st
import asyncio
import edge_tts
import base64
import os
import time
import re
from dotenv import load_dotenv
from openai import OpenAI
from groq import Groq
from streamlit_mic_recorder import mic_recorder
from vector_db import process_files, search_knowledge

# ১. সেটিংস ও এনভায়রনমেন্ট লোড
load_dotenv()
st.set_page_config(page_title="Rupa AI", page_icon="💖", layout="wide")

# ২. সেশন স্টেট ম্যানেজমেন্ট
if "or_key" not in st.session_state: st.session_state.or_key = os.getenv("OPENROUTER_API_KEY", "")
if "groq_key" not in st.session_state: st.session_state.groq_key = os.getenv("GROQ_API_KEY", "")
if "pc_key" not in st.session_state: st.session_state.pc_key = os.getenv("PINECONE_API_KEY", "")
if "messages" not in st.session_state: st.session_state.messages = []
if "is_muted" not in st.session_state: st.session_state.is_muted = False
if "mood" not in st.session_state: st.session_state.mood = "Happy"
if "custom_persona" not in st.session_state:
    st.session_state.custom_persona = "তুমি রূপা। মজিবর রহমানের প্রাক্তণ প্রেমিকা। উত্তর হবে সবসময় ২ বাক্যের মধ্যে খুব সংক্ষিপ্ত এবং সুনির্দিষ্ট।"

# --- ৩. UI স্টাইলিং (Mood Color & Center Alignment) ---
main_color = "#ff4baf" if st.session_state.mood == "Happy" else "#4a69bd"
bg_gradient = "linear-gradient(to right, #fcf6f8, #ffffff)" if st.session_state.mood == "Happy" else "linear-gradient(to right, #eef2f3, #ffffff)"

st.markdown(f"""
    <style>
    .stApp {{ background: {bg_gradient}; }}
    .main .block-container {{ padding-bottom: 200px !important; }}
    
    /* ইনপুট সেকশন ছোট এবং একদম সেন্টারে ফিক্সড করা */
    div[data-testid="stChatInput"] {{
        position: fixed;
        bottom: 40px;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: 65% !important;
        z-index: 1000;
        background-color: white;
        border-radius: 25px;
        box-shadow: 0px 10px 30px rgba(0,0,0,0.1);
        border: 2px solid {main_color} !important;
    }}
    
    .stChatMessage {{ border-radius: 15px; margin-bottom: 12px; border-left: 5px solid {main_color}; }}
    </style>
    """, unsafe_allow_html=True)

# --- ৪. ডাইনামিক ভয়েস ফাংশন ---
async def generate_voice(text, lang, mood):
    if st.session_state.is_muted: return
    # ভাষা অনুযায়ী আলাদা ইঞ্জিন
    voice = "en-US-EmmaNeural" if lang == "English" else "bn-BD-NabanitaNeural"
    # মুড অনুযায়ী পিচ
    pitch = "+5Hz" if mood == "Happy" else "-5Hz"
    rate = "+15%" if lang == "English" else "+8%"
    
    # অপ্রয়োজনীয় ক্যারেক্টার ক্লিন করা
    clean_text = re.sub(r'[^\w\s\u0980-\u09FF.,?!]', '', text).strip()
    try:
        communicate = edge_tts.Communicate(clean_text, voice, rate=rate, pitch=pitch)
        await communicate.save("rupa_speech.mp3")
    except: pass

def autoplay_audio():
    if not st.session_state.is_muted and os.path.exists("rupa_speech.mp3"):
        with open("rupa_speech.mp3", "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            st.markdown(f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">', unsafe_allow_html=True)

# --- ৫. সাইডবার ---
with st.sidebar:
    st.title("💖 Rupa's Brain")
    st.session_state.mood = st.radio("Select Mood:", ["Happy", "Sad"], horizontal=True)
    language = st.selectbox("Conversation Language", ["Bangla", "English"])
    
    if st.button("🔇 Mute" if not st.session_state.is_muted else "🔊 Unmute"):
        st.session_state.is_muted = not st.session_state.is_muted
        st.rerun()

    with st.expander("🖼️ Change Avatars"):
        upa_f = st.file_uploader("Rupa's Photo", type=["jpg", "png"])
        user_f = st.file_uploader("User's Photo", type=["jpg", "png"])
    upa_avatar = upa_f if upa_f else "https://cdn-icons-png.flaticon.com/512/6833/6833591.png"
    user_avatar = user_f if user_f else "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"

    with st.expander("🛠️ API Keys"):
        st.session_state.or_key = st.text_input("OpenRouter", value=st.session_state.or_key, type="password")
        st.session_state.groq_key = st.text_input("Groq", value=st.session_state.groq_key, type="password")
        st.session_state.pc_key = st.text_input("Pinecone", value=st.session_state.pc_key, type="password")

    with st.expander("👤 Customize Persona"):
        st.session_state.custom_persona = st.text_area("System Prompt:", value=st.session_state.custom_persona, height=100)

    st.write("🎤 Voice Input:")
    audio = mic_recorder(start_prompt="Record", stop_prompt="Stop", key='recorder')

    with st.expander("📚 Knowledge Base"):
        docs = st.file_uploader("Upload Docs", accept_multiple_files=True, type=['pdf', 'docx'])
        if st.button("Teach Rupa"):
            if docs and st.session_state.pc_key and st.session_state.or_key:
                with st.spinner("Uploading to Pinecone..."):
                    process_files(docs, st.session_state.pc_key, st.session_state.or_key)

# --- ৬. চ্যাট ডিসপ্লে ---
for m in st.session_state.messages:
    avatar = upa_avatar if m["role"] == "assistant" else user_avatar
    with st.chat_message(m["role"], avatar=avatar): st.markdown(m["content"])

# --- ৭. ইনপুট প্রসেসিং ---
user_query = None
if audio and st.session_state.groq_key:
    with open("temp.wav", "wb") as f: f.write(audio['bytes'])
    client_g = Groq(api_key=st.session_state.groq_key)
    with open("temp.wav", "rb") as f:
        ts = client_g.audio.transcriptions.create(file=("temp.wav", f.read()), model="whisper-large-v3")
        user_query = ts.text

text_input = st.chat_input("মজিবর, কিছু বলবে?")
if text_input: user_query = text_input

# --- ৮. রেসপন্স লজিক ---
if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user", avatar=user_avatar): st.markdown(user_query)

    try:
        client = OpenAI(api_key=st.session_state.or_key, base_url="https://openrouter.ai/api/v1")
        ctx = search_knowledge(user_query, st.session_state.pc_key, st.session_state.or_key)
        
        # ভাষা অনুযায়ী কঠোর ইনস্ট্রাকশন
        if language == "English":
            lang_rule = "You must reply ONLY in English text. Use a natural English voice tone."
        else:
            lang_rule = "তোমাকে অবশ্যই শুধুমাত্র বাংলা ভাষায় উত্তর দিতে হবে। কোনো ইংরেজি শব্দ ব্যবহার করো না।"
        
        mood_instr = "Talk in a very Happy and loving way." if st.session_state.mood == "Happy" else "Talk in a very Sad and emotional tone."

        with st.chat_message("assistant", avatar=upa_avatar):
            stream = client.chat.completions.create(
                model="qwen/qwen-2.5-72b-instruct",
                messages=[{"role": "system", "content": f"{st.session_state.custom_persona}\nContext: {ctx}\nMood: {mood_instr}\nRule: {lang_rule} Short response (max 2 sentences)."}] + st.session_state.messages,
                stream=True,
            )
            placeholder = st.empty()
            full_response = ""
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)
            
            # ভাষা ও মুড অনুযায়ী ভয়েস প্লে করা
            asyncio.run(generate_voice(full_response, language, st.session_state.mood))
            autoplay_audio()
            st.session_state.messages.append({"role": "assistant", "content": full_response})
    except Exception as e: st.error(f"Error: {e}")