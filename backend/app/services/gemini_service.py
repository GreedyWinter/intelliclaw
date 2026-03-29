import json
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request

from backend.app.config import GEMINI_API_ENDPOINT, GEMINI_MODEL, GOOGLE_API_KEY


class GeminiServiceError(RuntimeError):
    pass


@dataclass
class GeminiJsonResult:
    payload: dict[str, Any]
    raw_text: str
    model: str


class GeminiService:
    def __init__(
        self,
        *,
        api_key: str = GOOGLE_API_KEY,
        model: str = GEMINI_MODEL,
        endpoint: str = GEMINI_API_ENDPOINT,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.endpoint = endpoint.rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def generate_json(
        self,
        *,
        system_instruction: str,
        prompt: str,
        temperature: float = 0.2,
    ) -> GeminiJsonResult:
        if not self.enabled:
            raise GeminiServiceError("GOOGLE_API_KEY is not configured.")

        url = (
            f"{self.endpoint}/models/{self.model}:generateContent?"
            f"key={parse.quote(self.api_key)}"
        )
        payload = {
            "system_instruction": {
                "parts": [{"text": system_instruction}],
            },
            "contents": [
                {
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=60) as response:
                body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise GeminiServiceError(
                f"Gemini HTTP error {exc.code}: {detail}"
            ) from exc
        except error.URLError as exc:
            raise GeminiServiceError(f"Gemini network error: {exc.reason}") from exc

        try:
            data = json.loads(body)
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts).strip()
            json_payload = json.loads(text)
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise GeminiServiceError(
                f"Gemini returned an unexpected response: {body[:500]}"
            ) from exc

        return GeminiJsonResult(payload=json_payload, raw_text=text, model=self.model)
