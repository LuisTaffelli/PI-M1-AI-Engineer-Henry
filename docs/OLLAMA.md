# Ollama como proveedor local — 04/11/2026

Ollama se agrega a la misma interfaz GenerationResult(text, TokenUsage) usada por
OpenAI y Gemini. El servicio sigue aplicando contrato Pydantic, retry acotado y
guardrail. Ningún cambio en los adaptadores de los otros proveedores: no se cambian
sus requests, claves o modelos. Mock sigue siendo el predeterminado.

## Disponibilidad comprobada, no supuesta

El inventario del servidor local confirmó qwen2.5-coder:7b (GGUF Q4_K_M, unos 4,68 GB)
y variantes 0.5B ya importadas en GGUF F16 (unos 994 MB). Para una prueba pequeña se
eligió qwen2.5-coder:0.5b-test. Es un tag presente en este equipo, no una garantía
de que exista en otro ni un nombre para descargar automáticamente del registro.
La presencia de archivos safetensors por sí sola no acredita una importación;
en este caso /api/tags y /api/show sí confirmaron el modelo local generativo.
No se importaron, convirtieron o descargaron pesos ni se modificó Ollama.

Antes de usar un tag en otra máquina, comprobar la instancia local:

```bash
OLLAMA_HOST=http://127.0.0.1:11434 ollama list
```

No hay un proveedor comercial ni un modelo local impuestos por la consigna. Esta
integración es una decisión nuestra para experimentar; no reemplaza comparar los
prompts sobre etiquetas revisadas ni certifica el cumplimiento de dos proveedores
comerciales. Las categorías de Nubbix se conservan sin cambios.

## Configuración y ejecución explícita

```bash
.venv/bin/python -m src.main 'Consulta sintética' --config config.ollama.example.toml
```

Este comando sí hace inferencia local; no es un unit test. El ejemplo elige un
modelo ya importado, prompt v1, un intento total y 256 tokens máximos de salida.
La URL/num_ctx/timeout están en TOML. También se puede seleccionar --provider ollama
--model TAG con la configuración base; allí max_attempts conserva su valor 2, por
lo que un error de JSON podría causar una segunda generación local. No hay retry
HTTP ni descarga automática ante modelo ausente.

| Campo TOML | Default técnico |
|---|---|
| ollama_base_url | http://127.0.0.1:11434 |
| ollama_max_output_tokens | 256; permitido 16..4096 |
| ollama_num_ctx | 2048; permitido 512..16384 |
| ollama_timeout_seconds | 120; permitido 1..300 por generación HTTP |

El contexto está acotado para esta muestra pequeña; no se ha validado una política
para consultas enormes o truncamiento del contexto. No se recomienda usar esos
límites como prueba de que cualquier entrada cabe en el modelo.

## Recorrido y límites de conexión

1. Config/constructor aceptan HTTP con loopback y puerto explícito: 127.0.0.1,
   localhost (se normaliza a 127.0.0.1) o ::1. Rechazan hosts externos, credenciales
   en URL, paths ajenos, query o fragmentos. El transporte omite proxies del entorno
   y no sigue redirects. No consulta .env ni usa ninguna API key.
2. Cada generate consulta POST /api/show para comprobar GGUF y capacidad completion.
   Rechaza tags con cloud y metadatos remote_host/remote_model, además de formatos
   desconocidos. Es un control contra uso remoto accidental en un servidor local
   de confianza; no una auditoría de un servidor local malicioso. Ollama también
   tiene productos cloud, por eso el adaptador no acepta una URL remota.
3. Sólo después envía POST /api/chat: instrucciones de sistema y ticket separados,
   stream=false, temperature=0, num_predict y num_ctx acotados. format lleva el
   esquema generado por SupportResponse. El adaptador genérico también acepta
   format=json si no se le inyecta un esquema; el servicio siempre lo inyecta.
4. Extrae message.content de assistant, rechaza herramientas/imágenes y respuestas
   no terminadas o cortadas por longitud. No ejecuta herramientas ni código.
5. El servicio conserva model_validate_json, feedback de reparación y guardrail.
   HTTP/red/modelo no local fallan con códigos/mensajes fijos, sin cuerpos crudos.
   Un preflight fallido no genera texto. attempts cuenta invocaciones generate:
   una generación exitosa usa dos peticiones HTTP locales (show+chat), no dos LLM.

