"""Pipeline de medición end-to-end (HU7).

Corre las consultas reales de un CSV contra el sistema completo
(router.procesar_consulta) y compara la distribución de categorías
resultante contra el baseline calculado manualmente.

Uso como script:
    python tests/test_pipeline.py
    python tests/test_pipeline.py --csv otra_ruta.csv

También se puede correr como test de pytest (ver
test_pipeline_no_falla_con_csv_valido más abajo).
"""

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from router import procesar_consulta

RUTA_CSV_POR_DEFECTO = str(RAIZ / "data" / "consultas.csv")

CATEGORIAS = ("a", "b", "c", "d", "e")
BASELINE = {"a": 37.5, "b": 21.25, "c": 10.0, "d": 16.25, "e": 15.0}
UMBRAL_DESVIACION_PP = 3.0


def leer_consultas(ruta_csv: str) -> list:
    """Lee la columna "consulta" de un CSV separado por ";" (BOM incluido)."""
    with open(ruta_csv, encoding="utf-8-sig", newline="") as archivo_csv:
        lector = csv.DictReader(archivo_csv, delimiter=";")
        return [fila["consulta"] for fila in lector]


def clasificar_consultas(consultas: list) -> Counter:
    conteo = Counter()
    for texto in consultas:
        resultado = procesar_consulta(texto)
        conteo[resultado["categoria"]] += 1
    return conteo


def calcular_resumen(conteo: Counter, total: int) -> list:
    """Arma una fila por categoría (siempre las 5) con cantidad, %,
    baseline, diferencia en puntos porcentuales y si desvía >3pp."""
    filas = []
    for categoria in CATEGORIAS:
        cantidad = conteo.get(categoria, 0)
        porcentaje = (100 * cantidad / total) if total else 0.0
        baseline = BASELINE[categoria]
        diferencia = porcentaje - baseline
        filas.append(
            {
                "categoria": categoria,
                "cantidad": cantidad,
                "porcentaje": porcentaje,
                "baseline": baseline,
                "diferencia": diferencia,
                "desviado": abs(diferencia) > UMBRAL_DESVIACION_PP,
            }
        )
    return filas


def ejecutar_pipeline(ruta_csv: str) -> tuple:
    consultas = leer_consultas(ruta_csv)
    conteo = clasificar_consultas(consultas)
    filas = calcular_resumen(conteo, len(consultas))
    return len(consultas), filas


def imprimir_resumen(total: int, filas: list) -> None:
    print(f"Total: {total} consultas")
    print()

    encabezado = f"{'Cat':<4}{'Cant.':>7}{'%':>9}{'Baseline':>11}{'Diff':>9}  {'Estado'}"
    print(encabezado)
    print("-" * len(encabezado))
    for fila in filas:
        estado = "FUERA (>3pp)" if fila["desviado"] else "dentro"
        print(
            f"{fila['categoria']:<4}"
            f"{fila['cantidad']:>7}"
            f"{fila['porcentaje']:>8.2f}%"
            f"{fila['baseline']:>10.2f}%"
            f"{fila['diferencia']:>+8.2f}pp"
            f"  {estado}"
        )
    print()

    desviaciones = [fila for fila in filas if fila["desviado"]]
    if desviaciones:
        print("Desviaciones (> 3pp del baseline):")
        for fila in desviaciones:
            print(
                f"  - categoría '{fila['categoria']}': {fila['porcentaje']:.2f}% "
                f"vs baseline {fila['baseline']:.2f}% "
                f"(diferencia {fila['diferencia']:+.2f}pp)"
            )
    else:
        print("Sin desviaciones: las 5 categorías están dentro de 3pp del baseline.")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description="Pipeline de medición HU7")
    parser.add_argument(
        "--csv",
        default=RUTA_CSV_POR_DEFECTO,
        help="Ruta al CSV de consultas (default: data/consultas.csv)",
    )
    args = parser.parse_args()

    total, filas = ejecutar_pipeline(args.csv)
    imprimir_resumen(total, filas)


def test_pipeline_no_falla_con_csv_valido():
    total, filas = ejecutar_pipeline(RUTA_CSV_POR_DEFECTO)

    assert total > 0
    assert {fila["categoria"] for fila in filas} == set(CATEGORIAS)
    assert sum(fila["cantidad"] for fila in filas) == total
    for fila in filas:
        assert fila["cantidad"] >= 0
        assert 0.0 <= fila["porcentaje"] <= 100.0


if __name__ == "__main__":
    main()
