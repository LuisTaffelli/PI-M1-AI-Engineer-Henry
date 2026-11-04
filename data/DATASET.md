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
etiquetas antes de ejecutar el runner sobre este corpus; al crearlo no hubo llamadas
a LLM con él. Las pruebas locales posteriores se registran en docs/RESULTADOS_EVAL_LOCAL.md. En la revisión del 04/11/2026 Luis confirmó nubbix-b07=billing y
nubbix-a07=account. Las otras 30 etiquetas siguen propuestas, incluidas las seis
fronteras restantes analizadas abajo por IA. La corrección del formato no demuestra
que una etiqueta sea correcta ni constituye aprobación humana.

## Contrato por línea

- case_id: identificador estable y único, como nubbix-b01.
- query: único dato del caso que el runner envía al servicio.
- expected_category: billing, technical, account u other.
- label_reason: razón de la etiqueta propuesta; nunca se agrega al prompt.
- ambiguous: booleano explícito. true marca una frontera entre categorías, incluso
  cuando su etiqueta ya fue confirmada; no es un estado de aprobación, una segunda
  etiqueta ni autorización para cambiar la referencia después de ver resultados.

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

## Revisión de las ocho fronteras — 04/11/2026

Luis confirmó los dos ejemplos de factura/importes y factura/acceso porque la
necesidad cambia según el texto. Aplicamos esa misma lectura al resto: objetivo
principal explícito antes que palabra clave o causa técnica hipotética. La tabla
distingue confirmación humana de revisión razonada del asistente.

| ID | Etiqueta vigente | Necesidad que determina la propuesta | Estado de revisión |
|---|---|---|---|
| nubbix-b07 | billing | Revisar el importe por descuento faltante; el supuesto fallo es una hipótesis. | Confirmada por Luis. |
| nubbix-b08 | billing | Revisar un cargo tras bajar de plan; el acceso funciona y no pide cambiar permisos. | Consistente con el criterio; propuesta IA, sin confirmación individual. |
| nubbix-t07 | technical | Corregir sincronización: pago confirmado y comprobante correcto, sin importe cuestionado. | Consistente; propuesta IA, sin confirmación individual. |
| nubbix-t08 | technical | Reportar HTTP500 compartido al ingresar; no pide recuperar contraseña ni autorización. | Consistente; propuesta IA, sin confirmación individual. |
| nubbix-a07 | account | Revisar autorización de acceso a una factura existente. | Confirmada por Luis. |
| nubbix-a08 | account | Recuperar acceso bloqueado tras intentos; no describe error del servidor ni deuda. | Consistente; propuesta IA, sin confirmación individual. |
| nubbix-o07 | other | Consultar capacidad de exportación antes de comprar; no hay exportación fallida. | Consistente; propuesta IA, sin confirmación individual. |
| nubbix-o08 | other | Comparar precios/prestaciones antes de contratar; no hay un cobro en disputa. | Consistente; propuesta IA, sin confirmación individual. |

Las cuatro categorías y ejemplos de sincronización de pagos, permisos y consultas
comerciales proceden de la consigna disponible. Priorizar la necesidad expresada
y estas resoluciones particulares son criterios de anotación nuestros; sólo b07 y
a07 tienen confirmación humana individual registrada. No se transfirió esa
confirmación a las otras seis fronteras ni a los 24 casos no marcados.

**Resultado de la revisión:** se conservan las ocho etiquetas y todos los textos.
Los seis casos restantes expresan una necesidad principal suficiente para aplicar
el criterio actual; no requieren inventar una regla de desempate nueva. No se
cambió el JSONL ni ambiguous=true: la frontera temática persiste aunque dos
etiquetas se hayan aprobado. El conteo de ocho ambiguos del runner sigue siendo
correcto y no significa ocho etiquetas sin revisar.

**Decisiones que sí quedarían abiertas con otros textos:** si sólo dijera «no puedo
entrar» o mezclara dos pedidos principales (por ejemplo, revisar importe y recuperar
acceso), el contrato sólo admite una category. Habría que acordar cuándo pedir
aclaración y qué prioridad usar; no hay una política de desempate oficial en las
fuentes disponibles. Esos escenarios no están presentes en estos seis tickets y
no se resolvieron silenciosamente al revisarlos. Clasificar tampoco comprueba la
causa real del HTTP500 ni autoriza reembolsos o desbloqueos: esas acciones requieren
sus propias verificaciones/políticas, fuera de esta revisión.

Las justificaciones completas están en cada línea. Los 24 casos no marcados
siguen pendientes de revisión humana; ambiguous=false no certifica ausencia de
dudas. Si Luis cambia una etiqueta, registrar el motivo antes de usar nuevas salidas para
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
balance y lista de fronteras marcadas, no aprobación humana ni procedencia del contenido.
El estado de revisión parcial se conserva en esta tabla; el check no lo interpreta.
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

La revisión técnica posterior de los 32 casos está en docs/REVISION_ETIQUETAS.md;
conserva todas las referencias y no las presenta como aprobadas por una persona.
Sólo b07/a07 tienen confirmación humana previa. El runner general sigue mock y el
runner local optativo ahora admite comparar el corpus completo con presupuesto
explícito. La suite suplementaria eval_robustness.jsonl tiene ocho paráfrasis con
referencias propuestas; no sustituye el mínimo de 30 ni es un holdout independiente.
Las consultas sin objetivo único figuran aparte, sin imponerles una etiqueta.
Resultados y límites: docs/RESULTADOS_EVAL_LOCAL.md. La comparación local no certifica
calidad general ni completa la revisión humana o la rúbrica.
