import json
import os
import urllib.request
from jaros.llm.client import LlmRequest, LlmResponse

# #EXT-004-REQ-2 Start
class OllamaAdapter:
    """Standard-library-only adapter to communicate with a local Ollama model.

    Decouples model execution from the system control flow.
    """

    def __init__(self) -> None:
        self.host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.model = os.environ.get("OLLAMA_MODEL", "llama3")

    def complete(self, req: LlmRequest) -> LlmResponse:
        """Call Ollama generation endpoint and return standard response."""
        url = f"{self.host.rstrip('/')}/api/generate"
        payload = {
            "model": self.model,
            "prompt": req.prompt,
            "stream": False
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                resp_data = json.loads(response.read().decode("utf-8"))
                text = resp_data.get("response", "").strip()
                return LlmResponse(text=text, model=self.model)
        except Exception as exc:
            raise RuntimeError(f"Ollama complete failed: {exc}")
# #EXT-004-REQ-2 End
