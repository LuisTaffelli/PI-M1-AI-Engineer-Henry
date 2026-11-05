# Tokens y costos estimados — verificación del 05/11/2026

El evaluador multiproveedor registra consumo y costo por intento, caso, prompt y
corrida, sin consultar facturación ni ejecutar solicitudes adicionales para medir.
Usa Decimal sin redondear por intento; los importes JSON son strings USD o null.
**Es una estimación bajo tarifas públicas de texto Standard pagas, no una factura,
un saldo ni un tope monetario.** `billing_verified` siempre es false.

## Catálogo fechado y alcance

`pricing/standard-text-2026-11-05.json` es el catálogo predeterminado del evaluador
para OpenAI/Gemini. Importes en **USD por 1.000.000 tokens**, consultados el
**2026-11-05**; esa fecha es de verificación, no una fecha efectiva inferida:

| Proveedor/modelo exacto | Entrada ordinaria | Entrada cacheada | Salida, incluido reasoning | Escritura 30m | Escritura 12h |
|---|---:|---:|---:|---:|---:|
| OpenAI `gpt-6-luna` | 0.10 | 0.01 | 0.50 | 0.125 | 0.25 |
| Gemini `gemini-3.5-flash-lite` | 0.30 | 0.03 | 2.50 | No aplicada | No aplicada |

