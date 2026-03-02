"""
Generador de URLs para citas legislativas
Usa fuentes oficiales navegables directamente en el browser
"""

PARTIDO_IDS = {
    "MC": 7, "Morena": 3,
    "PAN": 2, "PRD": 4, "PRI": 1, "PT": 6, "PVEM": 5
}

URLS = {
    "votaciones_portal": "https://www.diputados.gob.mx/Votaciones.htm",
    "gaceta_base": "https://gaceta.diputados.gob.mx",
    "ine_elecciones": "https://www.ine.mx/voto-y-elecciones/elecciones-2024/",
    "camara_inicio": "https://www.diputados.gob.mx",
    "datos_abiertos": "https://datos.gob.mx/busca/dataset/camara-de-diputados",
    "transparencia": "https://www.diputados.gob.mx/LeyesBiblio/index.htm",
    "sitl_inicio": "https://sitl.diputados.gob.mx/LXV_leg/listados_votacionesnplxv.php",
}

# Nota: sitl.diputados.gob.mx usa sesiones PHP — las URLs con parámetros
# no cargan datos directamente en el browser. Se usan solo para scraping.
# Las fuentes navegables se construyen con las URLs del diccionario URLS.


def _fuentes_votaciones(partido: str) -> list[dict]:
    """3 fuentes distintas y navegables para cualquier consulta de votaciones."""
    return [
        {
            "url": URLS["votaciones_portal"],
            "label": f"Portal de Votaciones — {partido} · Cámara de Diputados LXV"
        },
        {
            "url": URLS["datos_abiertos"],
            "label": "datos.gob.mx — Dataset abierto Cámara de Diputados"
        },
        {
            "url": URLS["camara_inicio"],
            "label": "Cámara de Diputados — Portal oficial"
        },
    ]


def url_votacion_partido(partido: str, votacion_id: int) -> dict:
    return {
        "url": URLS["votaciones_portal"],
        "label": f"Votación #{votacion_id} — {partido} · Portal de Votaciones Cámara de Diputados"
    }


def url_todas_votaciones_partido(partido: str) -> dict:
    return {
        "url": URLS["votaciones_portal"],
        "label": f"Historial completo de votaciones — {partido} · Cámara de Diputados"
    }


def url_votacion_general(votacion_id: int) -> dict:
    return {
        "url": URLS["votaciones_portal"],
        "label": f"Votación #{votacion_id} — Registro oficial · Cámara de Diputados LXV"
    }


def url_disciplina_partido(partido: str) -> list[dict]:
    return [
        {
            "url": URLS["votaciones_portal"],
            "label": f"Votaciones nominales — {partido} · Cámara de Diputados"
        },
        {
            "url": URLS["datos_abiertos"],
            "label": "datos.gob.mx — Dataset abierto Cámara de Diputados"
        },
        {
            "url": URLS["camara_inicio"],
            "label": "Cámara de Diputados — Portal oficial"
        },
    ]


def url_radar_electoral(partido: str) -> list[dict]:
    return [
        {
            "url": URLS["votaciones_portal"],
            "label": f"Votaciones nominales — {partido} · Cámara de Diputados"
        },
        {
            "url": URLS["ine_elecciones"],
            "label": "INE — Elecciones Federales 2024"
        },
        {
            "url": URLS["datos_abiertos"],
            "label": "datos.gob.mx — Dataset abierto Cámara de Diputados"
        },
    ]


def url_buscar_diputado(partido: str, votaciones_ids: list) -> list[dict]:
    return [
        {
            "url": URLS["votaciones_portal"],
            "label": f"Votaciones nominales — {partido} · Cámara de Diputados"
        },
        {
            "url": URLS["datos_abiertos"],
            "label": "datos.gob.mx — Dataset abierto Cámara de Diputados"
        },
        {
            "url": URLS["camara_inicio"],
            "label": "Cámara de Diputados — Portal oficial"
        },
    ]


def url_patrones_generales() -> list[dict]:
    return [
        {
            "url": URLS["votaciones_portal"],
            "label": "Portal de votaciones nominales · Cámara de Diputados LXV"
        },
        {
            "url": URLS["datos_abiertos"],
            "label": "datos.gob.mx — Datos abiertos Cámara de Diputados"
        },
        {
            "url": URLS["camara_inicio"],
            "label": "Cámara de Diputados — Portal oficial"
        },
    ]


def url_comparativa_partidos() -> list[dict]:
    return [
        {
            "url": URLS["votaciones_portal"],
            "label": "Portal de Votaciones — Todos los partidos · Cámara de Diputados LXV"
        },
        {
            "url": URLS["datos_abiertos"],
            "label": "datos.gob.mx — Dataset abierto Cámara de Diputados"
        },
        {
            "url": URLS["camara_inicio"],
            "label": "Cámara de Diputados — Portal oficial"
        },
    ]


def url_contradicciones(partido: str) -> list[dict]:
    return [
        {
            "url": URLS["votaciones_portal"],
            "label": f"Votaciones nominales — {partido} · Cámara de Diputados"
        },
        {
            "url": URLS["gaceta_base"],
            "label": "Gaceta Parlamentaria — Iniciativas oficiales"
        },
        {
            "url": URLS["datos_abiertos"],
            "label": "datos.gob.mx — Datos abiertos legislativos"
        },
    ]
