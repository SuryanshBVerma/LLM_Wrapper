import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from IndicTransToolkit.processor import IndicProcessor
from flask import Flask, request, jsonify

'''
    TRANSLATION USING INDICTRANS MODELS.
    MODELS ARE BEING CASHED
'''

class KannadaTranslator:
    def __init__(self): 
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Initialize English to Kannada model
        self.en_kn_model_name = "ai4bharat/indictrans2-en-indic-dist-200M"
        self.en_kn_tokenizer = AutoTokenizer.from_pretrained(
            self.en_kn_model_name, 
            trust_remote_code=True
        )
        self.en_kn_model = AutoModelForSeq2SeqLM.from_pretrained(
            self.en_kn_model_name,
            trust_remote_code=True,
            torch_dtype=torch.float16,
            attn_implementation="flash_attention_2" if torch.cuda.is_available() else None
        ).to(self.device)
        
        # Initialize Kannada to English model
        self.kn_en_model_name = "ai4bharat/indictrans2-indic-en-dist-200M"
        self.kn_en_tokenizer = AutoTokenizer.from_pretrained(
            self.kn_en_model_name, 
            trust_remote_code=True
        )
        self.kn_en_model = AutoModelForSeq2SeqLM.from_pretrained(
            self.kn_en_model_name,
            trust_remote_code=True,
            torch_dtype=torch.float16,
            attn_implementation="flash_attention_2" if torch.cuda.is_available() else None
        ).to(self.device)
        
        self.ip = IndicProcessor(inference=True)
    
    def detect_language(self, text):
        """Simple language detection based on script"""
        if any('\u0C80' <= char <= '\u0CFF' for char in text):  # Kannada Unicode range
            return "kn"
        else:
            return "en"
    
    def translate(self, input_sentences):
        if not input_sentences:
            return []
        
        # Detect language from first sentence
        lang = self.detect_language(input_sentences[0])
        
        if lang == "en":
            return self._translate_en_to_kn(input_sentences)
        else:
            return self._translate_kn_to_en(input_sentences)
    
    def _translate_en_to_kn(self, sentences):
        batch = self.ip.preprocess_batch(
            sentences,
            src_lang="eng_Latn",
            tgt_lang="kan_Knda",
        )
        
        inputs = self.en_kn_tokenizer(
            batch,
            truncation=True,
            padding="longest",
            return_tensors="pt",
            return_attention_mask=True,
        ).to(self.device)
        
        with torch.no_grad():
            generated_tokens = self.en_kn_model.generate(
                **inputs,
                use_cache=True,
                min_length=0,
                max_length=256,
                num_beams=5,
                num_return_sequences=1,
            )
        
        generated_tokens = self.en_kn_tokenizer.batch_decode(
            generated_tokens,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )
        
        translations = self.ip.postprocess_batch(generated_tokens, lang="kan_Knda")
        return translations
    
    def _translate_kn_to_en(self, sentences):
        batch = self.ip.preprocess_batch(
            sentences,
            src_lang="kan_Knda",
            tgt_lang="eng_Latn",
        )
        
        inputs = self.kn_en_tokenizer(
            batch,
            truncation=True,
            padding="longest",
            return_tensors="pt",
            return_attention_mask=True,
        ).to(self.device)
        
        with torch.no_grad():
            generated_tokens = self.kn_en_model.generate(
                **inputs,
                use_cache=True,
                min_length=0,
                max_length=256,
                num_beams=5,
                num_return_sequences=1,
            )
        
        generated_tokens = self.kn_en_tokenizer.batch_decode(
            generated_tokens,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )
        
        translations = self.ip.postprocess_batch(generated_tokens, lang="eng_Latn")
        return translations


# === Flask Server ===
app = Flask(__name__)
translator = KannadaTranslator()


@app.route("/health")
def healthCheck():
    return "Translation Service is Up!!"

@app.route("/translate", methods=["POST"])
def translate_api():
    data = request.get_json(force=True)
    sentences = data.get("sentences")
    if not sentences or not isinstance(sentences, list):
        return jsonify({"error": "Missing or invalid 'sentences' (must be a list of strings)."}), 400
    translations = translator.translate(sentences)
    lang = translator.detect_language(sentences[0]) if sentences else None
    return jsonify({
        "input_language": lang,
        "translations": translations
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)