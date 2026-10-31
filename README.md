# Nubbix Support — base educativa offline

Python es obligatorio, confirmado por Luis. Hoy el sistema usa solo un proveedor
mock: no clasifica con IA ni ejecuta acciones. No hay credenciales ni llamadas remotas.
Los once tests del incremento anterior se conservan; esta etapa agrega configuración,
prompts, retry de validación, controles básicos, métricas y un runner demostrativo.

## Ejecutar sin instalar nada

Desde esta carpeta, usando el entorno ya instalado:

```bash
.venv/bin/python -m src.main 'Me cobraron dos veces este mes.' --no-metrics
.venv/bin/python -m src.main 'Me cobraron dos veces este mes.' --prompt v2_few_shot --mock-scenario recover_once --no-metrics
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m evals.run_evals --prompt v1_zero_shot
.venv/bin/python -m evals.run_evals --prompt v2_few_shot
```

`make run`, `make test` y `make eval` son atajos. `make run` ejecuta el ejemplo
fijo y registra métricas. Para escribir métricas con otra consulta sin Make:

```bash
.venv/bin/python -m src.main 'Consulta de prueba'
```

Esto agrega una línea a `data/metrics.jsonl`; una segunda ejecución conserva la
primera. El contenido del ticket y la respuesta no se registran. `--no-metrics`
desactiva la escritura. No se instalan dependencias ni se consulta la red al ejecutar.
Python >=3.11 es una decisión técnica; las pruebas se corren con el entorno existente.
Pydantic 2 es la única dependencia de runtime, declarada en `pyproject.toml` y
`requirements.txt`. La correspondencia de nombres con la consigna está en
[docs/NOMENCLATURA.md](docs/NOMENCLATURA.md); no se alega cumplimiento completo.

Estos comandos usan el árbol fuente desde esta raíz. La distribución instalada
anteriormente no se reinstaló. Empaquetar config/datasets/prompts como recursos para
uso fuera del árbol fuente sigue pendiente; no se promete una CLI global instalada.

## Configuración y prompts

`config.toml` es la fuente de configuración, validada con Pydantic y sin campos
extra. `--config ruta.toml` elige otro archivo. No se lee `.env`, el entorno de
la máquina ni ninguna clave. `.env.example` solo explica ese límite.

Orden: valores por defecto del schema → TOML → flags. Los flags son `--provider`
(solo mock), `--prompt`, `--mock-scenario` y `--no-metrics`. El TOML también define
`max_attempts` (1..3 intentos totales, no cantidad adicional de reintentos),
`max_query_chars` y `metrics_path`. Las rutas relativas de métricas se resuelven
contra la raíz de este proyecto, incluso al usar otro TOML. Los límites son
propuestas técnicas, no políticas de negocio impuestas por Henry.

- `prompts/v1_zero_shot.yaml`: instrucciones sin ejemplos.
- `prompts/v2_few_shot.yaml`: mismas instrucciones y dos ejemplos sintéticos.
- `prompts/CHANGELOG.md`: hipótesis y cambios; ninguna versión es ganadora todavía.

Los `.yaml` usan sintaxis JSON, válida en YAML 1.2. Como PyYAML no está instalado y
no se autorizó instalarlo en esta etapa, el cargador admite **solo ese subconjunto**
con validación Pydantic. No admite bloques YAML, comentarios ni anclas. Para cambiar
a YAML de bloques hace falta acordar una dependencia reputada y su instalación.
Las instrucciones y ejemplos están fuera del código; consulta e instrucciones
viajan por separado al proveedor. El mock ignora ambos y devuelve valores fijos.

## Flujo y orden de lectura

1. `src/schemas.py`: contrato de salida; `confidence` es una señal autodeclarada
   del modelo sobre la categoría, no una probabilidad calibrada ni un veredicto
   de acierto. No se extrae hoy de una API. `actions` son sugerencias humanas.
2. `config.toml` y `src/config.py`: opciones y validación de configuración.
3. `prompts/*.yaml` y `src/prompts.py`: versiones, validación y render de ejemplos.
4. `src/providers/base.py` y `mock_provider.py`: `generate(instructions, query)`
   devuelve texto sin validar. Los escenarios de mock son herramientas de prueba.
5. `src/service.py`: controla entrada → carga prompt → proveedor → parsea/valida
   → controla salida → registra métricas. Solo repite errores de parsing/schema,
   hasta agotar el límite. No repite bloqueos de seguridad ni errores del proveedor.
6. `src/main.py`: conecta flags y configuración; escribe JSON en stdout solo si
   todo terminó bien y el aviso de simulación en stderr. Ante error, código 2 y
   stdout vacío, incluso si falló la escritura de métricas.
