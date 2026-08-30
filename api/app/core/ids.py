"""UUIDv7. PLAN.md D3 - time-ordered ids keep the primary-key index sequential,
so 'the sets for this session, in order' stays a range scan.

Python 3.12 has no uuid7, so this implements RFC 9562 section 5.7 directly.
"""

from __future__ import annotations

import os
import time
import uuid


def uuid7() -> uuid.UUID:
    ms = int(time.time() * 1000) & 0xFFFFFFFFFFFF  # 48 bits of unix millis
    rand = os.urandom(10)
    b = bytearray(16)
    b[0:6] = ms.to_bytes(6, "big")
    b[6:16] = rand
    b[6] = (b[6] & 0x0F) | 0x70  # version 7
    b[8] = (b[8] & 0x3F) | 0x80  # variant 10
    return uuid.UUID(bytes=bytes(b))
