"""Nombres compartidos de prompts, sin imports de configuración ni proveedores."""

from typing import Literal

PromptName = Literal["v1_zero_shot", "v2_few_shot", "v3_structured", "v4_reasoning"]
PROMPT_TECHNIQUES = {
    "v1_zero_shot": "zero_shot",
    "v2_few_shot": "few_shot",
    "v3_structured": "zero_shot",
    "v4_reasoning": "zero_shot",
}
PROMPT_NAMES = tuple(PROMPT_TECHNIQUES)
DEFAULT_COMPARISON = ("v1_zero_shot", "v2_few_shot")
