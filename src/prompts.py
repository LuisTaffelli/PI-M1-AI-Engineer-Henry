"""Carga YAML 1.2 en su subconjunto JSON, sin dependencias nuevas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from .config import ROOT
from .schemas import NonEmptyText, SupportResponse


class Example(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    query: NonEmptyText
    response: SupportResponse


class PromptDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    version: NonEmptyText
    technique: Literal["zero_shot", "few_shot"]
    instructions: NonEmptyText
    examples: list[Example]

    @model_validator(mode="after")
    def check_examples(self):
        if self.technique == "zero_shot" and self.examples:
            raise ValueError("Zero-shot no admite ejemplos.")
        if self.technique == "few_shot" and len(self.examples) < 2:
            raise ValueError("Few-shot requiere al menos dos ejemplos aquí.")
        return self

    def render(self) -> str:
        parts = [self.instructions]
        for example in self.examples:
            parts.append(f"Ejemplo de consulta: {example.query}\nRespuesta: {example.response.model_dump_json()}")
        return "\n\n".join(parts)


def load_prompt(name: str) -> PromptDocument:
    if name not in ("v1_zero_shot", "v2_few_shot"):
        raise ValueError("Versión de prompt desconocida.")
    text = (ROOT / "prompts" / f"{name}.yaml").read_text(encoding="utf-8")
    document = PromptDocument.model_validate_json(text)
    expected = {"v1_zero_shot": "zero_shot", "v2_few_shot": "few_shot"}
    if document.version != name or document.technique != expected[name]:
        raise ValueError("Versión y técnica no coinciden con el archivo.")
    return document
