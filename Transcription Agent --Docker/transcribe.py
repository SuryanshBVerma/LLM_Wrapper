# Flask server for audio transcription
import torch
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq
import torchaudio
import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow CORS from all domains

# === CONFIG ===
MODEL_ID = "steja/whisper-small-kannada"
TARGET_SAMPLE_RATE = 16000
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# === Load the model (from local cache after first download) ===
print(f"[INFO] Loading model: {MODEL_ID} on {DEVICE}...")
processor = AutoProcessor.from_pretrained(MODEL_ID)
model = AutoModelForSpeechSeq2Seq.from_pretrained(MODEL_ID).to(DEVICE)
print("[INFO] Model loaded successfully!")

# === Audio transcription helper ===
def transcribe_audio(audio_path: str) -> str:
    if not os.path.isfile(audio_path):
        return "[ERROR] File not found: {}".format(audio_path)

    # Load audio (works for wav, mp3, flac if ffmpeg backend is available)
    waveform, sr = torchaudio.load(audio_path)

    # Downmix to mono if stereo
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)

    # Resample if needed
    if sr != TARGET_SAMPLE_RATE:
        waveform = torchaudio.functional.resample(
            waveform, orig_freq=sr, new_freq=TARGET_SAMPLE_RATE
        )
        sr = TARGET_SAMPLE_RATE

    # Convert to 1D numpy array
    waveform = waveform.squeeze().numpy()

    # Prepare input features
    inputs = processor(
        waveform,
        sampling_rate=sr,
        return_tensors="pt"
    ).to(DEVICE)

    # Generate transcription
    with torch.no_grad():
        generated_ids = model.generate(inputs["input_features"])
        transcription = processor.batch_decode(
            generated_ids, skip_special_tokens=True
        )[0]

    return transcription

# === Flask Routes ===
@app.route("/transcribe", methods=["POST"])
def transcribe_endpoint():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided."}), 400

    audio_file = request.files["audio"]

    # Save file as temp with original extension
    ext = os.path.splitext(audio_file.filename)[-1].lower()
    if ext not in [".wav", ".mp3", ".flac"]:
        return jsonify({"error": f"Unsupported file format: {ext}"}), 400

    temp_path = f"temp_audio{ext}"
    audio_file.save(temp_path)

    try:
        transcription = transcribe_audio(temp_path)
        return jsonify({"transcription": transcription})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "model": MODEL_ID})

# === Run Server ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
