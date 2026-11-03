"""Ejecutar desde la raíz: python -m src.main 'consulta'."""

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from .llm.providers.base import ProviderError
from .runtime.config import ROOT, load_settings
from .support.schemas import SupportResponse, validation_failure_code
from .support.service import simulate_response


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Nubbix: soporte con proveedor configurable."
    )
    parser.add_argument("query", help="Consulta de soporte, entre comillas.")
    parser.add_argument("--config", type=Path, default=ROOT / "config.toml")
    parser.add_argument("--provider", choices=["mock", "openai", "gemini"])
    parser.add_argument(
        "--model", help="Modelo elegido; obligatorio para proveedores remotos."
    )
    parser.add_argument("--prompt", choices=["v1_zero_shot", "v2_few_shot"])
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
            prompt=args.prompt,
            mock_scenario=args.mock_scenario,
            log_metrics=False if args.no_metrics else None,
        )
        response = simulate_response(args.query, settings=settings)
    except ProviderError as error:
        print(
            f"Error: proveedor [{error.code}]. No se produjo una respuesta válida.",
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
        label = "OpenAI" if settings.provider == "openai" else "Gemini"
        print(
            f"{label}: salida validada; confidence es autodeclarada.", file=sys.stderr
        )
    print(response.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
