# Nombres, decisiones y checkpoints históricos

Archivo histórico. Describe el estado de cada etapa, no instrucciones actuales.
[Volver a la bitácora](../BITACORA.md) · [README actual](../../README.md)
Las rutas escritas en comandos siguen referidas a la raíz del repositorio.

## Navegación

- [Refactor modular — 31/10/2026](#refactor-modular--31102026)
- [Pendientes](#pendientes)
- [Checkpoint local OpenAI — 03/11/2026](#checkpoint-local-openai--03112026)
- [Checkpoint Gemini — 03/11/2026](#checkpoint-gemini--03112026)
- [Corpus de 32 casos — 03/11/2026](#corpus-de-32-casos--03112026)
- [Estado de publicación — 03/11/2026](#estado-de-publicación--03112026)
- [Consumo normalizado — 04/11/2026](#consumo-normalizado--04112026)
- [Precios de texto estándar — 04/11/2026](#precios-de-texto-estándar--04112026)
- [Proveedor local — 04/11/2026](#proveedor-local--04112026)

# Correspondencia de nombres y alcance — 31/10/2026

Se contrastó la captura local original de «Contexto y Objetivos» del PI y la
síntesis local de «Entregables y requisitos»/guía. No hay una copia completa local
adicional del suplemento SUP M1; su digest aportado es contexto suplementario,
no una rúbrica nueva verificada. No se certifica cumplimiento académico total.

Fuente original: [Contexto y Objetivos](https://lp.soyhenry.com/share/lesson/W9H_JasyuOLs/s/HntBLeBul283).
La síntesis marca las rutas de su tabla como «sugeridas». La estructura aportada
por Luis incluye pyproject.toml y evals/run_evals.py. No se convierten rutas de
ejemplo en obligaciones de nombres exactos sin evidencia.

| Elemento | Evidencia y correspondencia actual |
|---|---|
| Dominio | Nubbix; TicketFlow/OrbitAir son prácticas distintas. |
| Contrato público JSON | Se conservan exactamente answer, confidence, category, actions. |
| Categorías | billing, technical, account, other; enum estricto del schema. |
| Confidence | Número finito 0..1 por decisión local; señal autodeclarada, no acierto ni probabilidad calibrada. No se atribuye a un dato observado de API. |
| Actions | Lista de textos por decisión local; sugerencias humanas, nunca operaciones ejecutadas. |
| CLI | src/main.py coincide; ejecución documentada por python -m src.main. La fuente no fija nombres exactos de flags. |
| Prompts | prompts/*.yaml coincide; v1_zero_shot.yaml y v2_few_shot.yaml distinguen variantes. Los nombres internos version/technique/instructions/examples son decisiones locales, no claves oficiales confirmadas. |
| Config | .env.example sin secretos existe, no se carga; config.toml y src/runtime/config.py conservan Settings y sus nombres de campos locales. |
| Dependencias | requirements.txt es copia exacta de 44 versiones recomendadas por el TA según Luis; decisión conservadora, no obligatoriedad académica verificada. pyproject.toml la lee como fuente única mediante dependencias dinámicas de setuptools. Python >=3.12; conjunto instalado desde PyPI y probado en un entorno aislado nuevo el 04/11 (132 tests), sin modificar el .venv original. Ruff es extra dev fuera de la lista TA; requirements-dev.txt remite a .[dev]. Ver REPRODUCIBILIDAD.md para plataforma y límites. |
| Dataset | evals/dataset.jsonl aparece como ruta sugerida en la síntesis; Luis propuso data/eval_dataset.jsonl. Existe data/eval_dataset.jsonl con 32 tickets sintéticos etiquetados provisionalmente; el sample de cuatro queda separado. Metadatos case_id/label_reason/ambiguous son decisiones locales, no nomenclatura oficial. Véase data/DATASET.md. |
| Runner | evals/run_evals.py sigue la estructura de Luis; evals/runner.py figura como ruta sugerida en la síntesis. No hay evidencia de exigir ambas entradas. |
| Métricas | data/metrics.jsonl coincide y se ignora en Git. timestamp, prompt_tokens/completion_tokens/total_tokens, latency_seconds y cost_usd expresan las magnitudes pedidas; no hay evidencia local de nombres literales oficiales para sus claves. En mock tokens/costo son null. Los adaptadores normalizan tokens y el servicio suma todos los intentos sólo con datos completos; partial deja agregados null y conserva usage_by_attempt. cost_usd usa string decimal exacto sólo con tarifa admitida y datos suficientes; de lo contrario null. Catálogo vacío/desactivado por defecto, sin precios comerciales. |
| Proveedores | src/llm/providers contiene contrato, mock, openai_provider.py (Responses) y gemini_provider.py (Interactions v1beta). OpenAI/Gemini son seleccionables, con suite offline y pruebas reales puntuales de contrato. No hay modelo comercial predeterminado ni evaluación general de calidad. El SDK declarado no está instalado. src/providers/ era agrupación sugerida; Anthropic no se agrega por un nombre de ejemplo. |
| Bonus | Suite de 10 ataques es opcional en la captura; no existe una suite completa ni run_adversarial.py. No se generan placeholders. |

## Refactor modular — 31/10/2026

Se conserva src/main.py como entrada y evals/run_evals.py como runner. Los módulos
internos se agrupan en src/support (schema, guardrails, servicio), src/llm (prompts
y proveedores) y src/runtime (configuración y métricas). Las rutas de módulos de
la estructura inicial se trataron como organización sugerida, no como contrato
público literal. No se cambian los campos JSON, flags, YAML, archivos de datos ni
ruta de métricas. No se agregan proveedores ni funcionalidades.

Los imports internos anteriores src.service/src.schemas/src.config no se mantienen
como aliases: no son entrypoints documentados. Packaging y tests apuntan a los
paquetes nuevos. Para usar fuera del directorio raíz hay que hacer disponible el
árbol fuente mediante PYTHONPATH o ejecutar make -C; no se instala una CLI global.

## Pendientes

Evaluación comparativa de proveedores reales configurables, verificación remota futura de usage/costo y tarifas comerciales revisadas, rate limits,
políticas/guardrails validados, revisión humana de los 32 casos y separación semántica del corpus,
comparación empírica de dos prompts y elección documentada, documentación final
reproducible y contraste con rúbrica completa. Cuatro muestras y scores del mock
no satisfacen esos requisitos. Los YAML se cargan con PyYAML safe_load y luego se validan
con Pydantic; los bloques multilínea conservan los datos de los prompts originales.
Eso no convierte los resultados del mock en una evaluación de LLM.

## Checkpoint local OpenAI — 03/11/2026

Se agrega selección mock/openai y model explícito, conservando contrato público,
entrypoints y los cambios locales previos de reparación/.env.example. No se modifican
los 44 pins. Como el SDK no está instalado y no se autorizó instalarlo, se usa urllib
para HTTP con transporte simulado en pruebas. No se accedió al .env real ni a claves.
La lectura de OPENAI_API_KEY ocurre al seleccionar el adaptador en ejecución, no al
cargar TOML o usar mock. No se hace carga automática de .env.

Esto no completa una integración remota verificada ni dos proveedores reales. No se
hicieron llamadas API o gastos. El runner de muestras sigue siendo sólo mock y rechaza
OpenAI para no realizar llamadas pagadas por un cambio de config. Este incremento
permanece sin commit/publicación para su explicación con Luis.

## Checkpoint Gemini — 03/11/2026

Se agrega gemini como valor de provider con model explícito y GEMINI_API_KEY en
el proceso. Misma interfaz generate(instructions, query) y mismo contrato Nubbix;
HTTP Interactions v1beta se mapea internamente a texto, con transporte falso en
pruebas. No se instala google-genai, no se modifica la referencia TA y no se leen
secretos ni se ejecutan llamadas. Mock sigue predeterminado y las evals de muestra
rechazan ambos proveedores remotos. Faltan pruebas remotas autorizadas, usage/costo,
modelos elegidos y evidencia de calidad; no se alega cumplimiento académico total.

## Corpus de 32 casos — 03/11/2026

Ruta aportada por Luis data/eval_dataset.jsonl ahora contiene ocho tickets por
categoría, distintos del sample y de los ejemplos few-shot. labels/metadata son
propuestos por IA para revisar con Luis. evals/run_evals.py añade --check-dataset;
conserva default sample, formato JSON público de respuestas y bloqueo de remotos.
Se comprueba coincidencia normalizada, no independencia semántica. El conteo
mínimo está preparado; revisión de etiquetas, evaluación de LLM y comparación
real de prompts siguen pendientes. No se certifica cumplimiento total.

## Estado de publicación — 03/11/2026

Los checkpoints anteriores conservan su estado temporal. Actualmente los dos
adaptadores tienen pruebas remotas puntuales de salida válida, además de suite
offline. Gemini recibe response_format text/application-json y el schema generado
por SupportResponse desde el servicio; no cambia el contrato público. CLI/config
continúan sin cargar .env automáticamente, y las evals siguen sólo mock. Los logs
de pruebas reales y apuntes externos permanecen locales/ignorados; no constituyen
resultados comparativos académicos publicados. Corpus32 y etiquetas provisorias
requieren revisión humana. No se certifica cumplimiento total.

## Consumo normalizado — 04/11/2026

Contrato interno Provider.generate pasa de str a GenerationResult(text, TokenUsage),
con prompt_tokens/completion_tokens/total_tokens opcionales. Nombres y agregado son
decisiones técnicas nuestras para las magnitudes pedidas; no se atribuyen al schema
público de Henry. CLI conserva answer/confidence/category/actions. usage_by_attempt
contiene sólo contadores por intento; usage_status distingue completo/parcial/ausente.
Errores de extracción pueden preservar uso normalizado mediante ProviderError.
No se registra usage HTTP crudo ni se toma ausencia como cero. Costo sigue null.
Adaptadores, mock y dobles/tests migrados; sin nuevas llamadas, claves o dependencias.

## Precios de texto estándar — 04/11/2026

cached_prompt_tokens, pricing_path y el catálogo pricing.example.json son decisiones
técnicas locales, no claves oficiales de la consigna. Runtime/pricing conserva
format_version/catalog_version y rate_version por proveedor/modelo/standard_text.
Decimal calcula estimaciones; cost_usd/cost_by_attempt se serializan como string
decimal o null para no perder precisión. No cambia SupportResponse ni los cuatro
campos CLI. Falta de datos/tarifa no se vuelve cero. Catálogo por defecto vacío y
pricing_path=None: ningún precio comercial activo. Los tests usan fixture-model
y tarifas ficticias; véase docs/PRICING.md para límites y verificación manual.

## Proveedor local — 04/11/2026

provider=ollama es una extensión elegida con Luis, no una categoría ni proveedor
obligatorio de la consigna. src/llm/providers/ollama_provider.py conserva interfaz
GenerationResult y contrato CLI. Prefiere GGUF local verificado, sin cloud/pull ni
API key. Contadores normalizados con total derivado; sin tarifa comercial local.
config.ollama.example.toml es una configuración explícita separada; mock sigue
predeterminado y no hay evaluación pagada nueva. Ver docs/OLLAMA.md para resultado
puntual y límites de calidad. No se certifica cumplimiento completo del PI.
