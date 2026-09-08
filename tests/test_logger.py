import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from logger import registrar_consulta

RESULTADO_A = {
    "texto_original": "¿Cómo solicito un producto del catálogo?",
    "categoria": "a",
    "respuesta": "1. Ingresar al portal interno...",
    "score": 0.999,
}

RESULTADO_B = {
    "texto_original": "¿Cuál es el precio actual del Producto Alfa?",
    "categoria": "b",
    "respuesta": "Esa información se actualiza en el sistema comercial, no puedo confirmarla aquí.",
}


def test_escribe_una_linea_jsonl_con_los_campos_esperados(tmp_path):
    ruta_log = tmp_path / "consultas.jsonl"

    registrar_consulta(RESULTADO_A, canal="correo", ruta_log=str(ruta_log))

    lineas = ruta_log.read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 1

    entrada = json.loads(lineas[0])
    assert entrada["texto_original"] == RESULTADO_A["texto_original"]
    assert entrada["categoria"] == "a"
    assert entrada["respuesta"] == RESULTADO_A["respuesta"]
    assert entrada["canal"] == "correo"
    assert entrada["score"] == RESULTADO_A["score"]
    assert "timestamp" in entrada


def test_no_agrega_score_si_el_resultado_no_lo_trae(tmp_path):
    ruta_log = tmp_path / "consultas.jsonl"

    registrar_consulta(RESULTADO_B, canal="chat", ruta_log=str(ruta_log))

    entrada = json.loads(ruta_log.read_text(encoding="utf-8").splitlines()[0])
    assert "score" not in entrada


def test_no_registra_campos_fuera_de_lo_permitido(tmp_path):
    ruta_log = tmp_path / "consultas.jsonl"

    registrar_consulta(RESULTADO_A, canal="correo", ruta_log=str(ruta_log))

    entrada = json.loads(ruta_log.read_text(encoding="utf-8").splitlines()[0])
    campos_permitidos = {
        "texto_original",
        "categoria",
        "respuesta",
        "canal",
        "timestamp",
        "score",
    }
    assert set(entrada.keys()) <= campos_permitidos


def test_multiples_llamadas_agregan_lineas_sin_sobreescribir(tmp_path):
    ruta_log = tmp_path / "consultas.jsonl"

    registrar_consulta(RESULTADO_A, canal="correo", ruta_log=str(ruta_log))
    registrar_consulta(RESULTADO_B, canal="chat", ruta_log=str(ruta_log))

    lineas = ruta_log.read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 2

    primera = json.loads(lineas[0])
    segunda = json.loads(lineas[1])
    assert primera["canal"] == "correo"
    assert segunda["canal"] == "chat"


def test_crea_la_carpeta_destino_si_no_existe(tmp_path):
    ruta_log = tmp_path / "carpeta_nueva" / "sub" / "consultas.jsonl"
    assert not ruta_log.parent.exists()

    registrar_consulta(RESULTADO_A, canal="formulario", ruta_log=str(ruta_log))

    assert ruta_log.exists()
    lineas = ruta_log.read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 1


def test_usa_ruta_por_defecto_logs_consultas_jsonl(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    registrar_consulta(RESULTADO_A, canal="telefono")

    ruta_por_defecto = tmp_path / "logs" / "consultas.jsonl"
    assert ruta_por_defecto.exists()
