"""Outbound email.

SPECIFICATIONS.MD Sec 32 Q3 (which provider) is still open. That question does
not block anything: the app depends on this Protocol, and the console sender
below is a complete implementation for development and tests. Answering Q3
means adding one more class, not changing any caller.
"""

from __future__ import annotations

import logging
from typing import Protocol

log = logging.getLogger("geektrainer.mail")


class EmailSender(Protocol):
    def send(self, *, to: str, subject: str, body: str) -> None: ...


class ConsoleEmailSender:
    """Development sender - writes to the log instead of the network."""

    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def send(self, *, to: str, subject: str, body: str) -> None:
        self.sent.append({"to": to, "subject": subject, "body": body})
        log.info("email to=%s subject=%s\n%s", to, subject, body)


_sender: EmailSender = ConsoleEmailSender()


def get_sender() -> EmailSender:
    return _sender


def set_sender(sender: EmailSender) -> None:
    global _sender
    _sender = sender
