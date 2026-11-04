# Experimentos de Nubbix — preparación del 04/11/2026

El objetivo es contrastar estrategias de prompts y escenarios, conservar resultados
y explicar los errores. No se modifica un modelo ni se persigue corregir cada fallo
individual. Este documento conserva la muestra inicial y registra el plan y comparaciones posteriores;
no certifica cumplimiento académico ni elige una versión ganadora.

Actualización posterior: se ejecutaron los 32 casos base y ocho paráfrasis por
ambos prompts; resultados completos en [RESULTADOS_EVAL_LOCAL.md](RESULTADOS_EVAL_LOCAL.md).
La muestra inicial de cuatro se conserva abajo como historia. Las 32 referencias
tienen [revisión técnica](REVISION_ETIQUETAS.md), sin aprobación humana nueva.

## Estado frente a los requisitos disponibles

Las fuentes locales incluyen Contexto/Objetivos primario parcial y una síntesis de
los entregables. No hay rúbrica completa con pesos. Las rutas sugeridas por la guía
no obligan a mover nuestro corpus o runner. Viernes es el objetivo de preparación
indicado por Luis, no una fecha/zona horaria académica verificada aquí.

| Prioridad | Evidencia disponible | Trabajo que aporta más antes de entregar |
|---|---|---|
| Alta: diseño y etiquetas | 32 tickets, 8 por categoría; 2 etiquetas confirmadas y 30 propuestas. | Revisión técnica de los 32 realizada y documentada; mantener explícitas fronteras y dos confirmaciones humanas previas. No marcar una etiqueta aprobada porque el modelo coincidió. |
| Alta: comparación reproducible | Dos YAML; runner general mock y runner local optativo con comparación completa de 32 y suite de ocho paráfrasis. | Comparación local realizada con criterios previos y fallos conservados. Completar otros escenarios acordados; no presentar el corpus de desarrollo como validación independiente. |
| Alta: instalación | 132 tests/lint/formato pasan en el entorno existente. | Instalación limpia verificada después en Linux x86_64/Python 3.14.8: 44 pins exactos, Ruff, pip check y 132 tests. El entorno original conserva sólo 6/44. Mantener el recorrido desde checkout y documentar plataformas aún no probadas; ver REPRODUCIBILIDAD.md. |
| Alta: alcance de seguridad | Heurísticas de injection y posible credencial; contrato y logs sin texto. | Definir qué se espera bloquear/permitir y probar ataques, paráfrasis y consultas legítimas parecidas. Un regex no acredita moderación completa. |
| Media: observabilidad/costos | Uso por intento, latencia, JSONL y calculadora con tarifas versionadas. | Para cada experimento separar tokens/costo estimado y cargo real. Ollama conserva USD desconocidos; no equiparar ejecución local con costo total cero. No activar tarifas comerciales sin verificarlas. |
| Media: presentación | CLI y OpenAI/Gemini/Ollama, pruebas puntuales históricas y decisiones registradas. | Resumir matriz experimental, resultados/fallos y límites; revisar comandos desde clon limpio. Nuevas llamadas comerciales requieren autorización y no se hicieron. |
| Por aclarar | Extras y rúbrica incompletos en las fuentes locales. | Aclarar obligatoriedad antes de agregar FastAPI, RAG, juez u otros extras. No son el próximo paso técnico por defecto. |

## Matriz de escenarios y alcance

La síntesis exige al menos dos versiones de prompt comparadas contra un dataset
etiquetado de 30+ casos. Tener varios datasets es una forma útil de separar hipótesis,
no un requisito adicional confirmado. Mantener procedencia y objetivo de cada suite.

