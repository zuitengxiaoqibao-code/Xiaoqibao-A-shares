from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from qibao_api.static_frontend import install_static_frontend


def make_app(web_dir: Path) -> TestClient:
    app = FastAPI()

    @app.get("/api/example")
    def example() -> dict[str, bool]:
        return {"ok": True}

    install_static_frontend(app, web_dir)
    return TestClient(app)


def test_static_frontend_serves_assets_and_spa_bookmarks(tmp_path: Path) -> None:
    web = tmp_path / "web"
    assets = web / "assets"
    assets.mkdir(parents=True)
    (web / "index.html").write_text("<main>desktop</main>", encoding="utf-8")
    (assets / "app.js").write_text("window.desktop=true", encoding="utf-8")
    client = make_app(web)

    assert client.get("/").text == "<main>desktop</main>"
    assert client.get("/a-shares").text == "<main>desktop</main>"
    assert client.get("/assets/app.js").text == "window.desktop=true"
    assert client.get("/api/example").json() == {"ok": True}


def test_static_frontend_never_turns_unknown_api_into_html(tmp_path: Path) -> None:
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text("<main>desktop</main>", encoding="utf-8")
    response = make_app(web).get("/api/missing")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


def test_missing_web_build_leaves_api_only_app(tmp_path: Path) -> None:
    app = FastAPI()
    install_static_frontend(app, tmp_path / "missing")

    assert TestClient(app).get("/").status_code == 404
