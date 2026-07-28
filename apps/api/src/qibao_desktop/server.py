import socket
import threading
import time
from urllib.error import URLError
from urllib.request import urlopen

import uvicorn


class LocalApiServer:
    def __init__(
        self,
        *,
        app,
        port: int = 0,
        startup_timeout: float = 30,
        log_level: str = "warning",
    ) -> None:
        self.startup_timeout = startup_timeout
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(("127.0.0.1", port))
        self._socket.listen(128)
        self.port = int(self._socket.getsockname()[1])
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=self.port,
            log_level=log_level,
            access_log=False,
            log_config=None,
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(
            target=self._run,
            name="qibao-local-api",
            daemon=False,
        )

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def is_alive(self) -> bool:
        return self._thread.is_alive()

    def _run(self) -> None:
        self._server.run(sockets=[self._socket])

    def start(self) -> None:
        self._thread.start()
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            if not self._thread.is_alive():
                raise RuntimeError("local API exited during startup")
            try:
                with urlopen(f"{self.url}/health", timeout=0.5) as response:
                    if response.status == 200:
                        return
            except (OSError, URLError):
                time.sleep(0.05)
        self.stop()
        raise TimeoutError("local API health check timed out")

    def stop(self) -> None:
        self._server.should_exit = True
        if self._thread.ident is not None:
            self._thread.join(timeout=10)
        try:
            self._socket.close()
        except OSError:
            pass

    def wait(self) -> None:
        self._thread.join()
