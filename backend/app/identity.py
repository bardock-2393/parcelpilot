from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Identity:
    session_id: str
    role: Literal["customer", "internal"]
    account_id: str | None  # None for internal role (cross-account access)

    @property
    def is_internal(self) -> bool:
        return self.role == "internal"
