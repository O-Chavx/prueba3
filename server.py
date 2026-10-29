"""Servidor MCP del BCRP. Empiecen aquí: buscar_series ya funciona; completen los TODO hasta que pasen las pruebas.

    uv run pytest                                           # el contrato: las 8 pruebas deben pasar
    uv run server.py                                        # el servidor, por stdio
    claude mcp add --scope project bcrp -- uv run server.py # conectarlo a Claude Code

Las cuentas las hace Python, no el modelo: así cada cifra sale de una llamada que se puede repetir.
"""
import re
import time
import unicodedata
from functools import cache
from pathlib import Path

import httpx
import pandas as pd
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

AQUI = Path(__file__).parent
CATALOGO = AQUI / "datos" / "catalogo_bcrp.csv"
URL_CATALOGO = "https://estadisticas.bcrp.gob.pe/estadisticas/series/metadata"
API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
SOLO_LECTURA = {"readOnlyHint": True, "openWorldHint": True}

mcp = FastMCP("bcrp", instructions=(
    "Series oficiales del Banco Central de Reserva del Perú (BCRP). Primero busca el código con buscar_series; "
    "luego usa resumen para variaciones, promedios y extremos, y serie para los datos. No calcules a mano: "
    "cita siempre el código de la serie y el periodo."))


def _sin_tildes(s):
    return unicodedata.normalize("NFD", str(s).lower()).encode("ascii", "ignore").decode()


@cache
def catalogo():
    """El catálogo oficial: 17 mil series en unos 7 MB. Se baja una vez y queda en datos/."""
    if not CATALOGO.exists():
        CATALOGO.parent.mkdir(exist_ok=True)
        r = httpx.get(URL_CATALOGO, timeout=120)
        r.raise_for_status()
        CATALOGO.write_text(r.content.decode("latin-1"), encoding="utf-8")
    df = pd.read_csv(CATALOGO, sep=";", dtype=str).fillna("")
    df = df.rename(columns={"Código de serie": "codigo", "Categoría de serie": "categoria", "Grupo de serie": "grupo",
                            "Nombre de serie": "nombre", "Frecuencia": "frecuencia",
                            "Fecha de actualización": "actualizada", "Fecha de inicio": "inicio"})
    df["texto"] = (df.categoria + " " + df.grupo + " " + df.nombre).map(_sin_tildes)
    return df


def _ficha(codigo):
    fila = catalogo().query("codigo == @codigo")
    if fila.empty:
        raise ToolError(f"No existe el código de serie {codigo!r}. Búsquenlo con buscar_series.")
    f = fila.iloc[0]
    return {"codigo": f.codigo, "nombre": f"{f.grupo} - {f.nombre}", "categoria": f.categoria,
            "frecuencia": f.frecuencia, "inicio": f.inicio, "actualizada": f.actualizada}


@mcp.tool(annotations=SOLO_LECTURA)
def buscar_series(texto: str, frecuencia: str | None = None, limite: int = 10) -> list[dict]:
    """Busca series del BCRP por palabras: todas deben aparecer en la categoría, el grupo o el nombre.

    Ejemplos: "ipc 12 meses", "tipo de cambio interbancario venta", "reservas internacionales netas",
    "tasa de referencia", "cobre precio". frecuencia: "Diaria", "Mensual", "Trimestral" o "Anual".
    Devuelve el código, el nombre completo, la frecuencia y desde cuándo hay datos. Si no hay resultados,
    prueben con menos palabras.
    """
    df = catalogo()
    m = pd.Series(True, index=df.index)
    for palabra in _sin_tildes(texto).split():
        m &= df.texto.str.contains(re.escape(palabra))
    if frecuencia:
        m &= df.frecuencia.str.lower() == frecuencia.lower()
    # primero las series vigentes y, entre ellas, las de nombre más corto (las más generales)
    sel = df[m]
    orden = sel.assign(vieja=sel.actualizada < "2025", largo=(sel.grupo + sel.nombre).str.len())
    return [_ficha(c) for c in orden.sort_values(["vieja", "largo"]).head(limite).codigo]


MESES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "set": 9, "sep": 9,
         "oct": 10, "nov": 11, "dic": 12}


def _tipo(frecuencia):
    """'Diaria', 'Mensual', 'Trimestral' o 'Anual' -> 'D', 'M', 'T' o 'A'."""
    f = _sin_tildes(frecuencia)
    for clave, tipo in (("diari", "D"), ("mensual", "M"), ("trimestr", "T"), ("anual", "A")):
        if f.startswith(clave):
            return tipo
    raise ToolError(f"No sé leer la frecuencia {frecuencia!r}.")