| Escenario | Datos y propósito | Criterio separado |
|---|---|---|
| Casos habituales | Corpus base revisado técnicamente y ejecutado; cuatro categorías y vocabulario diverso. | Exact match global/por categoría y errores de formato/transporte incluidos como fallos. |
| Fronteras | Ocho casos `ambiguous=true`, incluidos en la corrida base y reportados por separado. No se cambian sus referencias según salidas. | Matriz de confusión y motivo de la etiqueta; desacuerdo no implica automáticamente fallo del software. |
| Robustez de redacción | Ocho paráfrasis sintéticas ejecutadas en suite separada, sin copiar few-shot. Errores de escritura y múltiples motivos siguen como extensión propuesta; los sin referencia única no se puntúan. | Consistencia con una etiqueta humana previa; conservar juntos los grupos de paráfrasis para evitar contaminación entre conjuntos. |
| Seguridad | Diagnóstico offline posterior: diez ataques, cuatro controles normales, dos citas con decisión pendiente y tres fixtures de salida; ver SEGURIDAD_DIAGNOSTICO.md. No mide ataques contra modelos reales. | Bloqueo esperado, bypass y falsos positivos; no mezclar su tasa de bloqueo con accuracy de clasificación. |
| Fallos técnicos | Transportes falsos ya probados: timeout, JSON inválido, agotamiento y salida rechazada. | Código/etapa correctos, intentos acotados y privacidad; no contar como medición de calidad de un modelo. |

No hace falta multiplicar prompts indefinidamente. Primero contrastar v1 zero-shot
y v2 few-shot, registrar qué cambia y dónde difieren; una tercera estrategia sólo
si responde una pregunta concreta. Mantener los ejemplos de entrenamiento del
prompt separados de los casos evaluados. El conjunto que se use para explorar
prompts no se debe presentar luego como una validación independiente sin advertirlo.

## Runner local optativo

`evals.run_local_sample` exige `provider=ollama`, permiso explícito y una carpeta de
salida nueva. Permite de uno a cuatro IDs con presupuesto por defecto ocho, o
`--all-cases` con `--max-generations` explícito, hasta 64 por corrida. Valida el
corpus completo antes de seleccionar. `--diagnostic-suite` habilita una suite
suplementaria pequeña con las cuatro categorías, sin hacerla pasar por 30+ casos.
Por defecto compara v1 y v2; --prompt repetible permite elegir variantes v1-v4,
un intento por caso, salida de hasta 256 tokens, contexto de hasta 2048 y timeout
HTTP de hasta 30 s. Mantiene los límites menores que el TOML ya hubiera elegido.
No permite proveedores remotos ni usa `.env`, claves o tarifas comerciales.
El runner general `evals.run_evals` sigue admitiendo sólo mock.

Desde la raíz del proyecto:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m evals.run_local_sample \
  --config config.ollama.example.toml \
  --case-id nubbix-b01 --case-id nubbix-t01 \
  --case-id nubbix-a01 --case-id nubbix-o01 \
  --output data/local_runs/UNA-CARPETA-NUEVA \
  --allow-local-inference
