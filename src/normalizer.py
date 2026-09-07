"""Normalizador de texto para consultas comerciales."""

import re

# Diccionario de typos comunes del dominio -> forma corregida.
# Estructura separada de la lógica para facilitar su extensión.
TYPOS_COMUNES = {
    "komo": "cómo",
    "kiero": "quiero",
    "debuelvo": "devuelvo",
    "grcs": "gracias",
    "porfa": "por favor",
    "garantia": "garantía",
    "formularioo": "formulario",
}


def normalizar(texto: str) -> str:
    """Limpia el texto crudo de una consulta para el motor de similitud.

    - Convierte a minúsculas.
    - Colapsa signos de puntuación repetidos (ej. "???" -> "?").
    - Corrige typos comunes del dominio (ver TYPOS_COMUNES).
    """
    resultado = texto.lower()

    resultado = re.sub(r"([!?.,])\1+", r"\1", resultado)

    for typo, correccion in TYPOS_COMUNES.items():
        resultado = re.sub(
            rf"\b{re.escape(typo)}\b", correccion, resultado
        )

    return resultado
