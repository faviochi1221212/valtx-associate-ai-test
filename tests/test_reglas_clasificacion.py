import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from normalizer import normalizar
from reglas_clasificacion import clasificar_por_reglas

RESPUESTA_B = "Esa información se actualiza en el sistema comercial, no puedo confirmarla aquí."
RESPUESTA_C = "Esto no lo maneja el área comercial. Contacta a RRHH o IT según corresponda."
RESPUESTA_D = "Tu solicitud requiere revisión del equipo comercial, se generó un ticket."
RESPUESTA_E = "No logré entender tu consulta, ¿puedes reformularla con más detalle?"


# --- Categoría d: requiere juicio humano ---

def test_excepcion_es_categoria_d():
    texto = normalizar("Necesito un descuento mayor al de la tabla, ¿pueden hacer una excepción?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "d"
    assert resultado["respuesta"] == RESPUESTA_D


def test_queja_es_categoria_d():
    texto = normalizar("Tengo una queja sobre la atención que recibí, ¿con quién hablo?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "d"
    assert resultado["respuesta"] == RESPUESTA_D


# --- Categoría c: fuera de alcance del área comercial ---

def test_contrasena_es_categoria_c():
    texto = normalizar("¿Cómo reseteo mi contraseña del correo?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "c"
    assert resultado["respuesta"] == RESPUESTA_C


def test_sueldos_es_categoria_c():
    texto = normalizar("¿Cuándo pagan los sueldos este mes?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "c"
    assert resultado["respuesta"] == RESPUESTA_C


# --- Categoría b: dato cambiante o no documentado ---

def test_precio_es_categoria_b():
    texto = normalizar("¿Cuál es el precio actual del Producto Alfa?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "b"
    assert resultado["respuesta"] == RESPUESTA_B


def test_stock_es_categoria_b():
    texto = normalizar("¿Hay stock disponible del Producto Beta hoy?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "b"
    assert resultado["respuesta"] == RESPUESTA_B


# --- Categoría e: ambigua / no identificada ---

def test_consulta_vaga_es_categoria_e():
    texto = normalizar("Hola, tengo una duda.")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "e"
    assert resultado["respuesta"] == RESPUESTA_E


def test_pregunta_corta_es_categoria_e():
    texto = normalizar("¿Eso se puede?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "e"
    assert resultado["respuesta"] == RESPUESTA_E


# --- Caso especial: "especial" suelto no debe activar la categoría d ---

def test_palabra_especial_suelta_no_activa_categoria_d():
    texto = normalizar("¿Hay algún proceso especial para pedidos grandes?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] != "d"
    assert resultado["categoria"] == "e"


def test_frase_caso_especial_contigua_si_activa_categoria_d():
    texto = normalizar("Este es un caso especial, necesito que lo revisen manualmente.")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "d"
    assert resultado["respuesta"] == RESPUESTA_D


def test_csv_c029_caso_es_especial_no_es_frase_contigua():
    """Documenta un caso real de consultas.csv (fila C029): el texto dice
    "caso es especial" (con una palabra intermedia), no la frase contigua
    "caso especial". Bajo la regla de coincidencia de frase completa
    especificada en HU3, esto NO activa la categoría "d" y cae en "e".
    Revisar manualmente si se desea un matching más flexible."""
    texto = normalizar("Mi caso es especial, ¿pueden revisarlo manualmente?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "e"


# --- Prioridad: d > c > b > e cuando hay palabras clave de varias categorías ---

def test_prioridad_d_sobre_b_cuando_hay_ambas():
    texto = normalizar("Tengo un reclamo sobre el precio que me cobraron.")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "d"


def test_prioridad_c_sobre_b_cuando_hay_ambas():
    texto = normalizar("¿El precio de la laptop nueva ya está aprobado?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "c"


# --- Keywords sin tildes: el texto del usuario puede venir sin diacríticos ---

def test_facturacion_sin_tilde_es_categoria_c():
    texto = normalizar("necesito acceso al sistema de facturacion")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "c"
    assert resultado["respuesta"] == RESPUESTA_C


# --- Keyword "reclamar" (forma verbal de "reclamo") activa categoría d ---

def test_reclamar_es_categoria_d():
    texto = normalizar("El producto que recibí no es lo que esperaba, quiero reclamar.")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "d"
    assert resultado["respuesta"] == RESPUESTA_D


# --- Keywords nuevas para huecos de cobertura detectados en el QA de HU4 ---

def test_trimestre_y_fecha_limite_es_categoria_b():
    texto = normalizar("¿Cuál es la fecha límite para pedidos de este trimestre?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "b"
    assert resultado["respuesta"] == RESPUESTA_B


def test_sla_es_categoria_b():
    texto = normalizar("¿Cuál es el tiempo de atención (SLA) de una solicitud?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "b"
    assert resultado["respuesta"] == RESPUESTA_B


def test_cuotas_es_categoria_b():
    texto = normalizar("¿Puedo pagar en cuotas?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "b"
    assert resultado["respuesta"] == RESPUESTA_B


def test_soporte_tecnico_es_categoria_b():
    texto = normalizar("¿Ofrecen soporte técnico después de la compra?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "b"
    assert resultado["respuesta"] == RESPUESTA_B


def test_certificaciones_es_categoria_b():
    texto = normalizar("¿Tienen certificaciones de calidad?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "b"
    assert resultado["respuesta"] == RESPUESTA_B


def test_confidencialidad_es_categoria_b():
    texto = normalizar("¿Cuál es la política de confidencialidad de datos?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "b"
    assert resultado["respuesta"] == RESPUESTA_B


def test_envios_y_provincia_es_categoria_b():
    texto = normalizar("¿Hacen envíos a provincia?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "b"
    assert resultado["respuesta"] == RESPUESTA_B


def test_proximo_lote_es_categoria_b():
    texto = normalizar("¿Cuándo llega el próximo lote del Producto Gamma?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "b"
    assert resultado["respuesta"] == RESPUESTA_B


def test_recursos_humanos_es_categoria_c():
    texto = normalizar("¿Dónde queda la oficina de recursos humanos?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "c"
    assert resultado["respuesta"] == RESPUESTA_C


def test_comedor_es_categoria_c():
    texto = normalizar("¿Tienen un comedor en la oficina?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "c"
    assert resultado["respuesta"] == RESPUESTA_C


def test_proveedor_es_categoria_d():
    texto = normalizar("Quisiera proponer trabajar con un nuevo proveedor, ¿a quién contacto?")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "d"
    assert resultado["respuesta"] == RESPUESTA_D


def test_reembolso_es_categoria_d():
    texto = normalizar("Quiero un reembolso completo aunque usé el producto.")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "d"
    assert resultado["respuesta"] == RESPUESTA_D


def test_hablar_con_alguien_es_categoria_d():
    texto = normalizar("Necesito hablar con alguien, es complicado de explicar por chat.")
    resultado = clasificar_por_reglas(texto)
    assert resultado["categoria"] == "d"
    assert resultado["respuesta"] == RESPUESTA_D
