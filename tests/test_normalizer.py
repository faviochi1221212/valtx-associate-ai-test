import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from normalizer import normalizar


def test_minusculas():
    assert normalizar("COMO SOLICITO UN SERVICIO???") == "como solicito un servicio?"


def test_typos_multiples_y_puntuacion():
    assert (
        normalizar("kiero saber komo debuelvo un producto porfa")
        == "quiero saber cómo devuelvo un producto por favor"
    )


def test_signos_repetidos_interrogacion():
    assert normalizar("plazo devolucion?? urgente") == "plazo devolucion? urgente"


def test_formulario_y_gracias():
    assert (
        normalizar("hola necesito el formularioo de solicitud grcs")
        == "hola necesito el formulario de solicitud gracias"
    )


def test_garantia():
    assert normalizar("garantia cuanto es") == "garantía cuanto es"


def test_no_elimina_tildes_existentes():
    assert normalizar("¿Cuándo es la garantía?") == "¿cuándo es la garantía?"


def test_colapsa_exclamaciones():
    assert normalizar("no funciona!!!") == "no funciona!"
