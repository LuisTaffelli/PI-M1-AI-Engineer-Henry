# Comparación local de prompts y escenarios — 04/11/2026

Dos experimentos separados con `qwen2.5-coder:0.5b-test`, sin modificar pesos,
prompts, etiquetas o parámetros entre versiones. Referencias de clasificación
propuestas con revisión técnica documentada; **no validación humana nueva**.
Sólo b07 y a07 tenían confirmación previa de Luis. Esta es evidencia experimental
sobre el material de desarrollo, no una estimación de calidad en producción.

## Protocolo fijado y ejecución

- Corpus base: 32 tickets, ocho por categoría, ocho marcados ambiguos.
- Suite suplementaria: ocho paráfrasis, dos por categoría; derivadas de ocho
  objetivos del base y relacionadas con él, no un holdout independiente.
- Dos prompts YAML existentes: v1 zero-shot y v2 few-shot. Una generación por
  combinación, un intento total, temperatura 0, máximo 256 tokens de salida,
  contexto 2048 y timeout HTTP 30 s. No se usaron etiquetas/justificaciones como
  instrucciones al modelo; sólo query y el prompt seleccionado.
- Orden fijo v1 y luego v2 en cada suite; sin warmup, aleatorización ni repeticiones.
  Carga/caché del servidor pueden afectar latencia. No se concluye cuál es más rápido.
- Ollama 0.40.6; modelo GGUF F16 494.03M, 994158569 bytes. Digest observado antes y
  después de cada corrida, sin cambios:
  `08efee4699b2c84f8b793e888efd0de207bd8b00692a62337b40017048e3c075`.
- 80 generaciones en total, cero retries; 160 peticiones show/chat, además de las
  consultas de inventario/versión. Sin inferencia remota, descarga de pesos o claves.
- Plan, etiquetas y hashes guardados antes de generar. Las cuatro consultas de la
  muestra previa ya se habían observado: no se presenta la revisión como ciega.

## Corpus base: clasificación y formato separados

| Medida | v1 | v2 |
|---|---:|---:|
| Coincidencias con referencias propuestas | 11/32 (34,375%) | 18/32 (56,25%) |
| Salidas con contrato y guardrail propios superados | 31/32 | 30/32 |
| Respuestas incompletas del proveedor | 1 | 2 |
| billing | 0/8 | 6/8 |
| technical | 7/8 | 5/8 |
| account | 3/8 | 5/8 |
| other | 1/8 | 2/8 |
| Marcados ambiguos | 3/8 | 2/8 |
| No marcados ambiguos | 8/24 | 16/24 |
| Mediana de latencia del servicio | 0,229 s | 0,237 s |
| Mínima–máxima | 0,158–1,810 s | 0,168–1,084 s |
| Tokens totales derivados, incluidos fallos | 9351 | 14150 |

Cada fallo permanece en el denominador. Las tres respuestas incompletas fueron b04
con v1, b04 con v2 y t08 con v2: `failure_code=incomplete_response`, 256 tokens de
salida en cada una. Es compatible con alcanzar el límite de salida, pero no se
conservó el envelope HTTP crudo para distinguir qué condición exacta produjo ese
código. No se presenta como fallo de Pydantic ni como guardrail superado: ambas
etapas quedan desconocidas para esas respuestas. No se repitieron con más tokens.

v2 coincidió más en el global, especialmente en billing. A la vez, v1 coincidió más
en technical y en los casos marcados ambiguos. Esto muestra compromisos entre
estrategias: no corresponde declarar una versión universalmente superior ni
retocar la referencia para corregir el desacuerdo. La confusión completa por clase
está en la evidencia JSON; “error” identifica salida no validada.

## Suite de paráfrasis: resultado separado

| Medida | v1 | v2 |
|---|---:|---:|
| Coincidencias propuestas | 3/8 (37,5%) | 4/8 (50%) |
| Contrato y guardrail propios superados | 8/8 | 8/8 |
| billing | 0/2 | 2/2 |
| technical | 1/2 | 1/2 |
| account | 2/2 | 1/2 |
| other | 0/2 | 0/2 |
| Mediana del servicio | 0,219 s | 0,259 s |
| Tokens totales derivados | 2399 | 3427 |

