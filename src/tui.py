"""Menú opcional de terminal; delega inferencia y evaluación en las capas existentes."""

import argparse
import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from evals.adversarial import plan as paired_plan
from evals.adversarial import runner as paired_runner
from evals.classification import plan as corpus_plan
from evals.classification import runner as corpus_runner

from .llm.prompt_catalog import PROMPT_NAMES
from .llm.providers.base import ProviderError
from .runtime.config import ROOT, Settings, load_settings
from .support.guardrails import GuardrailError, check_input
from .support.schemas import SupportResponse, validation_failure_code
from .support.service import simulate_response

PROVIDERS = ("mock", "ollama", "openai", "gemini")


class BackToMenu(Exception):
    """Ctrl+C mientras se elige: descartar cambios y volver al menú."""


class EndSession(Exception):
    """EOF: terminar, no confundir entrada cerrada con confirmación."""


def initial_settings(config: Path) -> Settings:
    """Nunca heredar un proveedor remoto o la excepción Gemini al iniciar la UI."""
    settings = load_settings(
        config,
        provider="mock",
        mock_scenario="fixed",
        max_attempts=1,
        http_max_attempts=1,
        gemini_suite_retry_exception=False,
        http_retry_max_delay_seconds=30.0,
        http_retry_max_total_wait_seconds=60.0,
    )
    return settings.model_copy(update={"model": None})


