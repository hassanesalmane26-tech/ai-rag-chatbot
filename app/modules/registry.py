"""Immutable descriptors for capabilities available in each TRIDENT edition."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ModuleDescriptor:
    id: str
    label: str
    order: int
    editions: tuple[str, ...]
    status: str = "ready"


MODULES = (
    ModuleDescriptor("home", "Accueil", 10, ("genesis", "ai", "pro", "nova")),
    ModuleDescriptor("conversations", "Nova", 20, ("genesis", "ai", "pro", "nova")),
    ModuleDescriptor("knowledge", "Knowledge", 30, ("genesis", "ai", "pro", "nova")),
    ModuleDescriptor("memory", "Memory", 40, ("genesis", "ai", "pro", "nova")),
    ModuleDescriptor("files", "Files", 50, ("ai", "pro", "nova")),
    ModuleDescriptor("artifacts", "Artifacts", 60, ("ai", "pro", "nova")),
    ModuleDescriptor("activity", "Activity", 70, ("ai", "pro", "nova")),
    ModuleDescriptor("settings", "Settings", 80, ("ai", "pro", "nova")),
)


def modules_for_edition(edition: str = "ai") -> tuple[ModuleDescriptor, ...]:
    return tuple(
        sorted(
            (module for module in MODULES if edition in module.editions),
            key=lambda module: module.order,
        )
    )


def serialize_module(module: ModuleDescriptor) -> dict:
    return asdict(module)
