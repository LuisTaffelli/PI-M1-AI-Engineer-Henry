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

## Corrección de ubicación de la evidencia — 07/11/2026

Luis aclaró que quería commitear y pushear los casos originales citados de
`data/local_runs/`, no mantener un mirror en documentación. La asistencia revisó
privacidad e integridad, adaptó manifiestos/verificador/enlaces y preparó una
publicación limitada a esa evidencia, sin incorporar cambios previos de código
ni ejecutar más inferencias. Se preservan los resultados originales.
