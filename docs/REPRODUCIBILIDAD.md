# Instalación y reproducción verificadas — 04/11/2026

Se instaló el checkout actual con sus **44 pins exactos, Ruff y el proyecto** en un
entorno virtual nuevo desde PyPI oficial. Pasaron `pip check`, los 132 tests, lint,
formato y los recorridos mock descritos abajo. Se verificó Linux x86_64/Python
3.14.8; no se afirma compatibilidad probada en todas las plataformas o versiones.

El `.venv` original no se modificó. No se leyeron secretos, hicieron solicitudes a
modelos, activaron servicios pagos ni publicaron cambios. La muestra previa de
Ollama permanece conservada y no se repitió durante esta revisión.

## Dependencias y fundamento

La síntesis local de la consigna pide Python, dependencias declaradas y un
repositorio autocontenido con instrucciones reproducibles. No impone los SDK ni
los 44 paquetes particulares. Luis eligió esa lista por una referencia del TA;
se conserva porque ahora se pudo instalar y probar sin incompatibilidades observadas.
No hay fundamento para sustituir sus pins por versiones arbitrarias.

`requirements.txt` sigue idéntico a la referencia elegida, SHA-256
`4f5abcda3dbc5e732f1d63b0826e0a46b64b0037f13be84d03d410e89b6dcd06`.
`pyproject.toml` lo lee como fuente única runtime. Los únicos imports externos
directos encontrados mediante AST en src/evals/tests son Pydantic y PyYAML; sus
cuatro dependencias transitivas también están incluidas en los 44 pins. Los
adaptadores HTTP usan biblioteca estándar. No hacía falta agregar otro SDK para
que funcionaran.

Se añadió `requirements-dev.txt` con `.[dev]`: instala el proyecto y sus dependencias
runtime más Ruff, cuya versión ya se declara en el extra dev de pyproject. Esta
entrada se usa desde la raíz del checkout y evita duplicar listas o versiones.
`unittest` es biblioteca estándar; no se añadió pytest ni framework de evaluación.
El backend `setuptools>=77` se obtuvo mediante aislamiento de build de pip. Su
versión resuelta no se conservó: esto verifica el recorrido funcional, no un build
idéntico byte por byte con herramientas de build totalmente bloqueadas.

## Prerrequisitos y componentes opcionales

| Componente | Necesario para | Estado / configuración |
|---|---|---|
| Python >=3.12, venv y pip | Crear entorno e instalar | Probado 3.14.8; el mínimo declarado no implica pruebas en cada versión. |
| Checkout completo | Config, YAML, datasets y tests | Ejecutar desde su raíz; el wheel aislado no contiene esos recursos. |
| PyPI oficial y conectividad | Instalación inicial | Índice pypi.org, ruedas de files.pythonhosted.org; sin otros registros. |
| GNU Make | Atajos de desarrollo | Opcional: se pueden ejecutar Ruff y unittest directamente. |
| Ollama + modelo GGUF local | Inferencia local opcional | Servidor HTTP loopback activo, tag existente y configuración explícita. No lo instala pip ni se descargan pesos desde la aplicación. |
| OPENAI_API_KEY / GEMINI_API_KEY | Proveedor remoto correspondiente | Opcionales; variables de proceso, nunca valores versionados. No se carga .env automáticamente. Usar sólo con autorización y presupuesto. |

Mock y los tests offline no necesitan claves, Ollama ni red después de instalar.
No hace falta disponer de los tres proveedores para ejecutar el proyecto en mock.
Los pesos/modelos locales, saldos y acceso comercial no forman parte de los paquetes
Python ni se certifican por instalar sus SDK.

## Recorrido reproducible desde el checkout

Elegir un entorno nuevo: no sobrescribir uno existente. Desde la raíz del repo:

```bash
python3 -m venv /tmp/nubbix-entrega
PIP_CONFIG_FILE=/dev/null /tmp/nubbix-entrega/bin/python -m pip --isolated \
  --disable-pip-version-check install --no-cache-dir --only-binary=:all: \
  --index-url https://pypi.org/simple -r requirements-dev.txt
/tmp/nubbix-entrega/bin/python -m pip check
make check PYTHON=/tmp/nubbix-entrega/bin/python RUFF=/tmp/nubbix-entrega/bin/ruff
PYTHONDONTWRITEBYTECODE=1 /tmp/nubbix-entrega/bin/python -m src.main \
  'Consulta sintética' --no-metrics
PYTHONDONTWRITEBYTECODE=1 /tmp/nubbix-entrega/bin/python -m evals.run_evals \
  --dataset data/eval_dataset.jsonl --check-dataset
```

Sin GNU Make, ejecutar en su lugar:

```bash
/tmp/nubbix-entrega/bin/ruff check src evals tests
/tmp/nubbix-entrega/bin/ruff format --check src evals tests
PYTHONDONTWRITEBYTECODE=1 /tmp/nubbix-entrega/bin/python -m unittest discover -s tests -v
```

Para sólo dependencias de ejecución, `pip install -r requirements.txt` y ejecutar
desde el checkout; no instala Ruff ni el proyecto. `pip install .` instala además
el proyecto usando el backend. El extra dev agrega la herramienta de chequeos.
La restricción a wheels evita compilar dependencias de terceros; su disponibilidad
para otras plataformas/versiones de Python permanece sin comprobar.

