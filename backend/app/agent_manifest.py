from backend.app.agents.orchestrator import ProductGapOrchestrator


def get_agent_manifest() -> dict[str, object]:
    orchestrator = ProductGapOrchestrator()
    return {
        "orchestration_enabled": True,
        "evaluation_loop_enabled": True,
        "human_review_enabled": True,
        "adk_ready_notes": [
            "The backend orchestrator mirrors the Kaggle root-agent workflow.",
            "For ADK function declarations, avoid signatures like List[str] = None.",
            "Prefer list[str] | None for optional collection inputs in future ADK adapters.",
            "Specialist evaluators now score sentence structure and coverage before aggregate evaluation.",
            "Each PDF now produces one canonical extraction CSV per attempt for evaluator review.",
            "Sentence rewriting and aggregate extraction evaluation can call Gemini when GOOGLE_API_KEY is configured.",
            "The extraction stage now pauses for human review before gap analysis continues.",
        ],
        **orchestrator.describe(),
    }
