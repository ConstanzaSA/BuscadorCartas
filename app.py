from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from Funciones_Cartas import Comparar_cartas, Leer_Mazo_Moxfield, Leer_URLs


BASE_DIR = Path(__file__).resolve().parent
ARCHIVO_URLS = BASE_DIR / "Datos" / "URLs_Moxfield.txt"
LOGO_PATH = BASE_DIR / "assets" / "logo_magic.png"
FACEBOOK_URL = (
    "https://www.facebook.com/profile.php"
    "?id=100049903494774&locale=es_LA"
)

# Paleta visual: cambia estos valores para probar otros tonos.
COLOR_MORADO_OSCURO = "#302B4F"
COLOR_MORADO_MEDIO = "#6E5A87"
COLOR_LILA = "#AA8DAF"
COLOR_GRIS_VIOLETA = "#9292AA"

COLOR_FONDO = "#0D0C11"
COLOR_PANEL = "#191620"
COLOR_PANEL_SECUNDARIO = "#211D2A"
COLOR_TEXTO = "#F7F4FA"
COLOR_TEXTO_SECUNDARIO = "#C5BECC"
COLOR_BLANCO = "#FFFFFF"

VALOR_CK_CLP = 700

NOMBRES_CARPETAS = {
    "mainboard": "Mazo principal",
    "commanders": "Comandante",
    "sideboard": "Sideboard",
    "considering": "Considerando",
    "companions": "Compañero",
    "attractions": "Atracciones",
    "stickers": "Stickers",
}

st.set_page_config(
    page_title="Buscador de Cartas",
    page_icon="🃏",
    layout="wide",
)


def imagen_a_base64(ruta: Path) -> str:
    if not ruta.exists():
        return ""
    return base64.b64encode(ruta.read_bytes()).decode("utf-8")


def normalizar_nombre(nombre: str) -> str:
    return " ".join(str(nombre).strip().casefold().split())


def parsear_cartas(texto: str) -> list[str]:
    cartas: list[str] = []
    vistas: set[str] = set()

    for linea in str(texto).splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue

        coincidencia = re.match(r"^\s*\d+\s+(.+?)\s*$", linea)
        nombre = coincidencia.group(1).strip() if coincidencia else linea
        clave = normalizar_nombre(nombre)

        if clave and clave not in vistas:
            cartas.append(nombre)
            vistas.add(clave)

    return cartas


def nombre_carpeta(clave: str) -> str:
    return NOMBRES_CARPETAS.get(
        str(clave).casefold(),
        str(clave).replace("_", " ").title(),
    )


def precio_usd_texto(valor: Any) -> str:
    if valor is None or pd.isna(valor):
        return "Sin precio"
    return f"US${float(valor):,.2f}"


def precio_clp_texto(valor: Any) -> str:
    if valor is None or pd.isna(valor):
        return "Sin precio"
    return f"${float(valor):,.0f}".replace(",", ".")


@st.cache_data(ttl=300, show_spinner=False)
def cargar_mazo(url: str) -> dict[str, Any]:
    return Leer_Mazo_Moxfield(url)


def buscar_cartas(
    cartas_buscadas: list[str],
    urls: list[str],
    tipo_cambio: float,
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, str]]]:
    resultados: list[dict[str, Any]] = []
    errores: list[dict[str, str]] = []
    nombres_encontrados: set[str] = set()
    progreso = st.progress(0, text="Preparando búsqueda...")

    for indice, url in enumerate(urls, start=1):
        try:
            progreso.progress(
                (indice - 1) / max(len(urls), 1),
                text=f"Revisando mazo {indice} de {len(urls)}...",
            )
            mazo = cargar_mazo(url)
            coincidencias = Comparar_cartas(mazo, cartas_buscadas)

            for carta in coincidencias:
                cantidad = int(carta.get("cantidad") or 1)
                precio_ck = carta.get("precio_ck")
                precio_clp = (
                    round(float(precio_ck) * tipo_cambio)
                    if precio_ck is not None
                    else None
                )

                resultados.append(
                    {
                        "Imagen": carta.get("imagen_url", ""),
                        "Carta": carta.get("nombre", ""),
                        "Mazo": mazo.get("nombre", ""),
                        "Carpeta": nombre_carpeta(carta.get("tablero", "")),
                        "Cantidad": cantidad,
                        "Edición": carta.get("set_name", ""),
                        "Acabado": carta.get("finish", "nonfoil"),
                        "Precio CK": precio_ck,
                        "Precio CLP": precio_clp,
                        "Total CK": (
                            round(float(precio_ck) * cantidad, 2)
                            if precio_ck is not None
                            else None
                        ),
                        "Total CLP": (
                            round(precio_clp * cantidad)
                            if precio_clp is not None
                            else None
                        ),
                        "Card Kingdom": carta.get("cardkingdom_url", ""),
                        "Moxfield": mazo.get("url", ""),
                    }
                )
                nombres_encontrados.add(
                    normalizar_nombre(carta.get("nombre", ""))
                )

        except Exception as error:
            errores.append(
                {
                    "url": url,
                    "error": f"{type(error).__name__}: {error}",
                }
            )

    progreso.progress(1.0, text="Búsqueda terminada.")
    progreso.empty()

    mapa_buscadas = {
        normalizar_nombre(nombre): nombre
        for nombre in cartas_buscadas
    }
    no_encontradas = [
        nombre_original
        for nombre_normalizado, nombre_original in mapa_buscadas.items()
        if nombre_normalizado not in nombres_encontrados
    ]

    resultados.sort(
        key=lambda fila: (
            fila["Carta"].casefold(),
            fila["Mazo"].casefold(),
            fila["Carpeta"].casefold(),
        )
    )
    return resultados, no_encontradas, errores