Contrato primario consultado: [Chat](https://docs.ollama.com/api/chat),
[Show](https://docs.ollama.com/api-reference/show-model-details),
[JSON Schema](https://docs.ollama.com/capabilities/structured-outputs) y
[distinción cloud/local](https://docs.ollama.com/cloud).

## Métricas y estimación

prompt_eval_count y eval_count normalizan entrada/salida; total_tokens es su suma
**derivada**, no un campo total devuelto por Ollama. Si falta uno no se inventa el
total. cached_prompt_tokens permanece null: no se equipara caché de cómputo local
con tokens de entrada cacheados de una API comercial. La prueba real local lleva
provider=ollama, simulated=false; los transportes falsos inyectados se marcan
simulados. Falso no prueba por sí solo una conexión exitosa: revisar status/attempts.
No se aplican tarifas OpenAI/Gemini a Ollama. cost_usd queda null; no se midieron
costo de electricidad/hardware ni costo unitario local. Logs sin ticket/respuesta.

## Resultado observado de una muestra local

Una generación, cero retries, qwen2.5-coder:0.5b-test, prompt v1 y ticket ficticio
sobre cobro duplicado. Etiqueta esperada billing fijada antes. Resultado account,
confidence autodeclarada 0.9; Pydantic y guardrail válidos. Latencia observada 1,250 s,
234 tokens de entrada, 42 salida, 276 total derivado. No se guarda texto de respuesta en
las métricas. **La categoría falló en este caso aunque el JSON validara.**
Una muestra no mide accuracy general ni permite elegir modelo/prompts. Las pruebas
remotas históricas con ese ticket dieron billing, pero no son un benchmark pareado:
fechas, límites de salida, tokenizadores, hardware y condiciones de carga difieren.
No se repitió el ejemplo para obtener un acierto ni se cambió su etiqueta para
favorecer al modelo. Una futura comparación requiere corpus revisado, condiciones
registradas y autorización de los requests remotos; esta etapa no los hace.

## Verificación al retomar la integración — 04/11/2026 21:27 UTC

Se conservaron los cambios pendientes y se verificaron en una copia de trabajo sin
`.env`. El inventario de Ollama volvió a confirmar el tag elegido. Se ejecutó una
sola generación local nueva con v1, un intento, 256 tokens máximos y contexto 2048.
El ticket sintético fue: «Me cobraron dos veces la suscripción de Nubbix este mes.
¿Pueden revisar el cobro duplicado?», con etiqueta `billing` fijada antes.

Resultado: `account`, confidence autodeclarada `0.9`, contrato y guardrail válidos;
1,393 s, 232 tokens de entrada, 39 de salida y 271 de total derivado. Métricas:
`provider=ollama`, `simulated=false`, `status=ok`, `attempts=1`,
`usage_status=reported`, `cached_prompt_tokens=null`, `cost_usd=null`.
El texto difiere de la muestra anterior: esta comprobación valida conectividad e
integración, no es una repetición idéntica ni una evaluación comparativa.
El modelo pequeño volvió a errar la categoría; no se lo recomienda por calidad
basándose en estas muestras. No se modificaron pesos, prompts ni etiquetas.

Se volvieron a comprobar los 126 tests offline, lint, formato y la integridad del
corpus de 32 casos. El corpus sigue pendiente de revisión humana completa y el
runner permanece limitado a mock. No hubo inferencias remotas, lectura de secretos,
nuevas dependencias ni descargas de modelos.

## Pruebas offline

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -p test_ollama_provider.py -v
make check
```

Once tests nuevos, 126 en total: requests/schema y opciones, loopback/proxy/redirect,
cloud/modelo inexistente, recursos, errores sanitizados, salidas incompletas,
validación/retry/agotamiento, métricas privadas/CLI y contadores inválidos. Ningún
unit test usa el modelo real. No hay nuevos paquetes; pesos gguf/safetensors y
métricas locales quedan ignorados. El runner de eval sigue rechazando proveedores
no mock en este checkpoint para evitar inferencia accidental por cambiar un TOML.
