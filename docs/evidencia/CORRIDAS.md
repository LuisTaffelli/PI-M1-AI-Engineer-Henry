# Corridas originales versionadas

La evidencia se conserva directamente en [`data/local_runs/`](../../data/local_runs/),
sin mirror: **11 corridas, 56 archivos y 620 resultados** (2.194.373 bytes).
Los archivos originales no se modificaron. Las excepciones de `.gitignore` permiten
sólo los archivos inventariados; otras corridas, scripts de sesión y futuras salidas
siguen ignorados. No se ejecutaron inferencias para preparar esta publicación.

## Criterio de selección y referencias

Sólo se mantienen carpetas mencionadas explícitamente en los JSON de procedencia
o informes de esta carpeta. **Los manifiestos y este índice no son una fuente
independiente para incluir corridas**, ni basta una mención en documentación general.
Cada entrada del manifiesto señala el documento y JSON Pointer que la justifican:

- [Procedencia remota](PROCEDENCIA_METRICAS_REMOTAS_2026-11-06.json), `rows[].source`:
  cuatro corridas del 06/11: adversarial OpenAI/Gemini y base/paráfrasis OpenAI.
- [Procedencia previa](PROCEDENCIA_METRICAS_2026-11-05.json),
  `ollama.source_local_untracked`: `2026-11-04-v34-session-v1-v2`.
  El nombre histórico del campo se conserva, aunque esa fuente ahora está versionada.
- [Informe remoto](EVALS_REMOTOS_2026-11-06.json), `supplemental_runs[].run_dir`:
  los tres lotes OpenAI `base32-v4-remaining-1/2/3`.
- [Informe Gemini retry](EVALS_GEMINI_RETRY_2026-11-07.json), `suites[0].output`:
  `2026-11-07-gemini-adversarial-v1-v4-http3`.
- [Informe Gemini excepción](EVALS_GEMINI_EXCEPCION_2026-11-07.json),
  `suites[0/1].output`: adversarial y base32 `exception-01`.

Se retiraron del versionado seis carpetas Ollama sin una referencia explícita en
esos JSON de evidencia. Sus originales siguen en disco, ignorados por Git.
No se agregaron destinos sólo planificados, ensayos de otro clon ni la carpeta
offline-datasets citada únicamente por comandos: esta corrección reduce la
selección anterior, no incorpora resultados nuevos.

## Índice de evidencia

Cada corrida conserva `plan.json`, `metrics.jsonl`, `results.jsonl` y `summary.json`.
También se incluyen `pricing.json` y snapshots del modelo cuando existían.

### Histórico del 04/11 y 06/11: 8 corridas, 367 resultados

- [2026-11-04-v34-session-v1-v2](../../data/local_runs/2026-11-04-v34-session-v1-v2/)
- [2026-11-06-gemini-adversarial-v1-v4](../../data/local_runs/2026-11-06-gemini-adversarial-v1-v4/)
- [2026-11-06-openai-adversarial-v1-v4](../../data/local_runs/2026-11-06-openai-adversarial-v1-v4/)
- [2026-11-06-openai-base32-v4-remaining-1](../../data/local_runs/2026-11-06-openai-base32-v4-remaining-1/)
- [2026-11-06-openai-base32-v4-remaining-2](../../data/local_runs/2026-11-06-openai-base32-v4-remaining-2/)
- [2026-11-06-openai-base32-v4-remaining-3](../../data/local_runs/2026-11-06-openai-base32-v4-remaining-3/)
- [2026-11-06-openai-eval_dataset-v1-v4](../../data/local_runs/2026-11-06-openai-eval_dataset-v1-v4/)
- [2026-11-06-openai-eval_robustness-v1-v4](../../data/local_runs/2026-11-06-openai-eval_robustness-v1-v4/)

