# Transcription API endpoint
import sys
import requests
import pyttsx3
import time
import asyncio
import threading
import re

# API endpoints
LLM_API = "http://conversational-agent:5000/chat"  # LLM chat
TRANSLATE = "http://indic-translation:5000/translate"  # Kannada to English
TRANSCRIBE_API = "http://transcription-agent:5000/transcribe"  # Transcription Agent

def is_kannada(text):
    # Kannada Unicode range: 0C80–0CFF
    return any(0x0C80 <= ord(char) <= 0x0CFF for char in text if not char.isspace())


def speak_text(text):
    """
    Initializes a new TTS engine, speaks the text, and cleans up.
    This is more robust for use in loops. Emojis are removed before speaking.
    """
    try:
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002700-\U000027BF"  # Dingbats
            "\U000024C2-\U0001F251"  # Enclosed characters
            "]+",
            flags=re.UNICODE
        )
        text_no_emoji = emoji_pattern.sub(r'', text)
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.9)
        engine.say(text_no_emoji)
        engine.runAndWait()
        engine.stop()
    except Exception as e:
        print(f"[ERROR] TTS failed: {e}")
        print("[INFO] Check if a TTS engine like 'espeak' (Linux) or 'SAPI5' (Windows) is installed.")

def startup():
    print("Checking required services...")
    health_endpoints = {
        "LLM Service": "http://conversational-agent:5000/health",
        "Translation Service": "http://indic-translation:5000/health",
        "Transcription Service": "http://transcription-agent:5000/health"
    }
    while True:
        all_up = True
        for name, url in health_endpoints.items():
            try:
                resp = requests.get(url)
                if resp.status_code == 200:
                    print(f"✅ {name} is up.")
                else:
                    print(f"❌ {name} is not responding (status {resp.status_code}). Retrying...")
                    all_up = False
            except Exception as e:
                print(f"❌ {name} is not reachable: {e}. Retrying...")
                all_up = False
        if all_up:
            break
        print("Waiting 5 seconds before retrying...")
        time.sleep(5)

def chat():
    print("\n🤖 Translator & LLM Agent is ready! Type 'exit' to quit.\n")
    history = []

    def run_tts_async(text):
        t = threading.Thread(target=speak_text, args=(text,))
        t.daemon = True
        t.start()

    while True:
        # Choose input mode
        mode = ""
        while mode not in ["1", "2"]:
            print("Choose input mode:")
            print("1. Text input")
            print("2. Voice input (WAV file)")
            mode = input("Enter 1 or 2: ").strip()
        if mode == "1":
            user_input = input("🧑 You (Kannada): ")
            if user_input.lower().strip() in ['exit', 'quit']:
                print("👋 Goodbye.")
                break
        else:
            print("Paste the audio file in the \"audios\" folder.")
            file_name = input("🎤 Enter the file name :").strip()     
            if file_name.lower() in ['exit', 'quit']:
                print("👋 Goodbye.")
                break
            wav_path = "./audios/" + file_name

            print("[DEBUG] Transcribing audio...")
            try:
                with open(wav_path, "rb") as f:
                    files = {"audio": f}
                    resp = requests.post(TRANSCRIBE_API, files=files)
                    resp.raise_for_status()
                    user_input = resp.json().get("transcription", "")
                print(f"[DEBUG] Transcribed text: {user_input}")
            except Exception as e:
                print(f"[ERROR] Transcription failed: {e}")
                continue

        # Check if input is Kannada
        if is_kannada(user_input):
            try:
                response = requests.post(
                    TRANSLATE,
                    json={"sentences": [user_input]},
                )
                response.raise_for_status()
                user_input_en = response.json()["translations"][0]
            except Exception as e:
                print(f"[ERROR] Translation (KN->EN) failed: {e}")
                continue
            print(f"[DEBUG] User input in English: {user_input_en}")
        else:
            user_input_en = user_input

        # Call LLM API with translated input and history
        llm_payload = {
            "input": user_input_en,
            "history": history
        }
        try:
            llm_response = requests.post(
                LLM_API,
                json=llm_payload,
            )
            llm_response.raise_for_status()
            llm_data = llm_response.json()
            llm_output = llm_data.get("response", "[No response]")
            history = llm_data.get("history", history)
        except Exception as e:
            print(f"[ERROR] LLM API call failed: {e}")
            continue
        print(f"🤖 LLM Output (English): {llm_output}")

        # Speak text asynchronously, removing emojis
        run_tts_async(llm_output)

        # Translate LLM output from English to Kannada using HTTP POST
        try:
            response = requests.post(
                TRANSLATE,
                json={"sentences": [llm_output]},
            )
            response.raise_for_status()
            output_text_kn = response.json()["translations"][0]
        except Exception as e:
            print(f"[ERROR] Translation (EN->KN) failed: {e}")
            output_text_kn = "[Translation failed]"
        print(f"🤖 LLM Output (Kannada): {output_text_kn}")

if __name__ == "__main__":
    startup()
    chat()
