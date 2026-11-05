# Bitácora de verificaciones

Registros trasladados desde las guías. Cada uno conserva su fecha y alcance:
los conteos de tests y estados de publicación describen aquella etapa.
[Volver a la bitácora](../BITACORA.md) · [README actual](../../README.md)

## Carpetas y entorno (05/11/2026)

Checkpoint de la reorganización por responsabilidades, anterior al cambio posterior
del límite de entrada a 500 caracteres:

- `make check`: 194 tests, Ruff lint y formato correctos (82 archivos Python).
  El punto de partida tenía 188 tests; se agregaron seis regresiones de arquitectura,
  carga diferida de entorno y claves programáticas explícitas.
- Se comprobaron los seis comandos históricos y los seis nuevos módulos CLI con
  `--help`, además de `src.main`, desde otro directorio y sin claves.
- Los resultados JSON de smoke mock, control de corpus y diagnóstico de guardrails
  coincidieron antes/después, excluyendo sólo timestamp y hashes de fuentes del
  diagnóstico. Trece módulos trasladados conservaron su AST salvo imports.
- SHA-256 idéntico para 85 archivos YAML/JSON/JSONL existentes de prompts, datos,
  tarifas, suites y evidencia; no se alteraron resultados ni criterios.
- Pruebas con `.env` ficticio y transportes falsos: entorno exportado incluso vacío
  tiene prioridad, mapping inyectado vacío respeta el archivo ficticio, los imports
  y previews no leen claves y `api_key=` explícita evita consultar el entorno.
- Revisión independiente de sólo lectura sin fallos funcionales. No hubo llamadas
  API o a Ollama, lectura del `.env` real, instalación, commit ni push.

El [mapa actual](../ARQUITECTURA.md) distingue clasificación, adversariales,
utilidades compartidas y CLI. Los imports internos migraron a sus nuevas familias;
los comandos y exports documentados siguen disponibles. Este checkpoint no
certifica la instalación desde cero ni los cambios posteriores de funcionalidad.

## Límite de entrada e integración (05/11/2026)

Después del checkpoint de carpetas se agregó el techo de 500 puntos de código
Unicode sobre el texto original. El trabajo integrado pasó `make check`: **208
tests**, lint y formato de 83 archivos Python, incluidos 14 nuevos tests del límite.
Se verificaron fronteras 500/501, texto Unicode sin truncar, límites menores,
rechazo antes del prompt/proveedor, prevención de bypass programático, diagnóstico,
CLI y métricas sin consulta y con cero intentos. Se usaron transportes falsos y
se bloqueó la red; no hubo inferencia real ni lectura del `.env` del checkout.

Los criterios de score no se modificaron. La política de longitud sí cambió por
pedido explícito posterior; no se presenta como equivalencia funcional del
refactor original. Los experimentos guardados conservan sus parámetros históricos.

## Arquitectura (05/11/2026)

Origen: `docs/ARQUITECTURA.md`.

## Verificación

`make check`: 188 tests, Ruff lint y formato. Se mantienen pruebas de transporte
falso, cotas, gates sin credenciales, `.env` ficticio, retries, seguridad y costos.
Se agregaron regresiones de imports legacy, `--help` de todos los comandos desde
otro directorio sin entorno de credenciales y replay exacto del reporte pareado.
El replay previo de clasificación también sigue pasando. Se verifica empaquetado
de módulos Python y navegación de enlaces; no se vuelve a instalar ni a inferir.

## Precios (05/11/2026)

Origen: `docs/PRICING.md`.

## Verificación de este incremento

185 tests, lint y formato; fixtures de ambos proveedores, múltiples intentos,
mezcla de lifetimes, rangos, ausencia de contadores, precisión Decimal, subtotales,
snapshot inmutable, preview sin claves y recálculo sin sobrescritura. Sin llamadas
pagas ni lectura del `.env` real. No hay precios externos descargados en runtime.
La modularización general queda para un incremento posterior.

## Evaluador multiproveedor (04/11/2026)

Origen: `docs/EVALUACION_PROVEEDORES.md`.

## Validación de esta implementación

Pruebas offline con transportes falsos de los adaptadores reales OpenAI/Gemini,
claves ficticias explícitas y red bloqueada: permisos, preview, reintentos,
fallos/parcialidad, privacidad de artefactos, corpus mock y compatibilidad legacy.
No se ejecutaron llamadas reales a OpenAI, Gemini ni Ollama para validar este
incremento. Por ello no se afirma disponibilidad de modelos ni calidad remota.

## Experimentos (04/11/2026)

Origen: `docs/EXPERIMENTOS.md`.

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

### Evaluación de corpus multiproveedor

El nuevo comando `python -m evals.run_provider_evals` permite seleccionar OpenAI,
Gemini, Ollama o mock y comparar los mismos prompts y referencias. Por defecto
sólo previsualiza; la ejecución remota exige dos opciones explícitas y una cota
de llamadas que incluye reintentos. Ver [guía de evaluación multiproveedor](../EVALUACION_PROVEEDORES.md) para comandos, privacidad, métricas y límites de gasto.

