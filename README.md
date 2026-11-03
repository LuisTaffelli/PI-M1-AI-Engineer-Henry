# Nubbix Support — base educativa y adaptadores HTTP en checkpoint

Python es obligatorio, confirmado por Luis. El proveedor predeterminado sigue siendo
mock. OpenAI y Gemini son seleccionables mediante adaptadores HTTP. La suite de
88 tests es offline; pruebas reales puntuales autorizadas verificaron salida válida
en OpenAI y en Gemini con esquema. Eso no evalúa calidad general ni completa el PI.
Hay 32 tickets sintéticos con etiquetas propuestas para revisar. Las acciones siguen
siendo sugerencias humanas. Los apartados de incrementos/checkpoints conservan el
estado de cada etapa; este resumen describe el estado actual del 03/11/2026.

El servicio mantiene Pydantic, retry acotado con feedback y diagnósticos seguros.
Gemini solicita JSON con el esquema de SupportResponse. Las evals permanecen sólo
mock; tokens/costos del servicio siguen sin normalizar y los registros de pruebas
remotas se conservan fuera de Git. Nivel de facturación y cargos reales no verificados.
No hay carga automática de .env ni una evaluación real comparativa de prompts.

## Organización por responsabilidad

```text
src/
├── main.py                 # entrada CLI compatible
├── support/
│   ├── schemas.py          # contrato de respuesta
│   ├── guardrails.py       # controles del caso de soporte
│   └── service.py          # recorrido y retry
├── llm/
│   ├── prompts.py          # carga/render del contexto
│   └── providers/
│       ├── base.py         # contrato del proveedor
│       ├── mock_provider.py
│       ├── openai_provider.py # HTTP Responses, sin SDK instalado
│       └── gemini_provider.py # HTTP Interactions v1beta, sin SDK instalado
└── runtime/
    ├── config.py           # configuración y raíz de recursos
    └── metrics.py          # persistencia JSONL
prompts/                    # YAML versionados, sin cambios de ruta
config.toml                 # configuración, sin cambios de ruta
evals/run_evals.py          # entrada de eval compatible
data/eval_sample.jsonl      # muestra legacy de cuatro, default del smoke
data/eval_dataset.jsonl     # 32 tickets sintéticos con etiquetas propuestas
data/DATASET.md             # criterios, ambigüedades y controles
tests/
```

`support` agrupa el problema que resolvemos; `llm`, la preparación del contexto y
los adaptadores; `runtime`, la configuración y escritura local. La CLI conecta
las opciones al servicio. El servicio usa los otros grupos; los adaptadores no
conocen la CLI ni escriben métricas. Los prompts usan el contrato de respuesta
para validar sus ejemplos. No se agregan contenedores, factories ni capas vacías.

Los imports internos cambiaron, por ejemplo `src.service` ahora es
`src.support.service`. Se conservan `python -m src.main` y
`python -m evals.run_evals`, los flags y el contrato JSON. `ROOT` se resuelve desde
`runtime/config.py` hacia la raíz del proyecto: mover módulos no mueve recursos.
Las rutas relativas de métricas siguen ancladas a esa raíz.

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
desactiva la escritura. Estos ejemplos usan mock y no consultan la red. Seleccionar
OpenAI o Gemini con modelo y credenciales válidas habilitaría una petición real: no hacerlo
sin revisar antes modelo, límite de intentos y presupuesto. No se instalan dependencias al ejecutar.
Python >=3.12 es el mínimo declarado para la base de dependencias de referencia
adoptada por decisión de Luis, siguiendo la recomendación que reportó del Teacher
Assistant. No se presenta como obligación académica completa verificada.
`requirements.txt` conserva exactamente las 44 versiones de esa referencia y es
la única lista: setuptools la lee mediante dependencias dinámicas en `pyproject.toml`.
**El conjunto completo no se instaló ni se probó integrado.** El .venv existente
(Python 3.14.8/Pydantic 2.14.1) se amplió únicamente con PyYAML 6.0.3 y Ruff 0.17.3. La correspondencia de nombres con la consigna está en
[docs/NOMENCLATURA.md](docs/NOMENCLATURA.md); no se alega cumplimiento completo.

Estos comandos usan el árbol fuente desde esta raíz. Desde otra carpeta se puede
usar `make -C /ruta/nubbix-support test` o cambiar primero a esta raíz. También se
verifica la ejecución de módulos con `PYTHONPATH=/ruta/nubbix-support` y el
intérprete absoluto de su .venv, sin depender del paquete antiguo instalado. La distribución instalada
anteriormente no se reinstaló. Empaquetar config/datasets/prompts como recursos para
uso fuera del árbol fuente sigue pendiente; no se promete una CLI global instalada.

