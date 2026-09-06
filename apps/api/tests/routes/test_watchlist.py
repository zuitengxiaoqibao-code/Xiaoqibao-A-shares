from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.dependencies import get_watchlist_repository
from qibao_api.routes.research import router


class Repository:
    def __init__(self) -> None:
        self.symbols = ("600519",)

    def load(self):
        return type("Snapshot", (), {"symbols": self.symbols, "updated_at": None})()

    def save(self, symbols):
        self.symbols = tuple(symbols)
        return type("Snapshot", (), {"symbols": self.symbols, "updated_at": None})()


def client(repository: Repository) -> TestClient:
    application = FastAPI()
    application.include_router(router)
    application.dependency_overrides[get_watchlist_repository] = lambda: repository
    return TestClient(application)


def test_watchlist_can_be_loaded_and_replaced() -> None:
    repository = Repository()
    api = client(repository)

    loaded = api.get("/api/v1/a-shares/watchlist")
    saved = api.put("/api/v1/a-shares/watchlist", json={"symbols": ["000001", "600519"]})

    assert loaded.status_code == 200
    assert loaded.json()["symbols"] == ["600519"]
    assert saved.status_code == 200
    assert saved.json()["symbols"] == ["000001", "600519"]


def test_watchlist_returns_chinese_validation_error() -> None:
    response = client(Repository()).put(
        "/api/v1/a-shares/watchlist", json={"symbols": ["123"]}
    )

    assert response.status_code == 422
    assert "A 股代码" in response.text
