import re
import time
from urllib.parse import urlparse

import requests


CABECERAS_MOXFIELD = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
}


def _normalizar_nombre(nombre):
    return " ".join(str(nombre).strip().casefold().split())


def Parsear_Cartas_Texto(texto):
    """Convierte líneas como '1 Aether Vial' en nombres de cartas."""
    cartas = []
    nombres_vistos = set()

    for linea in str(texto).splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue

        coincidencia = re.match(r"^\s*\d+\s+(.+?)\s*$", linea)
        nombre = coincidencia.group(1).strip() if coincidencia else linea
        normalizado = _normalizar_nombre(nombre)

        if normalizado and normalizado not in nombres_vistos:
            cartas.append(nombre)
            nombres_vistos.add(normalizado)

    return cartas


def BuscarCartas(nombre_archivo):
    with open(nombre_archivo, "r", encoding="utf-8") as archivo:
        return Parsear_Cartas_Texto(archivo.read())


def Leer_URLs(nombre_archivo):
    urls = []
    with open(nombre_archivo, "r", encoding="utf-8") as archivo:
        for numero_linea, linea in enumerate(archivo, start=1):
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            if "moxfield.com/decks/" not in linea.casefold():
                print(
                    f"ADVERTENCIA: la línea {numero_linea} no parece ser "
                    f"una URL de Moxfield: {linea}"
                )
                continue
            urls.append(linea)
    return urls


def Obtener_ID_Moxfield(url):
    url = str(url).strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    partes = [parte for parte in parsed.path.split("/") if parte]

    try:
        posicion_decks = partes.index("decks")
        return partes[posicion_decks + 1]
    except (ValueError, IndexError) as error:
        raise ValueError(
            f"No se pudo obtener el ID desde esta URL: {url}"
        ) from error


def _convertir_precio(valor):
    if valor in (None, ""):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _obtener_precio_ck(carta, entrada):
    precios = carta.get("prices") or {}
    acabado = str(entrada.get("finish") or "nonfoil").strip().casefold()

    if acabado == "etched":
        clave = "ck_etched"
    elif acabado == "foil" or entrada.get("isFoil", False):
        clave = "ck_foil"
    else:
        clave = "ck"

    precio = _convertir_precio(precios.get(clave))
    if precio is None and clave != "ck":
        precio = _convertir_precio(precios.get("ck"))
    return precio


def _obtener_imagen_moxfield(carta):
    imagenes = (
        carta.get("image_uris")
        or carta.get("imageUris")
        or carta.get("images")
        or {}
    )

    if isinstance(imagenes, dict):
        for tamaño in ("normal", "large", "png", "small"):
            url = imagenes.get(tamaño)
            if url:
                return url

    for campo in ("imageUrl", "image_url", "imageUri", "image_uri"):
        url = carta.get(campo)
        if url:
            return url

    scryfall_id = carta.get("scryfall_id")
    if scryfall_id:
        return (
            f"https://api.scryfall.com/cards/{scryfall_id}"
            "?format=image&version=normal"
        )

    return ""


def Leer_Mazo_Moxfield(url):
    deck_id = Obtener_ID_Moxfield(url)
    api_url = f"https://api2.moxfield.com/v3/decks/all/{deck_id}"

    respuesta = requests.get(
        api_url,
        headers=CABECERAS_MOXFIELD,
        timeout=30,
    )

    if respuesta.status_code == 404:
        raise RuntimeError(
            "El mazo no existe, es privado o la URL está mal escrita."
        )
    if respuesta.status_code == 403:
        raise RuntimeError(
            "Moxfield bloqueó la consulta automática (error 403)."
        )

    respuesta.raise_for_status()
    datos = respuesta.json()

    nombre_mazo = datos.get("name", deck_id)
    boards = datos.get("boards", {})
    cartas = []

    if not isinstance(boards, dict):
        raise RuntimeError("La respuesta de Moxfield no contiene tableros válidos.")

    for nombre_tablero, tablero in boards.items():
        if not isinstance(tablero, dict):
            continue

        cartas_tablero = tablero.get("cards", {})
        if not isinstance(cartas_tablero, dict):
            continue

        for entrada in cartas_tablero.values():
            if not isinstance(entrada, dict):
                continue

            carta = entrada.get("card", {})
            if not isinstance(carta, dict):
                continue

            nombre = carta.get("name")
            if not nombre:
                continue

            cartas.append(
                {
                    "nombre": nombre,
                    "nombre_normalizado": _normalizar_nombre(nombre),
                    "cantidad": entrada.get("quantity", 1),
                    "tablero": nombre_tablero,
                    "scryfall_id": carta.get("scryfall_id"),
                    "moxfield_id": carta.get("id", ""),
                    "set": carta.get("set", ""),
                    "set_name": carta.get("set_name", ""),
                    "collector_number": carta.get("cn", ""),
                    "es_foil": entrada.get("isFoil", False),
                    "finish": entrada.get("finish", "nonfoil"),
                    "precio_ck": _obtener_precio_ck(carta, entrada),
                    "cardkingdom_url": carta.get("cardKingdomUrl", ""),
                    "imagen_url": _obtener_imagen_moxfield(carta),
                }
            )

    time.sleep(0.15)
    return {"nombre": nombre_mazo, "url": url, "cartas": cartas}


def Comparar_cartas(mazo, cartas_buscadas):
    buscadas_normalizadas = {
        _normalizar_nombre(nombre): nombre for nombre in cartas_buscadas
    }

    encontradas = []
    for carta_mazo in mazo.get("cartas", []):
        nombre_normalizado = carta_mazo.get("nombre_normalizado", "")
        if nombre_normalizado in buscadas_normalizadas:
            coincidencia = carta_mazo.copy()
            coincidencia["nombre_buscado"] = (
                buscadas_normalizadas[nombre_normalizado]
            )
            encontradas.append(coincidencia)

    return encontradas