## Ejecución y evidencia efectivas

Se creó un venv separado en `Documents/Codex/2026-11-04/task-2/repro-install-venv` y
una copia del checkout sin .env ni entornos. La instalación inicial fue de `.[dev]`
con build aislado, índice oficial, sin caché y sólo ruedas para terceros. Se limpió
el entorno del proceso de instalación y se deshabilitaron archivos de configuración
de pip con `PIP_CONFIG_FILE=/dev/null`. Posteriormente se verificó también la entrada
`-r requirements-dev.txt` en ese mismo entorno; no es una segunda instalación desde
cero. La nueva entrada solicita el mismo `.[dev]` que la instalación inicial.

| Comprobación | Resultado |
|---|---|
| Resolver y construir el proyecto desde cero | Correcto; 44 pins, Ruff y proyecto instalados (46 distribuciones). |
| Fuentes de descarga | Sólo índice oficial y files.pythonhosted.org; proyecto desde copia local. |
| Versiones de los 44 requisitos | Todas exactas, sin ausencias ni diferencias. |
| Metadata del proyecto instalado nuevo | Incluye los 44 requisitos actuales y Ruff condicionado al extra dev. |
| pip check en el venv nuevo | Sin dependencias rotas. |
| Lint / formato / unittest | Correctos; 37 archivos formateados, 132 tests. |
| CLI mock fixed y recover_once | Código 0, exactamente cuatro campos JSON. |
| CLI mock malformed | Código 2, stdout vacío; error controlado. |
| Control del corpus | 32 casos y cuatro categorías; no certifica etiquetas humanas. |
| Evals mock v1/v2 sobre 32 | Ambos 0,25; simulated=true, quality_claim=false: prueba del runner, no calidad de modelos. |
| JSONL de métricas | Segunda ejecución añade una línea y conserva byte a byte la primera; sin texto de ticket. |
| Código probado vs original | Coincidencia byte a byte en src/evals/tests. |
| CLI del wheel desde /tmp con Python -I | Código 2; faltan config/prompts/datasets en el paquete. |

[Evidencia compacta](INSTALLATION_CHECK_2026-11-04.json): versiones, plataforma,
hashes, comprobaciones y límites. Los logs completos e informe pip quedaron en
`Documents/Codex/2026-11-04/task-2/`: `repro-install.log`,
`repro-install-report.json`, `repro-check.log`, `repro-functional-checks.json` y
`repro-dev-entrypoint.log`. No contienen credenciales usadas por la instalación.

## Qué aclaró la fase offline anterior

El entorno original sólo tenía 6/44 pins y una distribución antigua de Nubbix que
declaraba únicamente `pydantic<3,>=2.12`. Por eso su `pip check` correcto no validaba
el checkout actual. Se comprobó desde /tmp con Python -I; fuera del checkout ese
entorno encuentra un src antiguo en site-packages. No se eliminó ni reinstaló.

Un venv vacío sin pip falló por ausencia de Pydantic. Un dry-run sin índice ni caché
falló al no hallar candidatos locales para anthropic. Esos resultados no demostraban
que los pins fueran incompatibles o inexistentes en PyPI. La instalación online
posterior autorizada resolvió correctamente los 44 y cierra ese pendiente para el
entorno concreto probado.

## Límites y próximos pasos proporcionados

La ejecución desde checkout está verificada. No se promete todavía una CLI global
instalada: el wheel no incluye los recursos del proyecto. Empaquetarlos sólo sería
necesario si se decide ofrecer ese modo; no es un requisito independiente confirmado.
No se agregan web, contenedores ni SDK para aparentar uso de paquetes declarados.

La comparación local posterior ya cubre los 32 tickets y ocho paráfrasis; ver
RESULTADOS_EVAL_LOCAL.md. Queda discutir las referencias propuestas y otros escenarios
que se acuerden, y registrar los límites de seguridad.
La matriz está en EXPERIMENTOS.md. El alcance de extras/rúbrica sigue parcialmente
pendiente en las fuentes disponibles. Durante la verificación no hubo commits ni push; posteriormente se organizaron
los cambios en commits locales por tema, sin publicación.


## Verificación posterior del runner ampliado

Después de aquella instalación limpia se amplió la evaluación local para 32 casos
y suites suplementarias, sin agregar dependencias ni cambiar los 44 pins. Con el
mismo entorno nuevo se verificaron 135 tests, lint y formato (37 archivos), incluidos
tres tests adicionales de presupuesto, corpus completo y distinción de suites.
La evidencia de instalación anterior conserva sus hashes y 132 tests de aquel
snapshot; no se reescribe como si hubiera instalado el código posterior. La
comparación local posterior y sus hashes están en EVAL_LOCAL_2026-11-04.json.

### Evaluación de corpus multiproveedor

El nuevo comando `python -m evals.run_provider_evals` permite seleccionar OpenAI,
Gemini, Ollama o mock y comparar los mismos prompts y referencias. Por defecto
sólo previsualiza; la ejecución remota exige dos opciones explícitas y una cota
de llamadas que incluye reintentos. Ver [guía de evaluación multiproveedor](EVALUACION_PROVEEDORES.md) para comandos, privacidad, métricas y límites de gasto.
