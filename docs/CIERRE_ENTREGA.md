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
  [REVISION_ETIQUETAS.md](REVISION_ETIQUETAS.md); Luis confirmó las 32 referencias
  el 05/11, incluida a05=account. Las ocho paráfrasis se reportan aparte. La revisión
  humana posterior no convierte el corpus de desarrollo en evaluación ciega.
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

## Estado de los cuatro puntos

1. **Referencias: revisión técnica y confirmación humana completas para el corpus base.**
   Luis confirmó las 32 etiquetas, incluida a05=account, después de leer el dataset.
   Los [desacuerdos y matices](REVISION_DESACUERDOS.md) quedan documentados; no se
   cambiaron categorías, textos ni flags. Esta aprobación es trazabilidad del
   proyecto, no una exigencia literal verificada de aprobación individual ni una
   nueva medición de calidad.
2. **Comparación: documentada sin optimizar el score.**
   Se explica cómo interpretó cada variante los casos, separando categoría, formato,
   fallos y condiciones. [Informe y pares de paráfrasis](REVISION_DESACUERDOS.md).
   Se conservan versiones y resultados, sin retocar prompts ni elegir ganador universal.
3. **Material autocontenido: preparado.**
   [Uso de IA](USO_IA.md) registra instrucciones y su influencia.
   [Muestras de métricas](METRICAS_EJEMPLOS.md) distinguen extractos de dos requests
   mock nuevos y una línea histórica real de Ollama. Se retiraron identificadores
   y horarios; se conservan procedencia, hashes y valores técnicos sin texto privado.
   `null` sigue significando desconocido, no costo cero.
4. **Ensayo offline: completado; contraste académico pendiente.**
   [Clon limpio, CLI, 188 tests, corpus y runner mock](bitacora/ENSAYO_ENTREGA_2026-11-05.md)
   verificados usando el venv ya instalado, sin nueva resolución de dependencias.
   Falta contrastar extras, moderación y datos de entrega con la consigna completa.
   Publicar avances y presentar el enlace académico son acciones distintas.

No hubo llamadas nuevas a modelos ni modificación de prompts, corpus o resultados
históricos. Cualquier nueva comparación remota debe fijar corpus, modelo, límites
y permiso de gasto; la cota de llamadas no es un tope monetario.
