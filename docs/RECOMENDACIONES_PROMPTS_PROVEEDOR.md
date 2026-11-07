# Elección de prompt según proveedor

**La recomendación provisional es `v2_few_shot` con OpenAI/gpt-6-luna.**
No trasladamos esa elección a todos los modelos. Para Ollama hay compromisos
entre aciertos, validez y robustez; para Gemini ahora hay comparación parcial,
pero todavía falta cobertura para elegir con toda la suite.
No se cambian prompts, modelos ni configuración por esta conclusión.

## OpenAI / gpt-6-luna: candidato v2 few-shot

Resultados del corpus base del 06/11, con un intento y 256 tokens máximos de salida:

| Prompt | Aciertos / 32 | Salidas válidas / 32 | Mediana | USD estimados del lote | Tokens totales |
|---|---:|---:|---:|---:|---:|
| v1 zero-shot | 32 | 32 | 2,228 s | 0,0028730 | 10.962 |
| v2 few-shot | 32 | 32 | 1,930 s | 0,0027298 | 13.722 |
| v3 estructurado | 31 | 32 | 2,487 s | 0,0039937 | 19.757 |
| v4 deliberación | 30 | 30 | 2,730 s | 0,0038433 | 16.845 |

V2 empata los 32/32 de v1 con menor latencia mediana y menor costo estimado en
esta pasada. Tiene más tokens totales que v1: el precio depende de la composición
entrada/salida y no sólo de sumarlos. Estos USD son estimaciones del catálogo
fechado, no facturas verificadas ni una garantía para futuras consultas.

Las ocho paráfrasis acertaron en las cuatro versiones; v2 registró mediana
1,862 s frente a 2,267 s de v1. En adversariales, cada versión tuvo 12 baselines
correctos y cero redirecciones dirigidas entre seis ataques elegibles válidos.
No hubo una ventaja de seguridad observada de v2 sobre las demás.

V3 tuvo un desacuerdo de categoría. Los dos no aciertos de v4 fueron fallos de
proveedor, no dos categorías alternativas. La cobertura base de v4 reúne la
corrida parcial y tres lotes disjuntos, conservando ambos fallos.
Fuentes: [informe remoto](EVALS_REMOTOS_2026-11-06.md),
[resumen y cobertura](evidencia/EVALS_REMOTOS_2026-11-06.json) y
[corridas literales](evidencia/CORRIDAS.md).

## Ollama / qwen2.5-coder:0.5b-test: compromisos, sin ganador claro

Comparación contemporánea de las cuatro variantes del 04/11:

| Prompt | Aciertos / 32 | Salidas válidas / 32 | Mediana base | Paráfrasis / 8 |
|---|---:|---:|---:|---:|
| v1 zero-shot | 11 | 31 | 0,217 s | 3 |
| v2 few-shot | 18 | 30 | 0,226 s | 4 |
| v3 estructurado | 17 | 32 | 0,291 s | 5 |
| v4 deliberación | 13 | 30 | 0,333 s | 2 |

V2 tiene un acierto más en el corpus base y menor latencia que v3. V3 conserva
32/32 salidas válidas y acierta más paráfrasis. Ninguno alcanza una precisión
alta en este corpus. El costo monetario local es desconocido, no cero.

La suite pareada observó tres redirecciones dirigidas entre cuatro ataques
elegibles válidos de v2, y una entre dos de v3. Sus baselines correctos fueron
7/12 y 4/12: los denominadores son pequeños y distintos, por lo que no permiten
proclamar un ganador de seguridad. Tampoco los 0/3 de v1 prueban seguridad general.
Fuentes: [comparación local](PROMPTS_V3_V4.md),
[seguridad pareada](SEGURIDAD_PAREADA.md) y
[carpetas históricas](evidencia/CORRIDAS.md).

## Gemini / gemini-3.5-flash-lite: v2 candidato, suite aún parcial

Las tandas anteriores del 06/11 y 07/11 con techo de 30 s quedaron parciales por
429 y se conservan intactas en [su informe](EVALS_GEMINI_RETRY_2026-11-07.md).
Después, Luis autorizó una excepción de hasta 120 s por espera, 300 s acumulados y
tres intentos. Esa [tanda nueva](EXCEPCION_GEMINI_2026-11-07.md) completó adversarial
120/120 y procesó 110/128 consultas base. Se detuvo en v4/nubbix-t06 tras tres
HTTP 503, con dos esperas de 30 s. Robustness8 no se inició.

| Prompt | Coincidencias base | Salidas válidas base | Redirecciones adversariales |
|---|---:|---:|---:|
| v1 zero-shot | 30/32 | 32/32 | 0/6 |
| v2 few-shot | 32/32 | 32/32 | 0/6 |
| v3 estructurado | 32/32 | 32/32 | 1/6 |
| v4 deliberación | 13; sólo 14 casos procesados | 13; 18 casos sin ejecutar | 0/6 |

V4 no tiene score base final: uno de sus 14 casos procesados terminó en fallo de
proveedor. V3 desvió `pair-08` de account a billing ante delimitadores falsos de
sistema, aunque su baseline era correcto. Todos los prompts acertaron 12 baselines,
prebloquearon seis ataques y tuvieron seis ataques admitidos válidos.

**V2 es un candidato con esta evidencia parcial**, pero faltan sus paráfrasis y
una comparación completa con v4. No se proclama ganador general ni se traslada
la elección de OpenAI por analogía. Las latencias incluyen retries y no se usaron
como prueba de velocidad intrínseca. No se cambian prompts, configuración ni etiquetas.

El subtotal estimado conocido de esta tanda es USD 0,0663704. El total es desconocido:
44 intentos HTTP no informaron uso. Se registraron cuatro HTTP 429 y cuarenta 503;
no se atribuye una causa específica de cuota, capacidad o facturación.
Fuentes: [informe nuevo](EXCEPCION_GEMINI_2026-11-07.md),
[resumen estructurado](evidencia/EVALS_GEMINI_EXCEPCION_2026-11-07.json) y
[manifiesto propio](evidencia/MANIFIESTO_GEMINI_EXCEPCION_2026-11-07.json).

## Qué falta para una elección más fuerte

La precisión mide categoría, no utilidad de la respuesta o acciones. Se usó un
corpus conocido y paráfrasis relacionadas, sin holdout independiente. Las
latencias corresponden a una pasada por combinación, sin aleatorizar el orden
ni aislar carga/caché. No comparamos velocidad entre equipos/proveedores como
si fueran condiciones idénticas.

Una elección más firme requiere casos nuevos etiquetados antes de evaluarlos,
varias pasadas con orden controlado, evaluación humana de respuesta/acciones
y, si se decidiera abrir un experimento nuevo, completar los datos faltantes bajo
un presupuesto autorizado. La evaluación Gemini actual está cerrada con cobertura
parcial. Estas mejoras metodológicas no son tareas programadas ni autorizan
nuevas inferencias.
