# Corpus sintético propuesto para Nubbix — 03/11/2026

`eval_dataset.jsonl` contiene 32 tickets escritos con asistencia de IA para este
proyecto: ocho billing, ocho technical, ocho account y ocho other. No contiene
exportaciones de soporte, personas, claves ni datos de clientes reales. Se creó
por separado de los cuatro ejemplos legacy de `eval_sample.jsonl`, que se conservan.
No se reutilizaron el ticket de cobro duplicado de las pruebas remotas ni las dos
consultas few-shot. El vocabulario de una categoría puede repetirse; no se pretende
que facturación o permisos sean temas exclusivos de un conjunto.

La síntesis local de consigna pide al menos 30 casos etiquetados y scores globales
y por categoría. Los ocho casos por categoría, IDs, justificaciones y banderas de
ambigüedad son decisiones pedagógicas nuestras. No constituyen nombres exigidos
por la rúbrica ni una distribución observada del tráfico real. Se fijaron estas
etiquetas antes de ejecutar el runner sobre este corpus; **no hubo llamadas a LLM
con él**. Todas las etiquetas son propuestas de IA pendientes de revisión de Luis.
La corrección del formato no demuestra que una etiqueta sea correcta.

## Contrato por línea

- case_id: identificador estable y único, como nubbix-b01.
- query: único dato del caso que el runner envía al servicio.
- expected_category: billing, technical, account u other.
- label_reason: razón de la etiqueta propuesta; nunca se agrega al prompt.
- ambiguous: booleano explícito. true marca una frontera a revisar, no una segunda
  etiqueta ni una autorización para cambiar la referencia después de ver resultados.

El loader mantiene compatibilidad con el sample anterior, cuyos casos sólo tienen
query y expected_category. El control estricto del corpus exige los metadatos.

## Criterio propuesto de etiquetado

Se prioriza el objetivo explícito del pedido, sin decidir sólo por palabras clave:

| Categoría | Criterio de trabajo |
|---|---|
| billing | Cobros, importes, comprobantes fiscales y modalidades de facturación. |
| technical | Fallas del producto, API, exportación o sincronización. |
| account | Autenticación, sesiones, incorporación/baja de acceso y permisos. |
| other | Consultas comerciales, aprendizaje y propuestas de capacidades nuevas. |

Estos criterios se apoyan en las categorías y ejemplos de la consigna, pero las
resoluciones de frontera son anotación propuesta, no respuestas oficiales. No se
inventan políticas de reembolso, plazos ni permisos empresariales.

## Ocho fronteras para revisar con Luis

| ID | Propuesta | Frontera / decisión |
|---|---|---|
| nubbix-b07 | billing | Descuento ausente frente a posible bug: el pedido es revisar importe, no una causa confirmada. |
| nubbix-b08 | billing | Cambio de plan frente a cobro: pide revisar precio, su acceso funciona. |
| nubbix-t07 | technical | Pago frente a sincronización: el importe está correcto; pide reparar estado integrado. |
| nubbix-t08 | technical | Login frente a servidor: error HTTP500 compartido, no recuperación de acceso. |
| nubbix-a07 | account | Factura frente a autorización: el documento existe; falla el permiso del solicitante. |
| nubbix-a08 | account | Bloqueo de autenticación frente a falla técnica: pide recuperar acceso. |
| nubbix-o07 | other | Exportación frente a consulta de capacidad previa a comprar; no hay falla. |
| nubbix-o08 | other | Precios frente a facturación: todavía no es cliente ni tiene un cargo cuestionado. |

Las justificaciones completas están en cada línea. Los 24 casos no marcados
también requieren revisión; ambiguous=false no certifica ausencia de dudas. Si
Luis cambia una etiqueta, registrar el motivo antes de usar nuevas salidas para
comparar prompts. No ajustar la referencia para favorecer al proveedor observado.

## Controles offline

Desde la raíz del proyecto:

```bash
.venv/bin/python -m evals.run_evals --dataset data/eval_dataset.jsonl --check-dataset
.venv/bin/python -m evals.run_evals --dataset data/eval_dataset.jsonl --prompt v1_zero_shot
.venv/bin/python -m evals.run_evals --dataset data/eval_dataset.jsonl --prompt v2_few_shot
```

El primer comando sólo comprueba datos/prompts, sin cargar claves, crear proveedor
ni inferir. Exige 30 o más casos, las cuatro categorías, IDs/consultas únicos,
metadatos explícitos y separación de los ejemplos de ambas variantes. Informa
balance y lista de ambiguos, no aprobación humana ni procedencia del contenido.
Normaliza caja, tildes, puntuación y espacios para detectar coincidencias. No
reconoce paráfrasis o duplicados semánticos: sigue haciendo falta revisión humana.

Los otros dos comandos siguen siendo **mock**, bloquean proveedores remotos y no
usan red ni métricas de requests. La ejecución por defecto sin --dataset conserva
el sample de cuatro para compatibilidad. El corpus con metadatos también pasa el
control antes de ejecutar el mock. Un --check-dataset sobre el sample falla porque
no cumple 30 ni metadatos; no se lo renombra para aparentar un conjunto completo.

## Qué significa Exact Match aquí

Cada salida válida recibe 1 si response.category == expected_category y 0 si no.
El score global es aciertos / todos los casos; el score por categoría usa los casos
con esa etiqueta de referencia. Los fallos de validación/proveedor cuentan como
0 y se informan como errors, no se eliminan del denominador. Los ocho ambiguos se
incluyen con su referencia propuesta y el reporte muestra ambiguous_total=8.

No se comparan literalmente answer o actions. Tampoco se mide utilidad de la
respuesta, seguridad completa, explicación, calibración de confidence, corrección
de la justificación ni calidad general del modelo. No hay LLM-as-Judge. Con sólo
ocho ejemplos por categoría, un caso mueve ese score 12.5 puntos porcentuales.
El balance facilita inspeccionar clases; no estima directamente desempeño bajo
una distribución de producción desconocida.

El mock fijo devuelve other siempre: debe dar 8/32 = 0.25, other=1.0 y las otras
tres=0.0, tanto en v1 como v2. Eso comprueba la tubería; no permite elegir prompt,
comparar proveedores ni presentar una evaluación real del PI.

## Separación y próximas decisiones

No copiar tickets de evaluación a examples de los YAML. Si en el futuro se usan
estos 32 para ajustar o seleccionar prompts, pasan a ser un conjunto de desarrollo;
para medir generalización sin ese sesgo hará falta otro conjunto reservado, con
etiquetas fijadas antes de evaluar. No se afirma un holdout ciego hoy: el mismo
asistente ayudó a escribir prompts y corpus. El check de coincidencias detecta
copias normalizadas, no garantiza independencia semántica.

Primero revisar las ocho fronteras y las demás etiquetas, después acordar diseño
de comparación, presupuesto y autorización. El runner aún no habilita evals con
LLM reales. Este incremento prepara datos y controles, no completa la comparación
empírica ni la selección final de prompt que pide la consigna.
