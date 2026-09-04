"""The single unavailable boundary left by the break-first migration."""

from __future__ import annotations


class ProductUnavailable(RuntimeError):
    """The gameplay product cannot be constructed without its executor adapter."""


def require_product(_disc: str | None) -> None:
    """Refuse until the title has a dynarec-only psxport composition."""

    raise ProductUnavailable(
        "the generated-source product was removed; the Vagrant Story adapter to "
        "psxport's dynarec-only executor is not implemented"
    )
