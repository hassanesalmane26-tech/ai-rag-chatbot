"""Provider-neutral image boundary. No provider credentials cross this contract."""
from dataclasses import dataclass
from typing import Protocol
import io
import re
import warnings

from PIL import Image

MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_PIXELS = 16_000_000
ASPECT_SIZES = {"1:1": "1024x1024", "3:2": "1536x1024", "2:3": "1024x1536"}


@dataclass(frozen=True)
class ImageGenerationRequest:
    prompt: str
    aspect_ratio: str
    source: bytes | None = None


@dataclass(frozen=True)
class ImageGenerationResult:
    content: bytes
    provider: str
    model: str


class ImageGenerationProvider(Protocol):
    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult: ...


def normalize_image(content: bytes) -> tuple[bytes, int, int]:
    """Decode bounded raster input and strip metadata; never serve uploaded SVG/HTML."""
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise ValueError("Image vide ou supérieure à 12 Mo.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                if image.format not in {"PNG", "JPEG", "WEBP"} or getattr(image, "n_frames", 1) != 1:
                    raise ValueError("Utilisez une image PNG, JPEG ou WebP non animée.")
                if image.width * image.height > MAX_PIXELS:
                    raise ValueError("Image supérieure à 16 mégapixels.")
                width, height = image.size
                image.load()
                output = io.BytesIO()
                image.convert("RGBA").save(output, format="PNG")
                normalized = output.getvalue()
                if len(normalized) > MAX_IMAGE_BYTES:
                    raise ValueError("Image décodée trop volumineuse.")
                return normalized, width, height
    except (OSError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError("Image invalide ou trop volumineuse.") from exc


def image_intent(text: str) -> bool:
    """Conservative explicit creation intent; never route a generic question to a paid tool."""
    return bool(re.match(
        r"^\s*(?:(?:please|s['’]il te pla[îi]t)\s+)?(?:g[ée]n[èe]re(?:r|z)?|cr[ée]e(?:r|z)?|dessine(?:r|z)?|generate|create|draw|make)\b.{0,65}\b(?:image|illustration|photo|picture|logo|visuel|portrait)\b",
        text, re.I,
    ))


def image_edit_intent(text: str) -> bool:
    """Explicit image reference required: ordinary text editing stays conversational."""
    return bool(re.match(
        r"^\s*(?:modifie|retouche|transforme|edit|modify|change)\b.{0,45}\b(?:image|photo|illustration|picture)\b",
        text, re.I,
    ))