[Manifiesto histórico](MANIFIESTO_CORRIDAS_2026-11-06.json).
OpenAI base32 se interrumpió con v4: los lotes `remaining-1/2/3` contienen los diez
casos pendientes, sin repetir ni ocultar errores. Gemini quedó parcial por HTTP
429 con 23/120 consultas. La corrida Ollama conservada es la fuente explícita
de la muestra histórica del 05/11; no se suman experimentos distintos.
Los [comandos y cobertura remotos](EVALS_REMOTOS_2026-11-06.json) son históricos,
no instrucciones para repetir llamadas sobre esos destinos.

### Gemini del 07/11: tandas independientes

- [2026-11-07-gemini-adversarial-v1-v4-exception-01](../../data/local_runs/2026-11-07-gemini-adversarial-v1-v4-exception-01/)
- [2026-11-07-gemini-adversarial-v1-v4-http3](../../data/local_runs/2026-11-07-gemini-adversarial-v1-v4-http3/)
- [2026-11-07-gemini-base32-v1-v4-exception-01](../../data/local_runs/2026-11-07-gemini-base32-v1-v4-exception-01/)

- [Retry acotado](MANIFIESTO_GEMINI_RETRY_2026-11-07.json): cinco archivos y 23
  resultados. HTTP 429 con espera superior al límite; no se hizo retry ni se inició
  clasificación. [Reporte](EVALS_GEMINI_RETRY_2026-11-07.json).
- [Excepción 120/300](MANIFIESTO_GEMINI_EXCEPCION_2026-11-07.json): diez archivos y
  230 resultados. Adversarial completo, base32 parcial tras tres HTTP 503 y
  paráfrasis sin iniciar. [Reporte](EVALS_GEMINI_EXCEPCION_2026-11-07.json).

Estas tandas no reemplazan los fallos previos ni autorizan reanudar Gemini.

## Verificación offline desde un clon

Con Python 3.12 o superior, desde la raíz del repositorio:

```bash
python docs/evidencia/verificar_corridas.py
python docs/evidencia/verificar_corridas.py --manifest MANIFIESTO_GEMINI_RETRY_2026-11-07.json
python docs/evidencia/verificar_corridas.py --manifest MANIFIESTO_GEMINI_EXCEPCION_2026-11-07.json
```

El verificador comprueba el inventario de cada carpeta, tamaños, SHA-256, JSON/JSONL,
métricas/resultados fila a fila, UUID locales únicos y medidas de los resúmenes.
También valida la referencia explícita de cada corrida en un documento de
evidencia permitido, los hashes históricos remotos y las siete muestras minimizadas.
No importa la aplicación, no lee `.env`, no crea proveedores y no usa la red.

Los manifiestos usan rutas relativas a la raíz del repositorio. Conservan el mtime
observado, pero **Git no conserva mtime al clonar**. `--check-mtime` sólo sirve en
el equipo que conserva esos tiempos (`--compare-originals` es un alias compatible).
Los timestamps dentro del JSON y los bytes originales sí se conservan.
Los planes registran el código histórico: sus hashes no necesariamente coinciden
con el checkout publicado, y esta publicación no incluye los cambios de retry
HTTP ni la reorganización de pruebas que siguen en preparación local.

## Privacidad y límites

La revisión de los 56 archivos no encontró consultas, respuestas crudas, acciones,
datos personales, información de salud, credenciales ni rutas privadas. Los
`request_id` son UUID aleatorios locales, no IDs de cuenta o credenciales.
Se conservan los casos sintéticos, horarios, fallos, valores `null` y estimaciones
de costo. Los snapshots sólo contienen metadatos técnicos del modelo.

No se publican `.env`, scripts de sesión ni otros experimentos. Los extractos
minimizados anteriores permanecen para mostrar unas pocas líneas; no son un mirror.
Un prebloqueo no llama al modelo y `status=ok` no significa acierto de categoría.
Los hashes demuestran integridad respecto del inventario, no autenticidad externa,
seguridad general ni calidad de las respuestas. No es una nueva evaluación.
