# Nubbix Support — PI de clasificación de tickets

CLI Python de soporte: clasifica tickets sintéticos y propone respuestas/acciones
para una persona. Contrato estricto `{answer, confidence, category, actions}`;
categorías `billing`, `technical`, `account`, `other`. No ejecuta las acciones.

Proveedores: mock (predeterminado), OpenAI, Gemini y Ollama local. Prompts YAML
v1 zero-shot, v2 few-shot, v3 estructurado y v4 orientado a deliberación sin pedir
razonamiento privado ni activar un modo del proveedor. Corpus base de 32 casos y
ocho paráfrasis; dos etiquetas confirmadas por Luis y las demás propuestas técnicas.

## Instalar y comprobar

En un clon nuevo, con Python >=3.12, venv y pip, sin un `.venv` previo:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
make check
```

Ejecutar desde el checkout completo: config, prompts y datasets son recursos del
repositorio. La instalación limpia ya se verificó en Linux x86_64/Python 3.14.8;
no implica soporte probado para cada plataforma. Ver [reproducción y dependencias](docs/REPRODUCIBILIDAD.md).

## Primer recorrido sin APIs

```bash
python -m src.main 'Me cobraron dos veces este mes.' --provider mock --no-metrics
python -m evals.run_evals --dataset data/eval_dataset.jsonl --check-dataset
python -m evals.run_guardrail_diagnostics
```

El mock sirve para comprobar el flujo; sus scores no miden un LLM. La validación
del corpus revisa formato/cobertura/separación, no aprueba etiquetas humanas.

## Evaluar corpus y prompts

```bash
python -m evals.run_provider_evals --provider mock \
  --prompt v1_zero_shot --prompt v2_few_shot --all-cases \
  --max-calls 64 --output data/local_runs/mock-v1-v2-01 --execute
```

La ejecución exige una salida nueva y conserva plan, resultados, métricas y resumen.
OpenAI/Gemini necesitan `--model` explícito y ambas opciones `--execute
--allow-remote-inference`; sin `--execute` sólo se previsualiza, sin claves ni red.
La cota incluye reparaciones de JSON/contrato y no garantiza un límite monetario.
Ver [comandos multiproveedor, privacidad y límites](docs/EVALUACION_PROVEEDORES.md).
Los comandos legacy de evaluación mock/local y sus imports siguen disponibles.

## Configuración, claves y observabilidad

`config.toml` define parámetros; los flags los sobreescriben. Las rutas de recursos
siguen ancladas a la raíz. OpenAI/Gemini usan primero la variable de entorno y luego
la clave seleccionada del `.env` local, sólo al construir el proveedor remoto.
No ejecutar `source .env` ni versionar claves. Ver [precedencia y errores](docs/CLAVES_LOCALES.md)
y [Ollama local sin descargas automáticas](docs/OLLAMA.md).

Las métricas JSONL guardan estados, intentos, latencia y consumo reportado; no guardan
el ticket, respuesta cruda o claves. El evaluador usa un catálogo de tarifas Standard
fechado, preserva su hash y copia, y agrega costos por prompt/corrida con Decimal.
Datos insuficientes conservan null. Son estimaciones, no facturación real ni un tope
de gasto. Ver [tarifas, desglose y recálculo offline](docs/PRICING.md).

## Diseño y evidencia

- [Mapa de responsabilidades y compatibilidad](docs/ARQUITECTURA.md).
- [Experimentos y escenarios](docs/EXPERIMENTOS.md), [revisión de etiquetas](docs/REVISION_ETIQUETAS.md).
- [Resultados locales](docs/RESULTADOS_EVAL_LOCAL.md), [prompts v3/v4](docs/PROMPTS_V3_V4.md).
- [Diagnóstico de guardrails](docs/SEGURIDAD_DIAGNOSTICO.md), [prueba adversarial pareada](docs/SEGURIDAD_PAREADA.md).
- [Historial completo de incrementos y verificaciones](docs/HISTORIAL_README.md).

La modularización separa comandos, corpus, ejecución y reportes; servicio, factory,
reparación y métricas; catálogo, aritmética y costos. Las 100 líneas son orientación:
se conservan excepciones cuando una división dificulta revisar el flujo.

Al cierre de este refactor pasaron **188 tests**, lint y formato: transportes falsos,
imports/CLIs desde otro directorio y replay de reportes históricos. No se hicieron
inferencias reales, instalaciones ni cambios de tarifas/prompt/dataset durante el
refactor. Los guardrails siguen siendo heurísticos, con posibles bypass y falsos
positivos; el corpus no constituye un holdout independiente ni un ranking general.
El proyecto no acredita cumplimiento total de una rúbrica que aún está incompleta.