Dos observaciones por categoría son muy sensibles a cada caso. Se describen los
resultados sin sumar ambas suites como 40 ejemplos independientes. La suite deriva
de objetivos del base y fue escrita con asistencia de IA; no mide generalización
independiente. No se evaluaron tono, veracidad o utilidad de answer/actions porque
los logs no conservan esos textos. Confidence no se usa como juez ni probabilidad
calibrada. USD queda desconocido: no equivale a costo total local cero.

## Comandos y conservación

Desde la raíz del checkout, con un entorno instalado según REPRODUCIBILIDAD.md,
reemplazar `.venv/bin/python` por el intérprete de ese entorno si corresponde. Los
nombres siguientes ya existen en la máquina original; para otra corrida usar una
carpeta nueva, sin sobrescribirlas:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m evals.run_local_sample \
  --config config.ollama.example.toml --all-cases --max-generations 64 \
  --output data/local_runs/2026-11-04-base32-v1-v2 --allow-local-inference

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m evals.run_local_sample \
  --config config.ollama.example.toml --dataset data/eval_robustness.jsonl \
  --diagnostic-suite --all-cases --max-generations 16 \
  --output data/local_runs/2026-11-04-robustness8-v1-v2 --allow-local-inference
```

Sin `--all-cases`, se conserva la selección de uno a cuatro IDs y presupuesto por
defecto ocho generaciones. El corpus completo requiere ampliar el presupuesto
explícitamente; máximo 64 por corrida. La suite pequeña necesita además
`--diagnostic-suite`: no se hace pasar por el requisito de 30+ casos. No se habilitan
proveedores comerciales. El runner general `evals.run_evals` conserva mock.

Los flags de formato/guardrail provienen de la aplicación. El runner conserva plan,
métricas, resultados y summary; la ejecución de esta jornada añadió snapshots de
inventario antes/después mediante un script local de sólo lectura. Esos snapshots
no los obtiene automáticamente la CLI: al repetir, registrar también versión/digest.
Los directorios raw quedan ignorados por Git, sin tickets ni respuestas crudas.

[Evidencia versionable](EVAL_LOCAL_2026-11-04.json) incluye los 80 registros numéricos,
IDs, referencias/predicciones, etapas, resúmenes, parámetros, hashes y modelo. Permite
recalcular sin volver a inferir. Los resultados anteriores se conservan sin reescribir.
Ejemplo de recálculo offline:

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path
from evals.run_local_sample import summarize
saved = json.loads(Path('docs/EVAL_LOCAL_2026-11-04.json').read_text())
for name, suite in saved['suites'].items():
    print(name, json.dumps(summarize(suite['results']), ensure_ascii=False))
PY
```

## Qué se completa y qué queda

Ya hay comparación local sobre 32 referencias y una suite suplementaria, con scores
globales/por categoría, conservación de fallos y distinción formato/calidad/latencia.
El runner es sencillo, sin framework de evals ni base de datos. La instalación
completa y ejecución desde checkout fueron verificadas; 135 tests/lint/formato
pasan tras ampliar el runner (tres tests nuevos, sin dependencias nuevas).

No se certifica rúbrica completa ni revisión humana de las 30 referencias. Los
escenarios sin objetivo único quedan en REVISION_ETIQUETAS.md, fuera del score,
hasta acordar un criterio. Seguridad sigue con heurísticas. El diagnóstico offline posterior de
SEGURIDAD_DIAGNOSTICO.md aporta expectativas y controles, separados de clasificación,
pero no prueba resistencia de modelos reales.
No se entrenó el modelo, alteraron pesos o persiguió corregir cada fallo.
La corrida no realizó commits ni push. Después se organizaron los cambios en commits
locales, sin publicación. Una posible decisión didáctica es usar v2 como
candidato a contrastar en nuevos escenarios por su global observado, dejando
expresos los retrocesos en technical/ambiguos y sin declararlo ganador definitivo.


La comparación posterior de cuatro variantes está en PROMPTS_V3_V4.md. Este informe
conserva la corrida inicial y sus números, sin sustituirla por los nuevos resultados.
