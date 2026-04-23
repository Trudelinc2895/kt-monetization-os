from api.config import settings
from api.services import private_orchestrator_service


def test_get_allowed_agent_keys_filters_unknowns_and_duplicates(monkeypatch):
    monkeypatch.setattr(
        settings,
        "PRIVATE_ORCHESTRATOR_ALLOWED_AGENTS_RAW",
        "ghost_agency,unknown,operator,ghost_agency",
    )

    assert private_orchestrator_service.get_allowed_agent_keys() == ["ghost_agency", "operator"]


def test_get_allowed_agent_keys_falls_back_to_default_catalog_when_config_invalid(monkeypatch):
    monkeypatch.setattr(settings, "PRIVATE_ORCHESTRATOR_ALLOWED_AGENTS_RAW", "unknown_only")

    assert private_orchestrator_service.get_allowed_agent_keys() == [
        "operator",
        "ghost_agency",
        "decision_engine",
    ]
