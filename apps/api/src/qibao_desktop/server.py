import socket
import threading
import time

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

    def launch(self) -> None:
        if self._thread.ident is not None:
            return
        self._thread.start()

    def wait_until_ready(self) -> None:
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            if not self._thread.is_alive():
                raise RuntimeError("local API exited during startup")
            if self._server.started:
                # Uvicorn flips `started` only after lifespan has completed and
                # the pre-bound loopback socket is serving.  A second HTTP
                # request here adds avoidable cold-start latency and can be
                # delayed independently by Windows' first localhost request.
                return
            time.sleep(0.05)
        self.stop()
        raise TimeoutError("local API startup timed out")

    def start(self) -> None:
        self.launch()
        self.wait_until_ready()

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
