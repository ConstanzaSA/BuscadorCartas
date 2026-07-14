import re
import time
from urllib.parse import urlparse
import requests


CABECERAS_MOXFIELD = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36")}


def BuscarCartas(nombre_archivo):
    cartas = []
    with open(nombre_archivo, "r", encoding="utf-8") as archivo:
        for numero_linea, linea in enumerate(archivo, start=1):
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            match = re.match(r"^\d+\s+(.+)$", linea)
            if match:
                nombre_carta = match.group(1).strip()
                cartas.append(nombre_carta)
    return cartas


def Leer_URLs(nombre_archivo):
    urls = []
    with open(nombre_archivo, "r", encoding="utf-8") as archivo:
        for numero_linea, linea in enumerate(archivo, start=1):
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            if "moxfield.com/decks/" not in linea.lower():
                print(
                    f"ADVERTENCIA: la línea {numero_linea} no parece ser "
                    f"una URL de mazo de Moxfield: {linea}")
                continue
            urls.append(linea)
    return urls


def Obtener_ID_Moxfield(url):
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    partes = [parte for parte in parsed.path.split("/") if parte]
    try:
        posicion_decks = partes.index("decks")
        return partes[posicion_decks + 1]
    except (ValueError, IndexError) as error:
        raise ValueError(f"No se pudo obtener el ID desde esta URL: {url}") from error


def _normalizar_nombre(nombre):
    return " ".join(nombre.strip().casefold().split())

def _convertir_precio(valor):
    if valor is None:
        return None

    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _obtener_precio_ck(carta, entrada):
    """
    Obtiene el precio de Card Kingdom correspondiente al acabado
    de la carta: normal, foil o etched.
    """

    precios = carta.get("prices") or {}

    acabado = str(
        entrada.get("finish") or "nonfoil"
    ).strip().lower()

    if acabado == "etched":
        clave = "ck_etched"

    elif acabado == "foil" or entrada.get("isFoil", False):
        clave = "ck_foil"

    else:
        clave = "ck"

    return _convertir_precio(precios.get(clave))


def _obtener_imagen_moxfield(carta):
    imagenes = (carta.get("image_uris") or carta.get("imageUris") or {})

    if isinstance(imagenes, dict):
        for tamaño in ("normal", "large", "png", "small"):
            url = imagenes.get(tamaño)
            if url:
                return url

    for campo in ("imageUrl","image_url","imageUri","image_uri"):
        url = carta.get(campo)
        if url:
            return url

    moxfield_id = carta.get("id")
    if moxfield_id:
        return (
            "https://assets.moxfield.net/cards/"
            f"card-{moxfield_id}-normal.webp")
    return ""


def Leer_Mazo_Moxfield(url):
    deck_id = Obtener_ID_Moxfield(url)
    api_url = f"https://api2.moxfield.com/v3/decks/all/{deck_id}"
    respuesta = requests.get(api_url,headers=CABECERAS_MOXFIELD,timeout=30)

    if respuesta.status_code == 404:
        raise RuntimeError("El mazo no existe, es privado o la URL está mal escrita.")

    if respuesta.status_code == 403:
        raise RuntimeError(
            "Moxfield bloqueó la consulta automática (error 403). "
            "Prueba nuevamente más tarde.")

    respuesta.raise_for_status()
    datos = respuesta.json()
    nombre_mazo = datos.get("name", deck_id)
    boards = datos.get("boards", {})
    cartas = []

    for nombre_tablero, tablero in boards.items():
        cartas_tablero = tablero.get("cards", {})
        for entrada in cartas_tablero.values():
            carta = entrada.get("card", {})
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
    time.sleep(0.25)
    return {"nombre": nombre_mazo,"url": url,"cartas": cartas}


def Comparar_cartas(mazo, cartas_buscadas):
    buscadas_normalizadas = {_normalizar_nombre(nombre): nombre for nombre in cartas_buscadas}
    encontradas = []
    for carta_mazo in mazo["cartas"]:
        nombre_normalizado = carta_mazo["nombre_normalizado"]
        if nombre_normalizado in buscadas_normalizadas:
            coincidencia = carta_mazo.copy()
            coincidencia["nombre_buscado"] = buscadas_normalizadas[nombre_normalizado]
            encontradas.append(coincidencia)
    return encontradas
