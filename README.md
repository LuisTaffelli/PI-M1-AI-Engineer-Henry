# Nubbix Support

Una CLI en Python que recibe consultas de soporte, las clasifica y propone una
respuesta y acciones para un agente humano. **No ejecuta esas acciones.**

El proyecto compara cómo distintos modelos interpretan los mismos tickets frente
a lo esperado. Conservamos prompts y resultados, incluidos los errores, sin ajustar
las versiones para que todo salga bien.

## Probarlo sin APIs

Necesitás Python 3.12 o superior. En un clon nuevo, desde la raíz del repositorio:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
make check
python -m src.main 'Me cobraron dos veces este mes.' --provider mock --mock-scenario fixed --no-metrics
```

El último comando no usa un modelo ni claves. Devuelve este JSON en stdout y un
aviso de simulación en stderr:

```json
{
  "answer": "SIMULACIÓN: recibimos tu consulta; un agente humano debe revisarla.",
  "confidence": 0.0,
  "category": "other",
  "actions": ["Revisar manualmente la consulta y asignar la categoría correcta."]
}
```

El mock siempre devuelve `other`: sirve para probar el recorrido, no para medir
clasificación. Con modelos, las categorías son `billing`, `technical`, `account`
y `other`; `confidence` es una estimación del modelo, no una probabilidad calibrada.

La consulta admite hasta **500 caracteres del texto original**, incluidos espacios
y saltos de línea. Se cuentan puntos de código Unicode, no tokens ni caracteres
visuales. Si supera el límite, se rechaza sin truncarla ni enviarla al proveedor;
`max_query_chars` permite reducirlo. Ver [detalle del guardrail](docs/ARQUITECTURA.md#límite-de-la-consulta).

## Qué comparamos

Hay adaptadores para OpenAI, Gemini y Ollama, además del mock; cuatro prompts YAML;
32 tickets sintéticos y ocho paráfrasis relacionadas. En la corrida local del
04/11/2026 con Qwen coder 0.5B, un intento y 256 tokens de salida:

| Prompt | Coincidencias en 32 tickets | Salidas válidas |
|---|---:|---:|
| v1: zero-shot | 11/32 | 31/32 |
| v2: few-shot | 18/32 | 30/32 |
| v3: estructurado | 17/32 | 32/32 |
| v4: deliberación | 13/32 | 30/32 |

Los fallos se incluyen en el total. Luis revisó y confirmó las 32 referencias del
corpus base el 05/11; esto no es un holdout ni un ranking general de modelos.
El [informe de variantes](docs/PROMPTS_V3_V4.md) detalla categorías, paráfrasis y
condiciones; la [revisión de desacuerdos](docs/REVISION_DESACUERDOS.md) explica casos concretos.

Para repetir con otro proveedor, consultá la [guía de evaluaciones](docs/EVALUACION_PROVEEDORES.md).
La [suite adversarial pareada](docs/SEGURIDAD_PAREADA.md#repetición-acotada-con-distintos-proveedores--05112026)
también admite Ollama, Gemini y OpenAI, con preview offline y un mock de prueba.
Las llamadas remotas requieren habilitación explícita y pueden tener costo.
La cota de llamadas no es un tope de gasto; los guardrails tampoco garantizan seguridad completa.

## Guías y bitácora

- [Instalación y reproducción](docs/REPRODUCIBILIDAD.md), [claves locales](docs/CLAVES_LOCALES.md) y [Ollama](docs/OLLAMA.md).
- [Arquitectura](docs/ARQUITECTURA.md) y [tokens y costos](docs/PRICING.md).
- [Dataset y criterios](data/DATASET.md), [etiquetas revisadas](docs/REVISION_ETIQUETAS.md) y [seguridad](docs/SEGURIDAD_PAREADA.md).
- [Uso de IA](docs/USO_IA.md), [muestras de métricas](docs/METRICAS_EJEMPLOS.md) y [cierre de entrega](docs/CIERRE_ENTREGA.md).
- [Bitácora del proyecto](docs/BITACORA.md): cambios, decisiones, verificaciones y registros anteriores.

La entrega aún requiere contrastar los pendientes con la consigna completa.

## Evidencia original versionada

Las [11 corridas citadas](docs/evidencia/CORRIDAS.md) se conservan directamente en
`data/local_runs/`: 56 archivos y 620 resultados, sin mirror. Los tres manifiestos
y el verificador permiten comprobarlos offline; otras salidas siguen ignoradas.
