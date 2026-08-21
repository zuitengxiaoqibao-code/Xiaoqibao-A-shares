from qibao_api.routes.monitor_center import router


def test_monitor_routes_are_exposed():
    paths = {route.path for route in router.routes}
    assert "/api/v1/monitor-center/rules" in paths
    assert "/api/v1/monitor-center/alerts" in paths
