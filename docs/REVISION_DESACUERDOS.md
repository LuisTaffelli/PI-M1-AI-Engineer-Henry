# Revisión de etiquetas y desacuerdos: 05/11/2026

Revisión técnica offline de los 32 tickets y de resultados ya conservados.
**No se cambió ninguna etiqueta, texto, bandera, prompt o resultado histórico.**
La pasada offline no hizo inferencias ni aprobó etiquetas. **Después de la revisión,
Luis confirmó o03 como other**, por considerarlo una sugerencia de UI/UX. Ahora
hay tres confirmaciones (b07, a07 y o03) y 29 propuestas. **A05 sigue pendiente.**
La decisión exacta está en [REVISION_ETIQUETAS.md](REVISION_ETIQUETAS.md).

## Objetivo comparativo aclarado por Luis

El propósito es ver cómo interpreta cada modelo los tickets frente a lo esperado,
sea Gemini, Luna u Ollama. **No se buscan prompts que hagan que todo salga bien**:
se conservan las versiones y se registran observaciones, condiciones y límites.
Los aciertos y errores son parte del resultado, no una lista para ajustar el prompt
al corpus ni una competencia por un ganador universal.

## Conclusión y criterio

No encontré evidencia suficiente para corregir una referencia. Un desacuerdo del
modelo, incluso de los cuatro prompts, no demuestra un error de anotación.
El criterio de [DATASET.md](../data/DATASET.md) sigue siendo coherente: clasificar
la necesidad explícita, sin confundir el objeto mencionado con el pedido ni
inventar una causa. Billing cubre cargos/comprobantes/modalidad de cobro; technical,
funciones que fallan; account, acceso/autenticación/permisos; other, consultas
comerciales, aprendizaje y propuestas sin incidencia operativa declarada.

La revisión se hizo después de conocer resultados. Sirve para revisar decisiones,
no constituye anotación ciega ni transforma el corpus de desarrollo en holdout.
La [revisión por caso previa](REVISION_ETIQUETAS.md) conserva sus fundamentos.

## Dónde se equivoca el modelo y dónde falta una decisión humana

Seis tickets no coinciden con la referencia en ninguno de los cuatro prompts:

| ID | Referencia que propongo conservar | Lectura del texto y desacuerdo observado |
|---|---|---|
| b04 | billing | Pide explicar un ajuste en una factura. V1/v2 no completaron respuesta; v3 predijo technical y v4 account. No son cuatro desacuerdos de clasificación válidos. |
| a02 | account | La invitación venció y pide otra. V1/v2 technical, v3 billing, v4 other. No hay evidencia de un fallo general de invitaciones. |
| o02 | other | Consulta capacidad de CRM antes de elegir el producto. V1/v2/v3 technical y v4 billing. Preguntar por integración no significa integración rota. |
| o04 | other | Pide modo oscuro futuro. V1 technical, v2/v3 billing; v4 incompleta. No consta que la función prometida exista y falle. |
| o05 | other | Consulta programa de alianzas. V1/v2/v3 technical; v4 incompleta. Una consultora no implica un incidente técnico. |
| o07 | other | Pregunta si puede exportar antes de comprar y aclara que no tiene cuenta. V1/v2/v4 account, v3 billing. No cambiar la referencia para seguir esa mayoría. |

Estas son **propuestas de conservación**, no confirmaciones atribuidas a Luis.
Los siguientes puntos requieren separar anotación y política del producto:

| Caso | Referencia actual | Decisión o matiz |
|---|---|---|
| b01 / b05 | billing | Comprobante faltante y periodicidad de cobro. Confirmar que estos pedidos se enrutan a facturación, sin diagnosticar un error ni prometer un cambio permitido. |
| a05 | account | El objetivo es recuperar acceso; el correo no recibido puede ser síntoma técnico. Confirmar el criterio de prioridad, sin asumir una falla general de envío. |
| o03 | other | Confirmada por Luis el 05/11: mejora de UI/UX para este texto. La decisión no establece una política general para todos los problemas de accesibilidad. |
| b08 / t07 / t08 / a08 | billing / technical / technical / account | El texto distingue cargo incorrecto, sincronización, HTTP 500 compartido y bloqueo de autenticación. Propuesta razonada, aún sin confirmación individual. |
| o07 / o08 | other | Capacidad/precios antes de contratar, sin incidente ni cargo existente. La propuesta no depende de qué responda el modelo. |

`ambiguous=true` marca ocho fronteras históricas, no ocho errores ni ocho etiquetas
sin aprobar. `false` no garantiza una única interpretación: a05 conserva un matiz
por revisar; la aprobación de o03 no modifica su flag histórico. **No se cambiaron flags a posteriori.** Si se
quiere que abarque toda duda posible, definir primero ese criterio y versionar
la revisión; conservar los ocho originales al recalcular informes anteriores.

