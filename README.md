# Nubbix Support

Una CLI en Python que recibe consultas de soporte, las clasifica y propone una
respuesta y acciones para un agente humano. **No ejecuta esas acciones.**

El proyecto compara cómo distintos modelos interpretan los mismos tickets frente
a lo esperado. Conservamos prompts y resultados, incluidos los errores, sin ajustar
las versiones para que todo salga bien.

## Probarlo sin APIs

Necesitás Python 3.12 o superior. En un clon nuevo, desde la raíz del repositorio:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
make check
python -m src.main 'Me cobraron dos veces este mes.' --provider mock --mock-scenario fixed --no-metrics
```

El último comando no usa un modelo ni claves. Devuelve este JSON en stdout y un
aviso de simulación en stderr:

```json
{
  "answer": "SIMULACIÓN: recibimos tu consulta; un agente humano debe revisarla.",
  "confidence": 0.0,
  "category": "other",
  "actions": ["Revisar manualmente la consulta y asignar la categoría correcta."]
}
```

El mock siempre devuelve `other`: sirve para probar el recorrido, no para medir
clasificación. Con modelos, las categorías son `billing`, `technical`, `account`
y `other`; `confidence` es una estimación del modelo, no una probabilidad calibrada.

La consulta admite hasta **500 caracteres del texto original**, incluidos espacios
y saltos de línea. Se cuentan puntos de código Unicode, no tokens ni caracteres
visuales. Si supera el límite, se rechaza sin truncarla ni enviarla al proveedor;
`max_query_chars` permite reducirlo. Ver [detalle del guardrail](docs/ARQUITECTURA.md#límite-de-la-consulta).

## Consultar con un modelo

Desde la raíz y con `.venv` activo. OpenAI/Gemini necesitan su clave en el entorno
o en `.env` local; la carga es automática, no ejecutes ese archivo ni lo publiques.
Ollama necesita el servicio local y el modelo ya instalado. Estos IDs se usaron
en el proyecto, pero su disponibilidad depende de tu cuenta/equipo.

**Estos comandos sí generan respuestas y los remotos pueden tener costo.**
`--http-max-attempts 3` habilita hasta dos retries ante errores HTTP transitorios,
con Retry-After de hasta 30 s por espera y 60 s acumulados sólo de espera.
El tiempo de red se suma: tres respuestas de 20 s más dos esperas de 10 s suman
80 s. El timeout de E/S es 30 s, no un plazo máximo para toda la consulta.

```bash
python -m src.main 'Me cobraron dos veces este mes.' \
  --provider openai --model gpt-6-luna --prompt v3_structured --http-max-attempts 3

python -m src.main 'Me cobraron dos veces este mes.' \
  --provider gemini --model gemini-3.5-flash-lite --prompt v3_structured --http-max-attempts 3

python -m src.main 'Me cobraron dos veces este mes.' \
  --provider ollama --model qwen2.5-coder:0.5b-test --prompt v3_structured
```

El TOML permite dos rondas para reparar JSON inválido: con tres intentos HTTP,
una consulta remota puede invocar al proveedor hasta seis veces. No se reintentan
timeouts ni respuestas incompletas. Por defecto el retry HTTP está desactivado;
[opciones, privacidad y costos](docs/REINTENTOS_HTTP.md).

## Evaluar datasets y ataques

Todas las salidas deben ir a un directorio **nuevo**. Los runners conservan plan,
métricas, resultados y resumen; no sobrescriben una corrida ni la reanudan solos.

### Corpus base: 32 tickets

Estos tres comandos son **previews sin red ni lectura de claves**. Usan v3 y una
ronda por caso. Cambiá el nombre de salida para cada experimento.

```bash
python -m evals.run_provider_evals --provider openai --model gpt-6-luna \
  --prompt v3_structured --all-cases --max-attempts 1 --http-max-attempts 1 \
  --max-calls 32 --output data/local_runs/openai-v3-base

python -m evals.run_provider_evals --provider gemini --model gemini-3.5-flash-lite \
  --prompt v3_structured --all-cases --max-attempts 1 --http-max-attempts 1 \
  --max-calls 32 --output data/local_runs/gemini-v3-base

python -m evals.run_provider_evals --provider ollama --model qwen2.5-coder:0.5b-test \
  --prompt v3_structured --all-cases --max-attempts 1 --http-max-attempts 1 \
  --max-calls 32 --output data/local_runs/ollama-v3-base
