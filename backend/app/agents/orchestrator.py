from fastapi import HTTPException

from backend.app.agents.base import AnalysisContext
from backend.app.agents.sub_agents import (
    ComparisonAgent,
    CanonicalExtractionAgent,
    CoverageEvaluatorAgent,
    DocumentListingAgent,
    ExtractionEvaluatorAgent,
    GrammarEvaluatorAgent,
    HumanReviewPreparationAgent,
    NormalizationAgent,
    ReportingAgent,
    SentenceRewriteAgent,
    TableExtractionAgent,
    TextExtractionAgent,
)


class ProductGapOrchestrator:
    def __init__(self) -> None:
        self.document_listing_agent = DocumentListingAgent()
        self.raw_extractor_agents = [TableExtractionAgent(), TextExtractionAgent()]
        self.sentence_structurer_agents = [SentenceRewriteAgent()]
        self.canonical_extraction_agent = CanonicalExtractionAgent()
        self.specialist_evaluators = [GrammarEvaluatorAgent(), CoverageEvaluatorAgent()]
        self.extraction_evaluator_agent = ExtractionEvaluatorAgent()
        self.human_review_preparation_agent = HumanReviewPreparationAgent()
        self.post_review_agents = [
            NormalizationAgent(),
            ComparisonAgent(),
            ReportingAgent(),
        ]

    def run_until_human_review(self, context: AnalysisContext) -> AnalysisContext:
        context.log_event(
            source="product_gap_root_orchestrator",
            target=self.document_listing_agent.name,
            event_type="dispatch",
            message="Starting document discovery for the extraction pipeline.",
            payload={"document_count": len(context.documents)},
        )
        context.step_results.append(self.document_listing_agent.run(context))
        if not context.listed_documents:
            context.failure_details = {
                "reason": "no_pdf_documents",
                "message": "No PDF documents are available for extraction.",
            }
            raise HTTPException(status_code=400, detail="No PDF documents are available for extraction.")

        for document in context.listed_documents:
            context.log_event(
                source="product_gap_root_orchestrator",
                target=None,
                event_type="document_started",
                message=f"Starting extraction workflow for {document['filename']}.",
                document_id=document["id"],
                payload={"filename": document["filename"]},
            )
            accepted = False
            for attempt in range(1, context.max_extraction_attempts + 1):
                context.log_event(
                    source="product_gap_root_orchestrator",
                    target=None,
                    event_type="attempt_started",
                    message=(
                        f"Attempt {attempt} of {context.max_extraction_attempts} started for "
                        f"{document['filename']}."
                    ),
                    document_id=document["id"],
                    attempt=attempt,
                )
                raw_candidates_before = len(context.raw_candidates.get(document["id"], []))
                for extractor in self.raw_extractor_agents:
                    context.log_event(
                        source="product_gap_root_orchestrator",
                        target=extractor.name,
                        event_type="dispatch",
                        message=f"Dispatching raw extraction to {extractor.name}.",
                        document_id=document["id"],
                        attempt=attempt,
                    )
                    context.step_results.append(extractor.run(context, document=document, attempt=attempt))
                new_raw_candidates = context.raw_candidates.get(document["id"], [])[raw_candidates_before:]

                for raw_candidate in new_raw_candidates:
                    for structurer in self.sentence_structurer_agents:
                        context.log_event(
                            source="product_gap_root_orchestrator",
                            target=structurer.name,
                            event_type="dispatch",
                            message=(
                                f"Dispatching sentence structuring for {raw_candidate.strategy} output."
                            ),
                            document_id=document["id"],
                            attempt=attempt,
                            payload={"source_candidate": raw_candidate.strategy},
                        )
                        context.step_results.append(
                            structurer.run(
                                context,
                                document=document,
                                source_candidate=raw_candidate,
                                attempt=attempt,
                            )
                        )

                context.log_event(
                    source="product_gap_root_orchestrator",
                    target=self.canonical_extraction_agent.name,
                    event_type="dispatch",
                    message="Building one canonical extraction CSV for evaluator review.",
                    document_id=document["id"],
                    attempt=attempt,
                )
                context.step_results.append(
                    self.canonical_extraction_agent.run(
                        context,
                        document=document,
                        attempt=attempt,
                    )
                )

                canonical_candidates = [
                    candidate
                    for candidate in context.canonical_candidates.get(document["id"], [])
                    if f"attempt_{attempt}" in candidate.csv_path.stem
                ]
                for candidate in canonical_candidates:
                    for evaluator in self.specialist_evaluators:
                        context.log_event(
                            source="product_gap_root_orchestrator",
                            target=evaluator.name,
                            event_type="dispatch",
                            message=f"Dispatching specialist evaluation to {evaluator.name}.",
                            document_id=document["id"],
                            attempt=attempt,
                            payload={"candidate": str(candidate.csv_path)},
                        )
                        context.step_results.append(
                            evaluator.run(
                                context,
                                candidate=candidate,
                                document=document,
                                attempt=attempt,
                            )
                        )

                evaluation_result = self.extraction_evaluator_agent.run(
                    context,
                    document=document,
                    attempt=attempt,
                )
                context.step_results.append(evaluation_result)
                if evaluation_result.details.get("accepted"):
                    context.log_event(
                        source="product_gap_root_orchestrator",
                        target=self.human_review_preparation_agent.name,
                        event_type="document_approved",
                        message=(
                            f"Evaluator approved extraction for {document['filename']} and will "
                            "prepare it for human review."
                        ),
                        document_id=document["id"],
                        attempt=attempt,
                        payload=evaluation_result.details,
                    )
                    accepted = True
                    break
                context.log_event(
                    source="product_gap_root_orchestrator",
                    target=None,
                    event_type="attempt_rejected",
                    message=(
                        f"Attempt {attempt} was not approved for {document['filename']}."
                    ),
                    document_id=document["id"],
                    attempt=attempt,
                    payload=evaluation_result.details,
                )

            if not accepted:
                decision = context.evaluation_decisions.get(document["id"])
                context.failure_details = {
                    "reason": "extraction_not_approved",
                    "document_id": document["id"],
                    "filename": document["filename"],
                    "current_iteration": context.current_iteration,
                    "max_attempts": context.max_extraction_attempts,
                    "latest_decision": {
                        "accepted": decision.accepted,
                        "chosen_strategy": decision.chosen_strategy,
                        "chosen_csv_path": str(decision.chosen_csv_path) if decision and decision.chosen_csv_path else None,
                        "score": decision.score if decision else 0.0,
                        "retry_requested": decision.retry_requested if decision else False,
                        "feedback": decision.feedback if decision else [],
                    }
                    if decision
                    else None,
                    "feedback_history": context.agent_feedback_history.get(str(document["id"]), []),
                }
                context.log_event(
                    source="product_gap_root_orchestrator",
                    target=None,
                    event_type="document_failed",
                    message=(
                        f"Extraction failed before human review because the evaluator never "
                        f"approved {document['filename']}."
                    ),
                    document_id=document["id"],
                    payload=context.failure_details,
                )
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Evaluator agent could not approve extraction for "
                        f"{document['filename']}. See the run diagnostics for feedback history "
                        "and candidate scores."
                    ),
                )

        context.log_event(
            source="product_gap_root_orchestrator",
            target=self.human_review_preparation_agent.name,
            event_type="dispatch",
            message="All documents were evaluator-approved. Preparing human review artifacts.",
        )
        context.step_results.append(self.human_review_preparation_agent.run(context))
        return context

    def resume_after_human_approval(self, context: AnalysisContext) -> AnalysisContext:
        if not context.review_artifacts:
            raise HTTPException(status_code=400, detail="No human-reviewed extraction artifacts are available.")

        for agent in self.post_review_agents:
            context.log_event(
                source="product_gap_root_orchestrator",
                target=agent.name,
                event_type="dispatch",
                message=f"Dispatching post-review stage to {agent.name}.",
            )
            context.step_results.append(agent.run(context))
        return context

    def describe(self) -> dict[str, object]:
        return {
            "root_agent": "product_gap_root_orchestrator",
            "sub_agents": [
                self.document_listing_agent.name,
                *[agent.name for agent in self.raw_extractor_agents],
                *[agent.name for agent in self.sentence_structurer_agents],
                self.canonical_extraction_agent.name,
                *[agent.name for agent in self.specialist_evaluators],
                self.extraction_evaluator_agent.name,
                self.human_review_preparation_agent.name,
                *[agent.name for agent in self.post_review_agents],
            ],
            "raw_extractors": [agent.name for agent in self.raw_extractor_agents],
            "sentence_structurers": [agent.name for agent in self.sentence_structurer_agents],
            "canonical_extraction_agent": self.canonical_extraction_agent.name,
            "specialist_evaluators": [agent.name for agent in self.specialist_evaluators],
            "aggregate_evaluator": self.extraction_evaluator_agent.name,
            "gemini_backed_agents": [
                "sentence_rewrite_agent",
                "extraction_evaluator_agent",
            ],
            "human_review_agent": self.human_review_preparation_agent.name,
            "intent": (
                "Break PDF extraction into raw extraction, sentence structuring, a single "
                "canonical per-document CSV, specialist evaluation, aggregate evaluation, "
                "human review, and only then continue to gap analysis."
            ),
        }
