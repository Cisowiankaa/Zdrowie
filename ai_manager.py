import os
from dataclasses import dataclass

@dataclass
class AIState:
    available: bool
    enabled: bool
    mode: str
    label: str
    reason: str | None = None

def _has_openai_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())

def get_ai_state(online: bool) -> AIState:
    if not online:
        return AIState(
            available=False,
            enabled=False,
            mode="offline",
            label="AI niedostępne — offline",
            reason="no_internet",
        )

    if not _has_openai_key():
        return AIState(
            available=False,
            enabled=False,
            mode="local",
            label="Tryb lokalny — AI niedostępne",
            reason="missing_api_key",
        )

    # Celowo nie wykonujemy płatnego testu API przy każdym odświeżeniu.
    # Prawdziwy request AI powinien mieć własny timeout i fallback.
    return AIState(
        available=True,
        enabled=True,
        mode="ai",
        label="AI dostępne",
    )