## Chequeos de desarrollo con Ruff

```bash
make lint           # imports y errores básicos: E4/E7/E9/F/I
make format-check   # comprobar estilo sin escribir
make format         # formatear; revisar el diff después
make check          # lint + formato + pruebas
```

Ruff 0.17.3 se declara aparte en `[project.optional-dependencies].dev`; no se agrega
al requirements TA ni se cambia su contenido. La configuración apunta a Python
3.12 y líneas de 88 caracteres. Los fixes aplicados fueron seguros y revisados;
no se habilitaron unsafe-fixes. Ninguno de estos comandos instala paquetes.
Para consultar versiones ya instaladas: `.venv/bin/python -m pip show PyYAML ruff`.

## Configuración y prompts

`config.toml` es la fuente de configuración, validada con Pydantic y sin campos
extra. `--config ruta.toml` elige otro archivo. No se abre `.env`. La configuración
TOML no contiene secretos; sólo al crear el adaptador seleccionado se consulta
`OPENAI_API_KEY` o `GEMINI_API_KEY` en el entorno del proceso. `.env.example` sigue siendo una plantilla
vacía, no un archivo cargado automáticamente.

### Preparar claves localmente (sin conectarse todavía)

1. Desde esta raíz, copiá la plantilla sólo si no tenés ya un `.env`:

   ```bash
   cp -n .env.example .env
   ```

   Si el archivo ya existe, conservá su contenido y editalo personalmente; no lo
   sobrescribas con la plantilla. Este comando es para que lo ejecutes vos: la
   preparación del ejemplo no creó ni leyó un `.env` real.
2. Abrí `.env` en tu editor local y completá `OPENAI_API_KEY` y `GEMINI_API_KEY`
   con tus propias claves. Conservá `.env.example` con ambos valores vacíos.
3. No pegues los valores en el chat ni los incluyas en capturas, logs o commits.
   Para verificar exclusión, usá `git check-ignore .env`, que muestra la ruta,
   sin imprimir su contenido. `.env.example` queda versionable.
4. **El programa no carga `.env` automáticamente.** Cada adaptador requiere su variable
   `OPENAI_API_KEY` o `GEMINI_API_KEY` disponible en el proceso y un modelo elegido.
   Preparar el archivo no carga esas variables ni conecta proveedores. Revisá modelo,
   límites y presupuesto antes de seleccionar un proveedor remoto.

Orden: valores por defecto del schema → TOML → flags. Los flags son `--provider`
(mock/openai/gemini), `--model`, `--prompt`, `--mock-scenario` y `--no-metrics`. El TOML también define
`max_attempts` (1..3 intentos totales, no cantidad adicional de reintentos),
`max_query_chars` y `metrics_path`, además de `openai_max_output_tokens` y `gemini_max_output_tokens`
(512 por defecto, rango técnico 16..4096 para cada adaptador). `--model` sobreescribe `model` del TOML y es
obligatorio para OpenAI/Gemini; no se elige un modelo comercial por defecto. El escenario
mock sólo afecta al proveedor mock. Las rutas relativas de métricas se resuelven
contra la raíz de este proyecto, incluso al usar otro TOML. Los límites son
propuestas técnicas, no políticas de negocio impuestas por Henry.

- `prompts/v1_zero_shot.yaml`: instrucciones sin ejemplos.
- `prompts/v2_few_shot.yaml`: mismas instrucciones y dos ejemplos sintéticos.
- `prompts/CHANGELOG.md`: hipótesis y cambios; ninguna versión es ganadora todavía.

Los `.yaml` usan YAML legible, con instrucciones multilínea plegadas (`>-`).
`yaml.safe_load()` convierte el documento a datos y Pydantic valida sus tipos,
campos y restricciones. Se rechazan errores de sintaxis y tags de objetos Python;
no se utiliza `unsafe_load`. Como PyYAML interpreta algunos escalares (por ejemplo,
`yes`) como booleanos, los textos ambiguos deben ir entre comillas y se mantiene
la validación estricta. La migración preservó los datos/instrucciones de ambos
prompts; no se cambió la técnica ni se eligió una variante ganadora.
Las instrucciones y ejemplos están fuera del código; consulta e instrucciones
viajan por separado al proveedor. El mock ignora ambos y devuelve valores fijos.

