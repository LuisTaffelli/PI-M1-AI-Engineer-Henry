# Revisión de referencias

## Confirmación humana del corpus base: 05/11/2026

Luis confirmó las **32 etiquetas del corpus base** después de leer el dataset,
incluida **nubbix-a05 = account**. Antes se habían confirmado b07, a07 y o03;
la aprobación completa cierra las 29 referencias que seguían propuestas.

Para o03 se mantiene el criterio explícito de Luis: el mayor contraste de los
gráficos es una mejora de UI/UX en este ticket y se conserva **other**. No es una
regla universal que excluya problemas de accesibilidad de technical.

La aprobación no cambia textos, categorías ni flags de `data/eval_dataset.jsonl`,
YAML o resultados históricos. Se mantienen ocho `ambiguous=true` y 24 `false`.
La revisión humana fue posterior a conocer resultados: no se presenta como ciega
ni como una aprobación de las respuestas de los modelos. Los fundamentos técnicos
de abajo explican las referencias; no son citas ni razonamientos atribuidos a Luis.

## Objetivo comparativo aclarado por Luis: 05/11/2026

Se busca observar cómo interpreta cada modelo los tickets frente a las referencias,
independientemente del proveedor. No retocar prompts para que todas las respuestas
coincidan ni maximizar el score. Las versiones y resultados se conservan; se explican
los desacuerdos con condiciones y límites. La aprobación posterior del corpus no permite cambiar etiquetas para favorecer
las respuestas observadas.

## Revisión técnica original: 04/11/2026

Revisión realizada por el asistente sobre los 32 tickets sintéticos y el criterio
propuesto en data/DATASET.md. **No es validación humana nueva ni respuesta oficial
de la consigna.** Sólo nubbix-b07 y nubbix-a07 tenían confirmación individual de
Luis registrada antes de esta revisión; las otras 30 referencias seguían propuestas.
La confirmación humana posterior de las 32 está registrada arriba; se conserva
esta cronología para no atribuir aprobación a la revisión técnica original.

No se modifican textos, etiquetas ni flags del JSONL. La referencia sigue siendo
el objetivo principal expresado, no una palabra aislada ni una causa hipotética.
El dominio, contrato y categorías proceden de las fuentes disponibles; los
desempates de negocio son decisiones de anotación propias y siguen sujetos a revisión.

Antes de esta revisión ya se habían visto salidas reales para b01/t01/a01/o01, en
ambos prompts. Por tanto no es revisión ciega. Se fija esta revisión antes de la
comparación completa y de la suite suplementaria; no se ajustan etiquetas según
sus resultados. Corpus y prompts son conjuntos de desarrollo asistidos por IA,
no un holdout independiente que permita afirmar generalización.

## Revisión por caso

Esta tabla conserva los fundamentos de la revisión técnica original. En ese
momento sólo b07/a07 tenían aprobación humana; el 05/11 Luis confirmó las 32
referencias. Las condiciones alternativas indican qué dato adicional podría
cambiar la interpretación; no afirman que ese dato esté presente.

