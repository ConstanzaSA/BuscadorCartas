from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from Funciones_Cartas import Comparar_cartas, Leer_Mazo_Moxfield, Leer_URLs


# ============================================================
# CONFIGURACIÓN
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
ARCHIVO_URLS = BASE_DIR / "Datos" / "URLs_Moxfield.txt"
LOGO_PATH = BASE_DIR / "assets" / "logo_magic.png"

FACEBOOK_URL = (
    "https://www.facebook.com/profile.php"
    "?id=100049903494774&locale=es_LA"
)

COLOR_MORADO_OSCURO = "#302B4F"
COLOR_MORADO_MEDIO = "#6E5A87"
COLOR_LILA = "#AA8DAF"
COLOR_GRIS_VIOLETA = "#9292AA"

COLOR_FONDO = "#0D0C11"
COLOR_PANEL = "#191620"
COLOR_TEXTO = "#F7F4FA"
COLOR_TEXTO_SECUNDARIO = "#C5BECC"
COLOR_BLANCO = "#FFFFFF"

# Conversión fija usada por la tienda.
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
    layout="wide",
)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def imagen_a_base64(ruta: Path) -> str:
    if not ruta.exists():
        return ""
    return base64.b64encode(ruta.read_bytes()).decode("utf-8")


def normalizar_nombre(nombre: str) -> str:
    return " ".join(str(nombre).strip().casefold().split())


def parsear_cartas(texto: str) -> list[dict[str, Any]]:
    """
    Acepta líneas como:
        3 Sol Ring
        1 Akroma's Will

    La cantidad escrita por el usuario se conserva como ``Cantidad_buscada``.
    Si una misma carta aparece más de una vez, sus cantidades se suman.
    Cuando no se escribe una cantidad, se asume 1.
    """
    cartas_por_nombre: dict[str, dict[str, Any]] = {}

    for linea in str(texto).splitlines():
        linea = linea.strip()

        if not linea or linea.startswith("#"):
            continue

        coincidencia = re.match(r"^\s*(\d+)\s+(.+?)\s*$", linea)

        if coincidencia:
            cantidad_buscada = int(coincidencia.group(1))
            nombre = coincidencia.group(2).strip()
        else:
            cantidad_buscada = 1
            nombre = linea

        if cantidad_buscada <= 0:
            continue

        clave = normalizar_nombre(nombre)
        if not clave:
            continue

        if clave in cartas_por_nombre:
            cartas_por_nombre[clave]["Cantidad_buscada"] += cantidad_buscada
        else:
            cartas_por_nombre[clave] = {
                "nombre": nombre,
                "Cantidad_buscada": cantidad_buscada,
            }

    return list(cartas_por_nombre.values())


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
    cartas_buscadas: list[dict[str, Any]],
    urls: list[str],
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, str]]]:
    resultados: list[dict[str, Any]] = []
    errores: list[dict[str, str]] = []
    nombres_encontrados: set[str] = set()

    nombres_solicitados = [
        carta["nombre"]
        for carta in cartas_buscadas
    ]
    cantidades_solicitadas = {
        normalizar_nombre(carta["nombre"]): int(carta["Cantidad_buscada"])
        for carta in cartas_buscadas
    }

    progreso = st.progress(0, text="Preparando búsqueda...")

    for indice, url in enumerate(urls, start=1):
        try:
            progreso.progress(
                (indice - 1) / max(len(urls), 1),
                text=f"Revisando mazo {indice} de {len(urls)}...",
            )

            mazo = cargar_mazo(url)
            coincidencias = Comparar_cartas(mazo, nombres_solicitados)

            for carta in coincidencias:
                nombre_encontrado = carta.get("nombre", "")
                clave_buscada = normalizar_nombre(
                    carta.get("nombre_buscado") or nombre_encontrado
                )
                cantidad_buscada = cantidades_solicitadas.get(
                    clave_buscada,
                    1,
                )
                cantidad_disponible = int(carta.get("cantidad") or 0)
                precio_ck = carta.get("precio_ck")

                precio_clp = (
                    round(float(precio_ck) * VALOR_CK_CLP)
                    if precio_ck is not None
                    else None
                )

                resultados.append(
                    {
                        "Imagen": carta.get("imagen_url", ""),
                        "Carta": nombre_encontrado,
                        "Mazo": mazo.get("nombre", ""),
                        "Carpeta": nombre_carpeta(
                            carta.get("tablero", "")
                        ),
                        "Cantidad_buscada": cantidad_buscada,
                        "Cantidad disponible": cantidad_disponible,
                        "Edición": carta.get("set_name", ""),
                        "Acabado": carta.get("finish", "nonfoil"),
                        "Precio CK": precio_ck,
                        "Precio CLP": precio_clp,
                        "Total CLP buscada": (
                            round(precio_clp * cantidad_buscada)
                            if precio_clp is not None
                            else None
                        ),
                        "Card Kingdom": carta.get(
                            "cardkingdom_url",
                            "",
                        ),
                        "Link Moxfield": mazo.get("url", ""),
                    }
                )

                nombres_encontrados.add(clave_buscada)

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
        normalizar_nombre(carta["nombre"]): carta["nombre"]
        for carta in cartas_buscadas
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


