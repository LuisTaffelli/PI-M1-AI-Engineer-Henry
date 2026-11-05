# Bitácora de Nubbix Support

Acá queda el recorrido del proyecto. El [README](../README.md) explica cómo usarlo;
las guías describen funcionamiento y experimentos. Estos registros conservan lo que
se hizo y verificó en cada etapa, incluso cuando después cambió el estado.

## 05/11/2026: decisiones y revisión documental

- Revisión offline de los resultados conservados: 32 casos, cuatro variantes y
  ocho paráfrasis. Se separaron desacuerdos de clasificación y respuestas incompletas.
  [Análisis y evidencia](REVISION_DESACUERDOS.md).
- Luis confirmó o03 como `other`, por interpretar la sugerencia de contraste como
  mejora de UI/UX. Quedan b07, a07 y o03 confirmados; a05 sigue pendiente.
  [Registro y criterio](REVISION_ETIQUETAS.md).
- Objetivo aclarado: observar cómo interpreta cada modelo los tickets frente a las
  referencias. No retocar prompts para maximizar aciertos ni buscar un ganador universal.
- A pedido de Luis, el README pasa a ser una entrada práctica. Los changelogs y
  checkpoints se reúnen acá; sus contenidos originales siguen accesibles abajo.
  Los YAML, datasets, métricas y JSON de resultados no se modificaron.
- Validación al cierre: 188 tests, lint y formato correctos; 186 enlaces/anclas
  locales verificados, ejemplo mock reproducido y contenido trasladado comprobado.
  Los cambios documentales siguen locales, sin commit ni push.

## Recorrido por etapas

- **24/10: primera CLI y contrato.** [Verificación inicial](bitacora/HISTORIAL_README.md#verificación-ejecutada--24102026).
- **30/10: proveedor simulado, configuración y retry.** [Segundo incremento](bitacora/HISTORIAL_README.md#segundo-incremento--frontera-proveedorservicio-30102026).
- **31/10: organización, dependencias y YAML.** [Refactor inicial](bitacora/HISTORIAL_README.md#verificación-del-refactor-modular--31102026) y [migración de prompts](bitacora/PROMPTS.md#migración-de-formato--31102026).
- **03/11: reparación, APIs y corpus.** [Feedback de reparación](bitacora/HISTORIAL_README.md#incremento-local-feedback-de-reparación--03112026), [OpenAI](bitacora/HISTORIAL_README.md#adaptador-openai-checkpoint-exclusivamente-offline--03112026), [Gemini](bitacora/HISTORIAL_README.md#gemini-equivalente-sólo-probado-offline--03112026) y [dataset](bitacora/HISTORIAL_README.md#dataset-de-evaluación-preparado-offline--03112026).
- **04/11: reproducción y experimentos.** [Instalación y runners](bitacora/VERIFICACIONES.md#reproducibilidad-04112026), [Ollama](bitacora/VERIFICACIONES.md#ollama-04112026), [cuatro prompts](PROMPTS_V3_V4.md) y [seguridad pareada](SEGURIDAD_PAREADA.md).
- **05/11: costos y modularización.** [Verificaciones de precios](bitacora/VERIFICACIONES.md#precios-05112026), [refactor por responsabilidades](bitacora/VERIFICACIONES.md#arquitectura-05112026) y [arquitectura actual](ARQUITECTURA.md).

Las frases “pendiente”, “sin publicar” y los conteos de tests de los archivos
históricos corresponden a su momento. No describen por sí solos el estado actual.

## Registros por tema

- [Historial completo de incrementos del README](bitacora/HISTORIAL_README.md), con índice por sección.
- [Hipótesis y cambios de prompts](bitacora/PROMPTS.md).
- [Decisiones de nomenclatura y checkpoints](bitacora/NOMENCLATURA.md).
- [Verificaciones trasladadas desde las guías](bitacora/VERIFICACIONES.md).
- [README anterior a esta reorganización](bitacora/README_ANTES_DE_REORGANIZAR.md).
- [Inventario de traslados y hashes](bitacora/TRASLADOS_2026-11-05.json), para comprobar que se preservó la información.

Las rutas antiguas de historial, nomenclatura y changelog de prompts conservan un
acceso a su nueva ubicación. Los comandos históricos se mantienen como evidencia;
para ejecutar hoy, usar el README y las guías actuales.
