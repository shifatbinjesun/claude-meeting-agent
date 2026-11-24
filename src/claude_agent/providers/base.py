"""Provider interfaces (adapter architecture)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class LiveOutput:
    kind: str                     # audio | output_text | input_text | interrupted | turn_complete | tool_call |
                                  # usage | session | error | go_away
    data: Any = None
    turn_id: int = 0
    meta: dict[str, Any] = field(default_factory=dict)


class TextProvider(Protocol):
    name: str

    async def generate(self, system: str, prompt: str, *, image_png: bytes | None = None,
                       max_tokens: int = 400) -> str: ...


class TTSProvider(Protocol):
    name: str
    sample_rate: int

    async def synthesize(self, text: str) -> bytes: ...   # mono s16le PCM at sample_rate
