from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class LoraInferenceAdapter:
    def __init__(self, base_model: str, adapter_path: str):
        self.base_model = base_model
        self.adapter_path = Path(adapter_path)
        self._tokenizer = None
        self._model = None

    def available(self) -> bool:
        return self.adapter_path.exists()

    def _load(self) -> None:
        if self._model is not None:
            return
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(self.base_model)
        base = AutoModelForCausalLM.from_pretrained(self.base_model)
        self._model = PeftModel.from_pretrained(base, str(self.adapter_path))

    def generate_json(self, prompt: str, max_new_tokens: int = 256) -> dict[str, Any]:
        if not self.available():
            raise FileNotFoundError(f"LoRA adapter not found at {self.adapter_path}")
        self._load()
        inputs = self._tokenizer(prompt, return_tensors="pt")
        outputs = self._model.generate(**inputs, max_new_tokens=max_new_tokens)
        text = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
        json_start = text.find("{")
        json_end = text.rfind("}")
        return json.loads(text[json_start : json_end + 1])
