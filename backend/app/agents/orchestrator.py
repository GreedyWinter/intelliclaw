from backend.app.agents.base import AnalysisContext
from backend.app.agents.sub_agents import (
    ComparisonAgent,
    DocumentListingAgent,
    NormalizationAgent,
    PdfExtractionAgent,
    ReportingAgent,
)


class ProductGapOrchestrator:
    def __init__(self) -> None:
        self.sub_agents = [
            DocumentListingAgent(),
            PdfExtractionAgent(),
            NormalizationAgent(),
            ComparisonAgent(),
            ReportingAgent(),
        ]

    def run(self, context: AnalysisContext) -> AnalysisContext:
        for sub_agent in self.sub_agents:
            step_result = sub_agent.run(context)
            context.step_results.append(step_result)
        return context

    def describe(self) -> dict[str, object]:
        return {
            "root_agent": "product_gap_root_orchestrator",
            "sub_agents": [sub_agent.name for sub_agent in self.sub_agents],
            "intent": (
                "Coordinate document listing, extraction, normalization, comparison, "
                "and reporting for product gap analysis."
            ),
        }
