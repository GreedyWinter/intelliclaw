from backend.app.agents.orchestrator import ProductGapOrchestrator


def get_agent_manifest() -> dict[str, object]:
    orchestrator = ProductGapOrchestrator()
    return {
        "orchestration_enabled": True,
        "adk_ready_notes": [
            "The backend orchestrator mirrors the Kaggle root-agent workflow.",
            "For ADK function declarations, avoid signatures like List[str] = None.",
            "Prefer list[str] | None for optional collection inputs in future ADK adapters.",
        ],
        **orchestrator.describe(),
    }
