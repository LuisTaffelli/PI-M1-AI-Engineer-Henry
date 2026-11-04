# Variantes v3/v4 y comparación — 04/11/2026

Se añaden dos prompts sin sustituir v1/v2, modificar sus ejemplos, etiquetas del
corpus o pesos. La consigna disponible pide al menos dos variantes comparadas;
v3 y v4 son un experimento adicional solicitado por Luis, no requisito nuevo.
Se conserva exactamente `{answer, confidence, category, actions}` y las cuatro
categorías. No se incorporan campos de explicación ni acciones ejecutadas.

## Diferencias propuestas antes de ejecutar

| Variante | Diseño e hipótesis | Límites |
|---|---|---|
| v1_zero_shot | Referencia inicial sin ejemplos. | Sin cambios. |
| v2_few_shot | Instrucción inicial más dos ejemplos de cobros/permisos. | Sin cambios ni ejemplos tomados del corpus. |
| v3_structured | Zero-shot con secciones de rol, autoridad, criterios, incertidumbre, respuesta y contrato. Clasifica por necesidad y distingue objetos de causas hipotéticas. Se busca consistencia de formato y criterios. | Es más largo; mayor detalle no garantiza mayor acierto. No contiene tickets evaluados ni reglas especiales para un fallo individual. |
| v4_reasoning | Zero-shot orientado a modelos capaces de deliberar: objetivo y restricciones concisos, consideración de alternativas y verificación de coherencia sin imponer un guion verbal paso a paso. | No solicita razonamiento privado, borradores o cadena de pensamiento. El nombre no acredita capacidad de reasoning del modelo. |

Ambos reconocen incertidumbre y sugieren aclaraciones si falta información o hay
dos pedidos sin prioridad. No inventan una política empresarial de desempate ni
convierten automáticamente other en abstención. El contrato exige una categoría;
por eso los escenarios sin referencia única siguen fuera del score, según
REVISION_ETIQUETAS.md. Confidence es autodeclarada, no probabilidad calibrada.

V4 **sólo cambia instrucciones**. No agrega `think`, `reasoning`, esfuerzo o modos
específicos a ningún proveedor. Solicitar deliberación en un prompt y activar una
opción de una API son cosas distintas; lo segundo depende del modelo/proveedor y
no se implementó aquí. Se probó con el Qwen coder 0.5B ya disponible, sin asumir
que soporta un modo especial de razonamiento. No se evaluó un modelo de reasoning
comercial ni local diferente. No se comparó calidad de razonamiento interno.

Los criterios proceden del dominio y contrato ya documentados. El conjunto base
es conocido: antes se habían observado sus resultados y se revisaron técnicamente
sus etiquetas. No es una evaluación ciega ni holdout independiente. Para reducir
ajuste al resultado no se copiaron sus consultas a ejemplos, cambiaron etiquetas,
retocaron las nuevas versiones después de ver resultados o repitieron fallos para
mejorar el score. Eso no prueba ausencia de sesgo de desarrollo.

## Integración y comparabilidad

`src/llm/prompt_catalog.py` comparte nombres/técnicas entre cargador, Settings y
CLIs. V1 sigue por defecto y el runner local sigue comparando v1/v2 si no se eligen
versiones. `--prompt` repetible permite seleccionar variantes en el runner local;
la CLI de soporte y el runner mock aceptan una versión por invocación. El control
de solapamiento inspecciona ejemplos de las cuatro variantes. Los JSONL previos se
pueden recalcular sin perder variantes; las evidencias anteriores no se reescriben.

Se fijaron los nuevos YAML antes de la ejecución. Se hizo una pasada por combinación:
32 casos base por cada prompt y ocho paráfrasis por cada prompt. La sesión volvió
a ejecutar v1/v2 con los mismos datos y límites para tener referencias contemporáneas.
Total 160 generaciones locales, cero retries, en tres directorios nuevos. Orden:
v1 y v2 en base, v3 y v4 en base; luego v1/v2/v3/v4 en paráfrasis. Sin aleatorización,
warmup o control de carga/caché; no es un ranking general de velocidad.

