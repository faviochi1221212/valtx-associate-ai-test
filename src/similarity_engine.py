"""Motor de similitud: compara una consulta normalizada contra preguntas canónicas."""

import json

from sentence_transformers import SentenceTransformer, util

MODELO_EMBEDDINGS = "paraphrase-multilingual-MiniLM-L12-v2"
UMBRAL_SIMILITUD = 0.85

_modelo = None


def _obtener_modelo() -> SentenceTransformer:
    global _modelo
    if _modelo is None:
        _modelo = SentenceTransformer(MODELO_EMBEDDINGS)
    return _modelo


def _cargar_qa_canonico(ruta_qa: str) -> list:
    with open(ruta_qa, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def buscar_pregunta_similar(texto_normalizado: str, ruta_qa: str) -> dict:
    """Compara texto_normalizado contra las preguntas canónicas en ruta_qa.

    Cada entrada de qa_canonico puede tener varias formulaciones
    ("preguntas"); se compara el texto contra todas ellas y cada entrada
    se queda con el score más alto obtenido entre sus formulaciones.

    Devuelve un diccionario con la formulación más similar encontrada, la
    respuesta de su entrada, el score de similitud (coseno) obtenido y si
    dicho score supera UMBRAL_SIMILITUD.
    """
    qa_canonico = _cargar_qa_canonico(ruta_qa)
    modelo = _obtener_modelo()

    embedding_consulta = modelo.encode(texto_normalizado, convert_to_tensor=True)

    # Aplana todas las formulaciones de todas las entradas en una sola lista,
    # recordando a qué entrada pertenece cada una.
    formulaciones = []
    indices_entrada = []
    for indice_entrada, par in enumerate(qa_canonico):
        for formulacion in par["preguntas"]:
            formulaciones.append(formulacion)
            indices_entrada.append(indice_entrada)

    embeddings_formulaciones = modelo.encode(formulaciones, convert_to_tensor=True)
    scores = util.cos_sim(embedding_consulta, embeddings_formulaciones)[0]

    indice_mejor = int(scores.argmax())
    mejor_score = float(scores[indice_mejor])
    mejor_entrada = qa_canonico[indices_entrada[indice_mejor]]

    return {
        "pregunta_canonica": formulaciones[indice_mejor],
        "respuesta": mejor_entrada["respuesta"],
        "score": mejor_score,
        "supera_umbral": mejor_score >= UMBRAL_SIMILITUD,
    }
