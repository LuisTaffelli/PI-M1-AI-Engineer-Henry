# README conservado antes de la reorganización del 05/11/2026

Archivo histórico. Describe el estado de cada etapa, no instrucciones actuales.
[Volver a la bitácora](../BITACORA.md) · [README actual](../../README.md)
Las rutas escritas en comandos siguen referidas a la raíz del repositorio.

## Navegación

- [Instalar y comprobar](#instalar-y-comprobar)
- [Primer recorrido sin APIs](#primer-recorrido-sin-apis)
- [Evaluar corpus y prompts](#evaluar-corpus-y-prompts)
- [Comparación de interpretaciones conservada](#comparación-de-interpretaciones-conservada)
- [Configuración, claves y observabilidad](#configuración-claves-y-observabilidad)
- [Diseño y evidencia](#diseño-y-evidencia)

# Nubbix Support — PI de clasificación de tickets

CLI Python de soporte: clasifica tickets sintéticos y propone respuestas/acciones
para una persona. Contrato estricto `{answer, confidence, category, actions}`;
categorías `billing`, `technical`, `account`, `other`. No ejecuta las acciones.

Proveedores: mock (predeterminado), OpenAI, Gemini y Ollama local. Prompts YAML
v1 zero-shot, v2 few-shot, v3 estructurado y v4 orientado a deliberación sin pedir
razonamiento privado ni activar un modo del proveedor. Corpus base de 32 casos y
ocho paráfrasis; tres etiquetas del corpus base confirmadas por Luis y 29 propuestas.

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
no implica soporte probado para cada plataforma. Ver [reproducción y dependencias](../REPRODUCIBILIDAD.md).

## Primer recorrido sin APIs

```bash
python -m src.main 'Me cobraron dos veces este mes.' --provider mock --mock-scenario fixed --no-metrics
python -m evals.run_evals --dataset data/eval_dataset.jsonl --check-dataset
python -m evals.run_guardrail_diagnostics
```

Salida del primer comando (JSON en stdout; aviso de simulación en stderr):

```json
{"answer":"SIMULACIÓN: recibimos tu consulta; un agente humano debe revisarla.","confidence":0.0,"category":"other","actions":["Revisar manualmente la consulta y asignar la categoría correcta."]}
```

El mock sirve para comprobar el flujo; su `other` fijo no clasifica el cobro ni mide
un LLM. La validación del corpus no aprueba etiquetas humanas.

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
Ver [comandos multiproveedor, privacidad y límites](../EVALUACION_PROVEEDORES.md).
Los comandos legacy de evaluación mock/local y sus imports siguen disponibles.

## Comparación de interpretaciones conservada

Ollama `qwen2.5-coder:0.5b-test`, 04/11/2026; un intento, 256 tokens de salida.
Coincidencias con referencias propuestas y formato se reportan por separado:

| Prompt | Coincidencias base | Salidas válidas base | Coincidencias paráfrasis |
|---|---:|---:|---:|
| v1 zero-shot | 11/32 | 31/32 | 3/8 |
| v2 few-shot | 18/32 | 30/32 | 4/8 |
| v3 estructurado | 17/32 | 32/32 | 5/8 |
| v4 deliberación | 13/32 | 30/32 | 2/8 |

V2 tuvo más coincidencias base; v3 preservó todos los contratos y más coincidencias
ante paráfrasis. El objetivo es observar cómo interpreta cada modelo las consultas
frente a lo esperado, no retocar prompts para maximizar aciertos. Se conservan las
cuatro versiones y v1 por defecto, con resultados y condiciones explícitos.
Las paráfrasis derivan del corpus, no son holdout; 29 etiquetas siguen propuestas.
[Protocolo, categorías y evidencia recalculable](../PROMPTS_V3_V4.md).

## Configuración, claves y observabilidad

`config.toml` define parámetros; los flags los sobreescriben. Las rutas de recursos
siguen ancladas a la raíz. OpenAI/Gemini usan primero la variable de entorno y luego
la clave seleccionada del `.env` local, sólo al construir el proveedor remoto.
No ejecutar `source .env` ni versionar claves. Ver [precedencia y errores](../CLAVES_LOCALES.md)
y [Ollama local sin descargas automáticas](../OLLAMA.md).

Las métricas JSONL guardan estados, intentos, latencia y consumo reportado; no guardan
el ticket, respuesta cruda o claves. El evaluador usa un catálogo de tarifas Standard
fechado, preserva su hash y copia, y agrega costos por prompt/corrida con Decimal.
Datos insuficientes conservan null. Son estimaciones, no facturación real ni un tope
de gasto. Ver [tarifas, desglose y recálculo offline](../PRICING.md).

## Diseño y evidencia

- [Cierre de entrega: evidencia y decisiones pendientes](../CIERRE_ENTREGA.md).
- [Mapa de responsabilidades y compatibilidad](../ARQUITECTURA.md).
- [Experimentos y escenarios](../EXPERIMENTOS.md), [revisión de etiquetas](../REVISION_ETIQUETAS.md).
- [Resultados locales](../RESULTADOS_EVAL_LOCAL.md), [prompts v3/v4](../PROMPTS_V3_V4.md).
- [Diagnóstico de guardrails](../SEGURIDAD_DIAGNOSTICO.md), [prueba adversarial pareada](../SEGURIDAD_PAREADA.md).
- [Historial completo de incrementos y verificaciones](../HISTORIAL_README.md).

La modularización separa comandos, corpus, ejecución y reportes; servicio, factory,
reparación y métricas; catálogo, aritmética y costos. Las 100 líneas son orientación:
se conservan excepciones cuando una división dificulta revisar el flujo.

Al cierre de este refactor pasaron **188 tests**, lint y formato: transportes falsos,
imports/CLIs desde otro directorio y replay de reportes históricos. No se hicieron
inferencias reales, instalaciones ni cambios de tarifas/prompt/dataset durante el
refactor. Los guardrails siguen siendo heurísticos, con posibles bypass y falsos
positivos; el corpus no constituye un holdout independiente ni un ranking general.
El proyecto no acredita cumplimiento total de una rúbrica que aún está incompleta.
