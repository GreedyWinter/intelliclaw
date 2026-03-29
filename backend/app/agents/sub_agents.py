from pathlib import Path
from typing import Any

import pandas as pd
import pdfplumber

from backend.app.agents.base import (
    AnalysisContext,
    AgentStepResult,
    BaseSubAgent,
    EvaluationDecision,
    ExtractionCandidate,
    ReviewArtifact,
)
from backend.app.services.gemini_service import GeminiService, GeminiServiceError


_GEMINI_SERVICE = GeminiService()


def _document_key(document_id: int) -> str:
    return str(document_id)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> pd.DataFrame:
    dataframe = pd.DataFrame(rows or [{"feature": ""}])
    dataframe.to_csv(path, index=False)
    return dataframe


def _make_human_sentence(feature: str, feedback: list[str]) -> str:
    sentence = " ".join(feature.replace("|", " ").split())
    if not sentence:
        return ""

    lowered = sentence.lower()
    if "use verbs" in " ".join(feedback).lower():
        if not any(
            verb in lowered
            for verb in ["supports", "includes", "provides", "offers", "allows", "detects", "identifies"]
        ):
            sentence = f"The product provides {sentence}"

    if not sentence[0].isupper():
        sentence = sentence[0].upper() + sentence[1:]

    if not any(lowered.startswith(prefix) for prefix in ["the product", "this product", "it "]):
        sentence = f"The product provides {sentence[0].lower() + sentence[1:]}"

    if not sentence.endswith((".", "!", "?")):
        sentence = f"{sentence}."

    return sentence


def _build_sentence_metrics(dataframe: pd.DataFrame) -> dict[str, float]:
    feature_series = dataframe.get("feature", pd.Series(dtype="string")).fillna("").astype(str)
    row_count = float(len(feature_series.index))
    non_empty = feature_series[feature_series.str.strip() != ""]
    sentence_like = non_empty[
        non_empty.str.contains(r"^[A-Z].+[.!?]$", regex=True)
    ]
    human_ratio = float(len(sentence_like.index) / len(non_empty.index)) if len(non_empty.index) else 0.0
    avg_words = (
        float(non_empty.str.split().map(len).mean())
        if len(non_empty.index)
        else 0.0
    )
    unique_ratio = (
        float(non_empty.nunique(dropna=True) / len(non_empty.index))
        if len(non_empty.index)
        else 0.0
    )
    score = (
        min(row_count / 25.0, 1.0) * 0.25
        + human_ratio * 0.45
        + min(avg_words / 12.0, 1.0) * 0.20
        + unique_ratio * 0.10
    )

    return {
        "row_count": row_count,
        "human_sentence_ratio": human_ratio,
        "average_words": avg_words,
        "unique_ratio": unique_ratio,
        "score": min(score, 1.0),
    }


def _candidate_for_attempt(candidate: ExtractionCandidate, attempt: int) -> bool:
    return f"attempt_{attempt}" in candidate.csv_path.stem


