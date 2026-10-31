"""Ejecutar desde la raíz: python -m src.main 'consulta'."""

import argparse
import sys
from pathlib import Path

from .support.service import simulate_response
from .runtime.config import ROOT, load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Nubbix: demo local con respuesta simulada.")
    parser.add_argument("query", help="Consulta de soporte, entre comillas.")
    parser.add_argument("--config", type=Path, default=ROOT / "config.toml")
    parser.add_argument("--provider", choices=["mock"])
    parser.add_argument("--prompt", choices=["v1_zero_shot", "v2_few_shot"])
    parser.add_argument("--mock-scenario", choices=["fixed", "malformed", "invalid_contract", "recover_once"])
    parser.add_argument("--no-metrics", action="store_true", help="No escribir métricas de esta llamada.")
    args = parser.parse_args()
    try:
        settings = load_settings(
            args.config, provider=args.provider, prompt=args.prompt,
            mock_scenario=args.mock_scenario, log_metrics=False if args.no_metrics else None,
        )
        response = simulate_response(args.query, settings=settings)
    except (ValueError, OSError):
        # Mensaje controlado: no volcar consultas ni detalles internos en errores.
        print("Error: entrada, configuración, respuesta o registro inválido. No se produjo una respuesta válida.", file=sys.stderr)
        return 2

    print("SIMULACIÓN LOCAL: sin LLM; categoría y confidence son valores de prueba.", file=sys.stderr)
    print(response.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
