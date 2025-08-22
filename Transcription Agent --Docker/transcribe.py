
# Flask server for audio transcription
import torch
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq
import torchaudio
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# === CONFIG ===
model_id = "steja/whisper-small-kannada"
sample_rate = 16000
device = "cuda" if torch.cuda.is_available() else "cpu"

# === Load the model (from local cache after first download) ===
processor = AutoProcessor.from_pretrained(model_id)
model = AutoModelForSpeechSeq2Seq.from_pretrained(model_id).to(device)

def transcribe_audio(audio_path):
    if not os.path.isfile(audio_path):
        return "[ERROR] File not found: {}".format(audio_path)
    waveform, sr = torchaudio.load(audio_path)
    if sr != sample_rate:
        waveform = torchaudio.functional.resample(waveform, orig_freq=sr, new_freq=sample_rate)
    inputs = processor(waveform.squeeze(), sampling_rate=sample_rate, return_tensors="pt").to(device)
    with torch.no_grad():
        generated_ids = model.generate(inputs["input_features"])
        transcription = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return transcription

@app.route('/transcribe', methods=['POST'])
def transcribe_endpoint():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided."}), 400
    audio_file = request.files['audio']
    temp_path = "temp_audio.wav"
    audio_file.save(temp_path)
    try:
        transcription = transcribe_audio(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    return jsonify({"transcription": transcription})

@app.route('/health')
def healthCheck():
    return "Transcription service is up !!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)