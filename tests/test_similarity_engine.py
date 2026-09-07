import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from normalizer import normalizar
from similarity_engine import UMBRAL_SIMILITUD, buscar_pregunta_similar

RUTA_QA = str(RAIZ / "data" / "qa_canonico.json")


def test_proceso_de_solicitud_supera_umbral():
    texto = normalizar("¿como pido un producto?")
    resultado = buscar_pregunta_similar(texto, RUTA_QA)
    assert resultado["score"] >= UMBRAL_SIMILITUD
    assert resultado["supera_umbral"] is True
    assert "F-01" in resultado["respuesta"]


def test_garantia_supera_umbral():
    texto = normalizar("cuanto dura la garantia del producto")
    resultado = buscar_pregunta_similar(texto, RUTA_QA)
    assert resultado["score"] >= UMBRAL_SIMILITUD
    assert resultado["supera_umbral"] is True
    assert "12 meses" in resultado["respuesta"]


def test_variante_catalogo_supera_umbral():
    texto = normalizar("¿cómo solicito un producto del catálogo?")
    resultado = buscar_pregunta_similar(texto, RUTA_QA)
    assert resultado["score"] >= UMBRAL_SIMILITUD
    assert resultado["supera_umbral"] is True
    assert "F-01" in resultado["respuesta"]


def test_variante_pasos_servicio_nuevo_supera_umbral():
    texto = normalizar("¿cuáles son los pasos para pedir un servicio nuevo?")
    resultado = buscar_pregunta_similar(texto, RUTA_QA)
    assert resultado["score"] >= UMBRAL_SIMILITUD
    assert resultado["supera_umbral"] is True
    assert "F-01" in resultado["respuesta"]


def test_consulta_de_precio_no_supera_umbral():
    texto = normalizar("cuanto cuesta el producto alfa")
    resultado = buscar_pregunta_similar(texto, RUTA_QA)
    assert resultado["score"] < UMBRAL_SIMILITUD
    assert resultado["supera_umbral"] is False


def test_consulta_de_stock_no_supera_umbral():
    texto = normalizar("cuanto stock tienen disponible ahorita en almacen")
    resultado = buscar_pregunta_similar(texto, RUTA_QA)
    assert resultado["score"] < UMBRAL_SIMILITUD
    assert resultado["supera_umbral"] is False
