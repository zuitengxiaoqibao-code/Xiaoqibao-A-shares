from pathlib import Path

import pytest

from qibao_api.a_shares.kronos_runtime import LazyKronosRuntime, KronosUnavailableError


def test_lazy_runtime_reports_missing_repository_before_importing_optional_dependencies(tmp_path: Path) -> None:
    runtime = LazyKronosRuntime(
        repo_path=tmp_path / "missing-kronos",
        tokenizer_name="NeoQuasar/Kronos-Tokenizer-2k",
        model_name="NeoQuasar/Kronos-mini",
    )

    with pytest.raises(KronosUnavailableError, match="kronos_repo_not_configured"):
        runtime.predict_paths([], [], 1)