def _fecha_api(fecha, tipo):
    """Lo que escribe el usuario ("2025-01", "2025-1", "2025-01-15", "2025-T1", "2025") -> lo que pide la API."""
    partes = re.findall(r"\d+", str(fecha))
    if not partes or len(partes[0]) != 4:
        raise ToolError(f"Fecha {fecha!r} no válida. Usen 2025-01 (mensual), 2025-01-15 (diaria), 2025-T1 o 2025.")
    anio, resto = partes[0], [int(x) for x in partes[1:]]
    if tipo == "A":
        return anio
    if tipo == "D":
        mes, dia = (resto + [1, 1])[:2]
        return f"{anio}-{mes:02d}-{dia:02d}"
    if tipo == "T" and "t" not in str(fecha).lower() and resto:   # "2025-07" en una serie trimestral -> T3
        return f"{anio}-{(resto[0] - 1) // 3 + 1}"
    return f"{anio}-{resto[0] if resto else 1}"


def _periodo(nombre, tipo):
    """Lo que devuelve la API ("Ene.2025", "01.Oct.26", "T1.25", "2025") -> "2025-01", "2026-10-01", "2025-T1", "2025"."""
    p = nombre.split(".")
    anio = lambda a: int(a) + 2000 if len(a) == 2 else int(a)
    if tipo == "M":
        return f"{anio(p[1])}-{MESES[_sin_tildes(p[0])[:3]]:02d}"
    if tipo == "D":
        return f"{anio(p[2])}-{MESES[_sin_tildes(p[1])[:3]]:02d}-{int(p[0]):02d}"
    if tipo == "T":
        return f"{anio(p[1])}-T{p[0].upper().lstrip('T')}"
    return str(anio(p[0]))


_descargas = {}


def _pedir(url, intentos=4):
    """GET a la API con reintentos: si hay muchos pedidos seguidos, el BCRP responde HTML en vez de JSON."""
    if url in _descargas:
        return _descargas[url]
    for i in range(intentos):
        try:
            r = httpx.get(url, timeout=60, follow_redirects=True)
            if r.status_code == 200 and r.text.lstrip().startswith("{"):
                _descargas[url] = r.json()
                return _descargas[url]
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(2 * 2 ** i)
    raise ToolError("El BCRP no respondió con datos. Esperen unos segundos y reintenten, o acoten las fechas.")


@mcp.tool(annotations=SOLO_LECTURA)
def serie(codigo: str, desde: str, hasta: str) -> dict:
    """Datos de una serie del BCRP entre dos fechas, ambas incluidas.

    Úsenla cuando necesiten los valores periodo a periodo. Para variaciones, promedios o extremos usen resumen.
    Fechas: "2025-01" (mensual), "2026-10-15" (diaria), "2025-T1" (trimestral) o "2025" (anual).
    Ejemplo: serie("PN01273PM", "2026-01", "2026-09"). Si no saben el código, búsquenlo con buscar_series.
    Devuelve el código, el nombre, la frecuencia, los datos [{periodo, valor}] y la URL de la fuente.
    """
    ficha = _ficha(codigo.strip().upper())
    tipo = _tipo(ficha["frecuencia"])
    d, h = _fecha_api(desde, tipo), _fecha_api(hasta, tipo)
    js = _pedir(f"{API}/{ficha['codigo']}/json/{d}/{h}")
    datos = []
    for p in js.get("periods", []):
        v = p["values"][0] if p.get("values") else "n.d."
        try:
            datos.append({"periodo": _periodo(p["name"], tipo), "valor": float(v)})
        except (ValueError, KeyError, IndexError):   # "n.d." o un nombre raro: se salta
            continue
    if not datos:
        raise ToolError(f"La serie {ficha['codigo']} no tiene datos entre {desde} y {hasta}. Prueben otro periodo; "
                        f"hay datos desde {ficha['inicio']}.")
    return {"codigo": ficha["codigo"], "nombre": ficha["nombre"], "frecuencia": ficha["frecuencia"], "datos": datos,
            "fuente": f"{API}/{ficha['codigo']}/html/{d}/{h}"}


