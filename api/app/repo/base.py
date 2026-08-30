"""Repository conventions.

Every user-owned query goes through a repo bound to one user_id. Routes never
build their own filters - PLAN.md D9, SPECIFICATIONS.MD 23.1.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import Session


class UserScoped:
    """Base for repositories over user-owned tables.

    Holding the user_id on the repo - rather than passing it per call - means a
    handler cannot forget it, and `scoped()` is the only way these repos build
    a statement.
    """

    def __init__(self, db: Session, user_id: uuid.UUID) -> None:
        if user_id is None:
            raise ValueError("UserScoped repositories require a user_id")
        self.db = db
        self.user_id = user_id

    def scoped(self, model) -> Select:
        return select(model).where(model.user_id == self.user_id)