## Conteos comparables, con fallos separados

Los dos planes base tienen el mismo hash de 32 casos, mismos parámetros/fuentes
conservadas y mismo digest de Qwen. Los hashes de ambos datasets y de los cuatro
YAML siguen iguales a los de esa ejecución. Son comparables descriptivamente
entre prompts en ese modelo, no pruebas de superioridad estadística o producción.

| Prompt | Coincidencias | Clasificaciones válidas distintas | Incompletas | Total |
|---|---:|---:|---:|---:|
| v1 | 11 | 20 | 1 | 32 |
| v2 | 18 | 12 | 2 | 32 |
| v3 | 17 | 15 | 0 | 32 |
| v4 | 13 | 17 | 2 | 32 |

Los fallos permanecen en el denominador. V2 y v3 comparten 12 aciertos y nueve
casos sin acierto; sólo v2 acierta seis y sólo v3 cinco. Su diferencia global es
**un caso de 32 (3,125 puntos porcentuales)**, no acuerdo en casi todos los tickets.
V3 además elimina las dos incompletas de v2; completarlas no siempre da la categoría
esperada. No hay repeticiones ni orden aleatorio para separar variabilidad/orden.

### Paráfrasis: comparar con sus ocho originales

No enfrentar 18/32 con 4/8 como si fueran las mismas observaciones. Se emparejaron
b02, b04, t05, t06, a06, a03, o05 y o06 con las ocho reformulaciones declaradas.

| Prompt | Aciertos en esos ocho originales | Aciertos en paráfrasis | Misma categoría entre ambos válidos |
|---|---:|---:|---:|
| v1 | 4/8 | 3/8 | 5/7 |
| v2 | 4/8 | 4/8 | 3/7 |
| v3 | 4/8 | 5/8 | 4/8 |
| v4 | 4/8 | 2/8 | 3/6 |

La estabilidad no equivale a acierto: dos categorías iguales pueden estar mal.
Los denominadores de estabilidad excluyen pares con una respuesta incompleta,
pero los de acierto conservan ocho casos. En v2 el 4/8 se mantiene pese a dos
aciertos que se pierden y dos que se ganan. En v3 se gana en b04 y o05, pero se
pierde en o06. No sumar ambos conjuntos como 40 ejemplos independientes.

La corrida local conservada `luna-robustness-v1-v4-01` usó esos mismos ocho textos
reformulados y YAML, con 8/8 por variante. Permitía **1024 tokens y dos intentos**,
frente a 256 y uno en Qwen; realizó un intento efectivo por caso. Modelo, proveedor
y límites difieren, así que no es una comparación controlada de proveedores ni
una evaluación remota de 32 tickets distintos. Su fuente completa sigue ignorada
por Git; el JSON de esta revisión conserva metadata, hashes y conteos derivados.
No se volvió a ejecutar ni se usa para deshacer referencias o desempatar prompts.

## Qué propongo hacer ahora

1. Confirmar o corregir las referencias con Luis por su texto y criterio, empezando
   por los seis casos fallados por todos y el matiz de a05. O03 ya está confirmado. Revisar luego el
   resto: esta priorización no certifica automáticamente las otras etiquetas.
2. Si una etiqueta cambia, registrar versión, motivo y autor de esa decisión antes
   de nuevas inferencias. Recalcular offline como una **reanotación** explícita,
   con denominadores separados; nunca sobrescribir evidencia ni llamarla nueva corrida.
3. Explicar qué interpreta cada variante/modelo, separando categoría, formato,
   recursos y seguridad. Conservar versiones y resultados sin ajustar prompts al
   corpus ni tratar las diferencias v2/v3 como una elección de ganador.
4. Para generalización futura, preparar casos nuevos y etiquetas antes de evaluar.
   No agregar ahora ejemplos de estos desacuerdos a los YAML y reportar el mismo
   corpus como evaluación independiente.

[Auditoría derivada](REVISION_DESACUERDOS_2026-11-05.json): hashes, 32 filas con
predicciones/estados, conteos pareados y origen de cifras. Fuente local versionada:
[EVAL_PROMPTS_V34_2026-11-04.json](EVAL_PROMPTS_V34_2026-11-04.json).
No contiene tickets completos, respuestas, acciones ni credenciales. Sus campos
de confirmación humana conservan el estado **anterior** a la respuesta de Luis sobre
o03; esa aprobación posterior se registra en los documentos, sin reescribir el
snapshot de la revisión offline ni sus conteos.
