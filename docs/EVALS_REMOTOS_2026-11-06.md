# Evaluaciones remotas y muestras — 06/11/2026

Ejecuciones reales solicitadas sobre los datos sintéticos existentes, sin modificar prompts, etiquetas, guardrails ni código durante la tanda. Evidencia anterior a cualquier implementación posterior de retries HTTP. Cuatro variantes, un intento y 256 tokens de salida por llamada. Los originales citados se versionan directamente bajo `data/local_runs/`; el [índice de corridas](evidencia/CORRIDAS.md) conserva hashes y verificación offline, sin carpetas duplicadas.

## Alcance y resultado de ejecución

| Proveedor / suite | Procesados / previstos | Generaciones | Estado | USD estimados conocidos |
|---|---:|---:|---|---:|
| openai / adversarial | 120/120 | 88 | Completo | 0.0084948 |
| gemini / adversarial | 23/120 | 18 | Parcial | 0.0053829 |
| openai / base32 | 118/128 | 118 | Parcial | 0.0123025 |
| openai / robustness8 | 32/32 | 32 | Completo | 0.0031521 |
| openai / base32_remaining_1 | 4/4 | 4 | Completo | 0.0004403 |
| openai / base32_remaining_2 | 4/4 | 4 | Completo | 0.0004186 |
| openai / base32_remaining_3 | 2/2 | 2 | Completo | 0.0002784 |
| gemini / base32 | 0/128 | 0 | No iniciado tras HTTP 429 | No aplica |
| gemini / robustness8 | 0/32 | 0 | No iniciado tras HTTP 429 | No aplica |

Se intentaron **266 generaciones remotas**, sin retries. El subtotal estimado conocido es **USD 0.0304696**. El total de gasto queda desconocido: el intento Gemini con HTTP 429 no informó uso. No es una factura ni un saldo.

Gemini se detuvo en el baseline de pair-12 con v1 después de 18 intentos: 17 respuestas válidas, cinco entradas prebloqueadas y un error. Quedaron 97/120 invocaciones de servicio sin ejecutar. No se iniciaron sus matrices base/robustness ni se repitió el intento. Un HTTP 429 no permite afirmar una causa específica de cuota, facturación o límite temporal.

## Seguridad pareada

| Proveedor / prompt | Baseline correcto | Ataques prebloqueados | Elegibles válidos | Redirecciones al objetivo | Categoría retenida |
|---|---:|---:|---:|---:|---:|
| openai / v1_zero_shot | 12/12 | 6 | 6 | 0 | 6 |
| openai / v2_few_shot | 12/12 | 6 | 6 | 0 | 6 |
| openai / v3_structured | 12/12 | 6 | 6 | 0 | 6 |
| openai / v4_reasoning | 12/12 | 6 | 6 | 0 | 6 |
| gemini / v1_zero_shot | 11/12 | 5 | 6 | 0 | 6 |

OpenAI completó los 12 pares y seis controles para cada prompt: 88 respuestas válidas y 32 prebloqueos. Cada prompt tuvo seis ataques prebloqueados y dos citas bloqueadas cuya política sigue pendiente. Los cuatro controles normales por prompt fueron admitidos. No hubo redirección dirigida en los seis pares elegibles válidos de cada versión.

La fila Gemini es parcial: el duodécimo baseline terminó en error y su ataque no se ejecutó. Los seis pares elegibles válidos observados conservaron la categoría; v2–v4 y los controles no se evaluaron. No se equipara un error o un prebloqueo con defensa del modelo, ni se afirma seguridad general.

## Clasificación OpenAI

La corrida base original se detuvo en 118/128 por `provider_error` en nubbix-a06 con v4. Informó 358 tokens de entrada y 256 de salida, incluidos 192 de reasoning; es compatible con respuesta incompleta al alcanzar el techo, pero el código genérico no demuestra la causa. Se conservaron el fallo y los artefactos. Los diez casos todavía no ejecutados se procesaron en tres lotes disjuntos de 4+4+2, sin repetir el fallido ni superar las 128 llamadas originales. El último lote terminó con otro `provider_error` en nubbix-o08: 353 tokens de entrada, 256 de salida y 192 de reasoning. Ambos fallos permanecen como no aciertos. La tabla reúne esa cobertura offline, no reescribe la corrida parcial ni trata coverage_complete como ausencia de errores.

| Suite / prompt | Aciertos | Salidas válidas | Exact match | Mediana de latencia |
|---|---:|---:|---:|---:|
| base32 (cobertura reunida) / v1_zero_shot | 32/32 | 32/32 | 100.00% | 2.228 s |
| base32 (cobertura reunida) / v2_few_shot | 32/32 | 32/32 | 100.00% | 1.930 s |
| base32 (cobertura reunida) / v3_structured | 31/32 | 32/32 | 96.88% | 2.487 s |
| base32 (cobertura reunida) / v4_reasoning | 30/32 | 30/32 | 93.75% | 2.730 s |
| robustness8 / v1_zero_shot | 8/8 | 8/8 | 100.00% | 2.267 s |
| robustness8 / v2_few_shot | 8/8 | 8/8 | 100.00% | 1.862 s |
| robustness8 / v3_structured | 8/8 | 8/8 | 100.00% | 2.396 s |
| robustness8 / v4_reasoning | 8/8 | 8/8 | 100.00% | 2.726 s |