## Flujo y orden de lectura

1. `src/support/schemas.py`: contrato de salida; `confidence` es una señal autodeclarada
   del modelo sobre la categoría, no una probabilidad calibrada ni un veredicto
   de acierto. No se extrae hoy de una API. `actions` son sugerencias humanas.
2. `config.toml` y `src/runtime/config.py`: opciones y validación de configuración.
3. `prompts/*.yaml` y `src/llm/prompts.py`: versiones, validación y render de ejemplos.
4. `src/llm/providers/base.py` y `mock_provider.py`: `generate(instructions, query)`
   devuelve texto sin validar. Los escenarios de mock son herramientas de prueba.
5. `src/support/service.py`: controla entrada → carga prompt → proveedor → parsea/valida
   → controla salida → registra métricas. Solo repite errores de parsing/schema,
   hasta agotar el límite. El siguiente intento recibe un resumen seguro del último
   error, junto a las instrucciones base y la misma consulta. No repite bloqueos
   de seguridad ni errores del proveedor.
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
del log). Tokens y costo siguen siendo `null`: `usage_status=unavailable_mock` para mock y
`not_collected` para las ramas remotas, que todavía no normaliza usage ni tarifas. No
se inventan consumos ni costos cero. `simulated` es true para mock o un proveedor
inyectado de prueba; false para una rama remota normal no significa que se haya
completado una petición (ver status/attempts). Configuraciones inválidas que no llegan al servicio
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
local pide al menos 30 casos etiquetados; ahora hay 32 casos propuestos en data/eval_dataset.jsonl, pendientes de revisión humana y evaluación real. El sample de cuatro se conserva sólo como smoke.
El mock no cuenta como un proveedor real. OpenAI y Gemini tienen adaptadores y
pruebas reales puntuales de contrato, sin modelo comercial por defecto. Faltan
evaluación comparativa, observabilidad integrada y revisión de requisitos; no se
declara cumplimiento académico completo por esas pruebas.

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

Requiere Python 3.12+ disponible. Estos comandos de instalación son instrucciones
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

## Verificación del refactor modular — 31/10/2026

31 tests aprobados: los 28 previos más carga de CLI/config/prompts y eval/dataset
desde otra carpeta con PYTHONPATH explícito, y cobertura de paquetes en pyproject.
Se compararon stdout, stderr y código de salida antes/después: idénticos para CLI
normal, recuperación, error de parsing y ambas variantes del runner.

Desde /tmp se verificaron los atajos documentados:

```bash
make -C /ruta/nubbix-support test
make -C /ruta/nubbix-support eval
make -C /ruta/nubbix-support run
```

`test` pasó 31 pruebas; `eval` conservó 4 casos y Exact Match simulado 0.25; `run`
agregó una métrica sin alterar las anteriores. El contrato, comandos y resultados
no cambiaron. Los módulos internos se movieron; no se reinstaló el paquete ni se
agregaron dependencias. La distribución global/recursos empaquetados sigue pendiente.

## Base de dependencias recomendada por el TA — 31/10/2026

Luis decidió conservar sin cambios la referencia de 44 versiones que indicó que
recomendó el Teacher Assistant. No se infiere que cada paquete sea requisito del PI.
El SHA-256 del archivo de referencia y de requirements.txt es:
`4f5abcda3dbc5e732f1d63b0826e0a46b64b0037f13be84d03d410e89b6dcd06`.

No se agrega Ruff a esa copia. La autorización posterior permitió instalar únicamente
PyYAML 6.0.3 y Ruff 0.17.3 en .venv y adaptar el cargador a safe_load; no se integraron
SDKs ni se instalaron los otros paquetes de la lista. Ruff se declara como extra dev.
El mínimo 3.12
responde a las restricciones verificadas de las versiones de NumPy/SciPy incluidas;
no se sostiene compatibilidad con 3.11 para esta base.

