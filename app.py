"""API HTTP del asistente de consultas comerciales (HU6).

Coordina HTTP <-> router (HU4) <-> logger (HU5): recibe la consulta,
delega la clasificación y el registro, y traduce el resultado a HTTP.
No reimplementa lógica de negocio.
"""

import json
import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "tests"))

from router import procesar_consulta
from logger import registrar_consulta
from test_pipeline import RUTA_CSV_POR_DEFECTO, ejecutar_pipeline

logging.basicConfig(level=logging.INFO)
_logger_interno = logging.getLogger("app")

RATE_LIMIT_POR_DEFECTO = "10/minute"
CANALES_VALIDOS = {"correo", "chat", "formulario", "telefono"}
MAX_LONGITUD_TEXTO = 500

# Única fuente de verdad para el texto de cada categoría: /medicion lo usa
# para la leyenda de las 5, /chat lo reutiliza (embebido como JSON para el
# JS del cliente) para mostrar solo la explicación de la categoría obtenida.
EXPLICACION_CATEGORIAS = {
    "a": "el sistema puede responder directamente, porque ya tiene la información necesaria (por ejemplo, sobre el catálogo, cómo pedir un producto o la garantía).",
    "b": "el sistema no puede dar una respuesta exacta porque se trata de algo que cambia seguido (como el precio, el stock o una promoción) y esa información no está guardada aquí -- le indica a la persona que lo confirme directamente en el sistema comercial.",
    "c": "la pregunta no es un tema del área comercial (por ejemplo, algo de Recursos Humanos o de sistemas) -- el sistema la redirige a quien corresponda.",
    "d": "la consulta necesita que una persona del equipo comercial la revise, porque es un caso especial, un reclamo o algo que hay que negociar directamente.",
    "e": "el sistema no logró entender bien la pregunta -- le pide a la persona que la explique de otra manera.",
}

_CSS_COMUN = """
body { font-family: system-ui, Arial, sans-serif; line-height: 1.5; color: #222; background: #f7f5f2; }
textarea, select, button, input { font-family: inherit; }
.pagina { max-width: 800px; margin: 0 auto; padding: 20px; box-sizing: border-box; background: #ffffff; box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08); }
h1 { margin-bottom: 0.3rem; }
h2 { margin-top: 1.5rem; margin-bottom: 0.4rem; font-size: 1.1rem; }
"""


def _limite_actual() -> str:
    """Límite vigente para el rate limiting, leído en cada request.

    Se resuelve así (en vez de fijarlo una sola vez al importar el
    módulo) para que los tests puedan configurar un límite más bajo con
    una variable de entorno, de forma aislada y determinística.
    """
    return os.environ.get("RATE_LIMIT", RATE_LIMIT_POR_DEFECTO)


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Asistente de consultas comerciales")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class ConsultaPayload(BaseModel):
    texto: str
    canal: str

    @field_validator("texto")
    @classmethod
    def _validar_texto(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError("texto no puede estar vacío")
        if len(valor) > MAX_LONGITUD_TEXTO:
            raise ValueError(f"texto no puede superar {MAX_LONGITUD_TEXTO} caracteres")
        return valor

    @field_validator("canal")
    @classmethod
    def _validar_canal(cls, valor: str) -> str:
        if valor not in CANALES_VALIDOS:
            raise ValueError(f"canal debe ser uno de: {sorted(CANALES_VALIDOS)}")
        return valor


@app.exception_handler(RequestValidationError)
async def _manejar_error_validacion(request: Request, exc: RequestValidationError) -> JSONResponse:
    mensajes = [error["msg"] for error in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Payload inválido: " + "; ".join(mensajes)},
    )


@app.post("/consulta")
@limiter.limit(_limite_actual)
async def crear_consulta(request: Request, payload: ConsultaPayload):
    try:
        resultado = procesar_consulta(payload.texto)
        registrar_consulta(resultado, canal=payload.canal)
    except Exception:
        _logger_interno.exception("Error inesperado procesando /consulta")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Error interno, intenta más tarde"},
        )

    return {"categoria": resultado["categoria"], "respuesta": resultado["respuesta"]}


