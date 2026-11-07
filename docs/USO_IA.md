# Uso de IA en el proyecto

Nubbix Support se desarrolló con asistencia de IA para proponer implementación,
pruebas, documentación y análisis de resultados. Este registro resume instrucciones
verificables y su influencia; no pretende ser una transcripción de todas las sesiones.
Luis decide el alcance y los criterios del trabajo. La asistencia no acredita por
sí sola calidad, cumplimiento académico ni comprensión de cada decisión.

## Dónde intervino

- Estructura de la CLI, contrato Pydantic, adaptadores, reparación y pruebas offline.
- Borradores de prompts y tickets sintéticos, con justificaciones de referencia.
- Herramientas de evaluación, contadores/costos y conservación de evidencia.
- Revisión de resultados, modularización y organización de documentación.

Los tests contrastan comportamiento concreto; no convierten datos propuestos por
IA en etiquetas humanas ni los scores del mock en calidad de un LLM.

## Pedidos y decisiones que orientaron el trabajo

Los siguientes puntos son resúmenes, no citas del chat ni una atribución de autoría
línea por línea.

- **Carga de claves, 04/11/2026.** Se pidió carga automática desde `.env`. Se incorporó
  lectura diferida de la clave seleccionada, con precedencia del entorno y pruebas
  con valores ficticios. No se ejecuta `.env` como script ni se consultan credenciales
  en previews. Ver [claves locales](CLAVES_LOCALES.md).
- **Criterio de o03, 05/11/2026.** Luis confirmó other para la sugerencia de mayor
  contraste de gráficos, por considerarla una mejora de UI/UX. El criterio se aplica
  a ese texto, sin excluir de technical toda falla de accesibilidad.
- **Propósito experimental, 05/11/2026.** Se aclaró que el objetivo es comparar cómo
  los modelos interpretan los tickets frente a las referencias. Se conservan
  versiones y desaciertos, sin ajustar los prompts para maximizar el score del corpus.
- **Documentación, 05/11/2026.** Se pidió una entrada legible y un historial separado.
  El README presenta uso y resultados; la [bitácora](BITACORA.md) conserva los cambios.
- **Revisión del corpus, 05/11/2026.** Luis confirmó las 32 etiquetas del corpus base
  después de leerlo, incluida a05=account. Se registró la aprobación sin cambiar
  textos, categorías, banderas de ambigüedad ni resultados previos.

- **Modularización, 05/11/2026.** Se pidió agrupar el código por responsabilidad,
  centralizar el entorno y distinguir evaluaciones comunes de adversariales. La
  asistencia propuso e implementó `classification/`, `adversarial/`, `common/` y
  `cli/`, junto con un único lector de entorno y `.env`. Se preservaron comandos,
  carga diferida y criterios de evaluación, sin ajustar prompts ni datasets.
  El [mapa de arquitectura](ARQUITECTURA.md) muestra cómo seguir cada recorrido.

- **Límite de entrada, 05/11/2026.** Se pidió un máximo de 500 caracteres para la
  consulta. Se concretó como 500 puntos de código Unicode originales, con rechazo
  previo a inferencia, sin truncar y con configuración sólo hacia abajo. Se agregaron
  pruebas de fronteras y Unicode; no se atribuye una garantía general de seguridad.

- **Adversariales multiproveedor, 05/11/2026.** Se pidió evaluar los mismos ataques
  también con Gemini y OpenAI. Se amplió el runner común, sin retocar prompts ni
  datasets: preview sin claves, permisos explícitos, un intento, cota acotada y
  resultados por proveedor/modelo. Las pruebas usan transportes falsos y mock;
  no se atribuyen nuevas mediciones de resistencia a modelos reales.

## Decisiones y límites visibles

- Las 32 referencias base tienen confirmación humana registrada en la
  [revisión](REVISION_ETIQUETAS.md). La aprobación es posterior a los experimentos;
  no convierte la evaluación en ciega ni valida todas las respuestas del modelo.
- El corpus y las paráfrasis son sintéticos y de desarrollo, no un holdout ciego.
- Los hashes actuales del corpus, sus paráfrasis y los cuatro YAML coinciden con
  los de las corridas conservadas del 04/11. Esta comprobación se refiere a esas
  versiones, no afirma que nunca hubo iteraciones anteriores.
