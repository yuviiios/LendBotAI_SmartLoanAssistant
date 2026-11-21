"""Persist the graph at user-visible boundaries. A revision guards every transition."""
import os
from functools import lru_cache
from uuid import uuid4

from sqlalchemy import Column, LargeBinary, Integer, JSON, MetaData, String, Table, create_engine, select, update
from sqlalchemy.exc import IntegrityError

metadata = MetaData()
applications = Table("loan_applications", metadata,
    Column("id", String(36), primary_key=True),
    Column("request_key", String(128), unique=True, nullable=False),
    Column("revision", Integer, nullable=False),
    Column("inputs", JSON, nullable=False),
    Column("decision", JSON),
)


letters = Table("sanction_documents", metadata,
    Column("id", String(36), primary_key=True), Column("pdf", LargeBinary, nullable=False))


def read_letter(application_id):
    with database().connect() as conn:
        return conn.execute(select(letters.c.pdf).where(letters.c.id == application_id)).scalar_one_or_none()


@lru_cache
def engine(url: str):
    db = create_engine(url, pool_pre_ping=True)
    with db.begin() as conn:
        # Concurrent cold starts must agree on the schema before accepting a turn.
        if db.dialect.name == "sqlite":
            conn.exec_driver_sql("BEGIN IMMEDIATE")
        elif db.dialect.name == "postgresql":
            conn.exec_driver_sql("SELECT pg_advisory_xact_lock(76120419)")
        metadata.create_all(conn)
    return db


def database():
    url = os.getenv("DATABASE_URL", "sqlite:///lendbot.db")
    if url.startswith(("postgres://", "postgresql://")):
        url = "postgresql+psycopg://" + url.split("://", 1)[1]
    return engine(url)


def load_application(application_id):
    with database().connect() as conn:
        return conn.execute(select(applications).where(applications.c.id == application_id)).mappings().first()


def open_application(inputs, request_key):
    key = request_key or str(uuid4())
    application_id = str(uuid4())
    try:
        with database().begin() as conn:
            conn.execute(applications.insert().values(id=application_id, request_key=key,
                         revision=0, inputs=inputs))
    except IntegrityError:
        with database().connect() as conn:
            row = conn.execute(select(applications).where(applications.c.request_key == key)).mappings().one()
            if row["inputs"] != inputs:
                raise ValueError("This request ID already belongs to different terms.")
            return row
    return load_application(application_id)


def save_decision(row, decision, pdf=None):
    with database().begin() as conn:
        changed = conn.execute(update(applications).where(applications.c.id == row["id"],
                     applications.c.revision == row["revision"]).values(
                     decision=decision, revision=row["revision"] + 1))
        if changed.rowcount and pdf is not None:
            conn.execute(letters.insert().values(id=row["id"], pdf=pdf))
    return load_application(row["id"])["decision"]


def cancel_pending(application_id):
    row = load_application(application_id)
    if row and row["decision"] and row["decision"]["result"]["status"] == "HOLD":
        save_decision(row, {"application_id": application_id, "stage": "CREDIT",
                            "result": {"status": "CANCELLED", "reason": "Customer changed or cancelled the application."}})
