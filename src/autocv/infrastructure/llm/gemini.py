import json
import time
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from autocv.prompts.resume import SYSTEM


class ProviderError(RuntimeError):
    """Safe diagnostic metadata; never retain the provider body or URL."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def call_gemini(key: str, user_prompt: str, model: str) -> str:
    """Call the specified Gemini model, retrying only transient failures."""
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{quote(model, safe='.-')}:generateContent"
    )
    body = json.dumps({
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": 0.15,
            "topP": 0.8,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json",
        },
    }, ensure_ascii=False).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            request = Request(url, data=body, method="POST",
                              headers={"Content-Type": "application/json; charset=utf-8",
                                       "x-goog-api-key": key})
            with urlopen(request, timeout=90) as response:
                try:
                    payload = json.loads(response.read().decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    raise ProviderError("provider_invalid_response", "Gemini returned an invalid response.") from None
            if not isinstance(payload, dict):
                raise ProviderError("provider_invalid_response", "Gemini returned an invalid response.")
            candidates = payload.get("candidates", [])
            if not candidates:
                raise ProviderError("provider_no_candidate", "Gemini returned no candidate.")
            if candidates[0].get("finishReason") == "MAX_TOKENS":
                raise ProviderError("provider_token_limit", "Gemini reached the output token limit; refusing to render an incomplete CV.")
            text = "".join(str(part.get("text", "")) for part in candidates[0].get("content", {}).get("parts", [])).strip()
            if not text:
                raise ProviderError("provider_empty_response", "Gemini returned an empty response.")
            return text
        except HTTPError as exc:
            # Never echo provider bodies, URLs or credentials, including in tracebacks.
            if exc.code not in {408, 429, 500, 502, 503, 504}:
                raise ProviderError(f"provider_http_{exc.code}", f"Gemini request failed with HTTP {exc.code}.") from None
            last_error = ProviderError(f"provider_http_{exc.code}", f"Gemini request failed with HTTP {exc.code}.")
        except URLError as exc:
            if isinstance(exc.reason, ssl.SSLCertVerificationError):
                raise ProviderError("provider_tls", "Could not verify the Gemini TLS certificate.") from None
            last_error = ProviderError("provider_network", "Could not reach the Gemini API.")
        except TimeoutError:
            last_error = ProviderError("provider_timeout", "The Gemini request timed out.")
        if attempt < 2:
            time.sleep(2 ** attempt)
    assert last_error is not None
    raise last_error
