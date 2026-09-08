import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "src"))

import app as app_module
import router

client = TestClient(app_module.app)


@pytest.fixture(autouse=True)
def resetear_rate_limiter():
    """Aísla cada test del estado (en memoria) del rate limiter.

    Se resetea ANTES de cada test para que el resultado no dependa del
    orden de ejecución ni de cuántas llamadas hicieron los tests previos
    (TestClient reporta siempre la misma IP simulada, así que todas las
    llamadas comparten el mismo contador salvo por este reset).
    """
    app_module.limiter.reset()
    yield


@pytest.fixture(autouse=True)
def aislar_log_real(tmp_path, monkeypatch):
    """Evita que las llamadas reales a registrar_consulta() (vía /consulta,
    que no recibe ruta_log y usa el default de logger.py) escriban en
    logs/consultas.jsonl del repositorio durante los tests."""
    monkeypatch.chdir(tmp_path)


PAYLOAD_VALIDO = {"texto": "¿Cómo solicito un producto del catálogo?", "canal": "chat"}


def test_consulta_valida_devuelve_200_con_categoria_y_respuesta():
    respuesta = client.post("/consulta", json=PAYLOAD_VALIDO)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert "categoria" in cuerpo
    assert "respuesta" in cuerpo


def test_consulta_valida_no_expone_score_ni_campos_internos():
    respuesta = client.post("/consulta", json=PAYLOAD_VALIDO)

    cuerpo = respuesta.json()
    assert set(cuerpo.keys()) == {"categoria", "respuesta"}
    assert "score" not in cuerpo
    assert "texto_original" not in cuerpo


def test_texto_vacio_devuelve_400_no_422():
    respuesta = client.post("/consulta", json={"texto": "", "canal": "chat"})

    assert respuesta.status_code == 400
    assert respuesta.status_code != 422


def test_texto_mayor_a_500_caracteres_devuelve_400_no_422():
    respuesta = client.post("/consulta", json={"texto": "a" * 501, "canal": "chat"})

    assert respuesta.status_code == 400
    assert respuesta.status_code != 422


def test_canal_no_reconocido_devuelve_400_no_422():
    respuesta = client.post("/consulta", json={"texto": "hola", "canal": "whatsapp"})

    assert respuesta.status_code == 400
    assert respuesta.status_code != 422


def test_texto_no_string_devuelve_400_no_422():
    respuesta = client.post("/consulta", json={"texto": 12345, "canal": "chat"})

    assert respuesta.status_code == 400
    assert respuesta.status_code != 422


def test_payload_invalido_no_expone_traceback_ni_detalles_internos():
    respuesta = client.post("/consulta", json={"texto": "", "canal": "chat"})

    cuerpo = respuesta.json()
    texto_completo = str(cuerpo)
    assert "Traceback" not in texto_completo
    assert ".py" not in texto_completo


def test_error_interno_inesperado_devuelve_500_con_mensaje_generico(monkeypatch):
    def _procesar_consulta_que_falla(texto_original):
        raise RuntimeError("boom: detalle interno que no debe llegar al cliente")

    monkeypatch.setattr(app_module, "procesar_consulta", _procesar_consulta_que_falla)

    respuesta = client.post("/consulta", json=PAYLOAD_VALIDO)

    assert respuesta.status_code == 500
    cuerpo = respuesta.json()
    assert cuerpo == {"detail": "Error interno, intenta más tarde"}
    assert "boom" not in str(cuerpo)
    assert "Traceback" not in str(cuerpo)
    assert "RuntimeError" not in str(cuerpo)


def test_rate_limit_excedido_devuelve_429(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT", "2/minute")

    respuesta_1 = client.post("/consulta", json=PAYLOAD_VALIDO)
    respuesta_2 = client.post("/consulta", json=PAYLOAD_VALIDO)
    respuesta_3 = client.post("/consulta", json=PAYLOAD_VALIDO)

    assert respuesta_1.status_code == 200
    assert respuesta_2.status_code == 200
    assert respuesta_3.status_code == 429