Fuentes oficiales: [Luna](https://developers.openai.com/api/docs/models/gpt-6-luna),
[precios OpenAI](https://developers.openai.com/api/docs/pricing),
[Gemini Standard/Paid](https://aistudio.google.com/docs/pricing#gemini-3.5-flash-lite).
Son los IDs registrados en pruebas previas del proyecto; no se presume tarifa de
aliases, modelos similares o nombres informales como “luna 6.1”.

Luna se limita aquí a **hasta 272.000 tokens de entrada por intento**: la fuente
publica otro tramo superior, pero el catálogo no lo aplica silenciosamente.
Gemini incluye pensamiento en el precio de salida; no se presume nivel gratuito.
Se excluyen Batch/Flex/Fast/Priority, descuentos de cuenta, créditos, impuestos,
recargos regionales, herramientas, multimodalidad y almacenamiento persistente de
caché. La tarifa de almacenamiento Gemini publicada es una unidad temporal distinta;
no se agrega a una llamada de texto sin datos de uso/tiempo de ese recurso.
Los adaptadores actuales no solicitan caché explícita persistente de Gemini.
No se verifica el tier efectivo de la cuenta: esta hipótesis Standard queda registrada.

## Configuración y evidencia

El runner `evals.run_provider_evals` elige, en este orden: `--no-pricing` desactiva;
`--pricing ruta.json` selecciona catálogo; luego `pricing_path` del TOML; finalmente
el catálogo incorporado. Mock/Ollama no activan tarifas remotas. Las rutas relativas
`--pricing`/TOML se resuelven contra la raíz del checkout. Rutas absolutas se admiten.
El servicio/CLI principal conserva el comportamiento optativo de `Settings.pricing_path`:
para sus métricas se puede añadir al TOML `pricing_path = "pricing/standard-text-2026-11-05.json"`.
La salida de soporte sigue teniendo exactamente cuatro campos.

La preparación valida el JSON y registra versión/hash sin leer claves ni hacer red.
Un catálogo explícito inválido detiene esa preparación antes de generar; usar
`--no-pricing` deliberadamente si se necesita evaluar sin estimación. Si el modelo
no tiene tarifa exacta, la clasificación puede correr y el costo queda `rate_missing`.
La ejecución guarda `pricing.json` con los bytes preparados: un cambio posterior
del catálogo fuente no modifica la tarifa de una corrida. Plan, métricas y resultados
conservan versión del catálogo, versión de tarifa, hash, fuente oficial y fecha.
`rate_source_url` sólo se copia para tarifas públicas verificadas (URL oficial sin query).

Cada actualización debe crear otro catálogo/versiones y volver a verificar sus
condiciones. El código valida metadatos; no certifica importes ni actualiza precios
por red. El schema sigue admitiendo catálogos v1 previos; los nuevos campos de rango
y escrituras son opcionales para compatibilidad. Para modelos con escrituras pagas,
configurar `requires_cache_write_usage` y ambas tarifas; no omitirlas para forzar un número.
`pricing.example.json` conserva el catálogo vacío. Las tarifas `fixture` sólo se
habilitan en pruebas inyectadas explícitas, nunca como precio remoto real.

## Contadores y fórmula

Se conserva `usage_by_attempt`, incluso si el JSON, contrato o guardrail falla.
OpenAI: entrada/salida totales, caché leída, escrituras totales y componentes 30m/12h,
y reasoning cuando está informado. Gemini: entrada, texto generado, pensamiento,
caché y uso de herramientas. Se aceptan sólo enteros no negativos; no se convierten
strings, floats o booleanos. Los totales deben reconciliarse.

```text
entrada_ordinaria = entrada_total - entrada_cacheada - escrituras_totales
USD = (entrada_ordinaria × tarifa_entrada
       + entrada_cacheada × tarifa_cacheada
       + escrituras_30m × tarifa_30m + escrituras_12h × tarifa_12h
       + salida_normalizada × tarifa_salida) / 1_000_000
```

Los dos componentes de escritura deben sumar el total. No se vuelve a agregar ese
total ni el reasoning: OpenAI ya lo incluye en salida; Gemini lo suma una vez al
texto sólo cuando sus contadores permiten reconciliar el total. `initial_input_tokens`
no se agrega nuevamente. Fuentes de campos: [caché OpenAI](https://developers.openai.com/api/docs/guides/prompt-caching)
y [Usage Interactions](https://aistudio.google.com/api-reference/interactions-api/create-interaction).
Uso de herramientas positivo, desglose contradictorio, tramo no soportado o datos
faltantes dejan costo desconocido. No se infiere caché cero por el tamaño del prompt.

`cost_components_by_attempt` separa entrada ordinaria, caché, cada escritura y
salida con reasoning. `cost_by_attempt` suma esos componentes y `cost_usd` suma
todos los intentos sólo si todos son calculables. `cost_unavailable_reason_by_attempt`
explica faltantes/rango; el estado `usage_unavailable` también puede indicar un
desglose insuficiente para la tarifa aunque los totales de tokens sean conocidos.
Otros estados: `not_requested`, `pricing_unconfigured`, `pricing_unavailable`,
`rate_missing`, `rate_unverified`, `partial`, `fixture_estimate`, `estimated`.

En `summary.json`, `usage_and_cost` global y por prompt distingue `total` de
`reported_subtotal` para cada contador y muestra cuántos intentos lo informaron.
`known_estimated_subtotal_usd` nunca reemplaza un `cost_usd` desconocido. No mezcla
costos de fixtures/simulaciones con estimaciones reales. El alcance es sólo los
casos procesados; `completed/not_run` del reporte indica corpus incompleto.
No se estima consumo con caracteres, confidence o conteo local del prompt.

## Comandos y corridas anteriores

Previsualización sin claves ni generación:

```bash
python -m evals.run_provider_evals --provider openai --model gpt-6-luna \
  --prompt v3_structured --case-id nubbix-b01 --max-attempts 2 --max-calls 2 \
  --output data/local_runs/luna-costos-01
```

Para una ejecución real, agregar `--execute --allow-remote-inference`; puede generar
cargos. El `.env` se carga sólo al construir el proveedor; conservar las demás
protecciones de la [guía del evaluador](EVALUACION_PROVEEDORES.md).

Para recalcular **offline**, con un catálogo actual, una corrida ya registrada:

```bash
python -m evals.reprice_run \
  --run-dir data/local_runs/luna-robustness-v1-v4-01 \
  --pricing pricing/standard-text-2026-11-05.json \
  --output data/local_runs/luna-robustness-costos-01
```

No llama proveedores, lee claves ni modifica originales. Requiere plan con
proveedor/modelo exactos y métricas compatibles no simuladas; conserva hashes de
origen, catálogo y fecha del recálculo. El resultado retrospectivo no afirma que
esos precios regían el día original. Nunca sobrescribe salidas existentes.
Registros antiguos que no conservaron escrituras de Luna seguirán con costo null:
ese dato no puede recuperarse del total ni inventarse. Los tokens conocidos sí se
resumen. No copiar tickets, respuestas o campos desconocidos al reporte de recálculo.

Las verificaciones de costos y recálculo están en la
[bitácora](bitacora/VERIFICACIONES.md#precios-05112026).
