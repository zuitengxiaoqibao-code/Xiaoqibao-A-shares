from qibao_api.routes.data_import import router


def test_data_import_router_exposes_expected_paths() -> None:
    paths = {route.path for route in router.routes}
    assert "/api/data-import/inspect" in paths
    assert "/api/data-import/ingest" in paths
    assert "/api/data-import/tasks/{task_id}" in paths
    assert "/api/data-sources/health" in paths
