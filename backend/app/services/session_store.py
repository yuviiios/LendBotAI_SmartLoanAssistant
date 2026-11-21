"""Durable chat turns with a short, per-session write lease."""
import json
import os
import time
from uuid import uuid4

import redis
from sqlalchemy import Column, Float, Integer, JSON, String, Table, select, update
from sqlalchemy.exc import IntegrityError

from app.services.applications import database, metadata

chats = Table("loan_chats", metadata,
    Column("id", String(128), primary_key=True), Column("state", JSON, nullable=False),
    Column("history", JSON, nullable=False), Column("revision", Integer, nullable=False),
    Column("owner", String(36)), Column("busy_until", Float, nullable=False),
)


class TurnConflict(Exception):
    pass


class SessionStore:
    def snapshot(self, session_id):
        with database().connect() as conn:
            row = conn.execute(select(chats).where(chats.c.id == session_id)).mappings().first()
        if row:
            return dict(row)
        state, history = {}, []
        if url := os.getenv("REDIS_URL"):
            # Import still-active sessions from the previous Redis-only release.
            client = redis.from_url(url, socket_timeout=2, socket_connect_timeout=2)
            try:
                old_state, old_history = client.mget(f"session:{session_id}", f"history:{session_id}")
                state, history = json.loads(old_state or "{}"), json.loads(old_history or "[]")
            finally:
                client.close()
        return dict(id=session_id, state=state, history=history, revision=0, busy_until=0)

    def begin(self, session_id, expected_revision):
        row = self.snapshot(session_id)
        if "owner" not in row:
            try:
                with database().begin() as conn:
                    conn.execute(chats.insert().values(**row))
            except IntegrityError:
                row = self.snapshot(session_id)
        if expected_revision is not None and expected_revision != row["revision"]:
            raise TurnConflict
        owner = str(uuid4())
        now = time.time()
        with database().begin() as conn:
            changed = conn.execute(update(chats).where(chats.c.id == session_id,
                chats.c.revision == row["revision"], chats.c.busy_until <= now).values(
                owner=owner, busy_until=now+60))
            if not changed.rowcount:
                raise TurnConflict
        return row, owner

    def finish(self, session_id, owner, **values):
        with database().begin() as conn:
            changed = conn.execute(update(chats).where(chats.c.id == session_id,
                chats.c.owner == owner).values(owner=None, busy_until=0, **values))
            if not changed.rowcount:
                raise TurnConflict
