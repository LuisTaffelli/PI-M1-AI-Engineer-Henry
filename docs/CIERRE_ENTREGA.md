# Cierre de entrega: evidencia y decisiones pendientes

Revisión offline del 05/11/2026. Guía de cierre, no certificado de cumplimiento:
la rúbrica completa y el alcance de extras no están resueltos en las fuentes
locales disponibles. Evitar agregar arquitectura o modelos antes de cerrar estos puntos.

## Qué ya tiene evidencia

- CLI de cuatro campos, categorías, reparación acotada y errores sanitizados:
  `src/main.py`, `src/support/` y tests. La respuesta sólo propone acciones.
- Adaptadores OpenAI, Gemini y Ollama, además del mock. Los tests usan transportes
  falsos; pasar pruebas offline no acredita acceso actual a una cuenta o modelo.
- Corpus base: 32 casos, ocho por categoría. Revisión técnica en
  [REVISION_ETIQUETAS.md](REVISION_ETIQUETAS.md); tres confirmaciones humanas
  (b07, a07 y o03) y 29 referencias propuestas. A05 sigue pendiente. Las ocho
  paráfrasis se reportan aparte.
- Cuatro YAML y comparación local reproducible: resultados globales y por categoría
  en [PROMPTS_V3_V4.md](PROMPTS_V3_V4.md). Fallos incluidos, sin entrenamiento ni
  cambio de referencias después de ver los resultados.
- Guardrails y ensayo pareado con controles: [SEGURIDAD_PAREADA.md](SEGURIDAD_PAREADA.md).
  Hay bypass y casos de citas pendientes. Un contrato válido no demuestra seguridad.
- Uso por intento, JSONL append-only y costo estimado con catálogo fechado:
  [PRICING.md](PRICING.md). `null` significa datos insuficientes, no gasto cero.
- Instalación limpia anterior, plataforma y límites documentados en
  [REPRODUCIBILIDAD.md](REPRODUCIBILIDAD.md). No es una nueva instalación de este día.
- Revisión actual: **188 tests**, lint y formato de **68 archivos** correctos con
  el venv aislado usado para la instalación anterior. Se reprodujo el ejemplo mock
  del README sin métricas; no hubo llamadas reales, claves leídas ni dependencias nuevas.

## Próximos pasos, en orden

1. **Revisar las referencias pendientes.** Usar la [revisión de desacuerdos](REVISION_DESACUERDOS.md):
   seis casos fallados por todos, matiz de a05 y luego el resto. O03 ya fue confirmado
   como other por Luis. Conservar resultados viejos.
   Si cambia una etiqueta, versionar esa decisión y no atribuirla a la corrida anterior.
2. **Explicar la comparación, sin optimizar el score.** Luis fijó como objetivo observar
   cómo interpreta cada modelo los tickets frente a lo esperado, sea Gemini, Luna,
   Ollama u otro. Conservar los prompts y registrar coincidencias, desacuerdos, fallos
   y condiciones. No corregirlos para que todo salga bien ni buscar un ganador universal.
   La revisión de referencias tampoco se ajusta a las respuestas del modelo.
   No hace falta ejecutar otra API para discutir la evidencia disponible.
3. **Cerrar el material autocontenido.** Preparar un resumen publicable de los prompts
   de asistencia de IA y su influencia; el registro de trabajo fuera del repositorio
   no acompaña por sí solo a un clon. Revisar el README y conservar una muestra
   sanitizada de métricas con procedencia, diferenciando simulación y uso real.
4. **Ensayar y revisar antes de publicar.** Seguir instalación, CLI, control de corpus
   y runner mock. Revisar configuración, archivos previstos y diferencias de Git;
   no incorporar `.env`, pesos, consultas privadas o corridas completas sin revisión.
   Resolver con la consigna los extras, la moderación requerida y los datos de entrega.
   Publicar avances y presentar el enlace académico son acciones distintas.

Una comparación remota nueva debe fijar antes corpus, variantes, modelo, límites y
permiso de gasto. El runner tiene cota de llamadas, no tope monetario. La suite de
ocho paráfrasis no sustituye al corpus de 30+ casos ni decide por sí sola el prompt.
