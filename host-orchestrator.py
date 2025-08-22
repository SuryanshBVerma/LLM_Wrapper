# Transcription API endpoint
import sys
def is_kannada(text):
    # Kannada Unicode range: 0C80–0CFF
    return any(0x0C80 <= ord(char) <= 0x0CFF for char in text if not char.isspace())
import requests

# API endpoints
LLM_API = "http://localhost:5001/chat"  # LLM chat
TRANSLATE = "http://localhost:5002/translate"  # Kannada to English
TRANSCRIBE_API = "http://localhost:5003/transcribe"  # Transcription Agent

# TTS initialization
tts_available = False
engine = None

try:
    import pyttsx3
    print("🔊 TTS Engine (pyttsx3) initializing...")
    engine = pyttsx3.init()
    # Set properties ONCE for better performance
    engine.setProperty('rate', 150)  # Speed percent
    engine.setProperty('volume', 0.9)  # Volume 0-1
    tts_available = True
    print("✅ TTS Engine is ready.")
except Exception as e:
    print(f"[WARNING] pyttsx3 initialization failed (likely missing espeak): {e}")
    tts_available = False

def speak_text(text):
    """Safely speak text using the pre-initialized TTS engine."""
    if not tts_available or not engine:
        print("[INFO] TTS not available, skipping speech.")
        return

    try:
        engine.say(text)
        return True
    except RuntimeError as e:
        print(f"[ERROR] TTS Runtime Error: {e}. The engine may be in a bad state.")
    except Exception as e:
        print(f"[ERROR] TTS failed during speech: {e}")


def startup():
    print("Checking required services...")
    # Use /health endpoint for health check
    health_endpoints = {
        "LLM Service": "http://localhost:5001/health",
        "Translation Service": "http://localhost:5002/health",
        "Transcription Service": "http://localhost:5003/health"
    }
    for name, url in health_endpoints.items():
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                print(f"✅ {name} is up.")
            else:
                print(f"❌ {name} is not responding (status {resp.status_code}).")
                sys.exit(f"Please check that {name} is running and accessible.")
        except Exception as e:
            print(f"❌ {name} is not reachable: {e}")
            sys.exit(f"Please check that {name} is running and accessible.")

def chat():
    print("\n🤖 Translator & LLM Agent is ready! Type 'exit' to quit.\n")
    history = []

    # Choose input mode
    mode = ""
    while mode not in ["1", "2"]:
        print("Choose input mode:")
        print("1. Text input")
        print("2. Voice input (WAV file)")
        mode = input("Enter 1 or 2: ").strip()

    while True:
        if mode == "1":
            user_input = input("🧑 You (Kannada): ")
            if user_input.lower().strip() in ['exit', 'quit']:
                print("👋 Goodbye.")
                break
        else:
            wav_path = input("🎤 Enter path to WAV file (or type 'exit' to quit): ").strip()
            if wav_path.lower() in ['exit', 'quit']:
                print("👋 Goodbye.")
                break
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
        speak_text(llm_output)

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
