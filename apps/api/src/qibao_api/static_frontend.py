from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def install_static_frontend(app: FastAPI, web_dir: Path) -> None:
    root = web_dir.expanduser().resolve()
    index = root / "index.html"
    assets = root / "assets"
    if not index.is_file():
        return
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="web-assets")

    @app.get("/{spa_path:path}", include_in_schema=False)
    async def serve_spa(request: Request, spa_path: str):
        if request.url.path.startswith(("/api/", "/ws/")):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (root / spa_path).resolve()
        if root in candidate.parents and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
