"""Logger: registra cada consulta procesada en formato JSONL (HU5).

Registra únicamente lo necesario para medir valor y auditar respuestas:
texto_original, categoria, respuesta, canal, timestamp y score (si
aplica). No debe expandirse a registrar metadata adicional.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

RUTA_LOG_POR_DEFECTO = "logs/consultas.jsonl"


def registrar_consulta(resultado: dict, canal: str, ruta_log: str = RUTA_LOG_POR_DEFECTO) -> None:
    """Agrega una línea JSONL con el resultado de procesar_consulta().

    resultado es el diccionario devuelto por router.procesar_consulta()
    (con "texto_original", "categoria", "respuesta" y opcionalmente
    "score"). canal identifica el medio de la consulta (ej. "correo",
    "chat", "formulario", "telefono").
    """
    entrada = {
        "texto_original": resultado["texto_original"],
        "categoria": resultado["categoria"],
        "respuesta": resultado["respuesta"],
        "canal": canal,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if "score" in resultado:
        entrada["score"] = resultado["score"]

    ruta = Path(ruta_log)
    ruta.parent.mkdir(parents=True, exist_ok=True)

    with open(ruta, "a", encoding="utf-8") as archivo_log:
        archivo_log.write(json.dumps(entrada, ensure_ascii=False) + "\n")
