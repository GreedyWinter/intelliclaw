from pathlib import Path

import pandas as pd
import pdfplumber

from backend.app.agents.base import AnalysisContext, AgentStepResult, BaseSubAgent


class DocumentListingAgent(BaseSubAgent):
    name = "document_listing_agent"

    def run(self, context: AnalysisContext) -> AgentStepResult:
        pdf_documents = [
            document
            for document in context.documents
            if str(document.get("file_path", "")).lower().endswith(".pdf")
        ]
        return AgentStepResult(
            name=self.name,
            status="completed",
            details={
                "document_count": len(pdf_documents),
                "documents": [
                    {
                        "id": document["id"],
                        "filename": document["filename"],
                        "file_path": document["file_path"],
                    }
                    for document in pdf_documents
                ],
            },
        )


class PdfExtractionAgent(BaseSubAgent):
    name = "pdf_extraction_agent"

    def run(self, context: AnalysisContext) -> AgentStepResult:
        extracted_files: list[str] = []

        for document in context.documents:
            file_path = document.get("file_path")
            if not file_path or not str(file_path).lower().endswith(".pdf"):
                continue

            source_path = Path(file_path)
            if not source_path.exists():
                continue

            rows: list[dict[str, str]] = []
            with pdfplumber.open(source_path) as pdf:
                for page_number, page in enumerate(pdf.pages, start=1):
                    text = (page.extract_text() or "").strip()
                    if not text:
                        continue

                    for line in text.splitlines():
                        normalized_line = line.strip()
                        if not normalized_line:
                            continue
                        rows.append(
                            {
                                "source_document": document["filename"],
                                "page": str(page_number),
                                "feature": normalized_line[:200],
                            }
                        )

            output_path = context.workspace_dir / f"document_{document['id']}_raw.csv"
            dataframe = pd.DataFrame(rows or [{"source_document": document["filename"], "page": "1", "feature": ""}])
            dataframe.to_csv(output_path, index=False)
            context.extracted_csvs.append(output_path)
            extracted_files.append(str(output_path))

        return AgentStepResult(
            name=self.name,
            status="completed",
            details={"extracted_csvs": extracted_files, "count": len(extracted_files)},
        )


class NormalizationAgent(BaseSubAgent):
    name = "normalization_agent"

    def run(self, context: AnalysisContext) -> AgentStepResult:
        normalized_files: list[str] = []

        for csv_path in context.extracted_csvs:
            dataframe = pd.read_csv(csv_path)
            if "feature" not in dataframe.columns:
                continue

            dataframe["normalized_feature"] = (
                dataframe["feature"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.lower()
                .str.replace(r"\s+", " ", regex=True)
            )
            dataframe = dataframe[dataframe["normalized_feature"] != ""]
            output_path = context.workspace_dir / csv_path.name.replace("_raw.csv", "_normalized.csv")
            dataframe.to_csv(output_path, index=False)
            context.normalized_csvs.append(output_path)
            normalized_files.append(str(output_path))

        return AgentStepResult(
            name=self.name,
            status="completed",
            details={"normalized_csvs": normalized_files, "count": len(normalized_files)},
        )


class ComparisonAgent(BaseSubAgent):
    name = "comparison_agent"

    def run(self, context: AnalysisContext) -> AgentStepResult:
        merged: pd.DataFrame | None = None
        source_columns: list[str] = []

        for csv_path in context.normalized_csvs:
            dataframe = pd.read_csv(csv_path)
            if "normalized_feature" not in dataframe.columns:
                continue

            document_name = csv_path.stem.replace("_normalized", "")
            source_columns.append(document_name)
            reduced = dataframe[["normalized_feature"]].drop_duplicates().copy()
            reduced[document_name] = "present"

            if merged is None:
                merged = reduced
            else:
                merged = merged.merge(reduced, on="normalized_feature", how="outer")

        if merged is None:
            merged = pd.DataFrame(columns=["normalized_feature"])

        for column in source_columns:
            if column in merged.columns:
                merged[column] = merged[column].fillna("missing")

        output_path = context.workspace_dir / "gap_matrix.csv"
        merged.sort_values("normalized_feature").to_csv(output_path, index=False)
        context.gap_matrix_path = output_path

        return AgentStepResult(
            name=self.name,
            status="completed",
            details={
                "gap_matrix_path": str(output_path),
                "feature_count": int(len(merged.index)),
                "source_columns": source_columns,
            },
        )


class ReportingAgent(BaseSubAgent):
    name = "reporting_agent"

    def run(self, context: AnalysisContext) -> AgentStepResult:
        document_count = len(context.documents)
        extracted_count = len(context.extracted_csvs)
        normalized_count = len(context.normalized_csvs)

        summary = (
            f"Processed {document_count} uploaded documents, extracted {extracted_count} "
            f"CSV files, normalized {normalized_count} datasets, and generated a gap "
            f"matrix at {context.gap_matrix_path}."
        )
        context.summary = summary

        return AgentStepResult(
            name=self.name,
            status="completed",
            details={
                "summary": summary,
                "gap_matrix_path": str(context.gap_matrix_path) if context.gap_matrix_path else None,
            },
        )
