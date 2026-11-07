# Reintento acotado de Gemini — 07/11/2026 (UTC)

Se intentó nuevamente la suite completa solicitada por Luis, con los cuatro prompts
existentes y sin cambiar código, etiquetas ni guardrails. La ejecución comenzó el
07/11 a las 00:02 UTC. Esta es una tanda nueva; no reemplaza ni reanuda los resultados
[del 06/11](EVALS_REMOTOS_2026-11-06.md).

Este informe describe esa primera repetición. La [excepción posterior](EXCEPCION_GEMINI_2026-11-07.md)
quedó cerrada con resultados parciales, sin nuevas inferencias ni reanudación
programada. La evidencia citada se publicó después en su ubicación original;
las observaciones sobre ausencia de publicación abajo corresponden a la ejecución.

## Resultado

**La suite quedó parcial por otro HTTP 429.** La petición fallida fue el baseline
`pair-12`, con `v1_zero_shot`. Esta vez el diagnóstico conservó que `Retry-After`
pedía una espera superior al límite de 30 segundos. La función nueva respetó el
límite: no recortó esa espera, no volvió a llamar y la CLI salió con código 2.
No se inició clasificación base ni paráfrasis después de ese error.

| Suite | Consultas procesadas / previstas | Invocaciones al proveedor | Estado |
|---|---:|---:|---|
| Adversarial, v1–v4 | 23/120 | 18 | Parcial; sólo comenzó v1 |
| Base32, v1–v4 | 0/128 | 0 | No iniciada tras el 429 |
| Robustness8, v1–v4 | 0/32 | 0 | No iniciada tras el 429 |

Las 23 consultas adversariales incluyen 17 respuestas válidas, cinco prebloqueos
de entrada y un error de proveedor. Hubo **cero retries HTTP y cero segundos de
espera por retry**: habilitar hasta tres intentos no obliga a usarlos cuando el
servidor exige una espera fuera del límite. No se relanzó el fallo ni se continuó
por otro proveedor o directorio. El cuerpo de error y el valor crudo del header no
se guardaron, por lo que no se conoce la causa específica ni la espera exacta.
Un 429 no demuestra por sí solo cuota diaria agotada, facturación o límite temporal.

## Condiciones fijadas y verificación

- Modelo `gemini-3.5-flash-lite`; prompts v1, v2, v3 y v4, en ese orden.
- Una ronda de generación JSON por caso; salida máxima de 256 tokens.
- Hasta tres intentos HTTP por generación, sólo ante estados permitidos.
- Espera máxima de 30 s por retry y 60 s acumulados por consulta; sin reintentar
  timeouts ni respuestas incompletas. [Contrato de retry](REINTENTOS_HTTP.md).
- Previews offline correctos: 360 invocaciones máximas adversariales, 384 base y
  96 paráfrasis. **840 en total** es una cota de invocaciones, no de gasto.
- `make check`: lint correcto, formato de 98 archivos correcto y 256 tests offline
  aprobados antes de invocar la API.
- Los hashes de código no cambiaron durante la ejecución. Prompts y datasets
  adversariales coinciden por hash con los de la tanda anterior.
- Sólo datos sintéticos existentes; no se publicaron resultados ni se hizo push.

El plan conservador reserva 280 consultas de servicio; los prebloqueos pueden
reducir las invocaciones. El escenario orientativo de 1.000 tokens de entrada y
256 de salida por cada una de las 840 invocaciones da USD 0,7896 usando el catálogo
Standard del 05/11. **No es una predicción, factura ni límite monetario.**

## Resultados parciales y costo

V1 acertó los once baselines con respuesta válida. El duodécimo terminó en error
y su ataque no se ejecutó: son once pares completos y uno incompleto. De los
ataques vistos, cinco fueron prebloqueados y seis quedaron admitidos y válidos;
los seis conservaron la categoría, sin redirecciones al objetivo observadas.
No se ejecutaron controles. Esto no prueba seguridad general y no permite
comparar v1 con v2–v4, que siguen sin procesar en esta tanda.

Las 17 respuestas con uso informado suman 3.268 tokens de entrada y 1.707 de
salida, con **subtotal estimado conocido USD 0,0052479**. El intento HTTP 429 no
informó uso: su costo y el total quedan desconocidos, no equivalen a cero. La
estimación usa tarifas guardadas del 05/11, no confirma la facturación de la cuenta.

**Gemini continúa sin un prompt ganador defendible.** No se recomienda una
variante a partir de una matriz incompleta. La [recomendación por proveedor](RECOMENDACIONES_PROMPTS_PROVEEDOR.md)
distingue la evidencia de OpenAI/Ollama y esta limitación de Gemini; no cambia el
default ni los YAML. Antes de otra tanda conviene revisar la disponibilidad o
cuota del servicio. Este informe no programa otra ejecución ni aumenta los límites.

## Evidencia y comandos

- [Resumen completo, comandos reales, previews, hashes y condiciones](evidencia/EVALS_GEMINI_RETRY_2026-11-07.json).
- [Plan de la corrida preservada](../data/local_runs/2026-11-07-gemini-adversarial-v1-v4-http3/plan.json).
- [Resultados por consulta](../data/local_runs/2026-11-07-gemini-adversarial-v1-v4-http3/results.jsonl)
  y [resumen del runner](../data/local_runs/2026-11-07-gemini-adversarial-v1-v4-http3/summary.json).

Los originales están en `data/local_runs/2026-11-07-gemini-adversarial-v1-v4-http3/`.
Los comandos se conservan para auditar lo ejecutado, no para repetirlos sobre la
misma salida. Las suites no iniciadas mantienen estado explícito, sin resultados
inventados ni puntuaciones completas.
