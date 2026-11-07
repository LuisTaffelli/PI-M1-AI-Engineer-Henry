# Reintentos HTTP acotados

Esta mejora es posterior a las [corridas remotas del 06/11](EVALS_REMOTOS_2026-11-06.md).
No las reescribe, reanuda ni cambia sus prompts. La implementación se verificó con
transportes falsos, claves ficticias y sleeps sustituidos. Después se usó en las
[tandas Gemini](EVALS_GEMINI_RETRY_2026-11-07.md), conservadas por separado; la
[última tanda](EXCEPCION_GEMINI_2026-11-07.md) quedó parcial y está cerrada, sin
nuevas inferencias ni reanudación programada.

## Activación y límites

Por defecto `http_max_attempts = 1`: no hay retry HTTP. Se activa explícitamente con
`--http-max-attempts 2` o `3` en la CLI de soporte y los dos runners multiproveedor,
o con la misma opción en TOML. El flag prevalece sobre el TOML. Afecta únicamente a
OpenAI y Gemini, no a Ollama ni al mock.

```toml
http_max_attempts = 1
http_retry_max_delay_seconds = 30.0
http_retry_max_total_wait_seconds = 60.0
```

- Hasta **3 intentos HTTP por ronda de generación**, incluido el primero.
- Hasta **30 segundos por espera** y **60 segundos acumulados por consulta de
  servicio**, compartidos entre las reparaciones de JSON. Los dos límites de
  espera pueden reducirse en TOML. Ampliarlos requiere la excepción de suite Gemini
  descrita abajo; no cambia estos defaults. No son un timeout global:
  se suman al tiempo de cada petición HTTP (timeout de E/S remoto de 30 s,
  que tampoco es un plazo de extremo a extremo). Por ejemplo, tres respuestas
  recibidas en 20 s cada una más dos esperas de 10 s suman 80 s.
- Sólo se reintentan **429, 500, 502, 503 y 504**. Un 429 puede representar una
  cuota persistente; estos retries no garantizan recuperarla ni diagnostican su causa.
- `Retry-After` admite delta-segundos enteros no negativos o una fecha HTTP.
  También admite formatos obsoletos RFC 850 y asctime (GMT implícita). Las fechas usan el reloj UTC local y redondean hacia arriba; una fecha
  vencida permite retry inmediato. Un reloj local incorrecto puede afectar la espera.
- Si el servidor pide más de 30 s, o más del límite configurado/restante, se
  conserva el error y se termina. **No se recorta la espera para reintentar antes.**
- Sin header válido se usa backoff de 1 y 2 s, más jitter entre 0 y 0,25 s,
  siempre sujeto a los límites. Un delta mayor al techo se reconoce como excesivo,
  no como header ausente. Valores negativos, fraccionarios o malformados son inválidos.

No se reintentan 400/401/403/404 ni otros códigos fuera de la lista, timeouts,
conexión interrumpida, JSON HTTP inválido, respuestas incompletas, refusals ni
rechazos de guardrails. Un timeout puede ocultar una generación ya consumida;
no se presupone idempotencia ni se repite una operación de resultado incierto.
Tampoco se cambia de proveedor, se aumenta el límite de tokens ni se modifica el prompt.

## Dos tipos de intento, una cota visible

`max_attempts` sigue controlando las rondas de generación para reparar JSON/contrato
inválido. `http_max_attempts` controla sólo los errores HTTP dentro de cada ronda.
Cada llamada de `Provider.generate` hace una única petición de generación. El
servicio repite instrucciones y consulta idénticas en retry HTTP; sólo una salida
JSON/contrato inválida habilita el feedback de reparación ya existente.

La cota del runner de clasificación es:

`casos × prompts × max_attempts × http_max_attempts <= max_calls <= 384`.

Para mock/Ollama el factor HTTP vale 1. El runner pareado fuerza una sola ronda
sin reparación JSON: `30 × prompts × http_max_attempts`, hasta 384. Un prebloqueo
no llama al proveedor, pero el plan reserva el peor caso sin anticipar bloqueos.
Con cuatro prompts y tres intentos HTTP: base 32 requiere 384, paráfrasis 8 requiere
96, y pareados requiere 360. Sin retry: 128, 32 y 120 respectivamente.

Ejemplo **preview sin red ni lectura de claves** de un caso con retry habilitado:

```bash
python -m evals.run_provider_evals --provider gemini \
  --model gemini-3.5-flash-lite --prompt v3_structured \
  --case-id nubbix-b01 --max-attempts 1 --http-max-attempts 3 \
  --max-calls 3 --output data/local_runs/gemini-retry-preview
```

