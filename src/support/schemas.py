"""Contrato local provisorio; consultar README antes de integrarlo a un LLM."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SupportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    answer: NonEmptyText
    confidence: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    category: Literal["billing", "technical", "account", "other"]
    actions: list[NonEmptyText]
