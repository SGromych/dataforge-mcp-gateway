"""Result container for DF API v2 write calls.

Write endpoints answer with four distinct shapes:

* ``201 Created`` / ``200 OK`` — the created or updated entity plus ``timestamp``
* ``204 No Content`` — ``DELETE`` succeeded, no body
* ``207 Multi-Status`` — a bulk or assignment call applied only part of the input;
  the body carries ``succeeded[]`` and ``failed[]``

207 must never be flattened into plain success: the caller has to see which rows were
rejected and why.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class WriteResult:
    status_code: int
    payload: dict[str, Any] | None = None
    partial: bool = False

    @property
    def failed(self) -> list[dict[str, Any]]:
        if not self.payload:
            return []
        raw = self.payload.get("failed")
        return raw if isinstance(raw, list) else []

    @property
    def succeeded(self) -> list[dict[str, Any]]:
        if not self.payload:
            return []
        raw = self.payload.get("succeeded")
        return raw if isinstance(raw, list) else []
