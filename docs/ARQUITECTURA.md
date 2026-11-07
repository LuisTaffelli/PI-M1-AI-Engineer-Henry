# Mapa de responsabilidades

El código está organizado por lo que hace. Para seguir una evaluación, primero
identificá si compara clasificación o si prueba seguridad, y después recorré su
CLI, carga de casos, ejecución y reporte. No se agregaron frameworks ni dependencias.

## Carpetas principales

```text
src/
  main.py                  CLI de soporte
  support/                 contrato, guardrails, reparación y servicio
  llm/                     prompts, factory, uso y adaptadores HTTP
  runtime/
    config.py              Settings y carga de TOML
    environment.py         único lector de os.environ y .env
    paths.py               raíz del checkout
    credentials.py         import compatible, sin lógica propia
    metrics.py             escritura JSONL
    request_metrics.py     registro por request
    pricing*.py            catálogo y cálculo de costos

evals/
  classification/          evaluaciones comunes de tickets etiquetados
    dataset.py             casos y controles de formato/cobertura
    smoke.py               recorrido con mock, sin calidad de modelo
    plan.py                selección, permisos y cota de llamadas
    runner.py              ejecución multiproveedor
    local.py               comparación local con sus límites originales
    scoring.py             filas, coincidencias y resultados por categoría
    report.py              resumen, fallos y corrida parcial
    reprice.py             recálculo offline sobre una corrida guardada
  adversarial/             evaluaciones de seguridad
    cases.py               ataques y controles del diagnóstico
    guardrails.py          diagnóstico offline, sin modelo
    pairs.py               protocolo limpio/atacado y orden de casos
    plan.py                preview pareado y cota común de llamadas
    runner.py              ejecución pareada multiproveedor
    report.py              efecto observado de ataques y bloqueos
  common/                  utilidades compartidas, no una suite de evaluación
    artifacts.py           hashes, JSON y lectura de métricas
    costs.py               agregación de tokens y costos
  cli/                     argumentos, salida y códigos de cada comando
  run_*.py                 entradas históricas compatibles
  reprice_run.py           entrada histórica del recálculo
```

Los JSONL de ataques conservan sus rutas en `evals/`; los corpus etiquetados siguen
en `data/`. Prompts, datasets, tarifas y resultados previos no se movieron ni editaron.

## Pruebas por responsabilidad

`tests/` acompaña este mapa con siete grupos: `integration/`, `providers/`,
`prompts/`, `guardrails/`, `service/`, `runtime/` y `evaluation/`. Los archivos
mixtos conservan sus casos y fixtures, agrupados por su responsabilidad principal.
Las pruebas de `evaluation/` verifican la mecánica de los runners sin modelos;
no sustituyen los experimentos académicos de `evals/`.

`make test` y `make check` siguen descubriendo toda la suite. La
[guía de tests](../tests/README.md) explica el alcance de cada carpeta y cómo
correr un grupo, un archivo o un caso. Los `__init__.py` permiten el descubrimiento
recursivo sin dependencias nuevas.

## Seguir la traza de una evaluación

- **Clasificación común:** `evals.run_provider_evals` → `cli/providers.py` →
  `classification/plan.py` → `classification/runner.py` → `support/service.py` →
  `classification/scoring.py` y `classification/report.py`.
- **Smoke test offline:** `evals.run_evals` → `cli/smoke.py` →
  `classification/dataset.py` y `classification/smoke.py`. El mock conserva su
  bucle simple y no mide la calidad de un LLM.
- **Comparación local:** `evals.run_local_sample` → `cli/local.py` →
  `classification/local.py` → `classification/scoring.py`.
- **Diagnóstico de guardrails:** `evals.run_guardrail_diagnostics` →
  `cli/guardrails.py` → `adversarial/cases.py` y `adversarial/guardrails.py`.
  Comprueba reglas de entrada/salida sin inferencia.
