# Transcription + Chat Agent
import sys
import requests
import pyttsx3
import threading


# API endpoints
LLM_API = "http://localhost:5001/chat"        # LLM chat
TRANSLATE = "http://localhost:5002/translate" # Translation service
TRANSCRIBE_API = "http://localhost:5003/transcribe"  # Transcription service


def is_kannada(text):
    """Detect if text contains Kannada script (Unicode range 0C80–0CFF)."""
    return any(0x0C80 <= ord(char) <= 0x0CFF for char in text if not char.isspace())


def speak_text(text):
    """Run text-to-speech in a blocking manner (emojis removed)."""
    import re
    try:
        emoji_pattern = re.compile(
            "[" 
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # pictographs
            "\U0001F680-\U0001F6FF"  # transport
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002700-\U000027BF"  # dingbats
            "\U000024C2-\U0001F251"  # enclosed chars
            "]+", flags=re.UNICODE
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


def run_tts_async(text):
    """Run TTS in a separate thread."""
    t = threading.Thread(target=speak_text, args=(text,))
    t.daemon = True
    t.start()


def startup():
    """Check if dependent services are alive."""
    print("Checking required services...")
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
                print(f"❌ {name} is not responding ({resp.status_code}).")
                sys.exit(f"Please check that {name} is running and accessible.")
        except Exception as e:
            print(f"❌ {name} is not reachable: {e}")
            sys.exit(f"Please check that {name} is running and accessible.")


def chat():
    """Interactive loop with mode selection every turn."""
    print("\n🤖 Translator & LLM Agent is ready! Type 'exit' to quit.\n")
    history = []

    while True:
        # Always ask for mode
        mode = ""
        while mode not in ["1", "2", "exit", "quit"]:
            print("\nChoose input mode:")
            print("1. Text input")
            print("2. Voice input (WAV/MP3 file)")
            mode = input("Enter 1 or 2 (or type 'exit' to quit): ").strip().lower()

        if mode in ["exit", "quit"]:
            print("👋 Goodbye.")
            break

        # === TEXT INPUT ===
        if mode == "1":
            user_input = input("🧑 You (Kannada/English): ").strip()
            if user_input.lower() in ["exit", "quit"]:
                print("👋 Goodbye.")
                break

        # === AUDIO INPUT (WAV/MP3) ===
        else:
            audio_path = input("🎤 Enter path to WAV/MP3 file (or 'exit' to quit): ").strip()
            if audio_path.lower() in ["exit", "quit"]:
                print("👋 Goodbye.")
                break
            print("[DEBUG] Transcribing audio...")
            try:
                with open(audio_path, "rb") as f:
                    files = {"audio": f}
                    resp = requests.post(TRANSCRIBE_API, files=files)
                    resp.raise_for_status()
                    user_input = resp.json().get("transcription", "")
                print(f"[DEBUG] Transcribed text: {user_input}")
            except Exception as e:
                print(f"[ERROR] Transcription failed: {e}")
                continue

        # === Translation if Kannada input ===
        if is_kannada(user_input):
            try:
                response = requests.post(TRANSLATE, json={"sentences": [user_input]})
                response.raise_for_status()
                user_input_en = response.json()["translations"][0]
            except Exception as e:
                print(f"[ERROR] Translation (KN->EN) failed: {e}")
                continue
            print(f"[DEBUG] User input in English: {user_input_en}")
        else:
            user_input_en = user_input

        # === Call LLM ===
        llm_payload = {"input": user_input_en, "history": history}
        try:
            llm_response = requests.post(LLM_API, json=llm_payload)
            llm_response.raise_for_status()
            llm_data = llm_response.json()
            llm_output = llm_data.get("response", "[No response]")
            history = llm_data.get("history", history)
        except Exception as e:
            print(f"[ERROR] LLM API call failed: {e}")
            continue

        print(f"🤖 LLM Output (English): {llm_output}")

        # === TTS (English Output) ===
        run_tts_async(llm_output)

        # === Translate back to Kannada ===
        try:
            response = requests.post(TRANSLATE, json={"sentences": [llm_output]})
            response.raise_for_status()
            output_text_kn = response.json()["translations"][0]
        except Exception as e:
            print(f"[ERROR] Translation (EN->KN) failed: {e}")
            output_text_kn = "[Translation failed]"
        print(f"🤖 LLM Output (Kannada): {output_text_kn}")


if __name__ == "__main__":
    startup()
    chat()
