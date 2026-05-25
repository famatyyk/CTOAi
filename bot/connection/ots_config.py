"""OTS connection config — server address, character and login settings.

Values are read from environment variables or .env file so secrets never
land in source code.
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


@dataclass
class OTSConfig:
    host: str = field(default_factory=lambda: _env("OTS_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(_env("OTS_PORT", "7171")))
    account: str = field(default_factory=lambda: _env("OTS_ACCOUNT", ""))
    password: str = field(default_factory=lambda: _env("OTS_PASSWORD", ""))
    character: str = field(default_factory=lambda: _env("OTS_CHARACTER", ""))
    # Client window title to look for (may differ per server)
    window_title: str = field(
        default_factory=lambda: _env("OTS_WINDOW_TITLE", "Tibia")
    )
    # Pixel offsets for this specific server client (override via env)
    hp_bar_region: tuple[int, int, int, int] = field(
        default_factory=lambda: _parse_region(
            _env("OTS_HP_BAR_REGION", "0,0,140,10")
        )
    )
    mp_bar_region: tuple[int, int, int, int] = field(
        default_factory=lambda: _parse_region(
            _env("OTS_MP_BAR_REGION", "0,12,140,22")
        )
    )

    def is_configured(self) -> bool:
        return bool(self.host and self.account and self.character)

    def summary(self) -> str:
        return (
            f"OTS {self.host}:{self.port}  "
            f"char={self.character or '(not set)'}  "
            f"configured={'yes' if self.is_configured() else 'NO'}"
        )


def _parse_region(s: str) -> tuple[int, int, int, int]:
    parts = [int(x.strip()) for x in s.split(",")]
    if len(parts) != 4:
        raise ValueError(f"Region must be 4 ints: {s!r}")
    return tuple(parts)  # type: ignore[return-value]


# Module-level singleton — import and use directly
_config: OTSConfig | None = None


def get_config() -> OTSConfig:
    global _config
    if _config is None:
        # Load .env if present (best-effort)
        _load_dotenv()
        _config = OTSConfig()
    return _config


def _load_dotenv() -> None:
    env_path = ".env"
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())