def tarjeta_metrica(titulo: str, valor: str, subtitulo: str = "") -> None:
    html = (
        '<div class="metric-card">'
        f'<div class="metric-title">{titulo}</div>'
        f'<div class="metric-value">{valor}</div>'
        f'<div class="metric-subtitle">{subtitulo}</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


st.markdown(
    f"""
    <style>
        :root {{
            --morado-oscuro: {COLOR_MORADO_OSCURO};
            --morado-medio: {COLOR_MORADO_MEDIO};
            --lila: {COLOR_LILA};
            --gris-violeta: {COLOR_GRIS_VIOLETA};
            --fondo: {COLOR_FONDO};
            --texto: {COLOR_TEXTO};
            --blanco: {COLOR_BLANCO};
        }}
        .stApp {{ background: var(--fondo); color: var(--texto); }}
        .block-container {{ max-width: 1360px; padding-top: 1.2rem; padding-bottom: 3rem; }}
        [data-testid="stHeader"] {{ background: transparent; }}
        .hero {{
            display: flex; align-items: center; justify-content: space-between;
            gap: 2rem; min-height: 180px; padding: 1.7rem 2.2rem;
            margin-bottom: 1.4rem; border-radius: 0 0 24px 24px;
            background: linear-gradient(115deg, var(--morado-oscuro) 0%, #44365F 65%, var(--morado-medio) 100%);
            box-shadow: 0 10px 28px rgba(48,43,79,.20); overflow: hidden;
        }}
        .hero h1 {{ color: white; font-size: clamp(2rem,4vw,3.4rem); line-height: 1; margin: 0 0 .7rem 0; font-weight: 800; letter-spacing: -.04em; }}
        .hero p {{ color: #EEEAF3; max-width: 760px; margin: 0; font-size: 1.02rem; }}
        .hero-logo {{ width: min(170px,24vw); max-height: 145px; object-fit: contain; border-radius: 18px; background: rgba(255,255,255,.94); padding: .55rem; box-shadow: 0 8px 22px rgba(0,0,0,.20); }}
        .panel-title {{ margin: 0 0 .25rem 0; color: var(--morado-oscuro); font-size: 1.15rem; font-weight: 800; }}
        .panel-caption {{ margin-bottom: .8rem; color: #686271; font-size: .92rem; }}
        .metric-card {{ min-height: 104px; margin-bottom: .75rem; padding: 1rem 1.1rem; border: 1px solid rgba(110,90,135,.18); border-left: 7px solid var(--lila); border-radius: 16px; background: white; box-shadow: 0 6px 18px rgba(48,43,79,.07); }}
        .metric-title {{ color: #6D6875; font-size: .85rem; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; }}
        .metric-value {{ margin-top: .18rem; color: var(--morado-oscuro); font-size: 1.75rem; line-height: 1.15; font-weight: 850; }}
        .metric-subtitle {{ min-height: 1.15rem; margin-top: .22rem; color: #817B86; font-size: .78rem; }}
        .section-title {{ margin: 2rem 0 .65rem 0; color: var(--morado-oscuro); font-size: 1.35rem; font-weight: 850; }}
        .facebook-strip {{ display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin: .3rem 0 1.2rem 0; padding: .85rem 1rem; border-radius: 14px; background: #EDE8F0; color: var(--morado-oscuro); }}
        .facebook-strip a {{ color: var(--morado-oscuro); font-weight: 800; text-decoration: none; }}
        div[data-testid="stTextArea"] textarea {{ min-height: 250px; border: 1.5px solid var(--gris-violeta); border-radius: 14px; background: #FBFAFC; }}
        div[data-testid="stTextArea"] textarea:focus {{ border-color: var(--morado-medio); box-shadow: 0 0 0 2px rgba(110,90,135,.16); }}
        .stButton > button, .stDownloadButton > button, .stLinkButton > a {{ min-height: 44px; border: none; border-radius: 999px; background: var(--morado-oscuro); color: white; font-weight: 800; }}
        .stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {{ background: var(--morado-medio); color: white; border: none; }}
        button[data-baseweb="tab"] {{ color: var(--morado-oscuro); font-weight: 800; }}
        button[data-baseweb="tab"][aria-selected="true"] {{ color: var(--morado-oscuro); border-bottom-color: var(--morado-oscuro); }}
        [data-testid="stDataFrame"] {{ border: 1px solid rgba(110,90,135,.20); border-radius: 14px; overflow: hidden; }}
        @media (max-width: 760px) {{ .hero {{ min-height: auto; padding: 1.4rem; }} .hero-logo {{ width: 105px; }} }}
    </style>
    """,
    unsafe_allow_html=True,
)

logo_base64 = imagen_a_base64(LOGO_PATH)
imagen_html = (
    f'<img class="hero-logo" src="data:image/png;base64,{logo_base64}" alt="Símbolos de Magic">'
    if logo_base64
    else ""
)

st.markdown(
    f"""
    <section class="hero">
        <div>
            <h1>Buscador de Cartas</h1>
            <p>Optimiza tu búsqueda de cartas para el stock actual de la tienda El Wombat Rabioso TCG.</p>
        </div>
        {imagen_html}
    </section>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="facebook-strip">
        <span>Revisa novedades y stock de <strong>El Wombat Rabioso TCG</strong>.</span>
        <a href="{FACEBOOK_URL}" target="_blank">Abrir página de Facebook ↗</a>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    urls_configuradas = Leer_URLs(ARCHIVO_URLS)
except FileNotFoundError:
    urls_configuradas = []

if not urls_configuradas:
    st.error(
        "No hay mazos configurados. Agrega una URL pública de Moxfield "
        "por línea en `Datos/URLs_Moxfield.txt`."
    )
    st.stop()

tipo_cambio = VALOR_CK_CLP
columna_buscador, columna_resumen = st.columns([1.45, 1], gap="large")

with columna_buscador:
    st.markdown(
        '<div class="panel-title">Cartas que estás buscando</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="panel-caption">Pega una carta por línea usando el formato <strong>cantidad + nombre</strong>.</div>',
        unsafe_allow_html=True,
    )

    with st.form("formulario_busqueda"):
        texto_cartas = st.text_area(
            "Lista de cartas",
            placeholder=(
                "1 Tifa, Martial Artist\n"
                "1 Adaptive Automaton\n"
                "1 Akroma's Will\n"
                "1 Sol Ring"
            ),
            label_visibility="collapsed",
        )
        enviar = st.form_submit_button(
            "Buscar cartas",
            type="primary",
            use_container_width=True,
        )

if enviar:
    cartas_buscadas = parsear_cartas(texto_cartas)
    if not cartas_buscadas:
        st.warning("Pega al menos una carta para comenzar.")
    else:
        with st.spinner("Consultando el stock de los mazos..."):
            resultados, no_encontradas, errores = buscar_cartas(
                cartas_buscadas,
                urls_configuradas,
                tipo_cambio,
            )
        st.session_state["resultados"] = resultados
        st.session_state["no_encontradas"] = no_encontradas
        st.session_state["errores"] = errores
        st.session_state["total_buscadas"] = len(cartas_buscadas)

resultados_actuales = st.session_state.get("resultados", [])
total_buscadas = st.session_state.get("total_buscadas", 0)

if resultados_actuales:
    df_actual = pd.DataFrame(resultados_actuales)
    cartas_unicas = int(df_actual["Carta"].nunique())
    unidades = int(df_actual["Cantidad"].sum())
    total_usd = float(df_actual["Total CK"].fillna(0).sum())
    total_clp = float(df_actual["Total CLP"].fillna(0).sum())
else:
    cartas_unicas = 0
    unidades = 0
    total_usd = 0.0
    total_clp = 0.0

with columna_resumen:
    tarjeta_metrica(
        "Cartas encontradas",
        f"{cartas_unicas}/{total_buscadas}" if total_buscadas else "—",
        f"{unidades} unidades disponibles" if resultados_actuales else "",
    )

    if resultados_actuales:
        csv_resultados = pd.DataFrame(resultados_actuales).to_csv(
            index=False,
            sep=";",
            decimal=",",
        ).encode("utf-8-sig")
        st.download_button(
            "Descargar CSV",
            data=csv_resultados,
            file_name="Resultados_Buscador_Cartas.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.button(
            "Descargar CSV",
            disabled=True,
            use_container_width=True,
        )

    tarjeta_metrica(
        "Valor CK tienda",
        f"1 CK = ${VALOR_CK_CLP} CLP"
    )

    tarjeta_metrica(
        "Valor total CLP",
        precio_clp_texto(total_clp) if resultados_actuales else "—",
    )

if "resultados" in st.session_state:
    resultados = st.session_state["resultados"]
    no_encontradas = st.session_state["no_encontradas"]
    errores = st.session_state["errores"]

    st.markdown(
        '<div class="section-title">Resultados de la búsqueda</div>',
        unsafe_allow_html=True,
    )

    if resultados:
        df = pd.DataFrame(resultados)
        pestaña_tabla, pestaña_cartas = st.tabs(
            ["Tabla completa", "Vista de cartas"]
        )

        with pestaña_tabla:
            columnas_tabla = [
                "Imagen",
                "Carta",
                "Mazo",
                "Cantidad",
                "Edición",
                "Acabado",
                "Precio CK",
                "Precio CLP",
            ]
            st.dataframe(
                df[columnas_tabla],
                hide_index=True,
                use_container_width=True,
                row_height=72,
                column_config={
                    "Imagen": st.column_config.ImageColumn(
                        "Imagen",
                        width="small",
                    ),
                    "Cantidad": st.column_config.NumberColumn(
                        "Cantidad",
                        format="%d",
                    ),
                    "Precio CK": st.column_config.NumberColumn(
                        "Precio CK",
                        format="US$ %.2f",
                    ),
                    "Precio CLP": st.column_config.NumberColumn(
                        "Precio CLP",
                        format="$ %d",
                    ),
                },
            )
            st.caption(
                "La carpeta específica se muestra en la Vista de cartas "
                "para mantener esta tabla condensada."
            )

        with pestaña_cartas:
            for inicio in range(0, len(resultados), 3):
                columnas = st.columns(3)
                for columna, fila in zip(
                    columnas,
                    resultados[inicio:inicio + 3],
                ):
                    with columna:
                        with st.container(border=True):
                            if fila["Imagen"]:
                                st.image(
                                    fila["Imagen"],
                                    use_container_width=True,
                                )
                            else:
                                st.info("Imagen no disponible")

                            st.markdown(f"### {fila['Carta']}")
                            st.caption(
                                f"{fila['Mazo']} · {fila['Carpeta']}"
                            )
                            st.write(f"**Cantidad:** {fila['Cantidad']}")
                            st.write(f"**Edición:** {fila['Edición']}")
                            st.write(f"**Acabado:** {fila['Acabado']}")
                            st.write(
                                "**Precio CK:** "
                                f"{precio_usd_texto(fila['Precio CK'])}"
                            )
                            st.write(
                                "**Precio aproximado CLP:** "
                                f"{precio_clp_texto(fila['Precio CLP'])}"
                            )

                            if fila.get("Card Kingdom"):
                                st.link_button(
                                    "Abrir en Card Kingdom",
                                    fila["Card Kingdom"],
                                    use_container_width=True,
                                )
                            st.link_button(
                                "Abrir mazo en Moxfield",
                                fila["Moxfield"],
                                use_container_width=True,
                            )
    else:
        st.info(
            "No se encontraron coincidencias en los mazos configurados."
        )

    st.markdown(
        '<div class="section-title">Cartas no encontradas</div>',
        unsafe_allow_html=True,
    )
    if no_encontradas:
        st.markdown(
            "\n".join(f"- {nombre}" for nombre in no_encontradas)
        )
    else:
        st.success("Todas las cartas solicitadas fueron encontradas.")

    if errores:
        with st.expander(
            f"Mazos que no pudieron consultarse ({len(errores)})"
        ):
            for error in errores:
                st.error(f"{error['url']}\n\n{error['error']}")
