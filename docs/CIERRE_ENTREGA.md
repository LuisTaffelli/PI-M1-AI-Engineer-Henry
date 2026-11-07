# Cierre de entrega: evidencia y decisiones pendientes

Revisión offline del 05/11/2026, con referencias académicas actualizadas el
07/11 tras consultar las páginas oficiales de Henry. Los ensayos de abajo
conservan su fecha original. Esta guía no certifica cumplimiento ni promete una nota.

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
- Revisión del 05/11: **188 tests**, lint y formato de **68 archivos** correctos con
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
4. **Ensayo offline completado; consigna oficial contrastada.**
   [Clon limpio, CLI, 188 tests, corpus y runner mock](bitacora/ENSAYO_ENTREGA_2026-11-05.md)
   verificados el 05/11 usando el venv ya instalado, sin nueva resolución de dependencias.
   El 07/11 se consultaron Entregables, Evaluación y Guía; el contraste figura abajo.
   Publicar avances y presentar el enlace académico son acciones distintas.

## Consigna oficial contrastada — 07/11/2026

- **Extra documentado: comparativa de modelos.** La [Evaluación](https://lp.soyhenry.com/share/lesson/W9H_JasyuOLs/s/lPEgXrjlgiaF)
  pide «al menos un extra credit» y lista FastAPI, caché con hash MD5,
  LLM-as-judge en runtime o comparativa de modelos. La comparación documentada de
  [OpenAI, Ollama y Gemini](RECOMENDACIONES_PROMPTS_PROVEEDOR.md) corresponde a una
  opción explícita; FastAPI no es la única alternativa. La [Guía](https://lp.soyhenry.com/share/lesson/W9H_JasyuOLs/s/67O1eXIoIT9i)
  llama opcionales a los extra credits y aclara que no reemplaza la consigna.
  Se conserva esa diferencia entre fuentes, sin prometer puntaje por el extra.
- **Guardrails.** [Entregables](https://lp.soyhenry.com/share/lesson/W9H_JasyuOLs/s/UfGW-mUVrYMR)
  exige «Al menos un guardrail de entrada (moderación / detección de injection)
  y uno de salida (validación de contenido).» No exige allí una API externa de
  moderación. [Contexto y Objetivos](https://lp.soyhenry.com/share/lesson/W9H_JasyuOLs/s/HntBLeBul283)
  mantiene el objetivo de mitigar injection y aplicar moderación de entrada y salida.
  Los controles existentes y sus bypasses se describen en [Seguridad pareada](SEGURIDAD_PAREADA.md);
  las heurísticas y el contrato JSON no demuestran moderación ni seguridad completas.
- **Presentación.** Entregables pide un enlace público a un repositorio Git
  autocontenido, ejecutable sin elementos externos no documentados. El repositorio
  está publicado; no se realizó la presentación académica en esta revisión.
- **Calendario visible.** La plataforma mostró para Proyecto integrador M1:
  «Inicio: Viernes 06/11 21:00 hs Fin: Lunes 09/11 09:00 hs».
  No mostró zona horaria; se conserva el horario tal como aparece, sin convertirlo
  ni asumir que corresponde a UTC o a la zona del equipo.

Las páginas consultadas no muestran pesos numéricos ni descriptores detallados
por nivel. Este contraste no permite calcular una nota. La evaluación Gemini
permanece cerrada con cobertura parcial; no se inició otra tanda de inferencias.

No hubo llamadas nuevas a modelos ni modificación de prompts, corpus o resultados
históricos. Cualquier nueva comparación remota debe fijar corpus, modelo, límites
y permiso de gasto; la cota de llamadas no es un tope monetario.
