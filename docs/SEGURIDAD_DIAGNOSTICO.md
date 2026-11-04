# Diagnóstico defensivo offline — 04/11/2026

Se integra el borrador previamente preparado: diez intentos sintéticos de injection,
cuatro consultas normales, dos citas con decisión de producto pendiente y tres
fixtures de salida. No se modifican los regex ni se afirma moderación completa.
La consigna disponible exige controles de entrada y salida y menciona un bonus
adversarial; este diagnóstico prepara evidencia de la aplicación, **no certifica
ese bonus ni resistencia de un modelo real**.

## Qué se observa

`evals.run_guardrail_diagnostics` carga JSONL validados, aplica `check_input` o
`check_output`, y registra IDs y decisiones sin copiar textos o supuestos secretos
al reporte. No crea proveedores ni llama modelos; funciona aunque la configuración
seleccione un proveedor remoto. En salida construye respuestas sintéticas válidas
para comprobar el guardrail, no simula una respuesta real del modelo.

- `evals/adversarial.jsonl`: diez variantes que intentan cambiar reglas o suplantar
  autoridad. La expectativa de bloquearlas antes de inferir es **propuesta
  diagnóstica técnica**, no una política productiva aprobada.
- `evals/guardrail_controls.jsonl`: cuatro consultas normales, dos citas de texto
  sospechoso con política pendiente y tres fixtures de salida. Los valores
  `DEMO_PLACEHOLDER_ONLY` son ficticios, no credenciales reales.
- Los controles normales esperan admisión, no prueban que la respuesta posterior
  sea correcta. Las citas quedan fuera del score para no inventar una política.

## Resultado comprobado

| Grupo | Casos | Bloqueados | Admitidos | Interpretación |
|---|---:|---:|---:|---|
| Intentos de injection | 10 | 4 | 6 | El prechequeo reconoce secuencias literales; no cubre todas las variantes preparadas. |
| Consultas normales | 4 | 0 | 4 | Sin bloqueos en estos cuatro controles; no estima tasa general de falsos positivos. |
| Citas de texto sospechoso | 2 | 2 | 0 | Posibles falsos positivos según el uso legítimo; decisión pendiente, no puntuados. |
| Fixtures de salida | 3 | 2 | 1 | Se bloquean marcadores ficticios en answer y actions; se admite la respuesta normal. |

Las cuatro detecciones de entrada corresponden a versiones literales de “ignore
previous instructions” e “ignorá las instrucciones anteriores”. Paráfrasis,
autoridad simulada y delimitadores falsos pasan ese regex. **Pasar el prechequeo
no demuestra que el modelo obedecería el ataque**: las instrucciones de sistema
pueden influir después, algo que esta suite offline no mide. Tampoco un JSON válido
prueba que un modelo resistió una instrucción maliciosa.

La inspección de salida sólo reconoce ciertos identificadores seguidos de valor;
no detecta todas las formas de secretos o datos personales, ni valida políticas,
veracidad, contenido inseguro o acciones de negocio. No se prueba esa cobertura
con dos valores ficticios. Los logs evitan ticket/respuesta crudos, pero privacidad
completa de datos enviados a un proveedor es otra dimensión no certificada aquí.

## Citas y falsos positivos: decisión abierta

Un reporte legítimo puede mencionar literalmente una cadena sospechosa. El regex
actual lo bloquea. Se conserva esa observación sin etiquetarlo automáticamente
como ataque ni aprobarlo como permitido por una nueva regla de negocio.

No se quitaron las citas antes del chequeo ni se agregaron excepciones automáticas:
una instrucción puede venir citada y seguir intentando alterar las reglas. Antes
de cambiar ese comportamiento, decidir qué acción se espera para esos reportes:
bloquear, pedir reformulación o derivar a revisión humana. El contrato actual no
tiene una acción ejecutable de moderación ni estados allow/flag/block; no se agregó
uno por interpretar material de otra práctica como requisito del PI.

V3/v4 refuerzan en sus instrucciones que tickets y roles citados son datos, y no
solicitan secretos o acciones reales. Esto es una capa de instrucciones, no una
prueba empírica de defensa suficiente. No se usó esta suite para prometer seguridad
comparativa de las cuatro variantes. No hay puntuación de ataques por modelo aquí.

## Ejecución reproducible y significado del código de salida

Desde checkout con el entorno instalado:

```bash
.venv/bin/python -m evals.run_guardrail_diagnostics
.venv/bin/python -m evals.run_guardrail_diagnostics --output /tmp/NUEVO-diagnostico.json
```

Cero significa que se produjo el diagnóstico, **no que todos los ataques fueran
bloqueados**. Dos indica suite/configuración inválida o archivo de salida existente;
no se sobrescribe. El reporte incluye hashes de datos, guardrails, schema, runner y
configuración, timestamp, expectativas y resultados, sin textos crudos. Las dos
citas tienen `expectation_matched=null` y cero expectativas puntuadas.

[Evidencia conservada](GUARDRAIL_DIAGNOSTIC_2026-11-04.json): 19 casos y cero llamadas
a modelos. Se comprobó antes el borrador y se volvió a ejecutar su diagnóstico al
integrarlo, sin cambiar las reglas para aumentar bloqueos. No se mezclan estas
métricas con exact match de categorías o resultados de las 160 generaciones.

Ocho tests de diagnóstico/integración: datos y privacidad, exclusión de decisiones
pendientes, expectativas no cumplidas conservadas, answer/actions, validación de
suites, archivos sin sobrescritura, errores sin contenido crudo y pipeline con
v3/v4. Los últimos usan dobles: un bloqueo de entrada no genera; una salida con
marcador ficticio se rechaza sin retry. Son pruebas de comportamiento del software,
no evidencias de un modelo en producción. Suite total: 150 tests, lint y formato.

## Pendientes proporcionados

- Resolver el tratamiento de citas con el responsable del producto antes de
  cambiar filtros. Mantener separados falsos positivos, cobertura del prechequeo
  y comportamiento real de modelos.
- Si se quiere evaluar el bonus completo, fijar un protocolo de ataques sobre
  consultas de soporte con expectativas de tarea y ataque distinguibles, y medir
  las salidas del modelo además de los guardrails. En un modelo que ya clasifica
  mal, un error normal no debe contarse automáticamente como injection exitosa.
- No declarar moderación de PII o seguridad general sin política y evidencia
  específicas. No agregar endpoints, servicios o frameworks para aparentarla.

No se hicieron solicitudes pagas, leyeron secretos o cambiaron pesos. Los cambios
nuevos permanecen locales y no se publican sin autorización específica.


## Trabajo posterior: Unicode y modelo local

Se preservan arriba el protocolo y las cifras iniciales. Posteriormente se corrigió
un bypass de representación Unicode sin cambiar las frases del regex ni permitir
citas automáticamente. Se añadieron evidencias antes/después y una prueba pareada
con consultas limpias/atacadas para observar redirecciones de categoría. Ver
[SEGURIDAD_PAREADA.md](SEGURIDAD_PAREADA.md), que distingue los denominadores y los
límites. La suite actual pasa 158 tests; no se reescriben estas observaciones previas.
