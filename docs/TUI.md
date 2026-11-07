# Menú opcional de terminal

Desde la raíz del repo: `make tui` o, con el entorno virtual activo,
`python -m src.tui`. No agrega dependencias. Es un menú numerado de texto con
`input`/`print`, no una interfaz de pantalla completa ni un chat con memoria.
La CLI `python -m src.main 'consulta' ...` conserva sus argumentos y salida JSON.

## Recorrido

1. **Probar tickets en loop:** ingresá una línea, revisá el preview y confirmá.
   `/volver` regresa al menú. Cada ticket se procesa solo, sin los anteriores.
2. **Evaluar dataset o adversariales:** elegí base (32 tickets), paráfrasis (8) o
   pares adversariales (30 llamadas de servicio por prompt), con el prompt actual
   o los cuatro. Elegí la cota de invocaciones y una carpeta nueva; revisá el plan.
3. **Configurar:** elegí mock, Ollama, OpenAI o Gemini, modelo explícito si aplica,
   prompt, rondas de reparación JSON, intentos HTTP remotos y tokens de salida.
   Los cambios duran la sesión, sin escribir `config.toml` ni inferir.
4. **Salir:** también sirve EOF (`Ctrl+D` en una terminal Unix).

El arranque fuerza mock/fixed, una ronda JSON y un intento HTTP aunque el TOML
elija un proveedor real, más retries o la excepción Gemini. Conserva el prompt,
límite de entrada, métricas y demás parámetros del archivo. Se puede seleccionar
otro TOML con `python -m src.tui --config ruta/config.toml`. La configuración debe
ser válida. El menú no permite la excepción Gemini de 120/300 s.

## Antes de ejecutar

Cada preview indica proveedor, modelo, prompts, cota de invocaciones, rondas JSON,
intentos HTTP y, si aplica, tokens de salida. Evaluaciones muestran además el plan
completo del runner y la carpeta de salida. **No crean proveedores, leen claves,
hacen inferencia ni crean la carpeta al previsualizar.**

- Mock/Ollama: escribir exactamente `EJECUTAR`.
- OpenAI/Gemini: escribir exactamente `REMOTO` para esa consulta o evaluación.
  Las consultas y prompts se envían al proveedor elegido y pueden generar cargos.
- Enter u otro texto cancela. La confirmación no se reutiliza en otra corrida.
- No se solicitan claves en el menú. Al inferir, los adaptadores mantienen su
  carga diferida del entorno/`.env`. No pegar secretos en el campo de modelo.

Las cotas se calculan y validan en los planes existentes. Base/paráfrasis incluyen
reparación JSON × intentos HTTP × casos × prompts. Adversariales mantiene una
ronda sin reparación, hasta 256 tokens y sus restricciones originales. La cota
configurable no supera 384 invocaciones; si no alcanza, se rechaza antes de inferir.
La cota inicial del formulario es 384, pero el preview muestra la cota real del
plan, que suele ser menor. No se ejecutan llamadas extra para alcanzar la reserva.

**No existe tope monetario automático ni garantía del costo total.** Un catálogo
de precios, si está configurado, sólo permite estimar el uso conocido. HTTP retry
es opt-in (hasta 3 intentos por generación, 30 s por espera y 60 s acumulados;
red aparte). Esto es distinto de volver a ejecutar una corrida interrumpida.
Ollama usa el servicio local existente; el menú no instala ni descarga modelos.

## Entrada, métricas y resultados

- Tickets de una línea: límite común de 500 puntos de código Unicode originales,
  o un límite menor configurado. Conserva espacios, sin truncar ni agregar historial.
  No admite composición multilínea en el menú; para eso usá la CLI original.
- Entrada vacía, demasiado larga o bloqueada se rechaza antes del preview y sin
  inferir. No agrega métricas para esos rechazos del menú. La validación del
  servicio sigue activa al ejecutar. Usá sólo consultas sintéticas, sin secretos.
- Tickets ejecutados respetan `log_metrics`/`metrics_path` del TOML y muestran el
  JSON validado. El preview indica si las métricas están activas. No se guarda
  historial de conversación en la TUI.
- Las evaluaciones usan sus mismos runners, guardrails, scoring y artefactos.
  Las rutas relativas de salida se resuelven desde la raíz del repo. Se sugiere
  una carpeta única en `data/local_runs/`, que no se crea hasta confirmar.
- No sobrescribe ni reanuda carpetas existentes. Muestra el resumen original,
  estado completo/parcial y fallos. Un mock completo no demuestra calidad o seguridad.
  Las acciones siguen siendo sugerencias para una persona; no se ejecutan.

## Cancelación y errores

`Ctrl+C` al elegir descarta esa selección y vuelve al menú. Si ocurre durante
configuración, conserva la configuración previa completa. EOF cierra la sesión
sin confirmar nada. Cancelar un preview no inicia inferencia.

Si interrumpís una llamada o evaluación, se detiene el flujo sin repetir la
solicitud ni reanudar la corrida. **La solicitud en curso puede haber llegado al
proveedor y generado consumo**, aunque no haya respuesta visible. Los archivos
ya escritos se conservan. Pueden faltar filas de resultados, métricas y
`summary.json`; no se fabrica un resumen ni se declara la corrida completa.
Una línea de métricas de una solicitud interrumpida no demuestra una respuesta
terminada. Revisá la carpeta antes de decidir una nueva corrida con otra salida.

Los errores muestran códigos locales, sin cuerpos HTTP ni respuestas inválidas.
Un fallo no dispara una nueva corrida. Los retries que sí se hayan elegido en
configuración siguen siendo responsabilidad del servicio, con sus límites.

## Implementación y verificación

`src/tui.py` delega tickets a `support.service.simulate_response` y evaluaciones
a `prepare_plan`/`execute_plan` de clasificación o adversariales. No duplica
prompts, contratos, scoring, adaptadores ni lógica de retry. Usa únicamente la
biblioteca estándar para la interfaz; las dependencias del proyecto no cambian.

Las pruebas en `tests/integration/test_tui.py` simulan la entrada y bloquean APIs
/lectura de claves. Cubren los tres runners con mock en directorios temporales,
aprobación remota nueva por operación, cotas/archivos existentes, 500/501 caracteres,
configuración cancelada y corridas interrumpidas antes/después de resultados.
Ejecutá `make check` para incluirlas con las regresiones de la CLI original.
