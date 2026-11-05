# Mapa de responsabilidades — refactor del 05/11/2026

La estructura general permanece: `src/`, `evals/`, `prompts/`, `data/`, `docs/` y
`pricing/`. No hay capas nuevas de framework, base de datos ni dependencias.
Las propiedades ya viven en TOML, YAML de prompts y JSON de tarifas; no se creó
un config global que mezcle reglas de negocio, mensajes y recursos sin relación.

## Recorrido de un request

`src.main` lee flags/TOML y llama `support.service.simulate_response`:

1. Guardrail de entrada, carga/render del prompt.
2. `llm.factory.create_provider` construye sólo el proveedor seleccionado, después
   del prechequeo; claves locales se resuelven diferidamente como antes.
3. Generación, Pydantic y reparación acotada con `support.repair`.
4. Guardrail de salida y respuesta con el mismo contrato.
5. `runtime.request_metrics` registra el resultado incluso tras un fallo.

`service.py` mantiene el orden y alcance de retries: no reintenta transporte ni
rechazos del guardrail. La factory recibe el generador de schema para construirlo
sólo en Gemini/Ollama, como antes. La interfaz `Provider` sigue en `llm/providers/base.py`.
El registro conserva los mismos estados, campos de privacidad, timestamps, uso y costos;
la latencia sigue incluyendo el trabajo de orquestación y reparaciones.

## Encontrar la responsabilidad correcta

| Qué cambiar | Módulo propietario |
|---|---|
| Flags de la CLI de soporte | `src/main.py` |
| Secuencia de validación/retry | `src/support/service.py` |
| Construcción de adaptadores | `src/llm/factory.py` |
| Mensaje seguro de reparación | `src/support/repair.py` |
| Guardrails y contrato | `src/support/guardrails.py`, `schemas.py` |
| Credenciales y configuración | `src/runtime/credentials.py`, `config.py` |
| Registro del request | `src/runtime/request_metrics.py`; writer en `metrics.py` |
| Schema/fuentes de precios | `src/runtime/pricing_catalog.py` |
| Aritmética y alcance de precio | `src/runtime/pricing_calculation.py` |
| Estado de costos por intento | `src/runtime/pricing.py` (API compatible) |
| Corpus etiquetado y separación | `evals/datasets.py` |
| Plan/cotas multiproveedor | `evals/evaluation_plan.py` |
| Ejecución multiproveedor | `evals/provider_evaluation.py` |
| Filas y scores de clasificación | `evals/classification_report.py` |
| Parcialidad y resumen de corrida | `evals/evaluation_report.py` |
| Agregación de uso/costos | `evals/usage_cost_report.py` |
| Hashes, JSON y registro esperado | `evals/artifacts.py` |
| Reglas legacy de ejecución local | `evals/local_evaluation.py` |
| Casos/controles defensivos | `evals/diagnostic_cases.py`, `paired_cases.py` |
| Diagnóstico offline | `evals/guardrail_report.py` |
| Ejecución/análisis pareado | `evals/paired_evaluation.py`, `paired_report.py` |
| Recálculo offline | `evals/reprice_run.py` |

Los `evals/run_*` son puntos de entrada. El mock de `run_evals` conserva su bucle
simple; no se fusionó con el runner pago ni se equipararon sus permisos o presupuestos.
Los motores locales mantienen los límites y orden propios; comparten persistencia
sin cambiar scores ni la semántica de los ataques.

## Compatibilidad y excepciones razonables

Siguen funcionando los comandos y sus flags existentes, más imports documentados
como `run_evals.Case/load_cases/check_dataset/normalized_query`,
`run_local_sample.run_sample/summarize`, `run_adversarial_pairs.AttackPair/load_protocol/analyze/run_pairs`
y `run_guardrail_diagnostics.DiagnosticCase/load_suite/evaluate`.
`runtime.pricing` reexporta schema/cálculos públicos; `simulate_response` mantiene
su firma y la inyección programática de un proveedor. Los dobles de construcción
ahora se interceptan en `src.llm.factory`; los de escritura, en `runtime.request_metrics`.

Hay módulos algo mayores de 100 líneas: planes y motores locales conservan juntos
validación, cotas, orden y persistencia para facilitar su revisión; catálogo/cálculo
se separan por función, sin dividir una fórmula a mitad. Adaptadores y normalización
de consumo no se fragmentaron sólo por tamaño. Los tests conservan fixtures y
escenarios legibles sin imponer un límite de líneas.

Los JSON/YAML de datasets/prompts/tarifas, config, resultados históricos y cinco
commits de costos se preservaron. Los hashes de fuentes de nuevas corridas cambian
por el refactor e incluyen los nuevos módulos; no se retocan hashes de corridas antiguas.
El diagnóstico offline amplía su cobertura de hashes con sus nuevos propietarios.

## Verificación

`make check`: 188 tests, Ruff lint y formato. Se mantienen pruebas de transporte
falso, cotas, gates sin credenciales, `.env` ficticio, retries, seguridad y costos.
Se agregaron regresiones de imports legacy, `--help` de todos los comandos desde
otro directorio sin entorno de credenciales y replay exacto del reporte pareado.
El replay previo de clasificación también sigue pasando. Se verifica empaquetado
de módulos Python y navegación de enlaces; no se vuelve a instalar ni a inferir.
