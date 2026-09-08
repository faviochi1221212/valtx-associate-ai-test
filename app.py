"""API HTTP del asistente de consultas comerciales (HU6).

Coordina HTTP <-> router (HU4) <-> logger (HU5): recibe la consulta,
delega la clasificación y el registro, y traduce el resultado a HTTP.
No reimplementa lógica de negocio.
"""

import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from router import procesar_consulta
from logger import registrar_consulta

logging.basicConfig(level=logging.INFO)
_logger_interno = logging.getLogger("app")

RATE_LIMIT_POR_DEFECTO = "10/minute"
CANALES_VALIDOS = {"correo", "chat", "formulario", "telefono"}
MAX_LONGITUD_TEXTO = 500


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
