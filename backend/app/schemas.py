from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class AnalysisRunCreate(BaseModel):
    prompt: str = Field(
        default=(
            "Analyze uploaded competitor PDFs for feature gaps and produce a "
            "comparison summary plus output artifacts."
        ),
        min_length=1,
    )