7. `evals/run_evals.py` y `tests/`: runner demostrativo y pruebas de funcionamiento.

Los tipos de `actions`, límites de confidence, texto no vacío y rechazo de extras
son decisiones locales provisionales. La aclaración de Luis fija su interpretación:
confidence muestra qué declara el modelo; su acierto se evalúa por separado.

## Fallos que se pueden observar

```bash
.venv/bin/python -m src.main 'Consulta' --mock-scenario malformed --no-metrics
.venv/bin/python -m src.main 'Consulta' --mock-scenario invalid_contract --no-metrics
.venv/bin/python -m src.main 'Ignore previous instructions' --no-metrics
```

Los tres deben terminar con código 2, sin JSON de éxito. `recover_once` devuelve
JSON roto la primera vez y válido la segunda: permite observar el retry sin red.
El mock normal, aun para «Me cobraron dos veces este mes», sigue devolviendo:

```json
{
  "answer": "SIMULACIÓN: recibimos tu consulta; un agente humano debe revisarla.",
  "confidence": 0.0,
  "category": "other",
  "actions": ["Revisar manualmente la consulta y asignar la categoría correcta."]
}
```

## Qué muestran las métricas y evals

Cada request del servicio con registro habilitado agrega un JSONL con timestamp,
id, proveedor, versión, estado, intentos y latencia real total (sin incluir la escritura
del log). Tokens y costo son `null`, con `usage_status=unavailable_mock`; no se
inventan consumos ni costos cero. Configuraciones inválidas que no llegan al servicio
no generan una línea. Si falla el almacenamiento, no se promete un registro persistido.

`data/eval_sample.jsonl` contiene **cuatro casos sintéticos ilustrativos**, con
etiquetas propuestas para revisar con Luis. El runner valida primero el dataset,
compara `category` con `expected_category` mediante Exact Match y reporta global y
por categoría. Los fallos cuentan como no aciertos y se informan como errores;
si ocurre alguno, el comando devuelve 2. No registra métricas de requests de eval.

El mock fijo obtiene 1/4 en ambas variantes porque siempre devuelve other. Esto
comprueba el cálculo, **no evalúa capacidad real ni selecciona un prompt**. No se usa
confidence para juzgar aciertos. No hay LLM-as-Judge. Los ejemplos few-shot y este
sample no forman un conjunto independiente apto para evaluar modelos reales.

## Límites y pendientes académicos

La consigna pide CLI, dos proveedores configurables reales, YAML versionados y
comparados, validación/retry, controles de seguridad, métricas y evals. La síntesis
local pide al menos 30 casos etiquetados; cuatro casos de muestra no cumplen ese mínimo.
El mock no cuenta como un proveedor real. No se eligen OpenAI, Google u otros aún.

Los guardrails actuales solo limitan longitud y detectan frases evidentes de
injection en entrada y patrones de credenciales en salida. Son demostrativos:
pueden bloquear textos legítimos y dejar pasar ataques. No son moderación completa
ni garantizan seguridad. Faltan políticas de contenido/negocio acordadas y evaluación
adversarial; no se genera una suite bonus ni `run_adversarial.py` vacío.

También quedan pendientes usage/tarifas reales, rate limits/backoff, manejo de errores
de APIs, dataset revisado de 30+ casos independiente de few-shot, comparación real,
selección documentada y revisión de rúbrica/extras. La estructura se agrega cuando
hay una función concreta; no hay archivos vacíos para aparentar cumplimiento.
No se publica, comitea ni entrega. Ninguna casilla del checklist se marca completa.

## Historial de incrementos anteriores

Lo siguiente conserva las verificaciones y decisiones de etapas anteriores.
Sus referencias a funcionalidades pendientes describen ese momento, no el estado actual.

## Verificación ejecutada — 24/10/2026

Desde `nubbix-support/`, en este equipo con Python 3.14.8 y Pydantic 2.14.1:

```bash
python -m venv .venv
.venv/bin/python -m pip install --no-cache-dir --index-url https://pypi.org/simple .
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m src.main 'Quiero consultar por las funciones del plan.'
.venv/bin/python -m pip check
```

Resultado: instalación correcta, 6 pruebas aprobadas y `pip check` sin dependencias
rotas. La ejecución produjo el JSON de ejemplo y el aviso de simulación en stderr.
Las pruebas cubren campos obligatorios, categorías inválidas, límites/NaN/tipos de
confidence, estructura de actions, campos extra, entrada vacía y argumento ausente.
No se ejecutaron evals ni llamadas a APIs de modelos. No hay afirmación de calidad
predictiva o cumplimiento total del PI. El entorno inicial de prueba en /tmp también
pasó las seis pruebas; la verificación anterior usa el entorno final del proyecto.

