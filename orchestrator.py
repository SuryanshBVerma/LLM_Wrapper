# Transcription API endpoint
import sys
def is_kannada(text):
    # Kannada Unicode range: 0C80–0CFF
    return any(0x0C80 <= ord(char) <= 0x0CFF for char in text if not char.isspace())
import requests

# API endpoints
LLM_API = "http://conversational-agent:5000/chat"  # LLM chat
TRANSLATE = "http://indic-translation:5000/translate"  # Kannada to English
TRANSCRIBE_API = "http://transcription-agent:5000/transcribe"  # Transcription Agent

import time
# Try to initialize pyttsx3, handle missing espeak gracefully
try:
    import pyttsx3
    engine = pyttsx3.init()
    tts_available = True
except Exception as e:
    print("[WARNING] pyttsx3 initialization failed (likely missing espeak):", e)
    tts_available = False

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

        # Convert LLM response to speech using pyttsx3 if available
        if tts_available:
            try:
                engine.say(llm_output)
                engine.runAndWait()
            except Exception as e:
                print(f"[ERROR] TTS failed: {e}")
        else:
            print("[INFO] TTS not available (missing espeak or pyttsx3). Skipping speech synthesis.")

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
