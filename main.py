"""Versión de consola opcional. Para la web: streamlit run app.py"""

import csv
from pathlib import Path

from Funciones_Cartas import (
    BuscarCartas,
    Comparar_cartas,
    Leer_Mazo_Moxfield,
    Leer_URLs,
)

BASE_DIR = Path(__file__).resolve().parent
ARCHIVO_CARTAS = BASE_DIR / "Datos" / "Cartas_Buscadas.txt"
ARCHIVO_URLS = BASE_DIR / "Datos" / "URLs_Moxfield.txt"
ARCHIVO_RESULTADOS = BASE_DIR / "Resultados.csv"


def texto_precio(valor):
    if valor is None:
        return "Sin precio"
    return f"{valor:.2f}".replace(".", ",")


def main():
    cartas = BuscarCartas(ARCHIVO_CARTAS)
    urls = Leer_URLs(ARCHIVO_URLS)
    resultados = []

    for url in urls:
        mazo = Leer_Mazo_Moxfield(url)
        encontradas = Comparar_cartas(mazo, cartas)

        for carta in encontradas:
            resultados.append(
                {
                    "Mazo": mazo["nombre"],
                    "Carpeta": carta["tablero"],
                    "Carta": carta["nombre"],
                    "Cantidad": carta["cantidad"],
                    "Edición": carta["set_name"],
                    "Precio CK": texto_precio(carta["precio_ck"]),
                    "Imagen": carta["imagen_url"],
                }
            )

    columnas = [
        "Mazo",
        "Carpeta",
        "Carta",
        "Cantidad",
        "Edición",
        "Precio CK",
        "Imagen",
    ]

    with open(
        ARCHIVO_RESULTADOS,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as archivo:
        escritor = csv.DictWriter(
            archivo,
            fieldnames=columnas,
            delimiter=";",
        )
        escritor.writeheader()
        escritor.writerows(resultados)

    print(f"Resultados guardados en: {ARCHIVO_RESULTADOS}")


if __name__ == "__main__":
    main()