class TerminalUI:
    def __init__(
        self,
        settings: Settings,
        *,
        read: Callable[[str], str] = input,
        write: Callable[[str], None] = print,
    ) -> None:
        self.settings = settings
        self.read = read
        self.write = write

    def ask(self, label: str) -> str:
        try:
            return self.read(label)
        except KeyboardInterrupt:
            raise BackToMenu from None
        except EOFError:
            raise EndSession from None

    def choose(self, title: str, options: tuple[str, ...]) -> int:
        self.write(title)
        for index, option in enumerate(options, 1):
            self.write(f"  {index}. {option}")
        while True:
            value = self.ask("Opción: ").strip()
            if value.isascii() and value.isdigit() and 1 <= int(value) <= len(options):
                return int(value) - 1
            self.write("Elegí un número de la lista. Ctrl+C vuelve; Ctrl+D sale.")

    def number(self, label: str, current: int, maximum: int, minimum: int = 1) -> int:
        while True:
            value = self.ask(f"{label} [{current}] ({minimum}..{maximum}): ").strip()
            if not value:
                return current
            if value.isascii() and value.isdigit() and minimum <= int(value) <= maximum:
                return int(value)
            self.write("Número fuera de rango.")

    def configure(self) -> None:
        provider = PROVIDERS[self.choose("Proveedor", PROVIDERS)]
        model = None
        if provider != "mock":
            while not model:
                model = self.ask("Modelo explícito (sin claves): ").strip()
        prompt = PROMPT_NAMES[self.choose("Prompt", PROMPT_NAMES)]
        attempts = self.number(
            "Rondas JSON por ticket/base", self.settings.max_attempts, 3
        )
        http_attempts = (
            self.number("Intentos HTTP por ronda", self.settings.http_max_attempts, 3)
            if provider in corpus_plan.REMOTE_PROVIDERS
            else 1
        )
        tokens = self.number("Máximo de tokens de salida", 256, 256, 16)
        # Commit atómico: cancelar cualquiera de las preguntas conserva la configuración.
        self.settings = Settings.model_validate(
            {
                **self.settings.model_dump(),
                "provider": provider,
                "model": model,
                "prompt": prompt,
                "max_attempts": attempts,
                "http_max_attempts": http_attempts,
                **{f"{p}_max_output_tokens": tokens for p in PROVIDERS if p != "mock"},
            }
        )
        self.write(
            "Configuración aplicada sólo a esta sesión. No se ejecutó inferencia."
        )

    def preview(self, settings: Settings, prompts: tuple[str, ...], bound: int) -> None:
        self.write("\nPREVIEW · todavía sin inferencia")
        self.write(
            f"Proveedor: {settings.provider} | Modelo: {settings.model or 'simulado'}"
        )
        self.write(f"Prompts: {', '.join(prompts)}")
        self.write(f"Máximo de invocaciones de proveedor: {bound}")
        self.write(
            f"Rondas JSON: {settings.max_attempts} | Intentos HTTP: "
            f"{settings.http_max_attempts if settings.provider in corpus_plan.REMOTE_PROVIDERS else 1}"
        )
        if settings.provider == "mock":
            self.write(
                "SIMULACIÓN sin LLM ni claves: no mide calidad o seguridad de modelos."
            )
        else:
            self.write(
                f"Máximo de tokens de salida por generación: "
                f"{getattr(settings, f'{settings.provider}_max_output_tokens')}"
            )
        if settings.provider in corpus_plan.REMOTE_PROVIDERS:
            self.write(
                "Se enviarán las consultas y los prompts a ese proveedor. Puede generar cargos. "
                "La cota de llamadas NO es un tope monetario; el costo total no está garantizado."
            )
            if settings.http_max_attempts > 1:
                self.write(
                    "Retry HTTP opt-in: hasta 30 s por espera y 60 s acumulados; red aparte."
                )

    def confirm(self, settings: Settings) -> bool:
        word = (
            "REMOTO"
            if settings.provider in corpus_plan.REMOTE_PROVIDERS
            else "EJECUTAR"
        )
        approved = (
            self.ask(f"Escribí {word} para esta corrida; Enter cancela: ").strip()
            == word
        )
        if not approved:
            self.write("Cancelado. No se ejecutó esta corrida.")
        return approved

    def interrupted(self, output: Path | None = None) -> None:
        self.write(
            "Interrumpido. No se reintentó ni reanudó la corrida. Una solicitud en curso "
            "puede haber llegado al proveedor; su resultado y costo pueden ser desconocidos."
        )
        if output is not None:
            self.write(
                f"Revisá {output}: si se crearon archivos, se conservan sin modificar. "
                "Pueden faltar resultados, métricas o summary.json. No es una corrida completa."
            )

    def error(self, error: ValueError | OSError) -> None:
        if isinstance(error, ProviderError):
            status = f" HTTP {error.http_status}" if error.http_status else ""
            self.write(
                f"Error de proveedor [{error.code}]{status}. Sin reintento automático de la corrida."
            )
        elif isinstance(error, GuardrailError):
            self.write(
                "Consulta o salida rechazada por guardrails. Si el proveedor ya fue "
                "invocado, puede haber consumo. No se repite automáticamente."
            )
        elif isinstance(error, ValidationError):
            code = (
                validation_failure_code(error)
                if error.title == SupportResponse.__name__
                else "configuration_invalid"
            )
            self.write(f"Error de validación [{code}].")
        else:
            self.write(
                "Entrada, respuesta, configuración o registro inválido. Revisá las opciones; no se repite automáticamente."
            )

    def tickets(self) -> None:
        self.write(
            f"Tickets independientes, sin historial enviado. Una línea, hasta "
            f"{self.settings.max_query_chars} caracteres originales; /volver regresa."
        )
        self.write("Usá ejemplos sintéticos, sin datos personales ni secretos.")
        while True:
            query = self.ask("\nTicket: ")
            if query == "/volver":
                return
            try:
                check_input(query, self.settings.max_query_chars)
            except GuardrailError as error:
                self.write(f"Rechazado: {error} No se envió al proveedor.")
                continue
            settings = self.settings
            http = (
                settings.http_max_attempts
                if settings.provider in corpus_plan.REMOTE_PROVIDERS
                else 1
            )
            self.preview(settings, (settings.prompt,), settings.max_attempts * http)
            self.write(
                f"Consulta: {len(query)} caracteres, sin recortar ni agregar historial."
            )
            self.write(
                f"Métricas: {settings.metrics_path if settings.log_metrics else 'desactivadas'}"
            )
            if not self.confirm(settings):
                continue
            try:
                response = simulate_response(query, settings=settings)
            except (KeyboardInterrupt, EOFError):
                self.interrupted()
                return
            except (ValueError, OSError) as error:
                self.error(error)
                continue
            self.write(response.model_dump_json(indent=2))
            self.write(
                "Acciones sugeridas, no ejecutadas. Confidence no es una probabilidad calibrada."
            )

    def evaluate(self) -> None:
        suite = self.choose(
            "Evaluación",
            (
                "Base (32 tickets)",
                "Paráfrasis (8 casos)",
                "Adversariales pareados",
                "Volver",
            ),
        )
        if suite == 3:
            return
        selection = self.choose(
            "Prompts", (f"Actual: {self.settings.prompt}", "Los cuatro")
        )
        prompts = (self.settings.prompt,) if selection == 0 else PROMPT_NAMES
        max_calls = self.number("Cota de invocaciones (no USD)", 384, 384)
        default = (
            ROOT
            / "data/local_runs"
            / (
                f"tui-{self.settings.provider}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
            )
        )
        output = Path(
            self.ask(f"Directorio NUEVO de salida [{default}]: ").strip() or default
        )
        if not output.is_absolute():
            output = ROOT / output
        plan = None
        started = False
        try:
            if suite == 2:
                plan = paired_plan.prepare_plan(
                    self.settings, prompts, output, max_calls=max_calls
                )
            else:
                dataset = (
                    ROOT
                    / "data"
                    / ("eval_dataset.jsonl" if suite == 0 else "eval_robustness.jsonl")
                )
                plan = corpus_plan.prepare_plan(
                    dataset,
                    self.settings,
                    [],
                    prompts,
                    output,
                    all_cases=True,
                    max_calls=max_calls,
                    diagnostic_suite=suite == 1,
                )
            self.preview(
                plan.settings, prompts, plan.metadata["provider_calls_upper_bound"]
            )
            self.write(f"Salida: {plan.output}")
            self.write(json.dumps(plan.metadata, indent=2, ensure_ascii=False))
            if not self.confirm(plan.settings):
                return
            self.write(
                "Ejecutando. Ctrl+C detiene; puede dejar artefactos parciales sin resumen."
            )
            started = True
            if suite == 2:
                report = paired_runner.execute_plan(
                    plan,
                    execute=True,
                    allow_local_inference=plan.settings.provider == "ollama",
                    allow_remote_inference=plan.settings.provider
                    in corpus_plan.REMOTE_PROVIDERS,
                )
            else:
                report = corpus_runner.execute_plan(
                    plan,
                    execute=True,
                    allow_remote_inference=plan.settings.provider
                    in corpus_plan.REMOTE_PROVIDERS,
                )
        except (KeyboardInterrupt, EOFError):
            if started:
                self.interrupted(plan.output)
            else:
                self.write("Preview interrumpido. No se inició inferencia.")
            return
        except (ValueError, OSError) as error:
            self.error(error)
            self.write(
                f"Salida prevista: {output}. Conservá cualquier archivo parcial; usá otra carpeta para una nueva corrida."
            )
            return
        self.write(json.dumps(report, indent=2, ensure_ascii=False))
        execution = report.get("execution", report)
        completed = execution["completed"]
        failures = execution.get(
            "failed_cases", execution.get("failed_provider_cases", 0)
        )
        failure_label = (
            "fallos de proveedor/configuración" if suite == 2 else "fallos registrados"
        )
        self.write(
            f"Estado: {'completa' if completed else 'PARCIAL'}; {failure_label}: {failures}."
        )
        self.write(f"Resumen del runner: {plan.output / 'summary.json'}")

    def run(self) -> int:
        self.write("NUBBIX SUPPORT · menú de terminal · mock inicial")
        while True:
            try:
                self.write(
                    f"\n{self.settings.provider} / {self.settings.model or 'simulado'} / {self.settings.prompt}"
                )
                choice = self.choose(
                    "Menú",
                    (
                        "Probar tickets en loop",
                        "Evaluar dataset o adversariales",
                        "Configurar proveedor/modelo/prompt",
                        "Salir",
                    ),
                )
                if choice == 3:
                    return 0
                (self.tickets, self.evaluate, self.configure)[choice]()
            except BackToMenu:
                self.write(
                    "\nSelección cancelada; volvemos al menú sin iniciar otra solicitud."
                )
            except EndSession:
                self.write("\nEntrada cerrada. Fin de la sesión.")
                return 0
            except (ValueError, OSError) as error:
                self.error(error)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config.toml")
    args = parser.parse_args(argv)
    try:
        settings = initial_settings(args.config)
    except (ValueError, OSError):
        print("Configuración inválida. No se inició inferencia.")
        return 2
    return TerminalUI(settings).run()


if __name__ == "__main__":
    raise SystemExit(main())
