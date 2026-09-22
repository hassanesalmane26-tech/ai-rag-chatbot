"""The only image module that knows the OpenAI SDK."""
import base64
from openai import OpenAI
from app.images.contracts import ASPECT_SIZES, MAX_IMAGE_BYTES, ImageGenerationRequest, ImageGenerationResult


class OpenAIImageProvider:
    def __init__(self, client, model: str):
        self.client, self.model = client, model

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        arguments = dict(model=self.model, prompt=request.prompt, size=ASPECT_SIZES[request.aspect_ratio], n=1, output_format="png")
        if request.source is None:
            response = self.client.images.generate(**arguments)
        else:
            response = self.client.images.edit(image=("source.png", request.source, "image/png"), **arguments)
        if not response.data or not response.data[0].b64_json:
            raise ValueError("Image provider returned no image")
        if len(response.data[0].b64_json) > (MAX_IMAGE_BYTES + 2) // 3 * 4:
            raise ValueError("Image provider returned an oversized image")
        return ImageGenerationResult(base64.b64decode(response.data[0].b64_json, validate=True), "openai", self.model)


def configured_provider(config):
    if config.image_provider != "openai" or not config.openai_key():
        return None
    # No hidden SDK retries: a timed-out request may have been billed already.
    return OpenAIImageProvider(OpenAI(api_key=config.openai_key(), timeout=config.image_timeout_seconds, max_retries=0), config.image_model)
