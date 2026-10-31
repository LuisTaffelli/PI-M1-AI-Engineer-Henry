# Variantes iniciales — 30/10/2026

- v1_zero_shot: instrucciones, categorías, contrato y límites sin ejemplos.
- v2_few_shot: mismas instrucciones más dos ejemplos sintéticos de cobros y permisos.

Hipótesis a contrastar: los ejemplos podrían mejorar clasificación y consistencia
del formato. Todavía no hay evidencia de mejora ni versión ganadora. Los valores de
confidence en ejemplos son ilustrativos, no etiquetas de acierto ni probabilidades.
No se usan estos dos ejemplos en el denominador de una evaluación real sin revisar
solapamientos. El dataset de cuatro filas es solo un smoke test ilustrativo.

Los .yaml usan sintaxis JSON, subconjunto de YAML 1.2. El cargador actual admite
únicamente ese subconjunto; no admite YAML con bloques, comentarios o anclas.
No se instaló PyYAML. Si se quiere YAML de bloques, se debe acordar la dependencia.

## Migración de formato — 31/10/2026

Se conserva version/technique/instructions/examples y sus valores exactos.
Las instrucciones pasan a un bloque YAML plegado (>-), cargado con PyYAML safe_load
y validado mediante Pydantic. Es una migración de representación sin cambios de
criterio ni de ejemplos; por eso se conservan las versiones v1/v2 y no se declara
una variante ganadora. Los párrafos previos sobre el subconjunto JSON describen
el estado anterior, no el cargador actual.
