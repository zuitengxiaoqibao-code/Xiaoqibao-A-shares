from qibao_api.routes.quant_strategy import router


def test_quant_router_exposes_draft_validation():
    assert "/api/v1/a-shares/quant-strategy/drafts/validate" in {route.path for route in router.routes}
