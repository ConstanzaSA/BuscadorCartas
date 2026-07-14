import time
import requests

CABECERAS_SCRYFALL = {"Accept": "application/json","User-Agent": "BuscadorCartasMoxfield/1.0",}
_cache_impresiones = {}
_cache_mas_baratas = {}
_ultima_busqueda = 0.0


def _precio_usd(carta):
    precio = carta.get("prices", {}).get("usd")
    if precio is None:
        return None
    try:
        return float(precio)
    except (TypeError, ValueError):
        return None


def _esperar_busqueda_scryfall():
    global _ultima_busqueda
    transcurrido = time.monotonic() - _ultima_busqueda
    espera = 0.55 - transcurrido
    if espera > 0:
        time.sleep(espera)
    _ultima_busqueda = time.monotonic()


def Precio_Impresion_Scryfall(scryfall_id):
    if not scryfall_id:
        return None
    if scryfall_id in _cache_impresiones:
        return _cache_impresiones[scryfall_id]
    url = f"https://api.scryfall.com/cards/{scryfall_id}"
    respuesta = requests.get(url, headers=CABECERAS_SCRYFALL, timeout=30)
    if respuesta.status_code == 404:
        return None

    respuesta.raise_for_status()
    carta = respuesta.json()
    resultado = {
        "nombre": carta.get("name", ""),
        "precio_usd": _precio_usd(carta),
        "set": carta.get("set", ""),
        "set_name": carta.get("set_name", ""),
        "collector_number": carta.get("collector_number", ""),
        "scryfall_uri": carta.get("scryfall_uri", "")}

    _cache_impresiones[scryfall_id] = resultado
    return resultado


def Precio_Mas_Barato_Scryfall(nombre):
    clave = nombre.strip().casefold()
    if clave in _cache_mas_baratas:
        return _cache_mas_baratas[clave]
    nombre_consulta = nombre.replace("\\", "\\\\").replace('"', '\\"')
    url = "https://api.scryfall.com/cards/search"
    params = {
        "q": f'!"{nombre_consulta}" game:paper',
        "unique": "prints",
        "order": "usd",
        "dir": "asc",
    }
    cartas_con_precio = []
    siguiente_url = url
    siguientes_params = params
    while siguiente_url:
        _esperar_busqueda_scryfall()
        respuesta = requests.get(
            siguiente_url,
            params=siguientes_params,
            headers=CABECERAS_SCRYFALL,
            timeout=30)

        if respuesta.status_code == 404:
            _cache_mas_baratas[clave] = None
            return None
        
        respuesta.raise_for_status()
        datos = respuesta.json()

        for carta in datos.get("data", []):
            precio = _precio_usd(carta)
            if precio is not None:
                cartas_con_precio.append((precio, carta))

        if datos.get("has_more"):
            siguiente_url = datos.get("next_page")
            siguientes_params = None
        else:
            siguiente_url = None

    if not cartas_con_precio:
        _cache_mas_baratas[clave] = None
        return None

    precio, carta_barata = min(cartas_con_precio, key=lambda elemento: elemento[0])
    resultado = {
        "nombre": carta_barata.get("name", nombre),
        "precio_usd": precio,
        "set": carta_barata.get("set", ""),
        "set_name": carta_barata.get("set_name", ""),
        "collector_number": carta_barata.get("collector_number", ""),
        "scryfall_uri": carta_barata.get("scryfall_uri", "")}
    _cache_mas_baratas[clave] = resultado
    return resultado


def Comparar_Precios(carta_moxfield):
    impresion = {
        "nombre": carta_moxfield.get("nombre", ""),
        "precio_ck": carta_moxfield.get("precio_ck"),
        "set": carta_moxfield.get("set", ""),
        "set_name": carta_moxfield.get("set_name", ""),
        "collector_number": carta_moxfield.get("collector_number", ""),
        "cardkingdom_url": carta_moxfield.get("cardkingdom_url", "")}

    mas_barata = Precio_Mas_Barato_Scryfall(carta_moxfield["nombre"])
    precio_ck = impresion["precio_ck"]
    precio_barato = (
        mas_barata["precio_usd"]
        if mas_barata
        else None)

    diferencia = None

    if precio_ck is not None and precio_barato is not None:
        diferencia = round(precio_ck - precio_barato,2)

    return {
        "impresion_moxfield": impresion,
        "impresion_mas_barata": mas_barata,
        "diferencia_usd": diferencia}
