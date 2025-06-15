from flask import request, jsonify, g
from functools import wraps
from config.model_utils import ModelConfig

model_config = ModelConfig()

def count_tokens(messages):
    """
    Simple token count approximation by counting words in message contents.
    This can be replaced with a more accurate tokenizer if needed.
    """
    token_count = 0
    for msg in messages:
        content = msg.get("content", "")
        token_count += len(content.split())
    return token_count

def model_constraints_middleware(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        data = request.get_json() or {}
        model = data.get("model", None)
        messages = data.get("messages") or data.get("input") or []
        if not model:
            return jsonify({"error": "Model is required"}), 400

        # Check if model is allowed
        if not model_config.is_model_allowed(model):
            return jsonify({"error": f"Model not allowed: {model}"}), 400

        # Validate input length against context window
        input_length = count_tokens(messages)
        if not model_config.validate_input_length(model, input_length):
            return jsonify({
                "error": f"Input length {input_length} exceeds context window for model {model}"
            }), 400

        # Store token count in flask.g for potential use downstream
        g.token_count = input_length

        return f(*args, **kwargs)
    return decorated_function