Sólo agregar `--execute --allow-remote-inference` ejecuta ese plan remoto y puede
producir cargos. Usar una salida nueva, revisar modelo/permisos y no relanzar a
ciegas una corrida parcial. Los modelos de ejemplo requieren acceso de la cuenta.

**No es un tope monetario ni de todo el tráfico HTTP** (por ejemplo redirecciones
internas de urllib o el `/api/show` local de Ollama). Cada retry puede consumir
cuota o generar costo, aunque la respuesta de error no informe tokens.

## Métricas y errores seguros

- `attempts` y `usage_by_attempt` cuentan todas las invocaciones, incluidos los
  errores HTTP. Un fallo sin usage queda desconocido, no con cero tokens/costo.
  Una recuperación puede tener `status=ok` y consumo/costo sólo parcial.
- `http_retry_count` cuenta los reintentos realizados. `http_retry_wait_seconds`
  suma las esperas solicitadas que completaron; no mide el tiempo exacto dormido.
  `latency_seconds` incluye las esperas y toda la orquestación.
- `http_retry_events` conserva sólo status numérico, estado normalizado del header
  (`missing`, `invalid`, `valid`, `too_long`), segundos normalizados solicitados,
  demora acotada, si se reintentó y una
  razón local de detención. No conserva el valor crudo de Retry-After ni otros
  headers, URL, reason, cuerpo de error, consulta, prompt, salida o clave.
- `failure_http_status` y `failure_code` describen el fallo terminal; quedan `null`
  después de recuperarse. OpenAI ahora comparte los diagnósticos seguros de Gemini,
  incluidos `http_error`, `transport_error`, `http_json_invalid` e `incomplete_response`.
- Los resúmenes nuevos incluyen cantidad y espera de retries. Los planes registran
  opciones y cotas, además de hashes. Plan de clasificación: formato 2; pareado: 3.
  Las corridas anteriores conservan sus versiones y valores originales.
- El CLI pareado devuelve **2** si termina con fallo de proveedor/configuración,
  aunque el fallo ocurra en el último caso y la cobertura sea completa. Cobertura
  completa no significa éxito. Código 0 tampoco certifica seguridad ni calidad.

## Comprobación offline

```bash
python -m unittest discover -s tests -p 'test_http_retry.py' -v
make check
```

Las regresiones cubren fechas/deltas, límites, agotamiento, ambos adaptadores,
privacidad, uso/costo desconocido, separación de reparación, planes, permisos y
el fallo del último caso. No recuperan detalles ausentes de errores históricos.

## Excepción explícita para la suite Gemini — 07/11/2026

Luis autorizó para esta tanda hasta **120 s por espera**, **300 s acumulados por
consulta** y **3 intentos en total**. Sólo los runners de evaluación admiten el
flag `--gemini-suite-retry-exception`, junto con `--http-max-attempts 3`. La excepción
no activa retries por sí sola ni modifica `config.toml`: sin opt-in siguen 1 intento,
30 s por espera y 60 s acumulados. Se rechaza con otro proveedor, reparación JSON
(`max_attempts` distinto de 1) o `--continue-on-error`. La CLI de consulta individual
rechaza una configuración con la excepción.

El flag establece los techos aprobados. También se puede usar un TOML de evaluación
separado con `provider = "gemini"`, modelo explícito, `max_attempts = 1`,
`gemini_suite_retry_exception = true`, `http_max_attempts = 3`,
`http_retry_max_delay_seconds = 120.0` y `http_retry_max_total_wait_seconds = 300.0`.
En TOML los techos pueden reducirse. El flag CLI explícito prevalece sobre el TOML.
Con tres intentos y una sola ronda sólo caben dos esperas: su máximo práctico es
240 s, menor al presupuesto de 300 s. Los tiempos de red se suman por separado.

Se conserva `retry_after_seconds` como entero normalizado, también si excede
120 s y el request aborta. Fechas HTTP se convierten a segundos con redondeo hacia
arriba; no se guarda el header original. Para un valor patológico de más de 1.000
dígitos sólo se guarda `retry_after_seconds_digits`, se marca `too_long` y se aborta
sin convertirlo, almacenarlo completo ni reintentar. Si falta o es inválido, el campo
queda `null`. No se guardan claves, cuerpo, URL, reason ni otros headers.

Los defaults y las corridas anteriores permanecen intactos. Los nuevos planes
incluyen el opt-in y sus límites, manteniendo las cotas de 360 llamadas para
adversarial v1–v4, 384 para base32 y 96 para robustness8. La excepción no amplía los
estados HTTP reintentables, no reintenta timeouts y no implica éxito ni gasto conocido.
La nueva evidencia y resultados se conservan por separado.