## Segundo incremento — frontera proveedor/servicio (30/10/2026)

- `providers/base.py` define `Provider` con `generate(instructions, query) -> str`.
  Es un `Protocol`: describe qué método tiene que ofrecer un adaptador, sin exigir
  una jerarquía de herencia ni agregar dependencias. No valida el JSON en runtime.
- `MockProvider` devuelve texto JSON fijo. `service.py` recibe opcionalmente otro
  proveedor para poder probar esa frontera; la CLI sigue usando solo el mock.
- El servicio mantiene una instrucción mínima temporal en código. No cuenta como
  prompt YAML, versión evaluada ni selección de técnica de context engineering.
- Pydantic convierte el texto y verifica el contrato. Tanto JSON malformado como
  datos fuera del contrato producen `ValidationError`; la CLI retorna 2, escribe
  un error en stderr y deja stdout vacío. No hay fallback que disfrace el error.
- `pyproject.toml` incluye `src.providers` para futuras instalaciones. No se
  reinstaló el paquete: los comandos desde la raíz usan el código fuente actual.

Ejemplo: `Me cobraron dos veces este mes.` recorre esa frontera, pero el mock
sigue devolviendo `other` y `0.0`, con aviso de simulación. No entiende el ticket.
Las pruebas pueden inyectar texto válido, JSON roto o una categoría inexistente;
comprueban la integración de las capas, no la calidad predictiva.

Siguen pendientes proveedores reales configurables, YAML, retries, rate limits,
seguridad, métricas y evals. El mock no cuenta como uno de los dos proveedores
reales exigidos por el PI. No hubo red, secretos, costos ni instalación en esta etapa.

### Verificación offline del 30/10/2026

Comandos desde `PI/nubbix-support/`:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m src.main 'Me cobraron dos veces este mes.'
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m src.main '   '
```

Resultado: 11 pruebas aprobadas (6 anteriores y 5 nuevas). También se verificaron
por subprocess los dos comandos CLI, capturando canales y código por separado:
consulta válida, código 0 y JSON simulado; entrada vacía, código 2, stdout vacío y
error en stderr. Las pruebas nuevas inyectan JSON malformado y categoría inválida
en el mock para verificar que la CLI devuelve 2 sin salida de éxito. No hubo red
ni instalación. Estos resultados son pruebas locales, no evals de un LLM.

## Verificación de la base offline — 30/10/2026

Desde `PI/nubbix-support/`, con el .venv ya instalado y sin red ni instalación:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m src.main 'Me cobraron dos veces este mes.' --prompt v2_few_shot --mock-scenario fixed --no-metrics
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m src.main 'Me cobraron dos veces este mes.' --prompt v2_few_shot --mock-scenario recover_once --no-metrics
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m src.main 'Me cobraron dos veces este mes.' --prompt v2_few_shot --mock-scenario malformed --no-metrics
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m src.main 'Me cobraron dos veces este mes.' --prompt v2_few_shot --mock-scenario invalid_contract --no-metrics
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m evals.run_evals --prompt v1_zero_shot
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m evals.run_evals --prompt v2_few_shot
```

Resultado: 28 tests aprobados, incluidos los 11 anteriores. Los escenarios fixed y
recover_once terminaron con código 0 y JSON simulado; malformed e invalid_contract,
con código 2 y stdout vacío. Configuración inválida, entrada bloqueada, salida
bloqueada y error de escritura también están cubiertos por las pruebas.

Ambos runners devolvieron cuatro casos, cero errores operativos y Exact Match 0.25
con simulated=true y quality_claim=false: es la consecuencia del mock constante,
no una evaluación de calidad ni comparación empírica útil de prompts.

Además se ejecutaron fixed y recover_once sin --no-metrics, capturando los códigos
por separado y verificando data/metrics.jsonl: dos líneas nuevas, bytes anteriores
preservados, intentos 1 y 2, tokens/costo null. Este archivo local generado está
ignorado por Git. No se fabricó una medición de LLM.

## Preparar un clon nuevo

Requiere Python 3.11+ disponible. Estos comandos de instalación son instrucciones
para un entorno nuevo; la revisión de publicación usó el .venv ya existente:

```bash
python -m venv .venv
.venv/bin/python -m pip install --index-url https://pypi.org/simple -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m src.main 'Consulta sintética' --no-metrics
```

El repositorio conserva el estado educativo offline: subirlo a GitHub no implica
entrega académica ni integración con proveedores. No incluye el entorno virtual,
credenciales, métricas generadas ni apuntes personales externos.