Mismo tag `qwen2.5-coder:0.5b-test`, Ollama 0.40.6 y digest estable antes/después:
`08efee4699b2c84f8b793e888efd0de207bd8b00692a62337b40017048e3c075`.
Temperatura 0, 256 tokens máximos de salida, contexto 2048, timeout HTTP 30 s y un
intento total. La longitud de prompt varía como parte del tratamiento; no se puede
atribuir una diferencia sólo a “razonar más”. No se activaron precios comerciales.

## Resultados observados, no selección universal

| Medida en base | v1 | v2 | v3 | v4 |
|---|---:|---:|---:|---:|
| Coincidencias con referencias propuestas | 11/32 | 18/32 | 17/32 | 13/32 |
| Salidas validadas | 31/32 | 30/32 | 32/32 | 30/32 |
| billing | 0/8 | 6/8 | 5/8 | 2/8 |
| technical | 7/8 | 5/8 | 5/8 | 4/8 |
| account | 3/8 | 5/8 | 5/8 | 5/8 |
| other | 1/8 | 2/8 | 2/8 | 2/8 |
| Marcados ambiguos | 3/8 | 2/8 | 6/8 | 3/8 |
| Latencia mediana de servicio | 0,217 s | 0,226 s | 0,291 s | 0,333 s |
| Tokens totales derivados | 9351 | 14150 | 20403 | 16284 |

| Medida en paráfrasis | v1 | v2 | v3 | v4 |
|---|---:|---:|---:|---:|
| Coincidencias propuestas | 3/8 | 4/8 | 5/8 | 2/8 |
| Salidas validadas | 8/8 | 8/8 | 8/8 | 7/8 |
| Mediana de servicio | 0,217 s | 0,253 s | 0,312 s | 0,423 s |
| Tokens totales derivados | 2399 | 3427 | 5060 | 4265 |

V3 validó todas las salidas y coincidió más en las paráfrasis y ambiguos de esta
muestra; v2 coincidió más en el global base. V4 no mejoró aquí; no permite concluir
que el razonamiento sea inútil ni que ese modelo haya usado un modo de reasoning.
No se eligió una variante definitiva ni se alteró el default. Las referencias
siguen propuestas salvo las dos confirmaciones humanas previas, no nuevas.

Las seis incompletas están incluidas como fallos: b04 con v1/v2, t08 con v2, o04/o05
con v4 y robust-t01 con v4. No se presentan como guardrail superado ni formato
válido; no se repitieron. La suite de paráfrasis está relacionada con el base y se
reporta separadamente. USD desconocidos no equivale a costo total local cero.

[Evidencia numérica](EVAL_PROMPTS_V34_2026-11-04.json): 160 registros sin tickets o
respuestas crudas, planes, hashes, modelos y summaries; recalculables offline con
`evals.run_local_sample.summarize`. No mide tono, veracidad o utilidad de answer.
Las corridas locales ignoradas tienen prefijo `2026-11-04-v34-session-`.

## Repetición explícita

Desde checkout, con el entorno instalado y un modelo local ya disponible; elegir
siempre un directorio nuevo:

```bash
.venv/bin/python -m src.main 'Consulta sintética' --prompt v3_structured --no-metrics
.venv/bin/python -m src.main 'Consulta sintética' --prompt v4_reasoning --no-metrics
.venv/bin/python -m evals.run_local_sample --config config.ollama.example.toml \
  --all-cases --prompt v3_structured --prompt v4_reasoning --max-generations 64 \
  --output data/local_runs/NUEVO-V3-V4 --allow-local-inference
```

Los primeros dos comandos usan mock con la configuración predeterminada. El tercero
sí genera localmente. El límite de 64 por corrida se conserva: para los cuatro
prompts en 32 casos dividir en dos pares, sin subir el presupuesto silenciosamente.
Para la suite de ocho se pueden elegir los cuatro con `--diagnostic-suite` y
`--max-generations 32`. No se cambian claves, modelo ni modo del proveedor con
`--prompt`. Usar un modelo distinto requiere otra comparación documentada.


La evaluación defensiva posterior está en SEGURIDAD_PAREADA.md. No se retocaron
estos YAML después de observar los ataques. La normalización Unicode de detección
se añadió como cambio de aplicación separado; no convierte los resultados de
clasificación anteriores en pruebas de seguridad.