- Formato válido, clasificación, seguridad y costos se informan por separado.
- Las [muestras de métricas](METRICAS_EJEMPLOS.md) son extractos minimizados: no
  incluyen identificadores de request, horarios, tickets, respuestas, acciones ni claves.
- La documentación de uso de IA no sustituye la explicación y revisión del alumno.

La bitácora y los commits permiten seguir cambios y verificaciones. El
[informe de desacuerdos](REVISION_DESACUERDOS.md) muestra observaciones que se
conservaron en lugar de corregir referencias para favorecer al modelo.


## Evaluaciones reales y evidencia — 06/11/2026

Luis pidió ejecutar adversariales OpenAI/Gemini, después los datasets y dejar
muestras simples de métricas. La asistencia preparó previews y ejecutó los cuatro
prompts sin alterarlos: un intento, salida máxima de 256 tokens y límites explícitos.
Gemini quedó parcial tras HTTP 429, sin retry; su clasificación no se inició.
OpenAI completó adversarial y robustness. La base se reunió a partir de la corrida
original y tres lotes de casos no ejecutados, sin repetir los dos fallos ni superar
128 intentos. No se retocaron etiquetas para mejorar el resultado.

Se conservaron desacuerdos, consumo desconocido, resultados originales y hashes.
El sample legacy y los fixtures de guardrails se evaluaron offline, sin presentarlos
como calidad de modelos. Se prepararon [informe y evidencia](EVALS_REMOTOS_2026-11-06.md)
y siete muestras minimizadas con procedencia. No hubo commit, push o entrega de
esta tanda. Cualquier implementación posterior de retries se verifica por separado;
no cambia estas observaciones ni autoriza repetirlas automáticamente.


## Reintentos HTTP y comandos de reproducción — 06/11/2026

Luis pidió respetar Retry-After cuando la espera fuera razonable y aclarar en README
cómo usar cada proveedor, evaluar datasets y ejecutar ataques. La asistencia
propuso e implementó una política opt-in: hasta tres intentos HTTP por ronda,
30 s por espera y 60 s acumulados por consulta, separada de reparación JSON.
Se reintentan sólo 429/500/502/503/504, se rechazan esperas excesivas sin recortarlas
y no se repiten resultados inciertos de transporte ni respuestas incompletas.
Se amplió el diagnóstico seguro de OpenAI y se corrigió el código de salida del
pareado cuando el último caso falla en proveedor/configuración.

Los presupuestos previos incluyen las llamadas extra y las métricas mantienen
consumo desconocido en los fallos, aunque una llamada posterior se recupere.
Se documentaron previews, permisos y ejecución por proveedor/corpus. Esta mejora
se implementó después de terminar la tanda remota y se comprobó offline; no alteró
prompts, datasets, resultados previos ni generó nuevas llamadas reales.
Ver [diseño, límites y pruebas](REINTENTOS_HTTP.md).


## Organización de tests — 06/11/2026

Luis pidió: «Me da un poco de toc, pero, podemos separar los tests en categorias
por carpetas? o responsabilidades? Gracias». La asistencia agrupó los 26 archivos
en siete responsabilidades, sin dividir sus clases ni cambiar sus fixtures o
assertions. Sólo se ajustó la profundidad de dos rutas basadas en `__file__` y se
agregaron `__init__.py` para el descubrimiento recursivo con `unittest`.

Se conservaron los mismos 256 casos: comparación de IDs antes/después ignorando
únicamente el nuevo prefijo de carpeta. `make check`, cada grupo aislado, el filtro
anterior por archivo y un caso por módulo pasaron. La [guía de tests](../tests/README.md)
explica dónde agregar pruebas y cómo ejecutarlas. No cambió el código de producción,
no hubo inferencias reales ni modificaciones de resultados, commit o push.


## Conservación literal de corridas y elección provisional

Luis pidió conservar las carpetas con las métricas citadas, además de su
procedencia, y explicar en README qué prompt se considera más viable. La
asistencia revisó los registros y conservó 14 corridas históricas del 04/11 y
06/11: 75 archivos y 671 resultados, sin modificar bytes, horarios, fallos ni
valores desconocidos. Se agregaron manifiesto SHA-256, guía y verificador offline.

