# Bitácora de verificaciones

Registros trasladados desde las guías. Cada uno conserva su fecha y alcance:
los conteos de tests y estados de publicación describen aquella etapa.
[Volver a la bitácora](../BITACORA.md) · [README actual](../../README.md)

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