def tarjeta_metrica(
    titulo: str,
    valor: str,
    subtitulo: str = "",
) -> None:
    html = (
        '<div class="metric-card">'
        f'<div class="metric-title">{titulo}</div>'
        f'<div class="metric-value">{valor}</div>'
        f'<div class="metric-subtitle">{subtitulo}</div>'
        "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


# ============================================================
# ESTILOS
# ============================================================

st.markdown(
    f"""
    <style>
        html,
        body,
        #root,
        [data-testid="stAppViewContainer"],
        [data-testid="stApp"] {{
            background-color: {COLOR_FONDO} !important;
        }}

        [data-testid="stHeader"] {{
            background-color: {COLOR_FONDO} !important;
            border: none !important;
            box-shadow: none !important;
        }}

        [data-testid="stDecoration"] {{
            display: none !important;
        }}

        .stApp {{
            background: {COLOR_FONDO};
            color: {COLOR_TEXTO};
        }}

        .block-container {{
            max-width: 1360px;
            padding-top: 1rem;
            padding-bottom: 3rem;
        }}

        p, span, label {{
            color: {COLOR_TEXTO};
        }}

        .buscador-hero {{
            position: relative;
            isolation: isolate;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 2rem;
            min-height: 160px;
            padding: 1.6rem 2rem;
            margin-bottom: 1.4rem;
            border: 1px solid rgba(170, 141, 175, 0.20);
            border-radius: 22px !important;
            background: linear-gradient(
                115deg,
                {COLOR_MORADO_OSCURO} 0%,
                #44365F 65%,
                {COLOR_MORADO_MEDIO} 100%
            );
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.30);
            overflow: hidden !important;
            clip-path: inset(0 round 22px);
        }}

        .buscador-hero-text {{
            flex: 1;
            min-width: 0;
        }}

        .buscador-hero h1 {{
            margin: 0 0 0.8rem 0;
            color: {COLOR_BLANCO};
            font-size: clamp(2rem, 4vw, 3.2rem);
            line-height: 1.05;
            font-weight: 850;
        }}

        .buscador-hero p {{
            margin: 0;
            color: #EEEAF3;
            font-size: 1rem;
        }}

        .hero-logo {{
            width: 125px !important;
            height: 125px !important;
            min-width: 125px !important;
            max-width: 125px !important;
            max-height: 125px !important;
            flex: 0 0 125px;
            object-fit: contain;
            margin-left: auto;
            padding: 7px;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.08);
            box-shadow: 0 7px 20px rgba(0, 0, 0, 0.25);
        }}

        .panel-title {{
            margin: 0 0 0.25rem 0;
            color: {COLOR_BLANCO};
            font-size: 1.15rem;
            font-weight: 800;
        }}

        .panel-caption {{
            margin-bottom: 0.8rem;
            color: {COLOR_TEXTO_SECUNDARIO};
            font-size: 0.92rem;
        }}

        .metric-card {{
            min-height: 104px;
            margin-bottom: 0.75rem;
            padding: 1rem 1.1rem;
            border: 1px solid rgba(170, 141, 175, 0.24);
            border-left: 7px solid {COLOR_LILA};
            border-radius: 16px;
            background: {COLOR_PANEL};
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.28);
        }}

        .metric-title {{
            color: {COLOR_TEXTO_SECUNDARIO};
            font-size: 0.85rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }}

        .metric-value {{
            margin-top: 0.18rem;
            color: {COLOR_BLANCO};
            font-size: 1.75rem;
            line-height: 1.15;
            font-weight: 850;
        }}

        .metric-subtitle {{
            min-height: 1.15rem;
            margin-top: 0.22rem;
            color: {COLOR_TEXTO_SECUNDARIO};
            font-size: 0.78rem;
        }}

        .section-title {{
            margin-top: 1.8rem;
            color: {COLOR_BLANCO};
            font-size: 1.35rem;
            font-weight: 850;
        }}

        .facebook-strip {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin: 0.3rem 0 1.2rem 0;
            padding: 0.85rem 1rem;
            border: 1px solid rgba(170, 141, 175, 0.20);
            border-radius: 14px;
            background: {COLOR_PANEL};
            color: {COLOR_TEXTO};
        }}

        .facebook-strip a {{
            color: #D4A7FF;
            font-weight: 800;
            text-decoration: none;
        }}

        div[data-testid="stTextArea"] textarea {{
            min-height: 250px;
            border: 1.5px solid {COLOR_GRIS_VIOLETA};
            border-radius: 14px;
            background: {COLOR_PANEL};
            color: {COLOR_BLANCO};
        }}

        div[data-testid="stTextArea"] textarea::placeholder {{
            color: #AFA8BA;
            opacity: 1;
        }}

        div[data-testid="stTextArea"] textarea:focus {{
            border-color: #A95AFF;
            box-shadow: 0 0 0 2px rgba(169, 90, 255, 0.20);
        }}

        .empty-warning {{
            margin-top: 1rem;
            padding: 0.9rem 1rem;
            border: 1px solid #8F62B0;
            border-radius: 12px;
            background: #2B2135;
            color: #F7F4FA;
            font-weight: 650;
        }}

        .stButton > button,
        .stDownloadButton > button,
        .stLinkButton > a {{
            min-height: 44px;
            border: 1px solid rgba(170, 141, 175, 0.35);
            border-radius: 12px;
            background: #842BD1;
            color: {COLOR_BLANCO};
            font-weight: 800;
        }}

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        .stLinkButton > a:hover {{
            border-color: #B66CFF;
            background: #9B3BE5;
            color: {COLOR_BLANCO};
        }}

        [data-testid="stDataFrame"] {{
            border: 1px solid rgba(170, 141, 175, 0.25);
            border-radius: 14px;
            overflow: hidden;
        }}

        @media (max-width: 700px) {{
            .buscador-hero {{
                min-height: 130px;
                padding: 1.2rem;
                gap: 1rem;
                border-radius: 18px !important;
                clip-path: inset(0 round 18px);
            }}

            .buscador-hero h1 {{
                font-size: 2rem;
            }}

            .hero-logo {{
                width: 85px !important;
                height: 85px !important;
                min-width: 85px !important;
                max-width: 85px !important;
                max-height: 85px !important;
                flex-basis: 85px;
            }}

            .facebook-strip {{
                align-items: flex-start;
                flex-direction: column;
            }}
        }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# ENCABEZADO
# ============================================================

logo_base64 = imagen_a_base64(LOGO_PATH)

imagen_html = (
    f'<img class="hero-logo" '
    f'src="data:image/png;base64,{logo_base64}" '
    f'alt="Símbolos de Magic">'
    if logo_base64
    else ""
)

st.markdown(
    f"""
    <section class="buscador-hero">
        <div class="buscador-hero-text">
            <h1>Buscador de Cartas</h1>
            <p>
                Optimiza tu búsqueda de cartas para el stock actual
                de la tienda El Wombat Rabioso TCG.
            </p>
        </div>
        {imagen_html}
    </section>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="facebook-strip">
        <span>
            Revisa novedades y stock de
            <strong>El Wombat Rabioso TCG</strong>.
        </span>
        <a href="{FACEBOOK_URL}" target="_blank">
            Abrir página de Facebook ↗
        </a>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# CONFIGURACIÓN DE MAZOS
# ============================================================

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


# ============================================================
# BUSCADOR
# ============================================================

columna_buscador, columna_resumen = st.columns(
    [1.45, 1],
    gap="large",
)

with columna_buscador:
    st.markdown(
        '<div class="panel-title">Cartas que estás buscando</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        (
            '<div class="panel-caption">'
            "Pega una carta por línea usando el formato "
            "<strong>cantidad + nombre</strong>."
            "</div>"
        ),
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
            height=250,
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
            for clave in (
                "resultados",
                "no_encontradas",
                "errores",
                "total_buscadas",
                "total_unidades_buscadas",
            ):
                st.session_state.pop(clave, None)

            st.markdown(
                """
                <div class="empty-warning">
                    Pega al menos una carta para comenzar la búsqueda.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            with st.spinner("Consultando el stock de los mazos..."):
                resultados, no_encontradas, errores = buscar_cartas(
                    cartas_buscadas,
                    urls_configuradas,
                )

            st.session_state["resultados"] = resultados
            st.session_state["no_encontradas"] = no_encontradas
            st.session_state["errores"] = errores
            st.session_state["total_buscadas"] = len(cartas_buscadas)
            st.session_state["total_unidades_buscadas"] = sum(
                int(carta["Cantidad_buscada"])
                for carta in cartas_buscadas
            )


# ============================================================
# RESUMEN
# ============================================================

busqueda_realizada = "resultados" in st.session_state
resultados_actuales = st.session_state.get("resultados", [])
total_buscadas = st.session_state.get("total_buscadas", 0)
total_unidades_buscadas = st.session_state.get(
    "total_unidades_buscadas",
    0,
)

if resultados_actuales:
    df_actual = pd.DataFrame(resultados_actuales)
    cartas_unicas = int(df_actual["Carta"].nunique())
    total_clp = float(
        df_actual["Total CLP buscada"].fillna(0).sum()
    )
else:
    cartas_unicas = 0
    total_clp = 0.0

with columna_resumen:
    tarjeta_metrica(
        "Valor CK tienda",
        f"1 CK = ${VALOR_CK_CLP} CLP",
        "Conversión fija utilizada por la tienda",
    )

    tarjeta_metrica(
        "Valor total CLP",
        precio_clp_texto(total_clp) if busqueda_realizada else "—",
        "Precio CLP × cantidad solicitada",
    )

    tarjeta_metrica(
        "Cartas encontradas",
        (
            f"{cartas_unicas}/{total_buscadas}"
            if busqueda_realizada
            else "—"
        ),
        (
            f"{total_unidades_buscadas} unidades solicitadas"
            if busqueda_realizada
            else ""
        ),
    )

    if resultados_actuales:
        columnas_csv = [
            "Carta",
            "Mazo",
            "Cantidad_buscada",
            "Edición",
            "Acabado",
            "Precio CK",
            "Precio CLP",
            "Total CLP buscada",
            "Link Moxfield",
        ]

        csv_resultados = pd.DataFrame(
            resultados_actuales
        )[columnas_csv].to_csv(
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


# ============================================================
# RESULTADOS
# ============================================================

if busqueda_realizada:
    resultados = st.session_state["resultados"]
    no_encontradas = st.session_state.get("no_encontradas", [])
    errores = st.session_state.get("errores", [])

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
                "Cantidad_buscada",
                "Cantidad disponible",
                "Edición",
                "Acabado",
                "Precio CK",
                "Precio CLP",
                "Total CLP buscada",
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
                    "Cantidad_buscada": st.column_config.NumberColumn(
                        "Cantidad buscada",
                        format="%d",
                    ),
                    "Cantidad disponible": st.column_config.NumberColumn(
                        "Cantidad disponible",
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
                    "Total CLP buscada": st.column_config.NumberColumn(
                        "Total CLP buscada",
                        format="$ %d",
                    ),
                },
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
                            st.write(
                                "**Cantidad buscada:** "
                                f"{fila['Cantidad_buscada']}"
                            )
                            st.write(
                                "**Cantidad disponible:** "
                                f"{fila['Cantidad disponible']}"
                            )
                            st.write(
                                f"**Edición:** {fila['Edición']}"
                            )
                            st.write(
                                f"**Acabado:** {fila['Acabado']}"
                            )
                            st.write(
                                "**Precio CK:** "
                                f"{precio_usd_texto(fila['Precio CK'])}"
                            )
                            st.write(
                                "**Precio CLP:** "
                                f"{precio_clp_texto(fila['Precio CLP'])}"
                            )
                            st.write(
                                "**Total CLP buscada:** "
                                f"{precio_clp_texto(fila['Total CLP buscada'])}"
                            )

                            if fila.get("Card Kingdom"):
                                st.link_button(
                                    "Abrir en Card Kingdom",
                                    fila["Card Kingdom"],
                                    use_container_width=True,
                                )

                            st.link_button(
                                "Abrir mazo en Moxfield",
                                fila["Link Moxfield"],
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
            "\n".join(
                f"- {nombre}"
                for nombre in no_encontradas
            )
        )
    else:
        st.success("Todas las cartas solicitadas fueron encontradas.")

    if errores:
        with st.expander(
            f"Mazos que no pudieron consultarse ({len(errores)})"
        ):
            for error in errores:
                st.error(
                    f"{error['url']}\n\n{error['error']}"
                )
