from dataclasses import dataclass

from connectivity_manager import get_connectivity_state
from ai_manager import get_ai_state

@dataclass
class RuntimeMode:
    code: str
    label: str
    online: bool
    ai_enabled: bool

def detect_runtime_mode() -> RuntimeMode:
    net = get_connectivity_state()
    ai = get_ai_state(net.online)

    if net.online and ai.enabled:
        return RuntimeMode(
            code="ONLINE_AI",
            label="Online + AI",
            online=True,
            ai_enabled=True,
        )

    if net.online:
        return RuntimeMode(
            code="ONLINE_LOCAL",
            label="Online — tryb lokalny",
            online=True,
            ai_enabled=False,
        )

    return RuntimeMode(
        code="OFFLINE",
        label="Offline",
        online=False,
        ai_enabled=False,
    )
