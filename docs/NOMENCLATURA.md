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
| Config | .env.example sin secretos existe, no se carga; config.toml/Settings y sus nombres de campos son decisiones locales. |
| Dependencias | Se agrega requirements.txt con la misma dependencia que pyproject.toml, para cubrir la referencia explícita de los apuntes. No se instala nada en esta revisión. |
| Dataset | evals/dataset.jsonl aparece como ruta sugerida en la síntesis; Luis propuso data/eval_dataset.jsonl. Hoy solo existe data/eval_sample.jsonl con cuatro casos ilustrativos. No se renombra el sample para aparentar un dataset mínimo de 30. |
| Runner | evals/run_evals.py sigue la estructura de Luis; evals/runner.py figura como ruta sugerida en la síntesis. No hay evidencia de exigir ambas entradas. |
| Métricas | data/metrics.jsonl coincide y se ignora en Git. timestamp, prompt_tokens/completion_tokens/total_tokens, latency_seconds y cost_usd expresan las magnitudes pedidas; no hay evidencia local de nombres literales oficiales para sus claves. En mock tokens/costo son null. |
| Proveedores | src/providers/base.py y mock_provider.py son reales en el código. openai_provider.py/anthropic_provider.py son nombres de ejemplo; no se crean archivos vacíos ni se elige proveedor aún. |
| Bonus | Suite de 10 ataques es opcional en la captura; no existe una suite completa ni run_adversarial.py. No se generan placeholders. |

## Pendientes

Dos proveedores reales configurables, métricas de usage/costo real, rate limits,
políticas/guardrails validados, dataset independiente de 30+ casos etiquetados,
comparación empírica de dos prompts y elección documentada, documentación final
reproducible y contraste con rúbrica completa. Cuatro muestras y scores del mock
no satisfacen esos requisitos. Los YAML admiten hoy únicamente el subconjunto JSON
de YAML 1.2, explícito en README; no se alega soporte general de YAML.
