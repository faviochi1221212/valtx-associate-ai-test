"""Router: une normalizer + similarity engine + reglas en un solo flujo (HU4).

Este módulo coordina el flujo de decisión de punta a punta; no reimplementa
la lógica de HU1/HU2/HU3, solo la invoca en orden. normalizer,
similarity_engine y reglas_clasificacion no importan este módulo, así que
no hay dependencias circulares.
"""

from pathlib import Path

from normalizer import normalizar
from similarity_engine import buscar_pregunta_similar
from reglas_clasificacion import clasificar_por_reglas

RUTA_QA_CANONICO = str(Path(__file__).resolve().parent.parent / "data" / "qa_canonico.json")


def procesar_consulta(texto_original: str) -> dict:
    """Procesa una consulta comercial y devuelve una única decisión.

    1. Normaliza texto_original.
    2. Busca la pregunta canónica más parecida (HU2).
    3. Si supera_umbral es True: categoría "a", respuesta canónica tal cual.
    4. Si no: clasifica por palabras clave (HU3), categoría b/c/d/e.
    """
    texto_normalizado = normalizar(texto_original)

    resultado_similitud = buscar_pregunta_similar(texto_normalizado, RUTA_QA_CANONICO)

    if resultado_similitud["supera_umbral"]:
        return {
            "texto_original": texto_original,
            "categoria": "a",
            "respuesta": resultado_similitud["respuesta"],
            "score": resultado_similitud["score"],
        }

    resultado_reglas = clasificar_por_reglas(texto_normalizado)

    return {
        "texto_original": texto_original,
        "categoria": resultado_reglas["categoria"],
        "respuesta": resultado_reglas["respuesta"],
    }
