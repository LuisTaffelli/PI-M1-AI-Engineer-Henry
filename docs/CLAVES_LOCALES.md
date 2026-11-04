# Claves locales: carga diferida y precedencia

El CLI `python -m src.main` y el evaluador `python -m evals.run_provider_evals`
usan el mismo camino: al construir OpenAI/Gemini, el adaptador busca únicamente su
variable (`OPENAI_API_KEY` o `GEMINI_API_KEY`). No hay que exportarla manualmente.

1. Un `api_key=` explícito programático tiene prioridad (permite fixtures aislados).
2. Si la variable existe en el entorno del proceso, usa ese valor, **incluso vacío**,
   sin abrir `.env`. Un valor exportado vacío falla como clave faltante y no recurre
   al archivo; quitarlo personalmente con `unset OPENAI_API_KEY` si se desea fallback.
3. Si no existe en el entorno, busca su asignación en **`<raíz del checkout>/.env`**,
   junto a `config.toml`. La ruta no depende del directorio actual ni de `--config`.
   No busca archivos en directorios padres, home, otros proyectos ni `.env.example`.

Conservá el `.env` existente y completalo personalmente en tu editor. Si todavía
no existe, la plantilla `.env.example` contiene ambas variables vacías y está
versionada; `.env` permanece ignorado por git. Nunca pegues claves en el chat,
argumentos, TOML, logs o commits. No usar `source .env`: la aplicación **no ejecuta
el archivo como script** y tampoco modifica `os.environ` ni exporta valores a otros
procesos. No hay caché: cada construcción remota resuelve otra vez la clave.

## Formato admitido

Archivo UTF-8 sin BOM, una asignación por línea:

```dotenv
# Sólo valores ficticios para mostrar sintaxis; completar personalmente.
OPENAI_API_KEY='valor-ficticio'
export GEMINI_API_KEY="otro-valor-ficticio" # comentario
```

Se admiten espacios alrededor de `=`, `export ` opcional, valores sin comillas
sin espacios, comillas simples o dobles y comentarios después de un valor citado
o separados por espacios en valores sin comillas. Las comillas se eliminan.
No hay expansión de `${VARIABLE}`, `$VARIABLE`, sustitución `$(comando)`, escapes
ni valores multilínea: cualquier expresión admitida se conserva literalmente,
nunca se ejecuta ni se interpreta como otra variable. Es un subconjunto deliberado
de dotenv, sin dependencia nueva. Las entradas ajenas a la clave seleccionada se
ignoran; no configuran el modelo, proveedor, prompts, proxies ni otros parámetros.

## Errores y límites

- Archivo ausente, clave ausente o vacía: el adaptador falla antes de la red.
- Sintaxis inválida o asignación duplicada de la clave seleccionada: error controlado;
  no se escoge arbitrariamente una copia. Corregir el archivo personalmente.
- Archivo ilegible o UTF-8 inválido: error controlado, sin mostrar contenido ni ruta
  privada del error de sistema. El entorno presente evita leer el archivo completo.
- CLI/evaluador conservan código de salida 2 ante errores; las métricas usan códigos
  sanitizados. No imprimir valores o excepciones crudas para diagnosticar claves.

La carga ocurre después del guardrail de entrada y sólo al crear el proveedor
remoto. Mock, Ollama, carga de TOML, imports, validación de dataset y previsualización
no leen `.env`. La previsualización no valida credenciales. Tampoco se leen cuando
falta la confirmación remota `--execute --allow-remote-inference` del evaluador.
Una llamada programática directa a un adaptador remoto sí resuelve la credencial;
usar `api_key=` ficticio explícito y transporte falso en tests.

Tener la clave disponible no agrega confirmación al CLI principal: al seleccionar
un proveedor remoto allí se puede iniciar una llamada como antes. El evaluador
conserva sus dos opciones explícitas, cota de llamadas/reintentos y salida nueva.
La carga automática no garantiza privacidad del ticket enviado ni un tope de dinero.
Ver [evaluación multiproveedor](EVALUACION_PROVEEDORES.md).

Las pruebas usan archivos temporales ficticios, entorno controlado y transportes
falsos; no se leyó ni editó el `.env` real para implementar o verificar esta función.
