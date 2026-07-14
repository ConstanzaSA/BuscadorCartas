import csv
import os
import sys
import traceback

from Funciones_Cartas import (BuscarCartas, Comparar_cartas, Leer_Mazo_Moxfield,Leer_URLs)
from Funciones_Precios import Comparar_Precios


ArchivoCartas = "Datos/Cartas_Buscadas.txt"
ArchivoURL = "Datos/URLs_Moxfield.txt"
ArchivosResultados = "Output/Resultados.csv"
ArchivoNoEncontradas = "Output/Cartas_No_Encontradas.txt"
ArchivoErrores = "Output/Errores.txt"


def ruta_local(nombre):
    carpeta = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(carpeta, nombre)


def texto_precio(valor):
    if valor is None:
        return "Sin precio"
    return f"{valor:.2f}".replace(".", ",")


def guardar_resultados(resultados):
    columnas = [
        "Mazo",
        "URL",
        "Carta",
        "Cantidad",
        "Edición",
        "Precio CK",
        "Imagen Moxfield"
    ]

    with open(
        ruta_local(ArchivosResultados),"w",newline="",encoding="utf-8-sig") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas, delimiter=";")
        escritor.writeheader()
        escritor.writerows(resultados)


def main():
    print("Buscador de Cartas en Moxfiled")

    cartas = BuscarCartas(ruta_local(ArchivoCartas))
    urls = Leer_URLs(ruta_local(ArchivoURL))

    if not cartas:
        print(f"ERROR: {ArchivoCartas} no tiene cartas validas.")
        input("Enter para cerrar...")
        return

    if not urls:
        print(f"ERROR: {ArchivoURL} no tiene URL validas.")
        input("Enter para cerrar...")
        return

    print(f"Cartas buscadas: {len(cartas)}")
    print(f"Mazos que a revisar: {len(urls)}")
    print()

    resultados = []
    errores = []
    nombres_encontrados = set()

    for indice, url in enumerate(urls, start=1):
        try:
            mazo = Leer_Mazo_Moxfield(url)
            encontradas = Comparar_cartas(mazo, cartas)
            print(f"Mazo: {mazo['nombre']}")
            print(f"Coincidencias: {len(encontradas)}")

            for numero, carta in enumerate(encontradas, start=1):
                print(
                    f"[{numero}/{len(encontradas)}] Consultando precio: " f"{carta['nombre']}")

                comparacion = Comparar_Precios(carta)
                impresion = comparacion["impresion_moxfield"] or {}
                barata = comparacion["impresion_mas_barata"] or {}

                precio_moxfield = impresion.get("precio_ck")
                precio_barato = barata.get("precio_usd")
                diferencia = comparacion.get("diferencia_usd")

                resultados.append(
                    {
                        "Mazo": mazo["nombre"],
                        "URL": mazo["url"],
                        "Carta": carta["nombre"],
                        "Cantidad": carta["cantidad"],
                        "Edición": (
                            impresion.get("set_name") or carta.get("set_name", "")
                        ),
                        "Precio CK": texto_precio(precio_moxfield),
                        "Imagen Moxfield": carta.get("imagen_url", "")
                    }
                )
                nombres_encontrados.add(carta["nombre_buscado"].casefold())

        except Exception as error:
            mensaje = f"{url} -> {type(error).__name__}: {error}"
            errores.append(mensaje)
            print(f"    ERROR: {error}")
        print()

    guardar_resultados(resultados)

    no_encontradas = [carta for carta in cartas if carta.casefold() not in nombres_encontrados]

    with open(ruta_local(ArchivoNoEncontradas),"w",encoding="utf-8",) as archivo:
        for carta in no_encontradas:
            archivo.write(carta + "\n")

    with open(ruta_local(ArchivoErrores), "w", encoding="utf-8") as archivo:
        for error in errores:
            archivo.write(error + "\n")

    print("Termino de Busqueda")
    print(f"Cartas Encontradas: {len(resultados)}")
    print(f"Cartas No Encontradas: {len(no_encontradas)}")

    if resultados and sys.platform.startswith("win"):
        try:
            os.startfile(ruta_local(ArchivosResultados))
        except OSError:
            pass

    input("Presiona Enter para cerrar...")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as error:
        print(f"ERROR: no se encontró el archivo: {error.filename}")
        input("Presiona Enter para cerrar...")

    except Exception as error:
        with open(ruta_local(ArchivoErrores), "w", encoding="utf-8") as archivo:
            traceback.print_exc(file=archivo)

        print(f"ERROR: {error}")
        print(f"Guardado en {ArchivoErrores}.")
        input("Presiona Enter para cerrar...")