- **Ataques pareados:** `evals.run_adversarial_pairs` → `cli/adversarial.py` →
  `adversarial/plan.py` y `adversarial/pairs.py` → `adversarial/runner.py` →
  `adversarial/report.py`. Compara limpio/atacado en Ollama, Gemini, OpenAI o mock.
  El preview no lee claves; la ejecución requiere los permisos correspondientes
  y una cota explícita. Ver [protocolo y comandos](SEGURIDAD_PAREADA.md#repetición-acotada-con-distintos-proveedores--05112026).
- **Recálculo de costos:** `evals.reprice_run` → `cli/reprice.py` →
  `classification/reprice.py` y `common/costs.py`, sin volver a llamar al modelo.

`--diagnostic-suite` en una evaluación de clasificación permite un corpus menor,
como las paráfrasis. No la transforma en una prueba adversarial. Clasificación y
seguridad conservan criterios, límites y reportes distintos; sólo comparten las
utilidades de `common/` y el servicio de soporte cuando corresponde.

## Configuración y entorno

`runtime/config.py` valida TOML y overrides de CLI; no carga credenciales.
`runtime/environment.py` es el único módulo que consulta el entorno o interpreta
`.env`. Los adaptadores sólo piden su clave a ese módulo cuando se construyen.

La precedencia sigue siendo `api_key=` explícita → variable del proceso → `.env`
del checkout. Una variable presente pero vacía no recurre al archivo. La carga es
diferida, no modifica `os.environ`, no ejecuta expresiones y no mantiene caché.
Mock, Ollama, imports, validación de corpus y preview no leen claves. Los detalles
y límites del formato están en [claves locales](CLAVES_LOCALES.md).

`runtime/paths.py` define `ROOT` una sola vez, sin depender del directorio actual.
`runtime/config.py` lo reexporta para conservar imports anteriores.

## Recorrido de un request

`src.main` lee flags/TOML y llama `support.service.simulate_response`:

1. Guardrail de entrada y carga/render del prompt.
2. `llm.factory.create_provider` construye sólo el proveedor seleccionado.
   OpenAI/Gemini resuelven su clave mediante `runtime.environment` después del prechequeo.
3. Generación, contrato Pydantic y reparación acotada con `support.repair`.
4. Guardrail de salida y respuesta con el mismo contrato.
5. `runtime.request_metrics` registra el resultado incluso tras un fallo.

El servicio separa reparación JSON de retry HTTP opt-in. `llm/http_retry.py`
normaliza Retry-After sin conservar headers; `support/http_retry.py` aplica límites
por ronda y por consulta. Sólo 429/500/502/503/504 remotos pueden repetirse. No se
reintenta transporte incierto, salida incompleta ni rechazos del guardrail. Cada
invocación se cuenta, incluso fallos sin usage. La latencia incluye esperas y
reparaciones; el costo desconocido no se convierte en cero. Ver
[política y métricas](REINTENTOS_HTTP.md).

La factory recibe el generador del schema y sólo lo usa para Gemini/Ollama.
La interfaz `Provider` sigue en `llm/providers/base.py`. El catálogo de tarifas y la aritmética siguen separados en
`runtime/pricing_catalog.py` y `runtime/pricing_calculation.py`, con la API de
`runtime/pricing.py` como punto de uso.

## Límite de la consulta

`support/guardrails.py` define `MAX_QUERY_CHARS = 500`. El guardrail cuenta
`len(query)` sobre el texto original: puntos de código Unicode, incluidos espacios,
saltos de línea e invisibles. No son bytes, tokens ni grafemas visibles; por ejemplo,
un emoji compuesto puede sumar varios puntos de código.

- Hasta 500 puntos de código pasa el control de longitud; los demás controles
  siguen aplicando. Con 501 se rechaza antes de cargar el prompt o construir el proveedor.
- No se trunca ni normaliza la consulta enviada. La vista normalizada se usa sólo
  para detectar patrones de injection, como antes.
- `max_query_chars` en TOML puede imponer un límite menor, de 1 a 500. La validación
  rechaza una configuración mayor y el guardrail también mantiene el techo para
  llamadas programáticas con settings no validados.
- La CLI termina con código 2, stdout vacío y el mensaje en stderr
  `Error: La consulta no puede superar los 500 caracteres.` Si se eligió un límite
  menor, informa ese valor. No imprime la consulta rechazada.
- Si el registro está habilitado, conserva `rejected_input` con cero intentos y sin
  texto de consulta. El límite no garantiza resistencia a ataques ni moderación completa.

Este cambio es posterior a la reorganización de carpetas. Los JSON de experimentos
históricos mantienen el límite que regía al ejecutarlos; no se reescriben como si
hubieran usado 500.

## Compatibilidad

Siguen funcionando los seis comandos históricos y sus flags. En el pareado,
la ampliación añade preview por defecto (salvo el permiso local histórico) y
código 2 para corridas parciales; código 0 no certifica resistencia.
También se preservan los imports documentados:

- `run_evals.Case/load_cases/check_dataset/normalized_query/evaluate`.
- `run_local_sample.run_sample/summarize`.
- `run_guardrail_diagnostics.DiagnosticCase/load_suite/evaluate`.
- `run_adversarial_pairs.AttackPair/load_protocol/run_pairs/analyze`.
- `reprice_run.reprice` y `main` de cada comando.
- `runtime.credentials.load_api_key`, `runtime.config.ROOT`, la API de
  `runtime.pricing` y la firma/inyección de `simulate_response`.

Los antiguos módulos internos planos se importan desde su nueva familia. Por
ejemplo, `evals.evaluation_plan` pasa a `evals.classification.plan` y
`evals.paired_report` a `evals.adversarial.report`. No se dejaron copias de la lógica
ni un alias dinámico que oculte la traza. Los tests interceptan la lectura de claves
en `src.runtime.environment` y el trabajo de cada evaluador en su nuevo propietario.

El traslado conservó el comportamiento de las funciones de evaluación. La ampliación
posterior del pareado añade preview, proveedores y cobertura de corridas parciales;
el análisis histórico conserva sus resultados. Los hashes
de fuentes en corridas nuevas reflejan las rutas actuales; las corridas históricas
conservan sus hashes originales. No se cambian scores históricos, criterios ni
avisos de revisión humana. Los permisos nuevos se describen en el protocolo pareado. La [bitácora de verificaciones](bitacora/VERIFICACIONES.md#carpetas-y-entorno-05112026)
registra el alcance comprobado.
