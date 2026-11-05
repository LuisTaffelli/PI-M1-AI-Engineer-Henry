"""Feedback acotado de validación, sin salida cruda ni razonamiento privado."""

from pydantic import ValidationError


def _validation_feedback(error: ValidationError) -> str:
    """Resumir hasta tres fallas sin copiar valores, mensajes o claves externas."""
    rules = {
        "answer": "answer: usá texto no vacío.",
        "confidence": "confidence: usá un número finito entre 0 y 1.",
        "category": "category: elegí billing, technical, account u other.",
        "actions": "actions: usá una lista de textos no vacíos; puede estar vacía.",
    }
    summaries = []
    for issue in error.errors(
        include_input=False, include_context=False, include_url=False
    ):
        location = issue["loc"]
        field = location[0] if location else None
        if issue["type"] == "json_invalid":
            summary = "La salida debe ser JSON válido y completo, sin texto adicional."
        elif issue["type"] == "extra_forbidden":
            summary = "Eliminá campos adicionales: sólo answer, confidence, category y actions."
        elif field in rules:
            summary = rules[field]
            if issue["type"] == "missing":
                summary = f"Falta el campo {field}. {summary}"
        else:
            summary = (
                "Devolvé un objeto JSON que cumpla los tipos y campos del contrato."
            )
        if summary not in summaries:
            summaries.append(summary)
        if len(summaries) == 3:
            break
    return (
        "Corrección de salida anterior:\n"
        + "\n".join(f"- {summary}" for summary in summaries)
        + "\nGenerá de nuevo la respuesta completa para la consulta original, sólo en JSON."
    )
