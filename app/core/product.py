"""Canonical, presentation-only TRIDENT product attribution."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ProductMetadata:
    product: str
    creator: str
    attribution: str
    project_mark: str

    def public_dict(self) -> dict[str, str]:
        return asdict(self)


TRIDENT_PRODUCT = ProductMetadata(
    product="TRIDENT",
    creator="Salmane Hassan",
    attribution="Created by Salmane Hassan",
    project_mark="A TRIDENT Project",
)
