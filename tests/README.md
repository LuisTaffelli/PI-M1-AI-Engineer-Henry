# Pruebas por responsabilidad

Estas pruebas verifican el funcionamiento del código con `unittest`, mocks y
transportes falsos. No hacen inferencias reales ni miden la calidad de un modelo.
La suite académica de evaluaciones sigue en `evals/`, con sus propios comandos.

## Dónde buscar cada prueba

```text
tests/
  integration/   contrato JSON, CLI/TUI, recorrido offline e imports/recursos
  providers/     OpenAI, Gemini, Ollama, salida estructurada y status HTTP
  prompts/       carga segura de YAML y compatibilidad de las cuatro versiones
  guardrails/    diagnóstico de reglas, Unicode y límite de entrada
  service/       frontera proveedor/servicio, reparación, retry HTTP y fallos
  runtime/       credenciales ficticias, tokens y cálculo de precios
  evaluation/    datasets, planes, runners, pares adversariales y costos de corridas
```

Cada archivo conserva sus casos y fixtures locales. Los tests que atraviesan
varias capas se agrupan por su responsabilidad principal: por ejemplo, el retry
HTTP vive en `service/` porque lo coordina el servicio, y los costos de una corrida
van en `evaluation/`. `integration/` reúne los recorridos generales y las reglas
de arquitectura. Los JSONL, YAML y reportes de referencia conservan sus rutas.

## Ejecutar todo

Desde la raíz del checkout, con el entorno virtual instalado:

```bash
make check  # lint, formato y todos los tests
make test   # sólo todos los tests
```

El comando de descubrimiento habitual no cambia:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
```

## Ejecutar una responsabilidad o un archivo

```bash
# Adaptadores HTTP, sin llamar a los proveedores.
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests/providers -v

# Retry HTTP del servicio, con transporte y esperas simulados.
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests/service -p 'test_http_retry.py' -v

# También funciona el filtro anterior, desde toda la suite.
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -p 'test_http_retry.py' -v
```

Podés sustituir `providers` por cualquiera de las carpetas del mapa. Para un test
concreto se puede usar su módulo, clase y método, por ejemplo:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest tests.integration.test_contract_cli.CliTests.test_missing_argument -v
```

Mantené `__init__.py` en `tests/` y en cada subcarpeta: permite descubrir los tests
recursivamente en las versiones de Python compatibles y ejecutarlos por módulo.
Los nombres de archivos `test_*.py` se mantienen para conservar los filtros `-p`.
No hace falta agregar un runner, framework ni configuración nuevos.

## Menú de terminal

`tests/integration/test_tui.py` prueba entrada simulada, validación, configuración,
previews, confirmación remota por corrida, límites, cancelación y conservación de
resultados parciales. Ejecuta los runners con mock en carpetas temporales; bloquea
lectura de claves y transportes de red. No son evaluaciones de calidad de un LLM.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest tests.integration.test_tui -v
```