```

Este comando sí genera texto local. No reutilizar el nombre de una corrida anterior:
fallará antes de inferir. Sin la bandera explícita también falla antes de inferir.
La CLI devuelve 2 ante errores técnicos/formato/guardrail y 0 si todas las salidas
validan; devolver 0 no significa acertar todas las categorías.

Antes de inferir guarda `plan.json` con IDs/etiquetas y hashes del corpus, prompts y
fuentes Python, además del modelo/configuración/límites efectivos. Luego conserva
`metrics.jsonl`, `results.jsonl` y `summary.json`. Los registros no incluyen tickets,
respuestas, excepciones crudas ni credenciales. El corpus y sus hashes permiten
identificar las consultas sintéticas sin copiarlas en cada log. Estas carpetas se
ignoran en Git y permanecen locales. Una interrupción conserva el plan y las líneas
ya escritas; si falta el summary, la corrida no debe presentarse como completa.

El nombre del modelo es un tag local mutable: estos hashes fijan código, corpus y
prompts, pero no los pesos. Para una comparación entre máquinas o después de cambiar
el tag también habrá que registrar el digest de Ollama y versión del servidor.

Los campos `application_contract_valid` y `application_output_guardrail_passed`
provienen de Pydantic y la heurística de nuestra aplicación, no son datos de
moderación devueltos por Ollama. Null indica que la etapa no fue observada; un
fallo previo no se convierte en un chequeo superado. La categoría sólo se conserva
si el servicio devuelve una respuesta validada. Las salidas rechazadas cuentan
como fallos del experimento. No se conserva el texto necesario para evaluar tono,
veracidad o utilidad de las respuestas: esa dimensión requeriría un protocolo
separado con datos sintéticos y criterios explícitos.

## Muestra efectivamente ejecutada

Corrida local `2026-11-04-four-categories-v1-v2`, modelo ya instalado
`qwen2.5-coder:0.5b-test`; sin descargas, entrenamiento, modificaciones de YAML o
etiquetas. Se fijaron b01/t01/a01/o01 antes de generar. Son cuatro casos normales,
no ambiguos, del corpus propuesto; el run no acredita revisión humana de etiquetas.
Orden fijo: cuatro v1 y luego cuatro v2; una generación por combinación, sin warmup,
aleatorización ni repeticiones. No es un benchmark pareado con los resultados
comerciales históricos, que usaron otros tickets/condiciones.

| Caso | Etiqueta propuesta | v1 zero-shot | v2 few-shot |
|---|---|---|---|
| nubbix-b01: comprobante fiscal faltante | billing | account | billing |
| nubbix-t01: CSV con tildes corruptas | technical | technical | technical |
| nubbix-a01: recuperación de segundo factor | account | technical | account |
| nubbix-o01: solicitar demostración comercial | other | technical | billing |

| Medida observada | v1 | v2 |
|---|---:|---:|
| Coincidencias con etiquetas propuestas | 1/4 | 3/4 |
| Contrato + guardrail propios superados | 4/4 | 4/4 |
| Errores técnicos / retries | 0 / 0 | 0 / 0 |
| Latencia mediana del servicio | 0,297 s | 0,212 s |
| Mínima–máxima | 0,221–1,423 s | 0,197–0,237 s |
| Tokens entrada / salida / total derivado | 919 / 250 / 1169 | 1459 / 205 / 1664 |
| USD estimados | desconocidos | desconocidos |

Por categoría hay una única observación por prompt; las tasas 0/1 o 1/1 no estiman
rendimiento general. v2 coincidió más en esta muestra y consumió más tokens de
entrada; no alcanza para elegir una versión definitiva. La primera solicitud v1
fue la más lenta. El orden, carga del modelo y cachés pueden influir en latencia;
no se concluye que v2 sea más rápido. Los errores quedan conservados como evidencia,
no se repitió la corrida para mejorar el resultado.

## Verificación de esta mejora

Nueve tests de este runner con transportes falsos (seis iniciales y tres para corpus/presupuesto/suite): consentimiento/proveedor/IDs/límites,
plan previo y preservación de resultados, distinción contrato/guardrail, timeout,
no sobrescritura y CLI sin permiso. Suite completa actual: 135 tests, lint y formato de
37 archivos correctos. Se añadió check_dataset(minimum_cases) para distinguir la suite suplementaria; por defecto sigue exigiendo 30. No cambian proveedores, prompts, etiquetas o pins existentes.
Estos resultados de desarrollo no equivalen a evaluación de rúbrica. La instalación
limpia se verificó posteriormente según REPRODUCIBILIDAD.md. Los cambios se organizaron posteriormente en commits locales por tema; no se hizo push.


Actualización posterior: v3/v4 agregadas con 160 generaciones locales comparables y
sin modificar resultados anteriores; ver PROMPTS_V3_V4.md. El diagnóstico de
seguridad se integró después, sin cambiar regex para mejorar sus cifras. Suite
actual de desarrollo: 158 tests. Son nuevas verificaciones, no una reescritura de
las evidencias de instalación anteriores. Nuevos cambios sin publicar.


La prueba pareada posterior añade doce consultas limpias/atacadas y controles
benignos. Se registran por separado prebloqueos, errores de base y redirecciones
observadas, sin sumar sus casos a accuracy ni elegir un prompt seguro. Una
corrección de normalización Unicode se verificó antes/después sin cambiar el texto
original que recibe el modelo. Ver SEGURIDAD_PAREADA.md para resultados y políticas
pendientes. Ninguno de estos pasos activa un modo de reasoning o modifica pesos.
