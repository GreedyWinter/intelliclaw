from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class AnalysisRunCreate(BaseModel):
    baseline_document_id: int | None = None
    prompt: str = Field(
        default=(
            "Analyze uploaded competitor PDFs for feature gaps and produce a "
            "comparison summary plus output artifacts."
        ),
        min_length=1,
    )


class HumanReviewSubmission(BaseModel):
    approved: bool
    feedback: str = Field(default="", max_length=4000)
