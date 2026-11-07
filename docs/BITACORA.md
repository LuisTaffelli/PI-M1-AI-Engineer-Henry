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

## 06/11/2026: evaluaciones remotas y métricas simples

- [Informe de ejecución](EVALS_REMOTOS_2026-11-06.md), con resultados y cobertura
  completa por prompt/categoría, limitaciones y hashes anteriores a retries HTTP.
- OpenAI: adversarial 120 invocaciones/88 generaciones; base32 con cobertura de
  128 intentos en corridas disjuntas, dos fallos preservados; robustness8×4 completo.
  Gemini: adversarial parcial tras 18 intentos, HTTP 429; matrices no iniciadas.
- 266 generaciones remotas, sin retries. Subtotal estimado conocido USD 0,0304696;
  total desconocido por el consumo no informado del 429. No es factura.
- Siete [muestras de métricas](METRICAS_EJEMPLOS.md#inferencias-remotas--06112026)
  con selección, campos y hashes verificables. Sample legacy y dos suites de
  guardrails cubiertos offline; no se modificaron prompts, datasets ni código
  durante la tanda. `make check` previo: 232 tests, lint y formato correctos.
- Esta tanda y su documentación quedan locales, sin commit, push ni entrega.

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


## 06/11/2026 — Retry-After acotado y comandos claros

- Pedido: respetar Retry-After con esperas razonables y documentar cómo usar los
  proveedores y evaluar corpus/paráfrasis/ataques. La implementación comenzó sólo
  después del cierre de las inferencias, con su evidencia preservada.
- Política opt-in: 1..3 intentos HTTP por ronda (predeterminado 1), 30 s por espera
  y 60 s acumulados sólo de espera por consulta. Acepta delta-segundos, IMF-fixdate,
  RFC 850 y asctime HTTP en GMT. Si excede el techo, no recorta ni reintenta temprano.
  Sin header válido: backoff 1/2 s con jitter de hasta 0,25 s. Sólo 429/500/502/503/504.
- No repite timeout/transporte incierto, salida incompleta/refusal, ni guardrails;
  reparación JSON sigue separada. Las cotas incluyen todos los intentos potenciales,
  con techo 384 en runners. No hay tope monetario. Cada error sin usage sigue
  desconocido, aunque una llamada posterior recupere la respuesta.
- OpenAI conserva status HTTP y códigos locales seguros. El pareado devuelve 2
  con fallo terminal de proveedor/configuración también en el último caso.
- README incluye comandos por proveedor, datasets, pareados, preview, permisos,
  cotas y enlaces. Nueva guía REINTENTOS_HTTP explica responsabilidades y métricas.
- Verificación final: make check pasó 256 tests, lint y formato de 89 archivos;
  incluye 24 pruebas nuevas de retry. Una revisión independiente detectó el formato
  asctime sin zona y se corrigió con regresión; también se verificó la ventana
  móvil de 50 años de RFC 850 en lugar del corte fijo del parser de correo. Se comprobaron 11 comandos del
  README offline, con red/claves bloqueadas y consultas sustituidas por mock sin
  escribir métricas. Enlaces relativos y git diff --check correctos.
- No se tocaron prompts, datasets ni corridas anteriores. Sin nuevas inferencias,
  lectura de secretos, commit o push. HEAD permanece f83113b.


## 06/11/2026 — Tests por responsabilidad

- Se movieron los 26 módulos a siete carpetas: `integration`, `providers`, `prompts`,
  `guardrails`, `service`, `runtime` y `evaluation`. [Mapa y comandos](../tests/README.md).
- `unittest` sigue descubriendo los mismos 256 casos, sin pérdidas ni duplicados.
  Sólo cambiaron dos referencias a la profundidad de `__file__`; los demás tests
  conservaron su contenido. No se tocaron fixtures, fuentes, prompts ni resultados.
- `make check` antes y después: 256 tests, lint y formato correctos. También pasaron
  los siete grupos aislados, el filtro antiguo `-p test_http_retry.py`, un caso por
  módulo y el descubrimiento desde la raíz. Los comandos generales no cambiaron.
- Se preservaron los cambios locales anteriores de retry, evaluaciones y métricas.
  Sin inferencias reales, commit ni push.


## Evidencia literal de las corridas del 04/11 y 06/11

- Se preservaron 14 carpetas en [corridas originales](evidencia/CORRIDAS.md): 75
  archivos y 671 resultados (~1,8 MB), byte a byte desde los originales locales.
  Incluyen planes, métricas, resultados, resúmenes y snapshots/precios existentes.
- Se mantuvieron UUID locales, timestamps, errores y costos desconocidos, sin
  tickets, respuestas, datos personales ni credenciales. El manifiesto registra
  hashes, tamaño, mtime y origen; Git no preserva mtime en futuros clones.
- [Guía y verificación](evidencia/CORRIDAS.md): todos los hashes coinciden y
  métricas/resultados se cotejaron fila a fila. Los 35 archivos remotos coinciden
  además con los hashes del informe anterior; las siete muestras se reconstruyen
  literalmente por selección de campos, sin modificar las muestras.
- El verificador pasó en una copia sin originales; detectó contenido alterado,
  archivos faltantes/extra y discrepancias de métricas aun con hash actualizado.
  Ruff del script y `make check` correctos: 256 tests y 98 archivos formateados.
  `git diff --check` correcto.
- README recomienda v2 few-shot provisionalmente para OpenAI/gpt-6-luna, sin
  generalizar a Gemini/Ollama ni cambiar defaults. La futura tanda Gemini se
  documentará aparte. Sin cambios de retry, inferencias nuevas, commit o push
  en esta conservación.

La corrida Gemini posterior del 07/11 quedó en un archivo y manifiesto separados:
cinco archivos, 23 resultados, 92.905 bytes. El verificador admite `--manifest`
para comprobarla sin mezclarla con el histórico. Se agregó
[comparación por proveedor](RECOMENDACIONES_PROMPTS_PROVEEDOR.md): OpenAI v2
provisional, Ollama con compromisos y Gemini inconcluso. Ambos archivos de
evidencia se cotejaron con sus originales y conservan los fallos.

## 07/11/2026: evidencia en su ubicación original

Por aclaración de Luis, se reemplazó el mirror por los archivos originales de
17 corridas en `data/local_runs/` (90 archivos, 924 resultados). Se conservaron
bytes, timestamps, errores y costos desconocidos; los manifiestos, enlaces y
verificador apuntan a esa única ubicación. `.gitignore` permite sólo los archivos
inventariados. No se hicieron inferencias ni se reanudó Gemini. Los cambios
previos de código, retry HTTP y reorganización de tests quedan fuera de este commit.

## 07/11/2026: reducción a referencias explícitas

Luis precisó que no quería conservar las 17 carpetas: sólo las citadas por los
archivos JSON de procedencia e informes de `docs/evidencia`, sin usar manifiestos
o documentación general para ampliar el conjunto. Quedan 11 carpetas, 56 archivos
y 620 resultados. Se retiraron seis carpetas del índice de Git, sin borrar sus
34 archivos locales ni cambiar sus bytes. Se ajustaron selección, manifiestos,
enlaces y verificación. No se hicieron inferencias ni se reescribió el historial.


## 07/11/2026: revisión final de los cambios pendientes

- Luis pidió commitear y pushear lo pendiente, manteniendo el historial existente.
  Se separaron la organización de tests (`4694955`), el retry HTTP y la excepción
  acotada Gemini (`e3ecd19`), y la documentación de uso/resultados.
- Se verificó cada árbol de código aislado del checkout: 232 tests después de
  mover los tests y 269 después de incorporar retry, con lint y formato correctos.
  También pasaron los 14 tests del verificador de evidencia.
- Los tres manifiestos validaron bytes, mtime, métricas y resúmenes: 11 corridas,
  56 archivos y 620 filas. No se agregaron corridas, mirrors ni archivos de secretos;
  las seis carpetas excluidas siguen fuera del árbol versionado.
- Se comprobaron 11 comandos de aplicación del README con red y lectura de claves
  bloqueadas: consultas sustituidas por mock sin métricas, runners en preview.
  No se repitió la instalación ni hubo inferencias reales.
- Enlaces y anclas locales correctos; se aclararon frases históricas sobre ausencia
  de publicación. Los informes siguen distinguiendo resultados parciales,
  costos desconocidos y controles offline de inferencias reales.
- Gemini queda cerrado con cobertura parcial. Publicar los avances no reanuda
  pruebas, no certifica una rúbrica incompleta ni realiza una entrega académica.
