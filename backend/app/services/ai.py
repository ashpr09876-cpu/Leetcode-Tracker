"""Provider-independent AI layer. Credentials stay on the backend; nothing here fabricates responses."""
import httpx

from app.core.config import Settings, get_settings


class AIError(Exception):
    pass


class AINotConfigured(AIError):
    pass


class AIProviderError(AIError):
    pass


class AIProvider:
    name = "base"

    def __init__(self, settings: Settings):
        self.s = settings

    def complete(self, system: str, messages: list[dict]) -> str:  # messages: [{"role": "user"|"assistant", "content": str}]
        raise NotImplementedError

    def _post(self, url: str, headers: dict, payload: dict) -> dict:
        try:
            r = httpx.post(url, headers=headers, json=payload, timeout=self.s.ai_timeout_seconds)
        except httpx.TimeoutException as e:
            raise AIProviderError(f"{self.name} request timed out") from e
        except httpx.HTTPError as e:
            raise AIProviderError(f"Could not reach {self.name} ({type(e).__name__})") from e
        if r.status_code >= 400:
            raise AIProviderError(f"{self.name} returned HTTP {r.status_code}")
        try:
            return r.json()
        except ValueError as e:
            raise AIProviderError(f"{self.name} returned an invalid response") from e

    @staticmethod
    def _shape(fn):
        try:
            text = fn()
        except (KeyError, IndexError, TypeError) as e:
            raise AIProviderError("Provider returned an unexpected response shape") from e
        if not isinstance(text, str) or not text.strip():
            raise AIProviderError("Provider returned an empty response")
        return text.strip()


class OllamaProvider(AIProvider):
    name = "ollama"

    def complete(self, system, messages):
        data = self._post(f"{self.s.ollama_base_url.rstrip('/')}/api/chat", {},
                          {"model": self.s.ollama_model, "stream": False,
                           "messages": [{"role": "system", "content": system}, *messages]})
        return self._shape(lambda: data["message"]["content"])


class OpenAIProvider(AIProvider):
    name = "openai"

    def complete(self, system, messages):
        data = self._post("https://api.openai.com/v1/chat/completions",
                          {"Authorization": f"Bearer {self.s.openai_api_key}"},
                          {"model": self.s.openai_model,
                           "messages": [{"role": "system", "content": system}, *messages]})
        return self._shape(lambda: data["choices"][0]["message"]["content"])


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def complete(self, system, messages):
        data = self._post("https://api.anthropic.com/v1/messages",
                          {"x-api-key": self.s.anthropic_api_key, "anthropic-version": "2023-06-01"},
                          {"model": self.s.anthropic_model, "max_tokens": 1500, "system": system, "messages": messages})
        return self._shape(lambda: "".join(b["text"] for b in data["content"] if b.get("type") == "text"))


class GeminiProvider(AIProvider):
    name = "gemini"

    def complete(self, system, messages):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.s.gemini_model}:generateContent"
        data = self._post(url, {"x-goog-api-key": self.s.gemini_api_key},
                          {"systemInstruction": {"parts": [{"text": system}]},
                           "contents": [{"role": "user" if m["role"] == "user" else "model",
                                         "parts": [{"text": m["content"]}]} for m in messages]})
        return self._shape(lambda: "".join(p["text"] for p in data["candidates"][0]["content"]["parts"]))


PROVIDERS = {"ollama": OllamaProvider, "openai": OpenAIProvider, "anthropic": AnthropicProvider, "gemini": GeminiProvider}


def is_configured(name: str, s: Settings) -> bool:
    return {"ollama": bool(s.ollama_base_url), "openai": bool(s.openai_api_key),
            "anthropic": bool(s.anthropic_api_key), "gemini": bool(s.gemini_api_key)}.get(name, False)


def configured_providers() -> list[str]:
    s = get_settings()
    return [n for n in PROVIDERS if is_configured(n, s)]


def resolve_provider(user_choice: str = "") -> AIProvider:
    s = get_settings()
    for name in (user_choice, s.ai_provider):
        if name and name in PROVIDERS and is_configured(name, s):
            return PROVIDERS[name](s)
    raise AINotConfigured("No AI provider is configured. Set AI_PROVIDER and the matching API key "
                          "(or OLLAMA_BASE_URL) in backend/.env, then restart the backend.")


SYSTEM_PROMPT = (
    "You are CodeTrack's DSA coach for a student preparing for coding interviews. "
    "Use ONLY the statistics in the JSON context below as facts about the user; never invent numbers, "
    "problems solved, or history. If the data is too thin to support a conclusion, say so. "
    "Be concise, specific, and practical. When recommending problems, name well-known LeetCode problems "
    "and say they are suggestions, not verified catalogue data.\n\nUSER CONTEXT:\n"
)