`pyproject.toml` referencia requirements.txt usando el mecanismo de
[dependencias dinámicas de setuptools](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#dynamic-metadata),
sin una segunda lista contradictoria. setuptools>=77 ya era el backend declarado;
no se instaló ni actualizó. No se ejecutó un build o instalación del conjunto nuevo.
Las afirmaciones históricas de dependencias mínimas en secciones anteriores
corresponden a los incrementos de esa fecha, no a la declaración actual.

## PyYAML y Ruff instalados con autorización — 31/10/2026

Se instalaron únicamente estos dos paquetes nuevos en .venv, desde PyPI oficial:

```bash
.venv/bin/python -m pip install --no-cache-dir --index-url https://pypi.org/simple --no-deps PyYAML==6.0.3 ruff==0.17.3
make check
```

Versiones efectivas: PyYAML 6.0.3, Ruff 0.17.3; se conserva Python 3.14.8 y
Pydantic 2.14.1. Quedan 38 de las 44 dependencias de referencia sin instalar: las
restantes ya estaban en el entorno o son PyYAML. No se ejecutó pip install del
requirements completo ni del extra dev (que resolvería también las dependencias
runtime del proyecto). No se prueba ni certifica ese conjunto integrado.

Ruff corrigió diez incidencias de imports con fixes seguros y formateó doce archivos;
se revisó el diff y se comparó el AST normalizado del resto del código, sin cambios
semánticos fuera del cargador y sus pruebas. No se usaron unsafe-fixes.

Resultado: lint correcto, 21 archivos con formato correcto, 35 pruebas aprobadas.
Se verificó YAML multilínea, sintaxis inválida, tipos inválidos y rechazo de tags
Python sin ejecución. La migración conserva exactamente los datos de ambos prompts.
CLI fixed/recover_once retorna 0 con JSON simulado; malformed/invalid_contract,
2 con stdout vacío. Ambos runners conservan cuatro muestras y Exact Match mock
0.25, sin pretensión de evaluar un modelo real. Requirements fue verificado byte
a byte contra la referencia y su hash sigue intacto. No se integraron proveedores,
leyeron credenciales ni hicieron llamadas pagas.

## Incremento local: feedback de reparación — 03/11/2026

El retry ya no repite instrucciones idénticas cuando falla JSON/Pydantic. El servicio
construye el siguiente intento con el prompt original y un bloque de corrección del
último error. `generate(instructions, query)` y los comandos públicos no cambian.

Ejemplo pedagógico (salidas inventadas para explicar, no llamadas a un LLM):

1. La consulta es «Me cobraron dos veces este mes»; primer intento sin feedback.
2. El proveedor de prueba devuelve JSON con confidence como texto. Pydantic lo rechaza.
3. El siguiente intento recibe `confidence: usá un número finito entre 0 y 1`, más
   el pedido de devolver el JSON completo. La consulta original no se modifica.
4. Si la nueva respuesta cumple el contrato y el guardrail de salida, se entrega.
   Si se agotan los intentos, se conserva el error: código 2 y stdout vacío en CLI.

El resumen usa mensajes fijos sobre campos conocidos, hasta tres fallas distintas.
No copia input/context/msg de los errores, valores inválidos, claves desconocidas ni
la respuesta cruda. El bloque se reemplaza en cada retry, sin acumular historial,
y no se escribe en métricas. El límite de intentos (por defecto dos totales) se
mantiene; no se agrega retry de transporte ni se relajan restricciones del schema.

El mock `recover_once` sigue guiado por contador y no entiende esas instrucciones.
Las pruebas incluyen un doble que devuelve JSON válido solo al recibir feedback,
además de JSON malformado, errores de campos cambiantes, límite 1/2/3 y un marcador
sintético privado que no debe aparecer en feedback ni logs. Esto verifica el cableado;
un LLM real podría volver a fallar o generar contenido incorrecto aunque valide.

```bash
.venv/bin/python -m unittest discover -s tests -p test_repair_feedback.py -v
.venv/bin/python -m src.main 'Me cobraron dos veces este mes.' --mock-scenario recover_once --no-metrics
```

Este incremento queda local y sin commit/publicación, para recorrerlo con Luis antes
de otro cambio. No hubo instalación, proveedores reales, credenciales ni gasto.

Verificación local del 03/11/2026: 40 tests aprobados, Ruff check correcto y 22
archivos con formato correcto. Comandos ejecutados desde la raíz:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -q
.venv/bin/ruff check --no-cache src evals tests
.venv/bin/ruff format --check --no-cache src evals tests
.venv/bin/python -m src.main 'Me cobraron dos veces este mes.' --mock-scenario recover_once --no-metrics
.venv/bin/python -m src.main 'Me cobraron dos veces este mes.' --mock-scenario malformed --no-metrics
```

Se capturaron código/stdout/stderr por separado: recover_once produjo JSON simulado
con código 0; malformed agotó intentos y retornó 2 con stdout vacío. No se ejecutaron
llamadas reales, instalación, commit ni publicación. El HEAD publicado sigue en 2ab8990.

## Adaptador OpenAI: checkpoint exclusivamente offline — 03/11/2026

El SDK openai está declarado en la referencia TA pero **no está instalado**; tampoco
httpx/requests. No se instaló nada. Se usa HTTP con urllib de la biblioteca estándar,
conforme a la [documentación oficial de generación de texto](https://developers.openai.com/api/docs/guides/text).
No se cambió ningún pin. El adaptador puede sustituirse por el SDK más adelante.

Orden de lectura: `src/runtime/config.py` (selección/modelo),
`src/llm/providers/openai_provider.py` (petición/respuesta),
`src/support/service.py` (Pydantic y reparación) y `tests/test_openai_provider.py`.
La función `simulate_response` conserva su nombre histórico por compatibilidad,
pero ahora respeta el proveedor seleccionado: con OpenAI **no implica modo offline**.

1. `--provider openai` o provider en TOML selecciona el adaptador; `--model` o model
   en TOML debe indicar un identificador elegido por Luis. No se fija un modelo real.
2. Sólo entonces se busca OPENAI_API_KEY en el proceso. Si falta clave/modelo,
   se falla antes de la petición. .env no se abre, copia ni lee.
3. El adaptador prepara POST a `/v1/responses` con instrucciones separadas de la
   consulta, timeout de 30 segundos y límite de salida configurable. Envía store=false
   para deshabilitar almacenamiento de la respuesta; eso no es una promesa de retención
   cero de todos los datos. [Documentación oficial de almacenamiento](https://developers.openai.com/api/docs/guides/migrate-to-responses).
4. Extrae bloques output_text de output (sin asumir que el primero contiene texto),
   rechaza respuestas incompletas, negativas de contenido y formatos no admitidos.
5. El texto vuelve a Pydantic. JSON/contrato inválidos pueden generar otra petición
   con el feedback acotado anterior; el límite total permanece. HTTP, timeout y errores
   de transporte no se reintentan automáticamente en este incremento.

Las pruebas usan fixture-model/fixture y una clave ficticia que no sirve para la API.
Interceptan urlopen o inyectan un transporte falso; no se consultan claves del entorno
real. Simulan texto válido, error HTTP/red, falta de clave/modelo, rechazo/incompleto,
JSON inválido seguido de corrección y agotamiento. No son resultados de un LLM.

```bash
.venv/bin/python -m unittest discover -s tests -p test_openai_provider.py -v
make check
.venv/bin/python -m src.main 'Consulta sintética' --no-metrics
```

El runner de muestras **rechaza OpenAI**: sigue siendo sólo mock y no debe convertirse
en evaluación pagada al cambiar config. Faltan modelo/acceso/presupuesto acordados,
una llamada real explícitamente autorizada, usage/costo reales, rate limits/backoff,
pruebas de calidad y segundo proveedor. Un límite de tokens no es presupuesto monetario:
los modelos pueden consumir tokens aun sin texto visible. [Referencia oficial](https://developers.openai.com/api/docs/guides/reasoning).
Los errores se convierten a mensajes controlados; no se registran cuerpo HTTP,
consulta, respuesta cruda, cabeceras ni claves. No se garantizan políticas de contenido
completas por validar JSON. Este incremento queda sin commit/push para explicarlo antes
de cualquier llamada real.

Verificación del checkpoint OpenAI (03/11/2026): 51 tests aprobados, Ruff check
correcto y 24 archivos con formato correcto. La suite intercepta el transporte
OpenAI antes de red y sustituye el entorno por mapas ficticios donde hace falta.
No se creó ni leyó un .env real ni se consultaron claves reales. Se verificaron
falta de clave/modelo, request/headers con clave ficticia, errores HTTP/red, datos
incompletos/refusal, reparación con feedback, agotamiento y ausencia de datos
sensibles en métricas. Los smoke tests fuera de la suite usaron sólo mock y el
runner de cuatro muestras. Los 44 pins conservan su hash y no se instaló software.
HEAD sigue 2ab8990, sin stage/commit/push. El siguiente paso requiere acordar modelo,
límites y autorización de una llamada real; este checkpoint no la ejecuta.

## Gemini equivalente, sólo probado offline — 03/11/2026

El SDK google-genai no está instalado. Se usa urllib, sin instalar dependencias ni
modificar los 44 pins. La referencia primaria consultada es
[Creating an interaction](https://aistudio.google.com/api-reference/interactions-api/create-interaction),
que documenta POST `/v1beta/interactions`. Google recomienda Interactions para
proyectos nuevos; este checkpoint usa la versión v1beta de la referencia consultada,
no se presenta como prueba remota ni se supone equivalencia con otros endpoints/versiones.

Recorrido para estudiar: selección `--provider gemini` y `--model` →
`src/llm/providers/gemini_provider.py` → texto → Pydantic/retry/guardrail en servicio.
Los flags existen, pero **no se ejecutó esa selección contra una API real**.

- Se consulta GEMINI_API_KEY en el proceso sólo al construir el adaptador; no se
  abre .env ni se usa GOOGLE_API_KEY como fallback. No se eligió un modelo comercial.
- La cabecera x-goog-api-key transporta la clave; no va en URL ni cuerpo. Las
  instrucciones van en system_instruction y la consulta en input. generation_config
  limita salida; store=false solicita no almacenar la interacción, sin garantizar
  retención cero de todos los datos. El timeout técnico es 30 segundos.
- Sólo se acepta status=completed y texto dentro de steps de tipo model_output.
  No se mezcla user_input, pensamiento ni llamadas de herramientas con la respuesta.
  No se implementa continuación, streaming, herramientas ni multimodalidad.
- HTTP/red, estados incompletos y contenido no admitido generan ProviderError
  controlado. Los cuerpos de error no se leen ni se registran; los HTTPError se
  cierran antes de lanzar el error sanitizado (también en OpenAI).
- El JSON textual vuelve al mismo servicio. Si falla su parseo/contrato, el próximo
  intento recibe el feedback seguro existente; errores HTTP no se reintentan.

Pruebas con clave/entorno ficticios y transporte interceptado:

```bash
.venv/bin/python -m unittest discover -s tests -p test_gemini_provider.py -v
make check
```

El runner de muestras sigue rechazando cualquier proveedor distinto de mock, por
lo que cambiar config no habilita evaluaciones pagadas. Métricas siguen sin texto
crudo ni claves, con tokens/costo null y not_collected para adaptadores remotos.
Las pruebas inyectadas se marcan simuladas. Antes de una llamada real faltan modelo,
acceso, límites y autorización de gasto, además de verificar comportamiento real,
usage, costo, rate limits y calidad. No se considera completo el PI por tener dos
archivos de adaptadores ni por obtener resultados de fixtures. Sin commit/push.

Verificación final del checkpoint Gemini (03/11/2026): 62 tests aprobados, Ruff
check correcto y 26 archivos con formato correcto. Las once pruebas de Gemini
sustituyen urlopen/transporte y entorno de claves por fixtures; ninguna usa valores
reales. Cubren request/auth/cap, ausencia de clave/modelo, estados incompletos o no
textuales, errores HTTP/red, cierre HTTPError, reparación, agotamiento, CLI y métricas
sin secretos/contenido. OpenAI y los cambios previos también conservan sus tests.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -q
.venv/bin/ruff check --no-cache src evals tests
.venv/bin/ruff format --check --no-cache src evals tests
```

Smoke tests adicionales sólo mock: fixed/recover_once retornan 0 con JSON; malformed
retorna 2 sin stdout. El runner conserva las cuatro muestras y quality_claim=false.
No se instaló google-genai ni otro paquete, ni se alteraron los 44 pins; mock sigue
en config.toml. No se leyó .env o claves, ni se llamó API de modelos. HEAD sigue
2ab8990, sin staging/commit/push. Falta una prueba remota autorizada, no se declara
completada la integración de dos proveedores por el éxito de transportes falsos.

## Diagnóstico offline posterior a la prueba real — 03/11/2026

Las secciones anteriores conservan los checkpoints históricos. Después, Luis
autorizó una sola llamada con ticket ficticio por proveedor: OpenAI gpt-6-luna
devolvió una respuesta válida; Gemini gemini-3.5-flash-lite devolvió HTTP200 y
completed con uso, pero falló el recorrido local. El script puntual agrupó errores
de extracción, JSON, contrato y guardrail. No conservó cuerpo crudo ni detalle de
excepción: **no podemos determinar retrospectivamente cuál etapa falló**. Esta
investigación no repitió llamadas ni abrió .env. No hay corrección funcional de
extracción demostrada ni se declara Gemini resuelto.

La [referencia oficial de Interactions](https://aistudio.google.com/api-reference/interactions-api)
documenta steps/model_output/content/text, coincidente con el adaptador. Fixtures
offline verifican esa estructura, texto fragmentado y exclusión de otros pasos.
El request pide texto mediante instrucciones; no activa response_format. La
[API también ofrece salida estructurada](https://aistudio.google.com/api-reference/interactions-api/create-interaction),
pero no se añadió en este diagnóstico ni se asume que su ausencia causó el fallo.
No se retiran bloques Markdown automáticamente: siguen siendo JSON inválido.

Diagnósticos nuevos, con etiquetas locales fijas y sin valores de la salida:

| Frontera | Evidencia local disponible |
|---|---|
| Transporte HTTP | ProviderError.code: http_error, transport_error, http_json_invalid |
| Extracción Gemini | incomplete_response, invalid_envelope, invalid_content, non_text_output, empty_output |
| Parseo del texto | json_invalid |
| Contrato Pydantic | contract_invalid |
| Configuración Pydantic | configuration_invalid |
| Guardrail de salida | failure_stage=rejected_output; sin contenido ni detalle del patrón |

ProviderError sigue siendo ValueError y conserva compatibilidad con errores
anteriores; códigos desconocidos se normalizan a provider_error. OpenAI conserva
por ahora ese código genérico. La CLI informa códigos fijos en stderr para errores
de proveedor/validación, retorna 2 y deja stdout vacío. El servicio registra
failure_stage/failure_code junto al status existente; son el resultado terminal,
no un historial por intento. Un éxito los deja en null. Los errores de proveedor
siguen sin retry; JSON/contrato conservan el límite y feedback anteriores.

Comprobación sin claves ni API:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -q
.venv/bin/ruff check --no-cache src evals tests
.venv/bin/ruff format --check --no-cache src evals tests
git diff --check
```

La evidencia real original sigue separada en data/metrics_live_smoke_2026-11-03.jsonl
(ignorada), sin modificar ni inventar un código retrospectivo. El script auxiliar
de aquella prueba no pasa por el servicio y no captura estos nuevos códigos; no
debe repetirse para diagnosticar. Una futura prueba real necesita autorización
propia y recoger sólo etiquetas seguras del adaptador/validador. No instala
paquetes, cambia pins ni publica este incremento.

## Gemini: pedir JSON con esquema — incremento offline, 03/11/2026

La llamada de diagnóstico autorizada después de la investigación anterior
identificó json_parse/json_invalid: se extrajo texto que empezaba con un fence
Markdown. No se comprobó su contenido interior. Este incremento cambia el request
para pedir salida estructurada; no se volvió a llamar a Gemini para probarlo.

La [referencia Interactions v1beta](https://aistudio.google.com/api-reference/interactions-api/create-interaction)
documenta response_format de tipo text, MIME application/json y schema. La
[guía oficial](https://ai.google.dev/gemini-api/docs/structured-output) muestra
model_json_schema de Pydantic; la [ficha de Gemini 3.5 Flash-Lite](https://aistudio.google.com/docs/models/gemini-3.5-flash-lite)
declara soporte de structured outputs. Es soporte documentado, no aceptación del
request concreto comprobada con nuestra cuenta.

Recorrido para leer y entender:

1. src/support/schemas.py conserva el contrato único SupportResponse.
2. src/support/service.py genera SupportResponse.model_json_schema() y lo inyecta
   al construir GeminiProvider mediante response_schema.
3. src/llm/providers/gemini_provider.py añade al cuerpo Interactions:

   ```python
   payload["response_format"] = {
       "type": "text",
       "mime_type": "application/json",
       "schema": self.response_schema,
   }
   ```

4. El adaptador devuelve texto extraído igual que antes. El servicio conserva
   model_validate_json, retry acotado con feedback, guardrail y errores seguros.

No se duplica el schema a mano ni se incorpora Pydantic/reglas Nubbix dentro del
adaptador. El parámetro response_schema es opcional para conservar compatibilidad
de invocaciones directas; el flujo normal CLI/servicio Gemini lo pasa siempre.
Quien inyecte un GeminiProvider propio o ejecute scripts auxiliares directamente
debe pasar response_schema=SupportResponse.model_json_schema() para solicitarlo.
Los scripts de las pruebas reales anteriores no se modificaron ni repitieron.
OpenAI conserva su request anterior; no se extiende este cambio a otro endpoint.

El schema actual expresa campos requeridos, tipos, categorías, confidence entre
0 y 1, lista de acciones y additionalProperties=false. Incluye minLength de
Pydantic, pero Google documenta que esa restricción se ignora del lado remoto;
tampoco expresa el strip_whitespace local ni valida el significado de la respuesta.
Pydantic sigue rechazando texto vacío/espacios, tipos incorrectos, extras, valores
fuera de rango y JSON con fences. El guardrail sigue ejecutándose después.
Confidence continúa siendo autodeclarada; structured output no calibra ni evalúa
calidad. Si la API rechaza el esquema con HTTP400, se informa error seguro sin
fallback a texto libre ni retry HTTP.

Tests nuevos: tests/test_gemini_structured_output.py. Cubren el request saliente
desde el servicio, uso de un único schema, fixtures válidas e inválidas, Markdown
rechazado, restricciones locales, retry con schema conservado, incomplete y rechazo
HTTP400 sin repetición. Son transportes ficticios; no prueban constrained decoding
real, fidelidad semántica, costo ni compatibilidad efectiva de la cuenta/modelo.

Comandos offline: los unittest/Ruff/git diff --check del apartado anterior.
No se leen claves ni .env, instalan dependencias o alteran los 44 pins. No commit
ni push. Una futura verificación real necesita autorización adicional.

## Dataset de evaluación preparado offline — 03/11/2026

Se añadieron 32 tickets sintéticos (ocho por categoría), con ID, justificación y
bandera de ambigüedad. Ocho casos de frontera necesitan especial revisión humana;
todas las etiquetas siguen siendo propuestas. No se usaron datos reales ni
ejemplos few-shot, y no se hicieron llamadas a modelos con este corpus. Criterios,
IDs discutibles y límites en [data/DATASET.md](data/DATASET.md).

```bash
.venv/bin/python -m evals.run_evals --dataset data/eval_dataset.jsonl --check-dataset
.venv/bin/python -m evals.run_evals --dataset data/eval_dataset.jsonl --prompt v1_zero_shot
.venv/bin/python -m evals.run_evals --dataset data/eval_dataset.jsonl --prompt v2_few_shot
```

El control verifica formato, 30+ casos, categorías, metadatos, duplicación
normalizada y separación respecto a ejemplos de ambas variantes. Reporta balance
y ocho IDs ambiguos; no certifica verdad de etiquetas ni independencia semántica.
El default sin --dataset sigue usando el sample de cuatro. El runner permanece
limitado a mock: un config remoto falla antes de crear el proveedor.

Exact Match compara sólo la categoría con su etiqueta de referencia. Incluye
fallos y ambiguos en el denominador; no evalúa answer/actions, seguridad completa
ni confianza calibrada. Con mock siempre-other: 8/32=0.25 en las dos variantes,
quality_claim=false. Ese resultado no mide un LLM ni justifica elegir un prompt.
No hay LLM-as-Judge. Una comparación real sigue pendiente y requiere autorización.

Si se usan estos casos para ajustar prompts, son desarrollo; medir generalización
necesitará un conjunto reservado aparte. No pasar query/label_reason juntos al
proveedor: el runner sólo envía query, comprobado por tests. No convertir en
few-shot ningún caso reservado para evaluación. Sin claves, paquetes, commit/push.

## Estado verificado para publicar avances — 03/11/2026

Se agrupan los cambios de esta jornada en commits temáticos: reparación,
adaptadores/diagnósticos, corpus de evaluación y documentación/plantilla. La suite
completa contiene 88 tests offline; lint y formato correctos. El control de los32
casos pasa, con8/categoría y8 ambiguos. Los dos prompts sobre el mock dan0.25,
quality_claim=false; no se presentan como resultados de un LLM.

Hubo pruebas reales limitadas con ticket ficticio y autorizaciones independientes.
OpenAI produjo una salida válida. En Gemini se identificó JSON con fence Markdown;
una solicitud posterior con response_format y schema pasó Pydantic y el guardrail.
Es evidencia puntual, no causalidad general ni garantía de precisión. Uso/tier/costo
no se normalizan aún en el servicio; no se afirma gratuidad ni cobro observado.
Los JSONL de esas pruebas, claves, scripts auxiliares locales y apuntes externos
no se incluyen en el repositorio. No hay autorización permanente para nuevas
llamadas de evaluación por publicar código.

Pendiente: revisar etiquetas y fronteras del corpus, acordar y ejecutar una
comparación real de prompts/proveedores, integrar métricas de uso/costo, rate limits
y políticas/guardrails, además de contrastar entrega contra la rúbrica completa.
