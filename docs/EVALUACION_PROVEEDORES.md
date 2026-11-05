# Evaluación de corpus con distintos proveedores

Desde la raíz del checkout, con el entorno de `docs/REPRODUCIBILIDAD.md` activo,
`python -m evals.run_provider_evals` compara las mismas referencias y prompts usando
el servicio normal: guardrail de entrada, proveedor, validación y reparación de
JSON/contrato, guardrail de salida, métricas. No entrena ni modifica pesos.
No agrega dependencias. Los comandos `evals.run_evals` (mock),
`evals.run_local_sample` y `evals.run_adversarial_pairs` (Ollama) conservan su interfaz.

## Previsualizar primero

Este comando valida corpus, selección, prompts y cota; imprime hashes y parámetros,
pero no crea archivos, construye proveedores, consulta claves ni accede a la red:

```bash
python -m evals.run_provider_evals \
  --provider gemini --model MODELO_GEMINI_HABILITADO \
  --prompt v3_structured --case-id nubbix-b01 \
  --max-calls 1 --output data/local_runs/gemini-v3-una-muestra
```

La previsualización no verifica acceso al modelo ni precios. `--provider` y
`--prompt` son obligatorios; para proveedores distintos de mock también `--model`.
Se pueden repetir `--prompt` para v1_zero_shot, v2_few_shot, v3_structured o
v4_reasoning. V4 no activa opciones de reasoning del proveedor.
Elegir entre uno y cuatro `--case-id` o `--all-cases`.
`--dataset` permite otro JSONL con el mismo contrato; por defecto usa los 32 casos
de `data/eval_dataset.jsonl`. `--diagnostic-suite` acepta al menos cuatro casos,
con las mismas validaciones, y marca el reporte como diagnóstico complementario.

## Ejecutar deliberadamente

Para una comprobación sin APIs, con resultados simulados:

```bash
python -m evals.run_provider_evals --provider mock \
  --prompt v3_structured --prompt v4_reasoning --all-cases \
  --max-calls 64 --output data/local_runs/mock-corpus --execute
```

Para Ollama local, previamente instalado y con un modelo GGUF ya disponible:

```bash
python -m evals.run_provider_evals --provider ollama \
  --model qwen2.5-coder:0.5b-test --prompt v3_structured \
  --case-id nubbix-b01 --max-calls 1 \
  --output data/local_runs/ollama-v3-una-muestra --execute
```

No descarga modelos; conserva la restricción loopback del adaptador. Ese tag es
el disponible durante las pruebas previas, no un requisito universal.

Para OpenAI o Gemini, agregar **ambas** opciones `--execute` y
`--allow-remote-inference` al comando previsualizado. Ejemplo de ejecución remota
que puede generar cargos (no ejecutado durante esta implementación):

```bash
python -m evals.run_provider_evals --provider openai \
  --model MODELO_OPENAI_HABILITADO --prompt v3_structured \
  --case-id nubbix-b01 --max-calls 1 \
  --output data/local_runs/openai-v3-una-muestra \
  --execute --allow-remote-inference
```

El proceso necesita `OPENAI_API_KEY` o `GEMINI_API_KEY` según proveedor. Usa primero
el entorno; si la variable no existe, carga automáticamente su valor del `.env`
de la raíz del checkout. No hace falta exportar ni ejecutar ese archivo.
La previsualización y una ejecución remota sin ambos permisos no leen credenciales.
No cargar claves en TOML, argumentos, datasets ni commits, ni imprimirlas para
diagnosticar acceso. Ver [precedencia, sintaxis y errores](CLAVES_LOCALES.md).

## Cota de llamadas y gasto

`--max-attempts` vale **1** por defecto en este runner, independientemente del TOML,
y admite 1..3. La cota previa es:

`casos seleccionados × prompts seleccionados × max_attempts <= max_calls <= 384`.

Un caso y un prompt con dos intentos requieren `--max-calls 2`; 32 casos, dos
prompts y dos intentos requieren 128. Se reserva el peor caso aunque todas las
primeras respuestas resulten válidas. El plan muestra la cota remota por separado:
mock y Ollama tienen cero llamadas remotas.

