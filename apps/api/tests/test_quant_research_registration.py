from qibao_api.main import app


def test_main_registers_quant_research_route() -> None:
    paths = {route.path for route in app.routes}

    assert "/api/v1/a-shares/quant-research" in paths
