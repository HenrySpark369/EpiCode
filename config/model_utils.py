import json
import os
from typing import Optional, Dict, Any

class ModelConfig:
    def __init__(self, config_path: str = "config/allowed_models.json"):
        self.config_path = config_path
        self.models = {}
        self.last_updated = None
        self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Model config file not found: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.models = data.get("models", {})
            self.last_updated = data.get("last_updated", None)

    def get_model(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve the configuration for a specific model by name."""
        return self.models.get(model_name)

    def is_model_allowed(self, model_name: str) -> bool:
        """Check if a model is in the allowed models list."""
        return model_name in self.models

    def get_rate_limit(self, model_name: str, tier: str = "free") -> Optional[int]:
        """Get the tokens per minute rate limit for a model at a given tier."""
        model = self.get_model(model_name)
        if model:
            rate_limits = model.get("rate_limits_tpm", {})
            return rate_limits.get(tier)
        return None

    def supports_feature(self, model_name: str, feature: str) -> bool:
        """Check if a model supports a specific feature."""
        model = self.get_model(model_name)
        if model:
            features = model.get("supported_features", [])
            return feature in features
        return False

    def validate_input_length(self, model_name: str, input_length: int) -> bool:
        """Validate if the input length is within the model's context window."""
        model = self.get_model(model_name)
        if model:
            return input_length <= model.get("context_window", 0)
        return False

    def get_pricing(self, model_name: str) -> Optional[Dict[str, float]]:
        """Get pricing details for a model."""
        model = self.get_model(model_name)
        if model:
            return model.get("pricing_per_1m_tokens")
        return None
