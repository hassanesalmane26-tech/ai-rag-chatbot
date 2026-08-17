"""OpenAI adapter; domain orchestration does not depend on the provider SDK."""

from app.ai.contracts import ModelRequest, ModelResult


class OpenAIResponseProvider:
    def __init__(self, client):
        self.client = client

    def complete(self, request: ModelRequest) -> ModelResult:
        response = self.client.responses.create(model=request.model, input=list(request.messages))
        return ModelResult(
            text=response.output_text,
            provider_request_id=getattr(response, "_request_id", None),
        )