@mcp.tool(annotations=SOLO_LECTURA)
def resumen(codigo: str, desde: str, hasta: str) -> dict:
    """Resumen de una serie del BCRP entre dos fechas: primer y último dato, cambio, variación %, promedio,
    máximo y mínimo (con su periodo).

    Úsenla siempre que la pregunta pida una variación, un promedio, un máximo o un mínimo: así nadie hace cuentas
    a mano. También sirve para el valor de un solo periodo (desde = hasta). Mismo formato de fechas que serie.
    Ejemplo: resumen("PN01273PM", "2025-12", "2026-09").
    """
    s = serie(codigo, desde, hasta)
    df = pd.DataFrame(s["datos"])
    punto = lambda i: {"periodo": df.periodo[i], "valor": float(df.valor[i])}
    primero, ultimo = punto(0), punto(len(df) - 1)
    cambio = ultimo["valor"] - primero["valor"]
    return {"codigo": s["codigo"], "nombre": s["nombre"], "frecuencia": s["frecuencia"], "n": len(df),
            "primero": primero, "ultimo": ultimo, "cambio": round(cambio, 6),
            "variacion_pct": round(100 * cambio / primero["valor"], 4) if primero["valor"] else None,
            "promedio": round(float(df.valor.mean()), 6),
            "maximo": punto(df.valor.idxmax()), "minimo": punto(df.valor.idxmin()), "fuente": s["fuente"]}


@mcp.tool(annotations=SOLO_LECTURA)
def ultimo_dato(codigo: str) -> dict:
    """El dato más reciente publicado de una serie del BCRP, con su periodo y el dato del año anterior.

    Úsenla cuando pregunten por el valor «actual», «más reciente» o «último» de algo (la inflación de hoy, el tipo
    de cambio de ayer, las reservas de este mes) y no sepan qué periodo ya está publicado. Ejemplo:
    ultimo_dato("PD04638PD"). Devuelve ultimo {periodo, valor}, hace_un_anio {periodo, valor} cuando existe,
    la variación % entre ambos, los días desde la última actualización del catálogo y la URL de la fuente.
    """
    ficha = _ficha(codigo.strip().upper())
    tipo = _tipo(ficha["frecuencia"])
    hoy = pd.Timestamp.today()
    atras = {"D": pd.DateOffset(days=400), "M": pd.DateOffset(months=26), "T": pd.DateOffset(months=40),
             "A": pd.DateOffset(years=5)}[tipo]
    formato = {"D": "%Y-%m-%d", "M": "%Y-%m", "T": "%Y-%m", "A": "%Y"}[tipo]
    s = serie(ficha["codigo"], (hoy - atras).strftime(formato), hoy.strftime(formato))
    ultimo = s["datos"][-1]
    # el mismo periodo un año antes: "2026-09" -> "2025-09", "2026-10-15" -> el último día hábil <= "2025-10-15"
    antes = str(int(ultimo["periodo"][:4]) - 1) + ultimo["periodo"][4:]
    previos = [x for x in s["datos"] if x["periodo"] <= antes]
    hace_un_anio = previos[-1] if previos else None
    return {"codigo": s["codigo"], "nombre": s["nombre"], "frecuencia": s["frecuencia"], "ultimo": ultimo,
            "hace_un_anio": hace_un_anio,
            "variacion_anual_pct": (round(100 * (ultimo["valor"] / hace_un_anio["valor"] - 1), 4)
                                    if hace_un_anio and hace_un_anio["valor"] else None),
            "actualizada": ficha["actualizada"], "fuente": s["fuente"]}


@mcp.resource("bcrp://serie/{codigo}", mime_type="application/json")
def ficha_serie(codigo: str) -> dict:
    """Ficha de una serie del BCRP: nombre, categoría, frecuencia, desde cuándo hay datos y última actualización."""
    return _ficha(codigo.strip().upper())


@mcp.prompt
def informe(tema: str) -> str:
    """Informe breve con cifras oficiales del BCRP sobre un tema, cada cifra con su código y periodo."""
    return (f"Escribe un informe de 5 viñetas sobre «{tema}» en el Perú con datos oficiales del BCRP.\n"
            "1. Busca las series pertinentes con buscar_series (2 o 3 como máximo).\n"
            "2. Usa ultimo_dato para saber cuál es el dato más reciente y resumen para variaciones, promedios y "
            "extremos del último año. No hagas cuentas a mano.\n"
            "3. Cada viñeta lleva una cifra, el código de la serie y el periodo, por ejemplo: "
            "«4.55 % (PN01273PM, 2026-09)».\n"
            "4. Cierra con una línea que diga qué no se puede concluir con estos datos.")


if __name__ == "__main__":
    mcp.run()