## Ollama (04/11/2026)

Origen: `docs/OLLAMA.md`.

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

## Reproducibilidad (04/11/2026)

Origen: `docs/REPRODUCIBILIDAD.md`.

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
de llamadas que incluye reintentos. Ver [guía de evaluación multiproveedor](../EVALUACION_PROVEEDORES.md) para comandos, privacidad, métricas y límites de gasto.

## Diagnóstico de seguridad (04/11/2026)

Origen: `docs/SEGURIDAD_DIAGNOSTICO.md`.

## Trabajo posterior: Unicode y modelo local

Se preservan arriba el protocolo y las cifras iniciales. Posteriormente se corrigió
un bypass de representación Unicode sin cambiar las frases del regex ni permitir
citas automáticamente. Se añadieron evidencias antes/después y una prueba pareada
con consultas limpias/atacadas para observar redirecciones de categoría. Ver
[SEGURIDAD_PAREADA.md](../SEGURIDAD_PAREADA.md), que distingue los denominadores y los
límites. La suite actual pasa 158 tests; no se reescriben estas observaciones previas.

## Resultados locales (04/11/2026)

Origen: `docs/RESULTADOS_EVAL_LOCAL.md`.

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



## Adversariales multiproveedor (05/11/2026)

Se amplió `evals.run_adversarial_pairs` para Gemini/OpenAI y mock, con el mismo
protocolo limpio/atacado y controles. Se preservó la invocación Ollama anterior,
y se agregó planificación offline, permisos separados y reporte de corridas parciales.
No se modificaron adaptadores, prompts, datasets, guardrails ni resultados históricos.

Verificación en el checkout de desarrollo con `make check`: **226 tests**, lint y
formato correctos (85 archivos Python). Las 18 nuevas pruebas cubren:

- Los tres adaptadores HTTP con transportes falsos: mismo texto/orden de prompts y
  consultas, 120 llamadas de servicio, 88 generaciones simuladas y 32 prebloqueos
  por proveedor para los cuatro prompts. No son mediciones de modelos reales.
- Preview y permisos sin leer claves ni acceder a red; mock marcado como simulado.
- Cotas de llamadas, un intento, límites de salida, no sobrescritura y privacidad.
- Fallos de configuración/transporte sin retry, artefactos parciales y pares sin
  ataque excluidos de elegibilidad; errores de formato no contados como defensa.
- CLI remota con ambos permisos, compatibilidad local, `--preview` explícito,
  catálogo copiado cuando se solicita y rechazo de mezclar corridas/proveedores.

El replay del JSON histórico sigue idéntico. `summary.json` añade `execution` con
cobertura y consumo aparte de `analyze(rows)`. El comentario desactualizado de
configuración sobre `.env` se corrigió; las claves siguen cargándose de forma diferida.
No hubo inferencias reales, lectura de credenciales, nuevas dependencias, commits
ni push. [Uso y límites](../SEGURIDAD_PAREADA.md#repetición-acotada-con-distintos-proveedores--05112026).

La revisión final detectó que los prebloqueos con cero intentos impedían informar
un total estimado aun teniendo consumo/precio completos de las generaciones.
Se corrigió el agregador compartido: esas filas siguen contando como procesadas,
pero no vuelven desconocido el costo de las llamadas efectivamente realizadas.
Dos regresiones, incluida una corrida pareada con transporte falso y catálogo,
comprueban el total; uso desconocido y mock siguen sin costo inventado.
También se comprobaron 228 enlaces locales, `git diff --check` y los 21 archivos
versionados JSON/JSONL/YAML de datos, prompts y resultados: idénticos a HEAD.


## Diagnóstico HTTP seguro de Gemini (05/11/2026)

Tras la prueba real inicial de cuatro tickets por proveedor, se observó un fallo
Gemini registrado como `http_error` sin número HTTP. El adaptador descartaba
`HTTPError.code` junto al resto de detalles; no hay evidencia conservada para
atribuir causa al error original. Los artefactos de esa prueba no se modifican.

Se añadió `ProviderError.http_status` con validación estricta de entero 400..599
sólo para `http_error`, su registro como `failure_http_status` y presentación
segura en la CLI. El cuerpo no se lee; URL, reason, headers y claves no se copian.
No hay retries nuevos, inferencias adicionales, lectura de credenciales reales,
instalaciones, commits ni push en esta mejora.

Comprobación posterior: `PYTHONDONTWRITEBYTECODE=1 make check`, **232 tests**
aprobados, lint correcto y 86 archivos con formato correcto. Seis tests nuevos
con transportes falsos cubren status válidos/inválidos, privacidad y cierre sin
leer cuerpo, propagación en CLI/métricas y ambos evaluadores, detención sin retry,
consumo desconocido y ausencia de status residual después de una respuesta válida.
