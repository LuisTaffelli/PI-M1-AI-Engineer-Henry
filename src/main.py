"""Ejecutar desde la raíz: python -m src.main 'consulta'."""

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from .llm.prompt_catalog import PROMPT_NAMES
from .llm.providers.base import ProviderError
from .runtime.config import ROOT, load_settings
from .support.guardrails import MAX_QUERY_CHARS, InputTooLongError
from .support.schemas import SupportResponse, validation_failure_code
from .support.service import simulate_response


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Nubbix: soporte con proveedor configurable."
    )
    parser.add_argument(
        "query",
        help=f"Consulta de soporte, entre comillas (máximo {MAX_QUERY_CHARS} caracteres).",
    )
    parser.add_argument("--config", type=Path, default=ROOT / "config.toml")
    parser.add_argument("--provider", choices=["mock", "openai", "gemini", "ollama"])
    parser.add_argument(
        "--model",
        help="Modelo elegido; obligatorio para proveedores distintos de mock.",
    )
    parser.add_argument("--prompt", choices=PROMPT_NAMES)
    parser.add_argument(
        "--http-max-attempts",
        type=int,
        choices=range(1, 4),
        help="Intentos HTTP por generación remota (1 desactiva retry; máximo 3).",
    )
    parser.add_argument(
        "--mock-scenario",
        choices=["fixed", "malformed", "invalid_contract", "recover_once"],
    )
    parser.add_argument(
        "--no-metrics",
        action="store_true",
        help="No escribir métricas de esta llamada.",
    )
    args = parser.parse_args()
    try:
        settings = load_settings(
            args.config,
            provider=args.provider,
            model=args.model,
            http_max_attempts=args.http_max_attempts,
            prompt=args.prompt,
            mock_scenario=args.mock_scenario,
            log_metrics=False if args.no_metrics else None,
        )
        if settings.gemini_suite_retry_exception:
            raise ValueError(
                "La excepción Gemini sólo se usa en runners de evaluación."
            )
        response = simulate_response(args.query, settings=settings)
    except InputTooLongError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    except ProviderError as error:
        http_detail = f" HTTP {error.http_status}" if error.http_status else ""
        print(
            f"Error: proveedor [{error.code}]{http_detail}. No se produjo una respuesta válida.",
            file=sys.stderr,
        )
        return 2
    except ValidationError as error:
        # La configuración también puede fallar antes de llegar al servicio.
        code = (
            validation_failure_code(error)
            if error.title == SupportResponse.__name__
            else "configuration_invalid"
        )
        print(
            f"Error: validación [{code}]. No se produjo una respuesta válida.",
            file=sys.stderr,
        )
        return 2
    except (ValueError, OSError):
        # Mensaje controlado: no volcar consultas ni detalles internos en errores.
        print(
            "Error: entrada, configuración, respuesta o registro inválido. No se produjo una respuesta válida.",
            file=sys.stderr,
        )
        return 2

    if settings.provider == "mock":
        print(
            "SIMULACIÓN LOCAL: sin LLM; categoría y confidence son valores de prueba.",
            file=sys.stderr,
        )
    else:
        label = {"openai": "OpenAI", "gemini": "Gemini", "ollama": "Ollama local"}[
            settings.provider
        ]
        print(
            f"{label}: salida validada; confidence es autodeclarada.", file=sys.stderr
        )
    print(response.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
