# Ensayo de entrega del 05/11/2026

[Bitácora](../BITACORA.md) · [Estado de cierre](../CIERRE_ENTREGA.md)

Se creó un clon local nuevo del commit
`1d63fab46c0ec9cb30bc05dbeaf50891b9cb6e34`, sólo con archivos versionados. Se usó el
venv aislado cuya instalación ya estaba verificada, sin reinstalar o resolver
paquetes. Esto comprueba el checkout limpio, **no una instalación nueva desde PyPI**.

## Resultados

| Comprobación | Resultado |
|---|---|
| Checkout limpio y sin `.env` | Correcto antes y después; los resultados generados quedaron ignorados. |
| Entorno del proceso | Sin variables de credenciales heredadas. |
| `pip check` y pins | Sin dependencias rotas; las 44 versiones coinciden con requirements.txt. |
| Lint y formato | Correctos, 68 archivos. |
| Tests | 188 correctos. |
| CLI mock fixed | JSON válido de cuatro campos, un intento. |
| CLI mock recover_once | JSON válido después de dos intentos. |
| JSONL append-only | Dos líneas; la primera permaneció byte a byte intacta. |
| Mock malformed y consulta vacía | Código 2 esperado, stdout vacío, sin JSON falso de éxito. |
| Control del corpus | 32 casos, ocho por categoría. No aprueba referencias humanas. |
| Runner mock v1/v2 | 64 ejecuciones: 32 tickets × 2 prompts; 8/32 coincidencias por variante. Simulación, no calidad. |
| Diagnóstico de guardrails | Reporte producido; código 0 no significa protección completa. |

La [evidencia JSON](../evidencia/ENSAYO_ENTREGA_2026-11-05.json) registra commit,
versiones pertinentes, comandos/comprobaciones y hashes. Se conservó la fecha y
se omitieron el horario exacto y la versión detallada del sistema. Los logs completos permanecen en la
copia temporal del ensayo. No se hicieron inferencias locales reales o remotas,
instalaciones, descargas ni modificaciones de prompts/datasets.

## Material autocontenido preparado

Se incorporaron [uso de IA](../USO_IA.md) y [muestras de métricas](../METRICAS_EJEMPLOS.md).
El ejemplo mock procede de este ensayo; el de Ollama, de una corrida histórica.
Ambos son extractos minimizados sin UUID ni horario, con procedencia, fecha y
hashes de origen/extracto. No son copias byte a byte de los registros completos. El exportador se detuvo al encontrar campos nuevos de
consumo/costos fuera de su lista inicial; se contrastaron con el esquema antes de
exportar. No falló la aplicación ni se ocultaron resultados.

## Pendientes que este ensayo no resuelve

El ensayo no aprobó etiquetas. Después, Luis confirmó las 32 referencias del
corpus base, incluida a05; ese pendiente quedó cerrado en el
[registro de revisión](../REVISION_ETIQUETAS.md). Siguen pendientes el alcance de
extras/moderación en la consigna completa y los datos exactos del canal/horario
de entrega. No se realizó una entrega académica. Las aprobaciones individuales son trazabilidad del proyecto;
no se presentan como un requisito literal de una rúbrica completa no disponible.

## Contraste de fuentes oficiales

La lectura pública de las cinco URLs registradas no devolvió contenido utilizable
en la herramienta de búsqueda. Un GET HTTP simple a
[Entregables](https://lp.soyhenry.com/share/lesson/W9H_JasyuOLs/s/UfGW-mUVrYMR)
respondió 200, sin redirección, con el título correcto pero sólo «Cargando contenido...»
en la sección. No se observó una pantalla de login ni se concluye que el sitio esté
caído. Sin navegador, credenciales ni acceso a endpoints adicionales.

No se obtuvo una nueva consigna completa. Para cerrar el contraste hacen falta
texto/capturas completas de Entregables/Evaluación y el anuncio vigente del plazo.
No se infiere accuracy mínima de 0,70, obligación de extras ni zona horaria.

## Validación del paquete documental minimizado

Después de preparar los extractos y registrar la confirmación del corpus:

- Los hashes de fuente, selección original y extracto coinciden; quitar sólo
  `request_id` y `timestamp` reproduce todos los valores de las tres líneas.
- Corpus, paráfrasis, cuatro YAML y snapshot de desacuerdos siguen idénticos a HEAD.
- 213 enlaces/anclas locales comprobados; sin destinos faltantes ni errores de diff.
- Se repitieron `make check` y el control del corpus en el árbol de trabajo:
  188 tests, lint, formato y 32 casos correctos. No fue otro ensayo de instalación.
- Revisión de contenido y segunda lectura independiente sin nuevas citas privadas,
  secretos, identificadores personales no pertinentes ni datos privados de terceros.

El control automático declara `label_review_status=not_verified_by_this_check`:
no lee las aprobaciones documentales ni las acredita. Su aviso genérico de etiquetas
pendientes no reemplaza la confirmación humana registrada del corpus base.