La unidad es una invocación de `Provider.generate`, incluidos intentos de
reparación. Cada intento remoto usa una solicitud de generación del adaptador;
no hay retry HTTP propio. Ollama hace además una comprobación local `/api/show`
antes de `/api/chat` en cada intento. La cota no es un contador de todo tráfico HTTP
(por ejemplo, redirecciones de urllib). Fallos de transporte no se reintentan;
sólo JSON/contrato inválido puede activar la reparación. Los guardrails pueden
rechazar antes del proveedor o después de una generación ya consumida.

`--max-output-tokens` vale 256 por defecto, admite 16..4096 y se registra para cada
adaptador. No garantiza que cualquier modelo acepte el límite ni complete su JSON;
los proveedores y modelos pueden contabilizar reasoning de formas diferentes.
Los parámetros Ollama restantes provienen del TOML y quedan en el plan. Los
adaptadores remotos tienen timeout de 30 segundos por intento.

**No hay tope monetario implementado.** La cota de llamadas, tokens de salida y
los timeouts no son presupuestos de dinero. Puede haber consumo en respuestas
inválidas, incompletas o con timeout. El runner usa un catálogo público Standard fechado y conserva `cost_usd: null`
cuando faltan datos. Permite `--pricing ruta.json` o `--no-pricing`; registra costos
y tokens globales/por prompt sin confundir estimación y factura. Ver
[tarifas, fórmulas y recálculo offline](PRICING.md). Revisar
precios, controles del proveedor y consumo de la cuenta antes de habilitarlo.
La [documentación oficial de precios de OpenAI](https://developers.openai.com/api/docs/pricing)
distingue cobros por modelo y tipos de tokens; contar solicitudes no determina
su importe. No se presentan esos controles externos como garantía de un tope.

Por defecto se detiene ante el primer caso fallido; `--continue-on-error` permite
seguir explícitamente, salvo error de configuración. Un error de clasificación
con salida válida no detiene el corpus. No hay reanudación ni repetición automática.
Usar siempre una salida nueva: nunca sobrescribe una corrida existente. Código de
salida 2 indica error/fallo/corrida parcial; un score bajo con respuestas válidas
no es un error de ejecución.

## Evidencia, métricas y privacidad

Cada ejecución conserva `plan.json` antes de generar, `metrics.jsonl` append-only,
`results.jsonl` y `summary.json`. Incluye hashes de corpus, prompts y fuentes,
proveedor/modelo, límites efectivos, estado/etapa/código de fallo, intentos,
latencia y consumo reportado por intento. Consumo desconocido queda desconocido.
`generation_attempts` y `remote_calls_attempted` registran lo intentado, sin
inferir facturación. Una interrupción abrupta puede dejar plan y JSONL sin summary;
conservarlos y revisarlos antes de decidir otra ejecución.

Los scores usan las referencias existentes: exact match global y por categoría,
confusión, separación de casos ambiguos, contrato válido y estado de guardrails.
Un fallo procesado queda en el denominador; casos no ejecutados se cuentan aparte.
Para prompts incompletos, `exact_match` queda null y sólo se informa el resultado
sobre procesados como tal. Las referencias no se vuelven validadas por una persona
por ejecutar este comando. Mock se marca simulado; no mide calidad de un LLM.

Para comparar, mantener corpus/hashes, prompts, selección, orden e intentos y
límites; usar directorios separados por proveedor/modelo. El orden es prompt y
luego orden de los casos; no hay warmup, aleatorización ni repetición estadística.
La latencia incluye guardrails, construcción del proveedor y reparaciones. Los
límites iguales no igualan tokenizadores o capacidades: pocas muestras no permiten
rankings generales. Los resultados locales históricos no se alteran.

Los JSONL no guardan texto del ticket, respuesta completa, acciones, claves ni
excepciones crudas. **Sí se envía al proveedor remoto el ticket completo y el
prompt**, con sus ejemplos y feedback de reparación sanitizado cuando corresponde.
Usar sólo datos sintéticos revisados. Identificadores, etiquetas y nombres de
modelos aparecen en los artefactos: tampoco deben contener datos privados.
La ausencia de texto en logs no elimina retención o políticas del proveedor.
Las salidas bajo `data/local_runs/` están ignoradas por git; revisar antes de
publicar cualquier evidencia. Los guardrails son heurísticos, no garantizan
protección completa, privacidad o moderación general.

Las pruebas offline de permisos, fallos y privacidad se registran en la
[bitácora](bitacora/VERIFICACIONES.md#evaluador-multiproveedor-04112026).
