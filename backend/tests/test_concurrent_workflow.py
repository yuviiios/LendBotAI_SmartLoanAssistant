from concurrent.futures import ThreadPoolExecutor
from statistics import quantiles
from threading import Barrier
from time import perf_counter
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.dependencies import get_chat_agent
from app.main import app
from app.services.applications import database, letters


def test_parallel_submissions_issue_one_document():
    req = {"pan": "ABCDE1234F", "phone": "0000000001", "address": "11 Demo Lane",
           "loan_amount": 100000, "monthly_income": 60000, "tenure_months": 24,
           "request_id": str(uuid4())}
    barrier = Barrier(8)

    def submit(_):
        with TestClient(app) as client:
            barrier.wait(timeout=15)
            return client.post("/api/apply-loan", json=req).json()["data"]

    with ThreadPoolExecutor(8) as pool:
        decisions = list(pool.map(submit, range(8)))
    assert all(d == decisions[0] for d in decisions)
    with database().connect() as conn:
        assert conn.scalar(select(func.count()).select_from(letters)) == 1


def test_two_tabs_cannot_advance_the_same_revision_twice(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    session_id = str(uuid4())
    barrier = Barrier(2)

    def send(_):
        with TestClient(app) as client:
            barrier.wait(timeout=15)
            return client.post("/api/chat", json={"session_id": session_id, "message": "Hello", "revision": 0}).status_code

    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(send, range(2))) == [200, 409]
    snapshot = TestClient(app).get(f"/api/chat/{session_id}").json()
    assert snapshot["revision"] == 1
    assert len(snapshot["history"]) == 2


def test_parallel_independent_conversations(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    get_chat_agent()
    def send(_):
        start = perf_counter()
        with TestClient(app) as client:
            response = client.post("/api/chat", json={"session_id": str(uuid4()), "message": "Hello", "revision": 0})
            assert response.status_code == 200
            assert response.json()["revision"] == 1
        return (perf_counter() - start) * 1000

    with ThreadPoolExecutor(8) as pool:
        samples = list(pool.map(send, range(32)))
    print(f"32 local greeting turns, concurrency 8, p95 {quantiles(samples, n=100, method='inclusive')[94]:.0f} ms")