| ID | Referencia conservada | Fundamento y cautela |
|---|---|---|
| b01 | billing | Pide comprobante fiscal faltante. Podría haber un fallo de visualización, pero no está reportado como necesidad principal; no diagnosticarlo. |
| b02 | billing | Corrección de razón social del comprobante; distinguirla de cambiar el usuario o email de acceso. |
| b03 | billing | Consulta por nota de crédito pendiente. No afirmar emisión ni política de devoluciones. |
| b04 | billing | Pide explicar un concepto ya facturado, no cotizar una contratación. |
| b05 | billing | Solicita cambio de periodicidad de cobro. Frontera de gestión de plan: conservar por objetivo explícito sin asumir que el cambio está permitido. |
| b06 | billing | Regularizar pago rechazado por banco. No hay evidencia de fallo general del gateway. |
| b07 | billing | Revisar descuento/importe; una causa técnica es hipótesis. Confirmación previa de Luis, no transferible a otros casos. |
| b08 | billing | Revisar precio cobrado tras bajar de plan; el texto aclara que el acceso funciona. Frontera marcada con account. |
| t01 | technical | Corrupción de caracteres al importar. No asumir una codificación o solución concreta sin diagnóstico. |
| t02 | technical | HTTP 500 generalizado en API. No inferir causa, plazo o incidente oficialmente declarado. |
| t03 | technical | Panel no termina de cargar para varias personas; no es un pedido explícito de permisos. |
| t04 | technical | Webhook antes operativo dejó de llegar. El origen podría ser cliente o servidor, pero la necesidad es diagnóstico de integración. |
| t05 | technical | Exportación queda detenida incluso con pocos datos. |
| t06 | technical | Filtro devuelve estados incompatibles con lo pedido. |
| t07 | technical | Reconciliar sincronización con pago/comprobante correctos; no revisar importe. Frontera marcada con billing. |
| t08 | technical | HTTP 500 compartido después de autenticar; no recuperar contraseña. Frontera marcada con account. |
| a01 | account | Recuperar segundo factor perdido. Nunca equivale a autorizar saltarse verificación de identidad. |
| a02 | account | Reemitir invitación vencida. Si nuevas invitaciones siempre vencieran al instante podría investigarse una falla, pero no se afirma aquí. |
| a03 | account | Cambiar correo de ingreso; no dirección fiscal del comprobante. |
| a04 | account | Dar de baja acceso de integrante. Acciones sólo sugeridas, sujetas a autorización humana. |
| a05 | account | Recuperar usuario/contraseña; falta el correo de recuperación. **Frontera latente no marcada**: podría ser technical con evidencia de falla de entrega general. No resolver causa por suposición ni cambiar el flag después de ver salidas. |
| a06 | account | Cerrar sesiones de un usuario, con verificación correspondiente. |
| a07 | account | Revisar autorización sobre factura existente; el objeto “factura” no convierte el pedido en billing. Confirmación previa de Luis. |
| a08 | account | Recuperar acceso bloqueado por intentos, sin fallo de servidor declarado. Frontera marcada con technical. |
| o01 | other | Demostración antes de contratar. No asumir cuenta existente ni apertura de incidente. |
| o02 | other | Consulta de capacidad de integración antes de elegir herramienta; no integración rota. |
| o03 | other | **Confirmada por Luis el 05/11/2026**: interpreta esta sugerencia de contraste como mejora de UI/UX. Se conserva other sin extender el criterio a toda falla de accesibilidad. |
| o04 | other | Solicitud de modo oscuro futuro; sería distinto si una función existente hubiera dejado de funcionar. |
| o05 | other | Alianza comercial de consultoría, fuera de las tres clases operativas. |
| o06 | other | Material o capacitación general, no incidente concreto. |
| o07 | other | Capacidad de exportar antes de comprar; no exportación fallida. Frontera marcada con technical. |
| o08 | other | Comparación de precios antes de ser cliente; no cargo existente en disputa. Frontera marcada con billing. |

“ambiguous=false” no prueba ausencia de interpretaciones alternativas. Se conservan
los ocho flags definidos previamente para mantener trazabilidad; el reporte separa
“marcados ambiguos” y “no marcados”, no certeza frente a incertidumbre absoluta.
Las fronteras adicionales b01/b05/a02/a05 quedan documentadas como matices, con
sus etiquetas ya confirmadas. La aprobación no cambia los flags históricos.

## Escenarios sin una etiqueta única fijada

Estos ejemplos se preparan como preguntas de diseño, **fuera del denominador de
accuracy**. No se los incorporó como tickets artificialmente etiquetados:

| Consulta sintética | Por qué no fijar aún una única referencia | Qué aclarar |
|---|---|---|
| “No puedo entrar.” | Falta mecanismo/error; acceso individual o fallo del producto son compatibles. | Mensaje exacto y si afecta a otras personas. |
| “Revisen el cobro y desbloqueen mi cuenta; ambos me urgen.” | Dos objetivos explícitos sin prioridad. | Qué resolver primero o si el producto debería separar tickets; el contrato actual sólo admite una categoría. |
| “Mi factura desapareció.” | Puede faltar emisión, acceso o visualización; no especifica objetivo. | Si existe para otra persona y si hay error/permisos. |
| “Quiero cambiar de plan.” | No aclara si es cotización, cobro o acceso. | Situación actual y cambio deseado. |

No se agregó categoría “ambiguous” ni se inventó una política automática de
abstención. Si se decide evaluar aclaraciones, fijar antes criterios para answer y
revisión humana: el runner actual sólo puntúa categoría, formato y estados técnicos.
No mide calidad de las respuestas abiertas ni verifica afirmaciones de negocio.

## Suite de robustez preparada

`data/eval_robustness.jsonl` contiene ocho paráfrasis sintéticas (dos por categoría)
con referencias técnicas propuestas y metadatos compatibles. Su procedencia es
explícita: deriva de los objetivos de b02/b04/t05/t06/a06/a03/o05/o06. Es un conjunto
suplementario relacionado con el base, **no ocho observaciones independientes de
producción ni un holdout**. No hay etiquetas humanas nuevas ni ejemplos few-shot
copiados. No modifica el corpus mínimo de 32.

Comparar cada prompt sobre ambas suites ayuda a describir sensibilidad al texto.
Reportar cada suite por separado, sin sumar 32+8 para aparentar más independencia.
Los casos de seguridad requieren otra referencia (bloqueo/bypass/falso positivo),
no mezclar su tasa de bloqueo con exact match de clasificación.


## Revisión de desacuerdos del 05/11/2026

[La revisión posterior](REVISION_DESACUERDOS.md) cruza las 32 referencias con
las cuatro variantes conservadas y empareja las ocho paráfrasis con sus originales.
Se preservan etiquetas y flags y se separan respuestas incompletas de
clasificaciones distintas. El informe distingue el análisis original de la
confirmación humana posterior, sin reescribir sus resultados.