def _chunked(items: list[Any], size: int) -> list[list[Any]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def _build_sentence_rewrite_prompt(
    *,
    filename: str,
    feedback: list[str],
    features: list[str],
) -> str:
    feedback_text = "\n".join(f"- {item}" for item in feedback) if feedback else "- None"
    feature_lines = "\n".join(f"{index + 1}. {feature}" for index, feature in enumerate(features))
    return (
        f"Document: {filename}\n"
        "Task: rewrite the extracted PDF lines into concise, human-readable product capability sentences.\n"
        "Requirements:\n"
        "- Keep each output as one standalone sentence.\n"
        "- Use the wording a human analyst would naturally write.\n"
        "- Preserve factual meaning and avoid inventing details.\n"
        "- Start each sentence with 'The product' when possible.\n"
        "- Return one sentence for each input line in the same order.\n"
        f"Feedback to address from prior iterations:\n{feedback_text}\n"
        "Input lines:\n"
        f"{feature_lines}\n"
        "Return JSON with this exact shape:\n"
        '{"sentences":[{"source_index":1,"sentence":"..."}]}'
    )


def _build_extraction_evaluation_prompt(
    *,
    filename: str,
    prompt: str,
    metrics: dict[str, float],
    feedback_history: list[str],
    preview_rows: list[str],
) -> str:
    feedback_text = "\n".join(f"- {item}" for item in feedback_history) if feedback_history else "- None"
    preview_text = "\n".join(f"- {row}" for row in preview_rows) if preview_rows else "- None"
    metrics_text = "\n".join(f"- {key}: {value}" for key, value in metrics.items())
    return (
        f"Document: {filename}\n"
        f"Project goal: {prompt}\n"
        "You are evaluating whether a single canonical extraction CSV is ready for human review.\n"
        "Evaluate whether the extraction is coherent, representative of the PDF, and usable for downstream gap analysis.\n"
        "Do not reject just because one extractor source contributed more rows than another if the content is still useful.\n"
        "Prior evaluator feedback:\n"
        f"{feedback_text}\n"
        "Extraction metrics:\n"
        f"{metrics_text}\n"
        "Preview rows:\n"
        f"{preview_text}\n"
        "Return JSON with this exact shape:\n"
        '{"accepted":true,"score":0.0,"feedback":["..."],"summary":"..."}'
    )


class DocumentListingAgent(BaseSubAgent):
    name = "document_listing_agent"
    role = "discovery"

    def run(self, context: AnalysisContext, **kwargs: Any) -> AgentStepResult:
        context.listed_documents = [
            document
            for document in context.documents
            if str(document.get("file_path", "")).lower().endswith(".pdf")
        ]
        context.log_event(
            source=self.name,
            target="product_gap_root_orchestrator",
            event_type="result",
            message=f"Document discovery found {len(context.listed_documents)} PDF files.",
            payload={
                "document_ids": [document["id"] for document in context.listed_documents],
                "filenames": [document["filename"] for document in context.listed_documents],
            },
        )
        return AgentStepResult(
            name=self.name,
            status="completed" if context.listed_documents else "failed",
            details={"document_count": len(context.listed_documents)},
        )


class TableExtractionAgent(BaseSubAgent):
    name = "table_extraction_agent"
    role = "raw_extractor"

    def run(
        self,
        context: AnalysisContext,
        *,
        document: dict[str, Any],
        attempt: int,
    ) -> AgentStepResult:
        source_path = Path(document["file_path"])
        rows: list[dict[str, Any]] = []

        with pdfplumber.open(source_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                for table in page.extract_tables() or []:
                    for row in table or []:
                        cleaned = [str(cell).strip() for cell in row if cell and str(cell).strip()]
                        if not cleaned:
                            continue
                        rows.append(
                            {
                                "page": page_number,
                                "feature": " | ".join(cleaned[:8])[:500],
                                "source_kind": "table",
                            }
                        )

        output_path = context.workspace_dir / f"document_{document['id']}_{self.name}_attempt_{attempt}.csv"
        dataframe = _write_csv(output_path, rows)
        candidate = ExtractionCandidate(
            document_id=document["id"],
            strategy=self.name,
            source_kind="raw_table",
            csv_path=output_path,
            row_count=int(len(dataframe.index)),
        )
        context.raw_candidates.setdefault(document["id"], []).append(candidate)
        context.log_event(
            source=self.name,
            target="sentence_rewrite_agent",
            event_type="candidate_created",
            message=f"Created raw table extraction candidate with {candidate.row_count} rows.",
            document_id=document["id"],
            attempt=attempt,
            payload={"csv_path": str(output_path), "row_count": candidate.row_count},
        )
        return AgentStepResult(
            name=self.name,
            status="completed" if candidate.row_count else "warning",
            document_id=document["id"],
            attempt=attempt,
            details={"csv_path": str(output_path), "row_count": candidate.row_count},
        )


class TextExtractionAgent(BaseSubAgent):
    name = "text_extraction_agent"
    role = "raw_extractor"

    def run(
        self,
        context: AnalysisContext,
        *,
        document: dict[str, Any],
        attempt: int,
    ) -> AgentStepResult:
        source_path = Path(document["file_path"])
        rows: list[dict[str, Any]] = []

        with pdfplumber.open(source_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = (page.extract_text() or "").strip()
                if not text:
                    continue
                for line in text.splitlines():
                    cleaned = " ".join(line.split())
                    if len(cleaned) < 4:
                        continue
                    rows.append(
                        {
                            "page": page_number,
                            "feature": cleaned[:500],
                            "source_kind": "text",
                        }
                    )

        output_path = context.workspace_dir / f"document_{document['id']}_{self.name}_attempt_{attempt}.csv"
        dataframe = _write_csv(output_path, rows)
        candidate = ExtractionCandidate(
            document_id=document["id"],
            strategy=self.name,
            source_kind="raw_text",
            csv_path=output_path,
            row_count=int(len(dataframe.index)),
        )
        context.raw_candidates.setdefault(document["id"], []).append(candidate)
        context.log_event(
            source=self.name,
            target="sentence_rewrite_agent",
            event_type="candidate_created",
            message=f"Created raw text extraction candidate with {candidate.row_count} rows.",
            document_id=document["id"],
            attempt=attempt,
            payload={"csv_path": str(output_path), "row_count": candidate.row_count},
        )
        return AgentStepResult(
            name=self.name,
            status="completed" if candidate.row_count else "warning",
            document_id=document["id"],
            attempt=attempt,
            details={"csv_path": str(output_path), "row_count": candidate.row_count},
        )


class SentenceRewriteAgent(BaseSubAgent):
    name = "sentence_rewrite_agent"
    role = "sentence_structurer"

    def run(
        self,
        context: AnalysisContext,
        *,
        document: dict[str, Any],
        source_candidate: ExtractionCandidate,
        attempt: int,
    ) -> AgentStepResult:
        feedback = [
            *context.agent_feedback_history.get(_document_key(document["id"]), []),
            *context.human_feedback_history.get(_document_key(document["id"]), []),
        ]
        dataframe = pd.read_csv(source_candidate.csv_path)
        rewritten_rows = []
        provider = "heuristic"
        features = [
            str(row.get("feature", "")).strip()
            for _, row in dataframe.iterrows()
            if str(row.get("feature", "")).strip()
        ]

        if _GEMINI_SERVICE.enabled and features:
            gemini_rows: list[dict[str, Any]] = []
            try:
                for chunk in _chunked(features, 40):
                    result = _GEMINI_SERVICE.generate_json(
                        system_instruction=(
                            "You rewrite extracted product-document fragments into clean factual "
                            "sentences. Always return strict JSON."
                        ),
                        prompt=_build_sentence_rewrite_prompt(
                            filename=document["filename"],
                            feedback=feedback,
                            features=chunk,
                        ),
                    )
                    for item in result.payload.get("sentences", []):
                        sentence = str(item.get("sentence", "")).strip()
                        if not sentence:
                            continue
                        gemini_rows.append(
                            {
                                "feature": sentence,
                                "source_strategy": source_candidate.strategy,
                                "source_kind": source_candidate.source_kind,
                            }
                        )
                rewritten_rows = gemini_rows
                provider = "gemini"
                context.log_event(
                    source=self.name,
                    target="gemini",
                    event_type="llm_generation",
                    message=(
                        f"Gemini rewrote {len(rewritten_rows)} rows for {source_candidate.strategy}."
                    ),
                    document_id=document["id"],
                    attempt=attempt,
                    payload={"provider": "gemini", "model": _GEMINI_SERVICE.model},
                )
            except GeminiServiceError as exc:
                context.log_event(
                    source=self.name,
                    target=None,
                    event_type="llm_fallback",
                    message="Gemini sentence rewriting failed, falling back to heuristic rewriting.",
                    document_id=document["id"],
                    attempt=attempt,
                    payload={"error": str(exc)},
                )

        if not rewritten_rows:
            for _, row in dataframe.iterrows():
                feature = str(row.get("feature", "")).strip()
                sentence = _make_human_sentence(feature, feedback)
                if not sentence:
                    continue
                rewritten_rows.append(
                    {
                        "feature": sentence,
                        "source_strategy": source_candidate.strategy,
                        "source_kind": source_candidate.source_kind,
                    }
                )

        output_path = (
            context.workspace_dir
            / f"document_{document['id']}_{self.name}_{source_candidate.strategy}_attempt_{attempt}.csv"
        )
        structured_df = _write_csv(output_path, rewritten_rows)
        metrics = _build_sentence_metrics(structured_df)
        candidate = ExtractionCandidate(
            document_id=document["id"],
            strategy=f"{self.name}:{source_candidate.strategy}",
            source_kind="sentence_csv",
            csv_path=output_path,
            row_count=int(metrics["row_count"]),
            metrics=metrics,
        )
        context.sentence_candidates.setdefault(document["id"], []).append(candidate)
        context.log_event(
            source=self.name,
            target="grammar_evaluator_agent",
            event_type="candidate_created",
            message=(
                f"Rewrote {candidate.row_count} rows into sentence-structured CSV from "
                f"{source_candidate.strategy}."
            ),
            document_id=document["id"],
            attempt=attempt,
            payload={
                "csv_path": str(output_path),
                "metrics": metrics,
                "feedback_used": feedback,
            },
        )
        return AgentStepResult(
            name=self.name,
            status="completed" if candidate.row_count else "warning",
            document_id=document["id"],
            attempt=attempt,
            details={
                "csv_path": str(output_path),
                "metrics": metrics,
                "source_strategy": source_candidate.strategy,
                "feedback_used": feedback,
                "provider": provider,
            },
        )


class CanonicalExtractionAgent(BaseSubAgent):
    name = "canonical_extraction_agent"
    role = "package_builder"

    def run(
        self,
        context: AnalysisContext,
        *,
        document: dict[str, Any],
        attempt: int,
    ) -> AgentStepResult:
        sentence_candidates = [
            candidate
            for candidate in context.sentence_candidates.get(document["id"], [])
            if _candidate_for_attempt(candidate, attempt)
        ]
        merged_rows: list[dict[str, Any]] = []

        for candidate in sentence_candidates:
            dataframe = pd.read_csv(candidate.csv_path).fillna("")
            source_label = candidate.strategy.split(":", maxsplit=1)[-1]
            for _, row in dataframe.iterrows():
                feature = str(row.get("feature", "")).strip()
                if not feature:
                    continue
                merged_rows.append(
                    {
                        "feature": feature,
                        "source_strategy": source_label,
                        "source_kind": row.get("source_kind", candidate.source_kind),
                    }
                )

        canonical_df = pd.DataFrame(merged_rows)
        if not canonical_df.empty:
            canonical_df = canonical_df.drop_duplicates(subset=["feature"]).reset_index(drop=True)

        output_path = context.workspace_dir / f"document_{document['id']}_canonical_extraction_attempt_{attempt}.csv"
        written_df = _write_csv(output_path, canonical_df.to_dict(orient="records"))
        metrics = _build_sentence_metrics(written_df)
        metrics["source_count"] = float(
            written_df.get("source_strategy", pd.Series(dtype="string")).fillna("").astype(str).nunique()
            if "source_strategy" in written_df.columns
            else 0.0
        )
        candidate = ExtractionCandidate(
            document_id=document["id"],
            strategy=self.name,
            source_kind="canonical_sentence_csv",
            csv_path=output_path,
            row_count=int(metrics["row_count"]),
            metrics=metrics,
        )
        context.canonical_candidates.setdefault(document["id"], []).append(candidate)
        context.log_event(
            source=self.name,
            target="grammar_evaluator_agent",
            event_type="candidate_created",
            message=(
                f"Built canonical extraction CSV for {document['filename']} with "
                f"{candidate.row_count} consolidated rows."
            ),
            document_id=document["id"],
            attempt=attempt,
            payload={
                "csv_path": str(output_path),
                "source_count": metrics["source_count"],
                "source_candidates": [item.strategy for item in sentence_candidates],
            },
        )
        return AgentStepResult(
            name=self.name,
            status="completed" if candidate.row_count else "warning",
            document_id=document["id"],
            attempt=attempt,
            details={
                "csv_path": str(output_path),
                "row_count": candidate.row_count,
                "source_count": int(metrics["source_count"]),
                "source_candidates": [item.strategy for item in sentence_candidates],
            },
        )


class GrammarEvaluatorAgent(BaseSubAgent):
    name = "grammar_evaluator_agent"
    role = "specialist_evaluator"

    def run(
        self,
        context: AnalysisContext,
        *,
        candidate: ExtractionCandidate,
        document: dict[str, Any],
        attempt: int,
    ) -> AgentStepResult:
        dataframe = pd.read_csv(candidate.csv_path)
        metrics = _build_sentence_metrics(dataframe)
        feedback: list[str] = []
        if metrics["human_sentence_ratio"] < 0.8:
            feedback.append("Use grammatically complete sentences with capitalization and punctuation.")
        if metrics["average_words"] < 6:
            feedback.append("Use verbs and fuller sentence phrasing that humans would naturally write.")
        candidate.metrics.update(metrics)
        candidate.feedback.extend(feedback)
        context.log_event(
            source=self.name,
            target="extraction_evaluator_agent",
            event_type="evaluation_result",
            message=(
                "Grammar evaluation completed."
                if not feedback
                else "Grammar evaluation requested improvements."
            ),
            document_id=document["id"],
            attempt=attempt,
            payload={"metrics": metrics, "feedback": feedback, "csv_path": str(candidate.csv_path)},
        )
        return AgentStepResult(
            name=self.name,
            status="completed",
            document_id=document["id"],
            attempt=attempt,
            details={"metrics": metrics, "feedback": feedback, "csv_path": str(candidate.csv_path)},
        )


class CoverageEvaluatorAgent(BaseSubAgent):
    name = "coverage_evaluator_agent"
    role = "specialist_evaluator"

    def run(
        self,
        context: AnalysisContext,
        *,
        candidate: ExtractionCandidate,
        document: dict[str, Any],
        attempt: int,
    ) -> AgentStepResult:
        dataframe = pd.read_csv(candidate.csv_path)
        row_count = len(dataframe.index)
        feedback: list[str] = []
        if row_count < 5:
            feedback.append("Capture more content from the PDF; the extraction is too sparse.")
        if (
            "source_strategy" in dataframe.columns
            and dataframe["source_strategy"].nunique() == 1
            and row_count < 20
        ):
            feedback.append(
                "Improve source coverage by bringing in another extraction strategy or more rows."
            )

        candidate.metrics["coverage_row_count"] = float(row_count)
        candidate.metrics["source_count"] = float(
            dataframe["source_strategy"].nunique() if "source_strategy" in dataframe.columns else 0
        )
        candidate.feedback.extend(feedback)
        context.log_event(
            source=self.name,
            target="extraction_evaluator_agent",
            event_type="evaluation_result",
            message=(
                "Coverage evaluation completed."
                if not feedback
                else "Coverage evaluation requested improvements."
            ),
            document_id=document["id"],
            attempt=attempt,
            payload={"row_count": row_count, "feedback": feedback, "csv_path": str(candidate.csv_path)},
        )
        return AgentStepResult(
            name=self.name,
            status="completed",
            document_id=document["id"],
            attempt=attempt,
            details={
                "row_count": row_count,
                "source_count": int(candidate.metrics["source_count"]),
                "feedback": feedback,
                "csv_path": str(candidate.csv_path),
            },
        )


class ExtractionEvaluatorAgent(BaseSubAgent):
    name = "extraction_evaluator_agent"
    role = "aggregate_evaluator"

    def run(
        self,
        context: AnalysisContext,
        *,
        document: dict[str, Any],
        attempt: int,
    ) -> AgentStepResult:
        document_key = _document_key(document["id"])
        candidates = [
            candidate
            for candidate in context.canonical_candidates.get(document["id"], [])
            if _candidate_for_attempt(candidate, attempt)
        ]
        if not candidates:
            decision = EvaluationDecision(
                document_id=document["id"],
                accepted=False,
                chosen_strategy=None,
                chosen_csv_path=None,
                score=0.0,
                retry_requested=attempt < context.max_extraction_attempts,
                feedback=["No canonical extraction CSV candidate was produced."],
            )
        else:
            chosen = max(candidates, key=lambda item: item.metrics.get("score", 0.0))
            score = chosen.metrics.get("score", 0.0)
            feedback = list(dict.fromkeys(chosen.feedback))
            accepted = score >= 0.62 and chosen.row_count >= 5 and not feedback
            summary = ""
            used_gemini = False

            if _GEMINI_SERVICE.enabled:
                try:
                    canonical_df = pd.read_csv(chosen.csv_path).fillna("")
                    preview_rows = canonical_df.head(20)["feature"].astype(str).tolist()
                    gemini_result = _GEMINI_SERVICE.generate_json(
                        system_instruction=(
                            "You evaluate whether a canonical product-document extraction is "
                            "ready for human review. Return strict JSON only."
                        ),
                        prompt=_build_extraction_evaluation_prompt(
                            filename=document["filename"],
                            prompt=context.prompt,
                            metrics=chosen.metrics,
                            feedback_history=context.agent_feedback_history.get(document_key, []),
                            preview_rows=preview_rows,
                        ),
                    )
                    accepted = bool(gemini_result.payload.get("accepted", accepted))
                    score = float(gemini_result.payload.get("score", score))
                    summary = str(gemini_result.payload.get("summary", "")).strip()
                    used_gemini = True
                    llm_feedback = [
                        str(item).strip()
                        for item in gemini_result.payload.get("feedback", [])
                        if str(item).strip()
                    ]
                    feedback = list(dict.fromkeys([*feedback, *llm_feedback]))
                    context.log_event(
                        source=self.name,
                        target="product_gap_root_orchestrator",
                        event_type="llm_evaluation",
                        message="Gemini completed the aggregate extraction evaluation.",
                        document_id=document["id"],
                        attempt=attempt,
                        payload={
                            "provider": "gemini",
                            "model": _GEMINI_SERVICE.model,
                            "accepted": accepted,
                            "score": score,
                            "feedback": feedback,
                            "summary": summary,
                        },
                    )
                except GeminiServiceError as exc:
                    context.log_event(
                        source=self.name,
                        target=None,
                        event_type="llm_fallback",
                        message="Gemini evaluation failed, falling back to heuristic approval.",
                        document_id=document["id"],
                        attempt=attempt,
                        payload={"error": str(exc)},
                    )

            if used_gemini:
                accepted = accepted and chosen.row_count >= 5
            else:
                accepted = accepted and chosen.row_count >= 5 and score >= 0.62 and not feedback
            retry_requested = not accepted and attempt < context.max_extraction_attempts
            if not feedback and not accepted:
                feedback = ["Improve sentence quality and extraction coverage before review."]
            if accepted:
                context.accepted_extractions[document["id"]] = chosen.csv_path
            context.agent_feedback_history.setdefault(document_key, []).extend(feedback)
            context.agent_feedback_history[document_key] = list(
                dict.fromkeys(context.agent_feedback_history[document_key])
            )
            decision = EvaluationDecision(
                document_id=document["id"],
                accepted=accepted,
                chosen_strategy=chosen.strategy,
                chosen_csv_path=chosen.csv_path,
                score=score,
                retry_requested=retry_requested,
                feedback=feedback,
            )

        context.evaluation_decisions[document["id"]] = decision
        context.log_event(
            source=self.name,
            target="product_gap_root_orchestrator",
            event_type="evaluation_decision",
            message=(
                "Extraction candidate approved for human review."
                if decision.accepted
                else "Extraction candidate not yet approved; another attempt is required."
                if decision.retry_requested
                else "Extraction candidate rejected after the final attempt."
            ),
            document_id=document["id"],
            attempt=attempt,
            payload={
                "accepted": decision.accepted,
                "retry_requested": decision.retry_requested,
                "chosen_strategy": decision.chosen_strategy,
                "chosen_csv_path": str(decision.chosen_csv_path) if decision.chosen_csv_path else None,
                "score": decision.score,
                "feedback": decision.feedback,
            },
        )
        return AgentStepResult(
            name=self.name,
            status="completed" if decision.accepted else "retry_requested" if decision.retry_requested else "warning",
            document_id=document["id"],
            attempt=attempt,
            details={
                "accepted": decision.accepted,
                "retry_requested": decision.retry_requested,
                "chosen_strategy": decision.chosen_strategy,
                "chosen_csv_path": str(decision.chosen_csv_path) if decision.chosen_csv_path else None,
                "score": decision.score,
                "feedback": decision.feedback,
            },
        )


class HumanReviewPreparationAgent(BaseSubAgent):
    name = "human_review_preparation_agent"
    role = "review_coordinator"

    def run(self, context: AnalysisContext, **kwargs: Any) -> AgentStepResult:
        context.review_artifacts.clear()
        for document in context.listed_documents:
            chosen_csv = context.accepted_extractions.get(document["id"])
            if chosen_csv is None:
                continue
            dataframe = pd.read_csv(chosen_csv)
            preview_rows = dataframe.head(10).fillna("").to_dict(orient="records")
            artifact = ReviewArtifact(
                document_id=document["id"],
                filename=document["filename"],
                csv_path=chosen_csv,
                preview_rows=preview_rows,
                evaluator_feedback=context.agent_feedback_history.get(_document_key(document["id"]), []),
                human_feedback=context.human_feedback_history.get(_document_key(document["id"]), []),
            )
            context.review_artifacts.append(artifact)
            context.log_event(
                source=self.name,
                target="human_reviewer",
                event_type="review_artifact_created",
                message=f"Prepared human review artifact for {document['filename']}.",
                document_id=document["id"],
                payload={
                    "csv_path": str(chosen_csv),
                    "preview_row_count": len(preview_rows),
                    "evaluator_feedback": artifact.evaluator_feedback,
                },
            )

        return AgentStepResult(
            name=self.name,
            status="completed" if context.review_artifacts else "failed",
            details={
                "review_artifacts": [
                    {
                        "document_id": artifact.document_id,
                        "filename": artifact.filename,
                        "csv_path": str(artifact.csv_path),
                        "preview_rows": artifact.preview_rows,
                        "evaluator_feedback": artifact.evaluator_feedback,
                        "human_feedback": artifact.human_feedback,
                    }
                    for artifact in context.review_artifacts
                ],
            },
        )


class NormalizationAgent(BaseSubAgent):
    name = "normalization_agent"
    role = "transformer"

    def run(self, context: AnalysisContext, **kwargs: Any) -> AgentStepResult:
        context.normalized_csvs.clear()
        normalized_files: list[str] = []

        for artifact in context.review_artifacts:
            dataframe = pd.read_csv(artifact.csv_path)
            dataframe["normalized_feature"] = (
                dataframe["feature"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
                .str.replace(r"\s+", " ", regex=True)
            )
            dataframe = dataframe[dataframe["normalized_feature"] != ""]
            output_path = context.workspace_dir / f"document_{artifact.document_id}_normalized.csv"
            dataframe.to_csv(output_path, index=False)
            context.normalized_csvs.append(output_path)
            normalized_files.append(str(output_path))
            context.log_event(
                source=self.name,
                target="comparison_agent",
                event_type="normalized_output_created",
                message=f"Normalized approved extraction for {artifact.filename}.",
                document_id=artifact.document_id,
                payload={"csv_path": str(output_path)},
            )

        return AgentStepResult(
            name=self.name,
            status="completed" if normalized_files else "failed",
            details={"normalized_csvs": normalized_files},
        )


class ComparisonAgent(BaseSubAgent):
    name = "comparison_agent"
    role = "comparator"

    def run(self, context: AnalysisContext, **kwargs: Any) -> AgentStepResult:
        merged: pd.DataFrame | None = None
        source_columns: list[str] = []

        for artifact, csv_path in zip(context.review_artifacts, context.normalized_csvs, strict=False):
            dataframe = pd.read_csv(csv_path)
            source_name = Path(artifact.filename).stem.replace(" ", "_")
            source_columns.append(source_name)
            reduced = dataframe[["normalized_feature"]].drop_duplicates().copy()
            reduced[source_name] = "present"
            merged = reduced if merged is None else merged.merge(reduced, on="normalized_feature", how="outer")

        if merged is None:
            merged = pd.DataFrame(columns=["normalized_feature"])

        for column in source_columns:
            if column in merged.columns:
                merged[column] = merged[column].fillna("missing")

        output_path = context.workspace_dir / "gap_matrix.csv"
        merged.sort_values("normalized_feature").to_csv(output_path, index=False)
        context.gap_matrix_path = output_path
        context.log_event(
            source=self.name,
            target="reporting_agent",
            event_type="comparison_complete",
            message="Gap matrix was generated from the human-approved normalized extractions.",
            payload={
                "gap_matrix_path": str(output_path),
                "feature_count": int(len(merged.index)),
            },
        )

        return AgentStepResult(
            name=self.name,
            status="completed",
            details={
                "gap_matrix_path": str(output_path),
                "feature_count": int(len(merged.index)),
            },
        )


class ReportingAgent(BaseSubAgent):
    name = "reporting_agent"
    role = "reporter"

    def run(self, context: AnalysisContext, **kwargs: Any) -> AgentStepResult:
        summary = (
            f"Human-approved extraction completed for {len(context.review_artifacts)} documents. "
            f"Normalized {len(context.normalized_csvs)} extraction files and wrote the gap matrix "
            f"to {context.gap_matrix_path}."
        )
        context.summary = summary
        context.log_event(
            source=self.name,
            target="product_gap_root_orchestrator",
            event_type="report_ready",
            message="Reporting completed for the current analysis run.",
            payload={"summary": summary, "gap_matrix_path": str(context.gap_matrix_path)},
        )
        return AgentStepResult(
            name=self.name,
            status="completed",
            details={"summary": summary, "gap_matrix_path": str(context.gap_matrix_path)},
        )
