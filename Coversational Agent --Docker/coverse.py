from flask import Flask, request, jsonify
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import os

app = Flask(__name__)

# Set your local model directory
model_dir = "./model/Qwen3-0.6B"
print(f"🔄 Loading Qwen3-0.6B from local directory: {model_dir}")

tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(model_dir, trust_remote_code=True)
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)
model.eval()

@app.route("/health")
def healthCheck():
    return "Coversational Service is Up!!"


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(force=True)
    user_input = data.get('input', '')
    history = data.get('history', [])  # List of dicts: [{"role": "user", "content": ...}, ...]

    # Format prompt for Qwen3
    messages = history + [{"role": "user", "content": user_input}]
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.eos_token_id
        )
    output_text = tokenizer.decode(outputs[0][inputs['input_ids'].shape[-1]:], skip_special_tokens=True)

    # Update history
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": output_text.strip()})

    return jsonify({
        "response": output_text.strip(),
        "history": history
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
