"""Clasificador por reglas de palabras clave para consultas que no superan
el umbral de similitud de HU2 (ver similarity_engine.py).

Las reglas viven en REGLAS_CLASIFICACION, separadas de la lógica de
clasificar_por_reglas, para que agregar una categoría nueva no requiera
tocar la función (abierto/cerrado): basta con añadir una entrada a la
lista, en la posición que le corresponda según su prioridad.
"""

import unicodedata

# Orden de prioridad: la lista se recorre de principio a fin y gana la
# primera categoría cuyas palabras clave aparezcan en el texto
# (d > c > b). Si ninguna aplica, se usa RESPUESTA_CATEGORIA_AMBIGUA (e).
REGLAS_CLASIFICACION = [
    {
        "categoria": "d",
        "palabras_clave": [
            "excepción",
            "reclamo",
            "reclamar",
            "negociar",
            "urgente",
            "queja",
            "caso especial",
        ],
        "respuesta": "Tu solicitud requiere revisión del equipo comercial, se generó un ticket.",
    },
    {
        "categoria": "c",
        "palabras_clave": [
            "contraseña",
            "sueldo",
            "vacaciones",
            "rrhh",
            "laptop",
            "facturación",
        ],
        "respuesta": "Esto no lo maneja el área comercial. Contacta a RRHH o IT según corresponda.",
    },
    {
        "categoria": "b",
        "palabras_clave": [
            "precio",
            "stock",
            "promoción",
            "promo",
            "tipo de cambio",
            "cotización",
        ],
        "respuesta": "Esa información se actualiza en el sistema comercial, no puedo confirmarla aquí.",
    },
]

RESPUESTA_CATEGORIA_AMBIGUA = "No logré entender tu consulta, ¿puedes reformularla con más detalle?"


def _quitar_acentos(texto: str) -> str:
    """Quita diacríticos (tildes, diéresis) de texto para comparación.

    Solo se usa internamente para el matching de palabras clave: no
    modifica el texto original que maneja el resto del sistema.
    """
    forma_descompuesta = unicodedata.normalize("NFD", texto)
    return "".join(
        caracter
        for caracter in forma_descompuesta
        if unicodedata.category(caracter) != "Mn"
    )


def clasificar_por_reglas(texto_normalizado: str) -> dict:
    """Clasifica texto_normalizado según REGLAS_CLASIFICACION.

    Devuelve un diccionario con "categoria" y "respuesta". Si el texto no
    contiene ninguna palabra clave conocida, la categoría es "e".

    La comparación ignora tildes/acentos (ej. "facturacion" matchea la
    keyword "facturación"), ya que las consultas reales suelen omitirlos.
    """
    texto_comparacion = _quitar_acentos(texto_normalizado)

    for regla in REGLAS_CLASIFICACION:
        for palabra_clave in regla["palabras_clave"]:
            if _quitar_acentos(palabra_clave) in texto_comparacion:
                return {
                    "categoria": regla["categoria"],
                    "respuesta": regla["respuesta"],
                }

    return {"categoria": "e", "respuesta": RESPUESTA_CATEGORIA_AMBIGUA}