```

Para **ejecutar** el comando revisado, añadí:
- OpenAI/Gemini: `--execute --allow-remote-inference` (puede generar cargos).
- Ollama: `--execute` (inferencia local, sin descargar modelos).

Para comparar los cuatro prompts, reemplazá `--prompt v3_structured` por
`--prompt v1_zero_shot --prompt v2_few_shot --prompt v3_structured --prompt v4_reasoning`
y usá `--max-calls 128`. Para habilitar retry remoto cambiá
`--http-max-attempts 1` a `3`: reservá 96 llamadas con un prompt o 384 con los cuatro.
La cota de llamadas **no es un límite monetario**.

### Paráfrasis: ocho casos complementarios

Mismo runner y permisos. El corpus pequeño requiere `--diagnostic-suite`:

```bash
python -m evals.run_provider_evals --provider openai --model gpt-6-luna \
  --dataset data/eval_robustness.jsonl --diagnostic-suite --all-cases \
  --prompt v3_structured --max-attempts 1 --http-max-attempts 1 \
  --max-calls 8 --output data/local_runs/openai-v3-parafrasis
```

Podés cambiar proveedor/modelo por los de los ejemplos anteriores. Con cuatro
prompts reservá 32 llamadas; con retry remoto de tres intentos, 24 o 96. No es un
holdout independiente ni una prueba de seguridad.

### Adversariales: pares limpios y atacados

Usan los mismos doce pares y seis controles: 30 llamadas de servicio por prompt.
No reparan salidas JSON inválidas. Estos comandos también son previews:

```bash
python -m evals.run_adversarial_pairs --provider openai --model gpt-6-luna \
  --prompt v3_structured --http-max-attempts 1 --max-calls 30 \
  --output data/local_runs/openai-v3-pareados \
  --pricing pricing/standard-text-2026-11-05.json

python -m evals.run_adversarial_pairs --provider gemini --model gemini-3.5-flash-lite \
  --prompt v3_structured --http-max-attempts 1 --max-calls 30 \
  --output data/local_runs/gemini-v3-pareados \
  --pricing pricing/standard-text-2026-11-05.json

python -m evals.run_adversarial_pairs --provider ollama --model qwen2.5-coder:0.5b-test \
  --prompt v3_structured --http-max-attempts 1 --max-calls 30 \
  --output data/local_runs/ollama-v3-pareados
