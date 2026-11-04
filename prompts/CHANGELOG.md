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

## Nuevas hipótesis v3/v4 — 04/11/2026

- v3_structured: zero-shot con secciones, criterio por necesidad explícita,
  autoridad de datos, incertidumbre y chequeo del contrato. No agrega ejemplos del
  corpus ni una regla particular para una etiqueta fallida.
- v4_reasoning: zero-shot conciso pensado para modelos capaces de deliberar, sin
  solicitar cadena de pensamiento o borradores; sólo JSON final. No activa modos
  think/reasoning del proveedor ni acredita que Qwen coder 0.5B los soporte.
- V1/v2 y defaults conservados. Catálogo compartido para CLI, config y evaluadores;
  selector de versiones explícito en el runner local. Los resultados viejos se
  conservan y pueden recalcularse.
- YAML nuevos fijados antes de una pasada local de 160 generaciones: base32 y
  paráfrasis8 por cuatro variantes, cero retries, mismos límites/modelo. No se
  retocaron después. Base: 11/18/17/13 aciertos propuestos; paráfrasis: 3/4/5/2.
  V3 validó todo, v2 tuvo mayor global base; no hay ganador universal ni prueba
  de razonamiento interno. Ver docs/PROMPTS_V3_V4.md para protocolo y límites.
