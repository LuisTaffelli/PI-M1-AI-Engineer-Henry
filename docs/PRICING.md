# Estimación offline de costo de tokens — 04/11/2026

El cálculo usa Decimal y tarifas explícitas, versionadas, en USD por millón de
tokens. No se incorporó ningún precio comercial ni se verificó una tarifa en esta
tanda. pricing.example.json tiene rates=[] y Settings.pricing_path es None por
defecto: los requests siguen con cost_usd=null hasta configurar datos suficientes.
No se llama a APIs de modelos ni se consulta facturación para calcular una estimación.

## Qué se calcula

```text
costo = ((entrada_total - entrada_cacheada) × precio_entrada
         + entrada_cacheada × precio_entrada_cacheada
         + salida_normalizada × precio_salida) / 1_000_000
```

La caché es parte de la entrada, no tokens adicionales. OpenAI se lee de
usage.input_tokens_details.cached_tokens; Gemini, de usage.total_cached_tokens.
Un contador ausente/incorrecto queda null, no se supone cero. Fuentes de campos:
[OpenAI usage](https://openai.github.io/openai-agents-python/ref/usage/) e
[Interactions Usage](https://aistudio.google.com/api-reference/interactions-api).
La salida de Gemini ya incluye pensamiento normalizado cuando reconcilia con su
total; OpenAI ya lo incluye en output_tokens. No se suma otra vez para precio.

Se calcula cada intento y después se suman con Decimal **sin redondeo por intento**.
El JSON de métricas guarda cost_usd y cost_by_attempt como strings decimales exactos
o null; no float binario. Por ejemplo, quien procese el JSON puede usar
Decimal(record["cost_usd"]). Esta elección es interna de métricas: la CLI conserva
los cuatro campos answer/confidence/category/actions.

Ejemplo ficticio usado en tests, no tarifa comercial ni cargo observado: entrada
USD2.00/MTok, entrada cacheada0.50, salida4.00. Un intento con100 entrada (40cacheados)
y20 salida da USD0.000220; otro con200 entrada (50cacheados) y30 salida da
USD0.000445; total USD0.000665. El primero puede fallar JSON y aun así consume los
tokens que informó su fixture. No se ejecutó ninguna solicitud real para el ejemplo.

## Catálogo y configuración

La configuración efectiva es TOML; pricing_path es opcional y relativo a la raíz
del proyecto, como metrics_path. También se admiten rutas absolutas explícitas.

```toml
# Añadir sólo cuando exista un catálogo revisado; no carga claves ni llama una API.
pricing_path = "pricing.json"
```

pricing.example.json documenta el formato vacío sin activar precios. Una entrada
de **prueba**, deliberadamente ficticia y sin modelos comerciales, tiene esta forma:

```json
{
  "format_version": 1,
  "catalog_version": "fixture-catalog-v1",
  "rates": [
    {
      "provider": "openai",
      "model": "fixture-model",
      "mode": "standard_text",
      "currency": "USD",
      "rate_version": "fixture-only-v1",
      "verification": "fixture",
      "source_url": "https://example.invalid/fixture-only",
      "checked_on": null,
      "input_usd_per_million": "2.00",
      "cached_input_usd_per_million": "0.50",
      "output_usd_per_million": "4.00"
    }
  ]
}
```

No sirve para cotizar modelos reales. Fixture sólo habilita cálculo si la llamada
es explícitamente una inyección de prueba (simulated=true); la ruta normal del
servicio rechaza esa tarifa y conserva null. verification=unverified no se usa ni
siquiera con esa inyección. Los tests también comprueban este bloqueo.

Para una tarifa comercial futura, una persona debe verificar importes/condiciones
contra una fuente oficial y recién entonces registrar verification=verified_public,
source_url HTTPS oficial y checked_on con fecha ISO. El programa valida esos
metadatos, **no lee la página ni prueba que el importe sea verdadero o vigente**.
No se hacen actualizaciones automáticas ni se certifica vigencia por tener fecha.
Al actualizar una tarifa se cambia su rate_version y la catalog_version, sin
sobrescribir la evidencia histórica de corridas anteriores. Los logs incluyen
ambas versiones y SHA256 del archivo para identificar exactamente la tabla usada.
No copian el catálogo, sus URLs, rutas de archivo o errores de parsing al JSONL.

La selección exige coincidencia exacta provider/model/mode; no adivina precios de
aliases o modelos parecidos. No admite duplicados, moneda distinta de USD ni modos
batch/flex/priority. Los importes deben ser strings decimales no negativos de hasta
9 dígitos enteros y12 decimales; rechaza floats/números JSON, NaN/infinito/exponentes.
El archivo es JSON de datos; no se ejecuta código ni se interpreta .env como catálogo.
No se agrega un SDK o dependencia nueva.

## Estados y datos incompletos

| cost_status | Resultado |
|---|---|
| not_requested | No hubo intentos de generación; sin costo calculado. |
| pricing_unconfigured | pricing_path sin configurar. |
| pricing_unavailable | Archivo ausente, ilegible o catálogo inválido; sin mensaje/cuerpo crudo. |
| rate_missing | No hay entrada exacta para proveedor/modelo/modalidad. |
| rate_unverified | Tarifa no verificada o fixture fuera del flujo simulado explícito. |
| usage_unavailable | Ningún intento tiene contadores suficientes para precio. |
| partial | Algunos intentos calculables y otros no; total null, detalle conocido conservado. |
| fixture_estimate | Todos calculables con precios ficticios: sólo prueba simulada. |
| estimated | Todos calculables con una tarifa declarada verificada; es estimación, no factura. |

Los totales de tokens pueden estar completos (usage_status=reported) mientras falta
caché: en ese caso el costo permanece desconocido. No se elimina el intento que
falla validación o extracción; el uso que informa también entra al cálculo. Si
falta uso de un intento, no se presenta el subtotal conocido como total de request.
Un catálogo inválido no convierte una respuesta válida en error ni reemplaza el
error original del proveedor/validador. El writer JSONL mantiene su comportamiento
append-only y puede informar un fallo propio de almacenamiento.

## Estimación frente a cargo real

cost_basis=standard_text_tokens_only limita el alcance a las tres tarifas de
**tokens de texto estándar y precio fijo**. No comprende impuestos, créditos,
promociones, nivel gratuito de cuenta, almacenamiento/escritura de caché,
herramientas, multimodalidad, cargos fijos ni precios por tramos de contexto.
No se deben marcar compatibles/verificadas tarifas que necesiten esas reglas sin
implementarlas primero. Tampoco comprueba el service tier real ni lee saldo:
se declara una hipótesis de precio estándar, no el importe debitado por el proveedor.
No se presume que Gemini sea gratis. Un resultado null es desconocimiento; cero
sólo puede salir de datos completos y una tarifa admitida, nunca de la ausencia.

## Comprobación offline

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -p test_pricing.py -v
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -q
.venv/bin/ruff check --no-cache src evals tests
.venv/bin/ruff format --check --no-cache src evals tests
```

La tanda agrega14tests y conserva los101 anteriores:115 en total. Prueba precisión
Decimal bajo contexto reducido, cache0/parcial/total/inválida, versiones/hash,
tarifa no verificada, falta de archivo/usage, catálogo inválido sin ocultar errores,
retry/agotamiento/incomplete, privacidad y bloqueo de precios ficticios en la ruta
normal. Sólo hay transportes/entornos falsos; no verifica precios ni comportamiento
real de proveedores. No se publican métricas locales ni claves.