def _renderizar_html_medicion(total: int, filas: list) -> str:
    filas_html = "\n".join(
        f"<tr class=\"fila-{fila['categoria']}\">"
        f"<td>{fila['categoria']}</td>"
        f"<td>{fila['cantidad']}</td>"
        f"<td>{fila['porcentaje']:.2f}%</td>"
        f"<td>{fila['baseline']:.2f}%</td>"
        f"<td>{fila['diferencia']:+.2f}pp</td>"
        f"<td>{'FUERA (>3pp)' if fila['desviado'] else 'dentro'}</td>"
        "</tr>"
        for fila in filas
    )

    leyenda_categorias_html = "\n".join(
        f"<li><strong>{categoria}</strong>: {explicacion}</li>"
        for categoria, explicacion in EXPLICACION_CATEGORIAS.items()
    )

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Medición - Asistente de consultas comerciales</title>
<style>
{_CSS_COMUN}
table {{ border-collapse: collapse; width: 100%; margin-top: 0.8rem; border: 1px solid #ccc; }}
th, td {{ border: 1px solid #ccc; padding: 6px 12px; text-align: left; }}
th {{ background: #f2f2f2; }}
tr.fila-a {{ background: #eaf3ff; }}
tr.fila-b {{ background: #fff8e1; }}
tr.fila-c {{ background: #f3e8ff; }}
tr.fila-d {{ background: #ffe8e8; }}
tr.fila-e {{ background: #eeeeee; }}
</style>
</head>
<body>
<div class="pagina">
<h1>Medición de clasificación</h1>
<p>Total: {total} consultas</p>

<p>Cuando alguien del área comercial recibe una pregunta (sobre
productos, plazos, garantías, etc.), este sistema la lee y decide
automáticamente qué hacer con ella: si puede responderla solo con la
información que ya tiene, si necesita avisar que ese dato cambia
seguido y no está aquí, si no es un tema que le corresponda, si debe
pasarla a una persona para que decida, o si simplemente no logró
entender la pregunta. Las letras a, b, c, d y e de la tabla de abajo
representan cada una de esas cinco situaciones.</p>

<h2>¿Qué significa cada categoría?</h2>
<ul>
{leyenda_categorias_html}
</ul>

<h2>¿Qué significa cada columna?</h2>
<ul>
<li><strong>Cantidad</strong>: cuántas de las 80 consultas reales cayeron en esa categoría.</li>
<li><strong>%</strong>: esa cantidad como porcentaje del total.</li>
<li><strong>Baseline</strong>: el porcentaje esperado, calculado a mano revisando las 80 consultas una por una antes de construir el sistema -- es la referencia contra la que se compara.</li>
<li><strong>Diferencia</strong>: cuánto se aleja el resultado del sistema respecto al baseline.</li>
<li><strong>Estado</strong>: si esa diferencia está dentro o fuera de un margen de tolerancia de 3 puntos porcentuales -- "dentro" en las 5 categorías significa que el sistema automatizado clasifica de forma consistente con el criterio humano original.</li>
</ul>

<table>
<thead>
<tr><th>Categoría</th><th>Cantidad</th><th>%</th><th>Baseline</th><th>Diferencia</th><th>Estado</th></tr>
</thead>
<tbody>
{filas_html}
</tbody>
</table>
</div>
</body>
</html>
"""


@app.get("/medicion", response_class=HTMLResponse)
async def medicion() -> str:
    total, filas = ejecutar_pipeline(RUTA_CSV_POR_DEFECTO)
    return _renderizar_html_medicion(total, filas)


def _renderizar_html_chat() -> str:
    explicaciones_json = json.dumps(EXPLICACION_CATEGORIAS, ensure_ascii=False)

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Demo - Asistente de consultas comerciales</title>
<style>
{_CSS_COMUN}
form {{ margin-top: 1rem; }}
label {{ font-weight: bold; }}
textarea, select, button {{ font: inherit; margin-top: 0.2rem; }}
textarea {{ display: block; width: 100%; box-sizing: border-box; }}
button {{ margin-top: 0.6rem; padding: 6px 16px; cursor: pointer; }}
#resultado {{ margin-top: 1rem; }}
#resultado.resultado-ok {{ padding: 0.8rem 1rem; border-left: 4px solid #2e7d32; background: #f1f8f1; border-radius: 4px; }}
#resultado.resultado-error {{ padding: 0.8rem 1rem; border-left: 4px solid #c62828; background: #fdf1f1; border-radius: 4px; }}
#resultado p {{ margin: 0.3rem 0; }}
</style>
</head>
<body>
<div class="pagina">
<h1>Demo: probar una consulta</h1>
<p>Aquí puedes probar una consulta individual y ver cómo el sistema la
clasifica y responde. Para ver el resultado sobre las 80 consultas
reales del CSV, visita <a href="/medicion">/medicion</a>.</p>
<p><em>Nota: el selector de "canal" es solo una etiqueta para fines de
registro interno. Elegirlo NO envía ningún mensaje real por ese canal
(no manda correos, no se conecta a ningún sistema externo). Esta página
es solo una ayuda para la exposición; los canales reales de producción
(correo, chat, formulario, teléfono) llaman directamente a
POST /consulta.</em></p>

<form id="formulario-chat">
<label for="texto">Consulta:</label><br>
<textarea id="texto" name="texto" rows="3" cols="60"></textarea><br><br>

<label for="canal">Canal (solo etiqueta, demo):</label>
<select id="canal" name="canal">
<option value="correo">correo</option>
<option value="chat" selected>chat</option>
<option value="formulario">formulario</option>
<option value="telefono">telefono</option>
</select><br><br>

<button type="submit">Enviar</button>
</form>

<div id="resultado"></div>

<script>
var EXPLICACION_CATEGORIAS = {explicaciones_json};

document.getElementById("formulario-chat").addEventListener("submit", async function (evento) {{
  evento.preventDefault();
  var texto = document.getElementById("texto").value;
  var canal = document.getElementById("canal").value;
  var contenedor = document.getElementById("resultado");
  contenedor.className = "";
  contenedor.textContent = "Enviando...";

  try {{
    var respuestaHttp = await fetch("/consulta", {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify({{ texto: texto, canal: canal }})
    }});
    var datos = await respuestaHttp.json();
    contenedor.textContent = "";

    if (respuestaHttp.ok) {{
      contenedor.className = "resultado-ok";

      var pCategoria = document.createElement("p");
      pCategoria.textContent = "Categoría: " + datos.categoria;
      var pRespuesta = document.createElement("p");
      pRespuesta.textContent = "Respuesta: " + datos.respuesta;
      contenedor.appendChild(pCategoria);
      contenedor.appendChild(pRespuesta);

      var explicacion = EXPLICACION_CATEGORIAS[datos.categoria];
      if (explicacion) {{
        var pExplicacion = document.createElement("p");
        pExplicacion.textContent = "Qué significa: " + explicacion;
        contenedor.appendChild(pExplicacion);
      }}
    }} else {{
      contenedor.className = "resultado-error";
      var pError = document.createElement("p");
      pError.textContent = "Error: " + (datos.detail || respuestaHttp.status);
      contenedor.appendChild(pError);
    }}
  }} catch (error) {{
    contenedor.className = "resultado-error";
    contenedor.textContent = "Error de red al llamar a /consulta.";
  }}
}});
</script>
</div>
</body>
</html>
"""


@app.get("/chat", response_class=HTMLResponse)
async def chat() -> str:
    return _renderizar_html_chat()