```

Para ejecutar, agregá `--execute --allow-remote-inference` en remotos, o
`--execute --allow-local-inference` en Ollama. Con cuatro prompts reservá 120;
con tres intentos HTTP remotos, 90 para un prompt o 360 para los cuatro.
Los prebloqueos no llaman al modelo. Cero redirecciones observadas no prueba
seguridad general; [protocolo, denominadores y límites](docs/SEGURIDAD_PAREADA.md).

Para validar mecánica sin modelos usá `make check`. También podés elegir
`--provider mock` sin `--model` en los runners; su salida es simulada y no mide
calidad. Detalles de selección por ID, parámetros, fallos y costos en la
[guía de evaluaciones](docs/EVALUACION_PROVEEDORES.md).

## Qué comparamos

Hay adaptadores para OpenAI, Gemini y Ollama, además del mock; cuatro prompts YAML;
32 tickets sintéticos y ocho paráfrasis relacionadas. En la corrida local del
04/11/2026 con Qwen coder 0.5B, un intento y 256 tokens de salida:

| Prompt | Coincidencias en 32 tickets | Salidas válidas |
|---|---:|---:|
| v1: zero-shot | 11/32 | 31/32 |
| v2: few-shot | 18/32 | 30/32 |
| v3: estructurado | 17/32 | 32/32 |
| v4: deliberación | 13/32 | 30/32 |

Los fallos se incluyen en el total. Luis revisó y confirmó las 32 referencias del
corpus base el 05/11; esto no es un holdout ni un ranking general de modelos.
El [informe de variantes](docs/PROMPTS_V3_V4.md) detalla categorías, paráfrasis y
condiciones; la [revisión de desacuerdos](docs/REVISION_DESACUERDOS.md) explica casos concretos.

La [tanda remota del 06/11](docs/EVALS_REMOTOS_2026-11-06.md) conserva resultados
posteriores: OpenAI obtuvo 32/32, 32/32, 31/32 y 30/32 en el corpus base; v4 incluye
dos fallos de proveedor, sin repetirlos. Gemini quedó parcial por HTTP 429.
Las ocho paráfrasis coincidieron en cada prompt de OpenAI. El informe separa
calidad, validez, seguridad y subtotal conocido de costo total desconocido.
Estos experimentos se ejecutaron antes de incorporar los retries HTTP.

### Qué prompt elegiríamos hoy

Para **OpenAI con `gpt-6-luna` elegiríamos `v2_few_shot` como candidato
provisional**. En la tanda del 06/11 acertó 32/32, igual que v1, con menor
latencia mediana observada: **1,93 s frente a 2,23 s**. También acertó las ocho
paráfrasis; en los ataques pareados no observamos diferencias entre las cuatro
versiones. V3 obtuvo 31/32 y v4 30/32, con dos fallos de proveedor incluidos.

Es una elección para este modelo y esta muestra, no un ganador universal: hubo
una pasada, el corpus es conocido y las paráfrasis no son un holdout independiente.
Gemini sigue sin comparación completa. Tras las dos tandas parciales por 429,
[la excepción acotada del 07/11](docs/EXCEPCION_GEMINI_2026-11-07.md) completó
adversarial y base v1–v3 (30/32, 32/32 y 32/32). Base v4 se frenó en un HTTP 503
tras tres intentos; las paráfrasis no se iniciaron. V3 mostró una redirección
adversarial entre seis ataques admitidos y válidos. Ollama mostró otro equilibrio entre aciertos y validez.
No se evaluó aquí la calidad completa de las respuestas ni la seguridad general.
La recomendación no cambia automáticamente el prompt configurado ni los ejemplos.

Las [11 corridas citadas explícitamente](docs/evidencia/CORRIDAS.md) conservan
planes, `metrics.jsonl`, `results.jsonl` y resúmenes originales, incluidos horarios
y fallos. Los tres manifiestos SHA-256 y su verificador permiten revisar la
selección sin volver a llamar a ningún proveedor. Incluye la corrida Gemini de
retry y las dos de excepción 120/300, cada tanda con su manifiesto independiente.
Ver [criterios y resultados por proveedor](docs/RECOMENDACIONES_PROMPTS_PROVEEDOR.md).

Para repetir con otro proveedor, consultá la [guía de evaluaciones](docs/EVALUACION_PROVEEDORES.md).
La [suite adversarial pareada](docs/SEGURIDAD_PAREADA.md#repetición-acotada-con-distintos-proveedores--05112026)
también admite Ollama, Gemini y OpenAI, con preview offline y un mock de prueba.
Las llamadas remotas requieren habilitación explícita y pueden tener costo.
La cota de llamadas no es un tope de gasto; los guardrails tampoco garantizan seguridad completa.

## Guías y bitácora

- [Pruebas por responsabilidad](tests/README.md): carpetas y comandos para ejecutar toda la suite o un grupo.
- [Instalación y reproducción](docs/REPRODUCIBILIDAD.md), [claves locales](docs/CLAVES_LOCALES.md) y [Ollama](docs/OLLAMA.md).
- [Arquitectura](docs/ARQUITECTURA.md) y [tokens y costos](docs/PRICING.md).
- [Dataset y criterios](data/DATASET.md), [etiquetas revisadas](docs/REVISION_ETIQUETAS.md) y [seguridad](docs/SEGURIDAD_PAREADA.md).
- [Uso de IA](docs/USO_IA.md), [muestras de métricas](docs/METRICAS_EJEMPLOS.md) y [cierre de entrega](docs/CIERRE_ENTREGA.md).
- [Bitácora del proyecto](docs/BITACORA.md): cambios, decisiones, verificaciones y registros anteriores.

La consigna oficial se contrastó el 07/11/2026. La Evaluación admite la comparativa
de modelos como extra; el [cierre de entrega](docs/CIERRE_ENTREGA.md#consigna-oficial-contrastada--07112026)
registra requisitos, la diferencia con la guía y el calendario sin zona horaria.
Esta revisión no garantiza una nota ni acredita la presentación académica.

## Evidencia original versionada

Las [11 corridas citadas](docs/evidencia/CORRIDAS.md) se conservan directamente en
`data/local_runs/`: 56 archivos y 620 resultados, sin mirror. Los tres manifiestos
y el verificador permiten comprobarlos offline; otras salidas siguen ignoradas.
