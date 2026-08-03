from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
import sys
import threading

from qibao_api.contracts.bars import DailyBar


class KronosUnavailableError(RuntimeError):
    pass


class LazyKronosRuntime:
    def __init__(
        self,
        *,
        repo_path: Path | None,
        tokenizer_name: str,
        model_name: str,
        device: str | None = None,
        max_context: int = 512,
    ) -> None:
        self.repo_path = repo_path
        self.tokenizer_name = tokenizer_name
        self.model_name = model_name
        self.device = device
        self.max_context = max_context
        self._predictor = None
        self._lock = threading.RLock()

    def predict_paths(
        self,
        bars: Sequence[DailyBar],
        future_dates,
        sample_count: int,
    ) -> list[list[Decimal]]:
        predictor = self._load_predictor()
        try:
            import pandas as pd
        except Exception as error:
            raise KronosUnavailableError("kronos_dependencies_missing") from error

        frame = pd.DataFrame([
            {
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": float(bar.volume),
                "amount": float(bar.amount),
            }
            for bar in bars
        ])
        x_timestamp = pd.Series(pd.to_datetime([bar.trade_date for bar in bars]))
        y_timestamp = pd.Series(pd.to_datetime(list(future_dates)))
        paths: list[list[Decimal]] = []
        try:
            for _ in range(sample_count):
                prediction = predictor.predict(
                    df=frame,
                    x_timestamp=x_timestamp,
                    y_timestamp=y_timestamp,
                    pred_len=len(future_dates),
                    T=1.0,
                    top_p=0.9,
                    sample_count=1,
                    verbose=False,
                )
                paths.append([
                    Decimal(str(value)) for value in prediction["close"].tolist()
                ])
        except Exception as error:
            raise RuntimeError("kronos_prediction_failed") from error
        return paths

    def _load_predictor(self):
        with self._lock:
            if self._predictor is not None:
                return self._predictor
            if self.repo_path is None or not self.repo_path.is_dir():
                raise KronosUnavailableError("kronos_repo_not_configured")
            try:
                import torch  # noqa: F401
                if str(self.repo_path) not in sys.path:
                    sys.path.insert(0, str(self.repo_path))
                from model import Kronos, KronosPredictor, KronosTokenizer
            except Exception as error:
                raise KronosUnavailableError("kronos_dependencies_missing") from error
            try:
                tokenizer = KronosTokenizer.from_pretrained(self.tokenizer_name)
                model = Kronos.from_pretrained(self.model_name)
                model.eval()
                self._predictor = KronosPredictor(
                    model,
                    tokenizer,
                    device=self.device,
                    max_context=self.max_context,
                )
            except Exception as error:
                raise KronosUnavailableError("kronos_model_unavailable") from error
            return self._predictor
