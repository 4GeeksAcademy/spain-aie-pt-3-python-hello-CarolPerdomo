# Inventario con FastAPI y agente LLM

API persistente en CSV y agente CLI con bucle manual en Python, sin frameworks de agentes. El SDK de OpenAI solo se utiliza para llamar al modelo.

**Arranque breve:** la API está en [api/app.py](api/app.py) y el agente en [agent.py](agent.py). Tras instalar las dependencias, ejecuta `python -m uvicorn api.app:app --host 127.0.0.1 --port 8000` en una terminal. En otra, configura la clave, el host y el modelo como se indica abajo y ejecuta `python agent.py`. Mantén la API funcionando mientras usas el agente.

## Instalación

Requisitos: Linux (`fcntl` para bloquear archivos), Python 3.10 o superior y una clave de OpenAI o de un proveedor compatible, como 4Geeks, para un modelo con llamadas a herramientas. Desde la raíz del proyecto:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Arranque

Primero, en la terminal 1, inicia la API:

```bash
source .venv/bin/activate
export INVENTORY_ALERT_THRESHOLD=10
python -m uvicorn api.app:app --host 127.0.0.1 --port 8000
```

Documentación interactiva: http://127.0.0.1:8000/docs. Detén el proceso con `Ctrl+C`.

Después, en la terminal 2, introduce la clave sin guardarla en el código ni en el historial del shell e inicia el agente:

```bash
source .venv/bin/activate
read -rsp "OPENAI_API_KEY: " OPENAI_API_KEY
printf '\n'
export OPENAI_API_KEY
export OPENAI_MODEL=gpt-4o-mini
export INVENTORY_API_URL=http://127.0.0.1:8000
python agent.py
```

El agente comprueba que la API esté disponible antes de aceptar mensajes. Las llamadas al LLM requieren Internet y pueden generar costes. `salir`, `exit`, `quit`, `Ctrl+C` o fin de entrada terminan la sesión.

Ejemplos: “Añade arroz con 20 kg”, “Retira 3 kg de arroz”, “Muestra el inventario” y “¿Qué productos tienen menos de 5 unidades?”.

## Usar el host de 4Geeks

La clave de 4Geeks no se envía a OpenAI. Después de introducirla en `OPENAI_API_KEY` con el comando `read` anterior, configura el destino y consulta los modelos disponibles:

```bash
export OPENAI_BASE_URL=https://llm.4geeks.ai/v1
python -c "from openai import OpenAI; print('\n'.join(model.id for model in OpenAI().models.list()))"
```

El modelo verificado en este proyecto es el siguiente. Si no está habilitado para tu clave, selecciona otro ID de la lista que admita llamadas a tools:

```bash
export OPENAI_MODEL="madrid-spain/openrouter/deepseek/deepseek-v4-flash"
python agent.py
```

La variable `OPENAI_API_KEY` conserva su nombre porque usamos el SDK compatible de OpenAI; su valor debe ser la clave de 4Geeks. No compartas ni imprimas la clave. Un 401 indica credenciales rechazadas por ese host; un error de modelo puede indicar un ID incorrecto o no habilitado. Para volver al servicio de OpenAI, elimina `OPENAI_BASE_URL` con `unset OPENAI_BASE_URL`, configura una clave de OpenAI y un modelo autorizado.

## API

| Método | Ruta | Datos | Respuesta correcta |
| --- | --- | --- | --- |
| GET | `/inventory` | Sin cuerpo | 200, lista completa |
| POST | `/inventory` | `{"name":"Arroz","quantity":20,"unit":"kg"}` | 201, producto con `id` |
| PATCH | `/inventory/{product_id}` | `{"delta":-3}` | 200, producto actualizado |
| GET | `/inventory/alerts` | `?threshold=5` opcional | 200, productos por debajo del umbral |

Las cantidades y deltas son enteros, sin fracciones. Los nombres y unidades no pueden estar vacíos y el stock no puede ser negativo. El umbral por defecto es 10; `INVENTORY_ALERT_THRESHOLD` lo configura al arrancar y `threshold` lo cambia para una consulta. Se usa una comparación estricta: cantidad menor que el umbral.

Errores con campo descriptivo `detail`: 404 si el ID no existe, 409 si la salida supera el stock, 422 para datos o parámetros inválidos y 500 para fallos de almacenamiento.

## Agente y persistencia

Observar (mensaje e historial) → Pensar (llamada al LLM) → Actuar (llamadas HTTP) → Actualizar (resultados vinculados por `tool_call_id`) → Repetir. Procesa todas las tools de cada respuesta y termina si no hay llamadas pendientes. Cada turno permite un máximo de 20 llamadas al LLM. No hay reintentos automáticos de modificaciones; ante un fallo de conexión se advierte que hay que consultar el estado antes de repetirlas.

El historial vive en memoria durante la sesión y no se restaura al reiniciar. Los archivos se guardan en la raíz del proyecto, independientemente del directorio de ejecución:

- `products.csv`: columnas `id,name,quantity,unit`. Se crea en el primer acceso al inventario; usa IDs autoincrementales, bloqueo entre procesos y reemplazo atómico al guardar.
- `conversation_log.csv`: columnas `actor,message,tool_call,timestamp`. Siempre se abre en modo adición, conserva sesiones anteriores y usa fechas UTC ISO 8601. Registra actores `user`, `agent`, `tool_call` y `tool_result`; los datos de tools se serializan como JSON dentro del CSV.

Los CSV y archivos de credenciales se excluyen de Git. El registro puede contener información privada; limita el acceso a esos archivos. La API no incluye autenticación y debe mantenerse en localhost para este ejercicio.

### Contribuidores

Esta plantilla fue creada como parte de los [Recursos de Python de 4Geeks](https://4geeks.com/es/technology/python) para el aprendizaje en [4Geeks.com](https://4geeks.com) por [Alejandro Sanchez](https://twitter.com/alesanchezr) y [muchos otros contribuyentes](https://github.com/4GeeksAcademy/python-hello/graphs/contributors).