La recomendación se limitó a v2 few-shot con OpenAI/gpt-6-luna en la muestra
observada: empata 32/32 con v1 y tiene menor latencia mediana; no se trasladó
a todos los proveedores ni cambió la configuración. La comparación con una
nueva suite Gemini queda separada de esta evidencia histórica. Se conservaron
los cambios preexistentes del proyecto, sin llamadas a modelos ni publicación
durante esta preparación.

La nueva corrida Gemini del 07/11 se archivó por separado con cinco archivos
literales y 23 resultados. La asistencia documentó los compromisos por proveedor
sin declarar ganador Gemini ni Ollama; la recomendación OpenAI sigue provisional.


## Excepción Gemini y nueva tanda — 07/11/2026 UTC

Luis aprobó excepcionalmente hasta 120 s por espera, 300 s acumulados por consulta
y tres intentos. La asistencia implementó un opt-in exclusivo de runners Gemini,
con una ronda JSON, defaults conservados, segundos normalizados sin headers crudos
y 13 regresiones offline nuevas. `make check` aprobó 269 tests y revisión estática.
La tanda completó adversarial y parte de base32; se detuvo ante el tercer HTTP 503
en v4/nubbix-t06, sin iniciar robustness8. Se preservaron resultados y errores,
sin ajustar los prompts o etiquetas para mejorar scores, ni publicar o hacer push.
La [evidencia y sus límites](EXCEPCION_GEMINI_2026-11-07.md) distingue los 503 de los
429 y corrige el diagnóstico intermedio que confundía algunas esperas de 30 s.

## Corrección de ubicación de la evidencia — 07/11/2026

Luis aclaró que quería commitear y pushear los casos originales citados de
`data/local_runs/`, no mantener un mirror en documentación. La asistencia revisó
privacidad e integridad, adaptó manifiestos/verificador/enlaces y preparó una
publicación limitada a esa evidencia, sin incorporar cambios previos de código
ni ejecutar más inferencias. Se preservan los resultados originales.

## Precisión del alcance de evidencia — 07/11/2026

Luis corrigió la selección de 17 corridas y pidió sólo las mencionadas en los
archivos de evidencia. La asistencia separó las referencias reales de los
inventarios circulares: mantuvo 11 carpetas citadas en los JSON de procedencia
o informes de `docs/evidencia` y retiró seis del versionado conservando los
originales locales. Cada corrida seleccionada ahora señala su referencia exacta;
ni manifiestos ni documentación general amplían el alcance.


## Revisión y publicación de pendientes — 07/11/2026

Luis pidió: «Pushea y commitea lo que falte, yo creo que ya esta todo por lo que
veo, no se si falto un punto del PI». La asistencia revisó los cambios locales,
los separó por responsabilidad y validó tests, formato, enlaces y manifiestos
antes de publicar. Se aclaró el estado histórico de los informes sin modificar
sus resultados. Se mantuvo la decisión de conservar el historial Git y la
selección de 11 corridas, sin reintroducir las seis excluidas ni un mirror.
La revisión no abrió otra tanda Gemini, no ejecutó inferencias ni equivalió a
una entrega académica o certificación de la consigna completa.


## Menú de terminal opcional — 06/11/2026 Argentina (07/11 UTC)

Luis pidió una mini TUI para probar tickets en loop y ejecutar datasets o ataques
más fácilmente, dejando la publicación para otro día. La asistencia propuso e
implementó un menú numerado con biblioteca estándar que reutiliza el servicio y
los planes/runners existentes, sin cambiar prompts, datasets, scoring ni CLI.

Se priorizó mock al iniciar, consultas independientes, límite original de 500
caracteres, configuración sólo de sesión y preview con opt-in por cada corrida.
OpenAI/Gemini requieren escribir REMOTO; el límite de llamadas no es un tope en
USD. Ctrl+C/EOF no provocan reenvíos ni reanudación y se advierte de consumo y
artefactos incompletos cuando una solicitud pudo haber empezado. La revisión
independiente mejoró el mensaje de guardrail de salida para no ocultar el posible
consumo. No se guardaron claves ni se ejecutaron inferencias reales.

Se añadieron 27 pruebas offline de interacción, permisos, límites, cancelación y
artefactos parciales. `make check` pasó 296 tests, lint y formato. Se ensayó además
la entrada real de terminal con mock, retorno al menú, Ctrl+C y Ctrl+D. La
[guía de uso](TUI.md) documenta alcance y límites; esta etapa quedó sin commit/push.
