import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from router import procesar_consulta

CASOS_END_TO_END = [
    ("¿Cómo solicito un producto del catálogo?", "a"),
    ("¿Cuánto dura la garantía?", "a"),
    ("¿Puedo cancelar una solicitud ya enviada?", "a"),
    ("¿Cuál es el precio actual del Producto Alfa?", "b"),
    ("¿Hay stock disponible del Producto Beta hoy?", "b"),
    ("¿Cómo reseteo mi contraseña del correo?", "c"),
    ("¿Cuándo pagan los sueldos este mes?", "c"),
    ("Necesito un descuento mayor al de la tabla, ¿pueden hacer una excepción?", "d"),
    ("Tengo una queja sobre la atención que recibí, ¿con quién hablo?", "d"),
    ("Hola, tengo una duda.", "e"),
]


@pytest.mark.parametrize("texto_original, categoria_esperada", CASOS_END_TO_END)
def test_procesar_consulta_end_to_end(texto_original, categoria_esperada):
    resultado = procesar_consulta(texto_original)
    assert resultado["categoria"] == categoria_esperada
    assert resultado["texto_original"] == texto_original


def test_categoria_a_incluye_score_para_trazabilidad():
    resultado = procesar_consulta("¿Cómo solicito un producto del catálogo?")
    assert resultado["categoria"] == "a"
    assert "score" in resultado
    assert isinstance(resultado["score"], float)


def test_categoria_b_no_requiere_score():
    resultado = procesar_consulta("¿Cuál es el precio actual del Producto Alfa?")
    assert resultado["categoria"] == "b"
