# Bitácora de Nubbix Support

Acá queda el recorrido del proyecto. El [README](../README.md) explica cómo usarlo;
las guías describen funcionamiento y experimentos. Estos registros conservan lo que
se hizo y verificó en cada etapa, incluso cuando después cambió el estado.

## 05/11/2026: decisiones y revisión documental

- Revisión offline de los resultados conservados: 32 casos, cuatro variantes y
  ocho paráfrasis. Se separaron desacuerdos de clasificación y respuestas incompletas.
  [Análisis y evidencia](REVISION_DESACUERDOS.md).
- Luis confirmó o03 como `other`, por interpretar la sugerencia de contraste como
  mejora de UI/UX. En ese momento quedaban b07, a07 y o03 confirmados; a05 seguía pendiente.
  [Registro y criterio](REVISION_ETIQUETAS.md).
- Objetivo aclarado: observar cómo interpreta cada modelo los tickets frente a las
  referencias. No retocar prompts para maximizar aciertos ni buscar un ganador universal.
- A pedido de Luis, el README pasa a ser una entrada práctica. Los changelogs y
  checkpoints se reúnen acá; sus contenidos originales siguen accesibles abajo.
  Los YAML, datasets, métricas y JSON de resultados no se modificaron.
- Validación al cierre: 188 tests, lint y formato correctos; 186 enlaces/anclas
  locales verificados, ejemplo mock reproducido y contenido trasladado comprobado.
  En ese cierre los cambios seguían locales, antes de la publicación registrada abajo.

## 05/11/2026: publicación y ensayo del entregable

- Publicados con autorización los commits daf2131 (revisión/evidencia), 4895a0b
  (bitácora) y 1d63fab (README). El HEAD remoto se verificó igual a 1d63fab.
- [Ensayo offline en un clon limpio](bitacora/ENSAYO_ENTREGA_2026-11-05.md): 188 tests,
  dependencias verificadas y 64 ejecuciones mock, sin llamadas a modelos.
- Preparados [uso de IA](USO_IA.md) y [ejemplos de métricas](METRICAS_EJEMPLOS.md),
  con procedencia y límites. Son materiales nuevos posteriores a esos tres commits.

## 05/11/2026: confirmación del corpus y minimización del material nuevo

- Luis confirmó las 32 referencias del corpus base después de leerlo, incluida
  a05=account. Se actualizó el estado en las guías sin cambiar datos, flags, prompts
  ni resultados. El snapshot de la revisión offline conserva su estado histórico.
- El registro de IA resume pedidos y decisiones sin copiar conversaciones privadas.
  Las muestras JSONL omiten identificadores de request y horarios; el ensayo omite
  la versión detallada del sistema. Los originales locales se conservan y la
  procedencia distingue hashes de origen y de los extractos minimizados.
- Esta actualización y el material de cierre permanecen locales, pendientes de
  revisión para publicación. No hubo nuevas inferencias ni una entrega académica.

## 05/11/2026: carpetas de evaluación y entorno centralizado

- Las evaluaciones comunes viven en `evals/classification/` y las de seguridad en
  `evals/adversarial/`. `common/` contiene persistencia/costos y `cli/` los argumentos
  y salidas. Los comandos anteriores quedan como entradas pequeñas compatibles.
- `src/runtime/environment.py` concentra la lectura del entorno y `.env`;
  configuración TOML y rutas tienen responsabilidades separadas. Se conservan
  precedencia, carga diferida y ausencia de cambios globales al entorno.
- [Arquitectura y recorridos](ARQUITECTURA.md), [claves locales](CLAVES_LOCALES.md)
  y [uso de IA](USO_IA.md) actualizados. [Checkpoint del refactor](bitacora/VERIFICACIONES.md#carpetas-y-entorno-05112026):
  194 tests, lint/formato, equivalencia offline y 85 archivos de datos intactos.
  Ese checkpoint es anterior al nuevo límite de 500 caracteres.
- Cambios locales, sin commit/push ni inferencias. Se preservó el trabajo documental
  previo; el aviso del control automático de etiquetas no cambió en este refactor.

## 05/11/2026: límite explícito de entrada

- A pedido de Luis, la consulta tiene un techo de 500 puntos de código Unicode del
  texto original, sin truncar. La configuración puede reducirlo, no ampliarlo.
- El rechazo ocurre antes de cargar prompts, construir adaptadores o inferir. La
  CLI explica el máximo sin repetir el texto; métricas registran cero intentos.
- [Comportamiento y límites](ARQUITECTURA.md#límite-de-la-consulta) y
  [verificación integrada](bitacora/VERIFICACIONES.md#límite-de-entrada-e-integración-05112026):
  208 tests, lint y formato correctos. Sin llamadas a modelos ni cambios en corpus,
  prompts o resultados históricos. Sigue siendo una protección acotada.

## 05/11/2026: adversariales también con Gemini y OpenAI

- A pedido de Luis, el protocolo pareado ya admite Gemini/OpenAI, Ollama y mock.
  Mismos casos/prompts, un intento, cota explícita y preview sin claves ni red.
- Se conserva el comando Ollama previo. Los remotos requieren `--execute` y
  `--allow-remote-inference`; un error técnico conserva una corrida parcial.
- [Comandos y límites](SEGURIDAD_PAREADA.md#repetición-acotada-con-distintos-proveedores--05112026)
  y [checkpoint](bitacora/VERIFICACIONES.md#adversariales-multiproveedor-05112026):
  226 tests, lint y formato correctos. Adaptadores probados con transportes falsos;
  no son nuevos scores de modelos reales. Sin APIs, claves, commits ni push.

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

## 07/11/2026: evidencia en su ubicación original

Por aclaración de Luis, se reemplazó el mirror por los archivos originales de
17 corridas en `data/local_runs/` (90 archivos, 924 resultados). Se conservaron
bytes, timestamps, errores y costos desconocidos; los manifiestos, enlaces y
verificador apuntan a esa única ubicación. `.gitignore` permite sólo los archivos
inventariados. No se hicieron inferencias ni se reanudó Gemini. Los cambios
previos de código, retry HTTP y reorganización de tests quedan fuera de este commit.