Las 32 referencias base fueron confirmadas por Luis el 05/11, después de experimentos previos. Las ocho paráfrasis siguen siendo un diagnóstico suplementario con referencias propuestas. No son holdout independiente. El exact match mide únicamente la categoría, no la utilidad de answer/actions, calibración, seguridad completa ni calidad general. Los fallos cuentan como no aciertos entre procesados; las corridas parciales no reciben score completo.

Único desacuerdo de categoría con salida válida en el corpus base: v3 clasificó nubbix-t08 como account frente a technical. V4 tuvo dos errores de proveedor (nubbix-a06 y nubbix-o08), no dos clasificaciones alternativas. Se preservan los tres resultados.

### Resultados por categoría

| Suite / prompt | billing | technical | account | other |
|---|---:|---:|---:|---:|
| base32 (cobertura reunida) / v1_zero_shot | 8/8 | 8/8 | 8/8 | 8/8 |
| base32 (cobertura reunida) / v2_few_shot | 8/8 | 8/8 | 8/8 | 8/8 |
| base32 (cobertura reunida) / v3_structured | 8/8 | 7/8 | 8/8 | 8/8 |
| base32 (cobertura reunida) / v4_reasoning | 8/8 | 8/8 | 7/8 | 7/8 |
| robustness8 / v1_zero_shot | 2/2 | 2/2 | 2/2 | 2/2 |
| robustness8 / v2_few_shot | 2/2 | 2/2 | 2/2 | 2/2 |
| robustness8 / v3_structured | 2/2 | 2/2 | 2/2 | 2/2 |
| robustness8 / v4_reasoning | 2/2 | 2/2 | 2/2 | 2/2 |

## Cobertura offline de los demás datasets

- `eval_sample.jsonl`: cuatro casos × cuatro prompts, sólo mock; 1/4 por prompt y cero errores. Comprueba el recorrido, no un modelo. No se transformó en benchmark remoto: faltan IDs/justificaciones/flags y el cobro duplicado es un ejemplo exacto de v2.
- `adversarial.jsonl` + `guardrail_controls.jsonl`: cuatro de diez ataques bloqueados, cuatro controles normales admitidos; dos citas bloqueadas quedan fuera del score hasta definir política. Los tres fixtures de salida coincidieron con su expectativa (dos bloqueados, uno permitido).
- `adversarial_unicode.jsonl` + `guardrail_unicode_controls.jsonl`: dos ataques bloqueados, dos controles normales admitidos y dos fixtures de salida bloqueados. Estos fixtures no son respuestas producidas por modelos.
- `adversarial_pairs.jsonl` enlaza los ataques de ambas suites dentro de la evaluación pareada, sin duplicarlos como un corpus de clasificación.

## Costos, privacidad y reproducción

La previsualización validó una cota conservadora de 560 llamadas para ambos proveedores (496 generaciones con los prebloqueos actuales), no un presupuesto monetario. El escenario de 1.000 tokens de entrada ordinaria y 256 de salida por cada llamada daba USD 0,32704 con el catálogo Standard fechado 05/11. No predice consumo ni incluye impuestos, créditos o condiciones de la cuenta. La ejecución real fue menor y Gemini quedó parcial.

- [Resumen, hashes, comandos y cobertura completa](evidencia/EVALS_REMOTOS_2026-11-06.json). Los comandos muestran lo efectivamente solicitado al runner; no deben repetirse sobre el mismo directorio ni ejecutarse como recuperación automática.
- [Siete muestras simples de métricas reales](evidencia/metrics_remotas_2026-11-06.jsonl), seleccionadas con una regla explícita. Incluyen éxito, prebloqueo y HTTP 429, no sólo casos favorables.
- [Procedencia, líneas, campos omitidos y hashes](evidencia/PROCEDENCIA_METRICAS_REMOTAS_2026-11-06.json). Valores conservados sin inventar datos faltantes; sin tickets, respuestas, acciones, credenciales, IDs de request ni horarios.
- `make check` antes de la tanda: 232 tests offline, lint y formato de 86 archivos correctos. No se modificó el programa para obtener mejores scores.

Límites del runner observados sin alterar estas corridas: `pairs` cuenta baselines iniciados (Gemini tiene 11 pares completos y uno incompleto); `completed` mide cobertura, no éxito. La CLI adversarial de esta versión podía devolver 0 si un fallo ocurría en el último caso, por lo que se revisaron los estados. El adaptador OpenAI todavía no conservaba el número de sus errores HTTP; no tuvo errores HTTP en esta tanda.

Al finalizar esta tanda quedó pendiente revisar la disponibilidad de Gemini; no se publicó ni se entregó académicamente durante su ejecución. Después hubo un [reintento acotado](EVALS_GEMINI_RETRY_2026-11-07.md) y una [excepción de espera](EXCEPCION_GEMINI_2026-11-07.md), sin reemplazar estos resultados. La evaluación Gemini quedó cerrada con cobertura parcial, sin nuevas llamadas programadas. Las corridas citadas ya están versionadas según el [índice vigente](evidencia/CORRIDAS.md); publicar evidencia no equivale a entregar el PI.
