# Ejemplos de métricas y su procedencia

Estos archivos son **extractos minimizados de registros reales del programa**.
Se retiraron `request_id` y `timestamp`, sin sustituirlos por datos inventados.
Los originales locales se conservan: los extractos no son el esquema completo
ni copias byte a byte. No incluyen tickets, respuestas, acciones ni credenciales.
Son muestras de observabilidad, no un benchmark nuevo.

## Simulación del ensayo

[metrics_mock_2026-11-05.jsonl](evidencia/metrics_mock_2026-11-05.jsonl) contiene dos
requests del ensayo en un clon limpio: uno válido en un intento y otro que repara
JSON simulado y termina en dos. La segunda escritura del archivo original conservó
intacta la primera; esa prueba ocurrió antes de preparar los extractos.

`provider=mock` y `simulated=true`. Tokens y costo quedan `null`: no hubo consumo
de un modelo. Las latencias son las medidas en esa ejecución local; la fecha está
en la procedencia. No son métricas de Gemini, OpenAI ni Ollama.

## Inferencia local histórica

[metrics_ollama_2026-11-04.jsonl](evidencia/metrics_ollama_2026-11-04.jsonl) extrae
una línea de la corrida anterior con qwen2.5-coder:0.5b-test y v1. Reportó 230 tokens
de entrada, 53 de salida y 283 totales. `provider=ollama`, `simulated=false` y
`cost_usd=null`: no hay estimación monetaria admitida para esa ejecución local.
Esto no equivale a costo total cero. No se volvió a ejecutar el modelo para preparar
la muestra. `status=ok` indica salida validada, no categoría acertada.

La fila numérica correspondiente está en
[EVAL_PROMPTS_V34_2026-11-04.json](EVAL_PROMPTS_V34_2026-11-04.json): corrida
2026-11-04-v34-session-v1-v2, nubbix-b01, v1_zero_shot. La referencia era billing
y el modelo devolvió account; se conserva ese desacuerdo.

## Comprobar origen y significado

- [Procedencia y hashes de las muestras](evidencia/PROCEDENCIA_METRICAS_2026-11-05.json).
- [Ensayo offline del checkout](evidencia/ENSAYO_ENTREGA_2026-11-05.json).
- [Significado de tokens, componentes y costo estimado](PRICING.md).

La procedencia identifica fecha, archivo y líneas de origen, los campos omitidos,
el hash del origen y el del extracto. Para comprobarlos localmente, seleccionar
las líneas indicadas, quitar sólo `request_id` y `timestamp` y comparar los objetos
JSON. Los demás valores se conservan; no se simularon identidades ni horarios.

La línea histórica conserva los demás campos del esquema de su momento. Las
líneas del ensayo incluyen campos de tokens/costos incorporados después. No se
rellenaron datos faltantes ni se retrocedió la fecha de tarifas para hacerlas parecer
equivalentes.

## Evidencia original completa

Las [11 corridas inventariadas](evidencia/CORRIDAS.md) se versionan directamente
en `data/local_runs/`, sin mirror. Los archivos originales y sus hashes permiten
verificar las muestras y los resultados offline, incluidos errores y valores
desconocidos. Otras corridas exploratorias siguen ignoradas por Git.
