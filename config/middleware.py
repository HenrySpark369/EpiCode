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

import logging
from flask import request, jsonify, g
from functools import wraps
from config.model_utils import ModelConfig

model_config = ModelConfig()
logger = logging.getLogger(__name__)

class ModelValidationError(Exception):
    def __init__(self, error_code, message):
        self.error_code = error_code
        self.message = message
        super().__init__(message)

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
        client_ip = request.remote_addr or "unknown"

        try:
            if not model:
                raise ModelValidationError("MODEL_REQUIRED", "Model is required")

            if not model_config.is_model_allowed(model):
                raise ModelValidationError("MODEL_NOT_ALLOWED", f"Model not allowed: {model}")

            input_length = count_tokens(messages)
            if not model_config.validate_input_length(model, input_length):
                raise ModelValidationError(
                    "INPUT_LENGTH_EXCEEDED",
                    f"Input length {input_length} exceeds context window for model {model}"
                )

            g.token_count = input_length
            logger.debug(f"Request from {client_ip}: model={model}, tokens={input_length}")

        except ModelValidationError as e:
            logger.warning(f"Validation error from {client_ip}: {e.error_code} - {e.message}")
            response = jsonify({"error_code": e.error_code, "error": e.message})
            response.status_code = 400
            return response

        except Exception as e:
            logger.error(f"Unexpected error in model_constraints_middleware: {e}", exc_info=True)
            response = jsonify({"error_code": "INTERNAL_ERROR", "error": "Internal server error"})
            response.status_code = 500
            return response

        return f(*args, **kwargs)
    return decorated_function
