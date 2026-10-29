# ¿Inventa cifras Claude? Memoria contra un MCP del BCRP

## Qué construí

`server.py` es un servidor MCP (FastMCP 4, stdio) sobre las 17,167 series del BCRP:

| Pieza | Qué hace |
|---|---|
| `buscar_series` | Busca el código de una serie por palabras en el catálogo oficial |
| `serie` | Descarga los datos entre dos fechas, normaliza los periodos (`Set.2026` → `2026-09`) y devuelve la URL de la fuente |
| `resumen` | Primero, último, cambio, variación %, promedio, máximo y mínimo: el modelo no hace cuentas a mano |
| `ultimo_dato` (propia) | El dato más reciente publicado, el del año anterior y la variación anual, con su fuente. Sirve para preguntas de «cuánto es hoy» cuando el modelo no sabe qué periodo ya salió |
| `bcrp://serie/{codigo}` (recurso) | La ficha de la serie: nombre, frecuencia, inicio y última actualización |
| `informe(tema)` (prompt) | Cinco viñetas con una cifra cada una, citando código y periodo |

`.mcp.json` conecta `bcrp` y `fetch`, sin claves. Las 8 pruebas de `test_server.py` pasan sin cambiar el archivo.

## Resultados

Diez preguntas (las 8 del curso y 2 mías), con Haiku y `claude -p`:

| Modo | Acierta | Se equivoca | No sabe | Segundos promedio |
|---|---|---|---|---|
| memoria | 0 | 0 | 10 | 7.9 |
| mcp | 10 | 0 | 0 | 13.4 |

Corrida base guardada en `resultados_base.csv`. Mis dos preguntas son `expo_ago26` (exportaciones FOB de agosto de 2026,
serie PN38714BM) y `oro_ago26` (cotización promedio del oro LME en agosto de 2026, serie PN01654XM); la `verdad` la saqué
de la tabla de la web del BCRP, no de mi MCP.

![Aciertos por modo](grafico.png)

### Qué falló cada modo y por qué

- **Memoria:** no acertó ninguna, pero tampoco inventó: respondió `null` en las 10. En `fuente` explica que no tiene
  acceso a datos del INEI ni del BCRP. Casi todas las preguntas son de 2026, posteriores a lo que el modelo aprendió.
- **MCP:** 10 de 10. En cada caso la `fuente` cita el código de la serie, el periodo y la URL de la API del BCRP, así que
  el valor sale de la serie oficial y no de una cuenta a mano. Tarda más (13 s contra 8 s) porque primero busca la serie
  y luego la descarga.

### Experimento extra: contra la búsqueda web

`uv run evaluar.py --modos memoria web mcp` (resultado en `resultados.csv`; la figura es de esta corrida):

| Modo | Acierta | Se equivoca | No sabe | Segundos promedio |
|---|---|---|---|---|
| memoria | 0 | 0 | 10 | 4.6 |
| web | 8 | 1 | 1 | 20.4 |
| mcp | 10 | 0 | 0 | 8.2 |

- **Web, `cobre_ago26`:** respondió 651 en vez de 689.70. Tomó la cotización del cobre en la LME (PN01652XM), no el precio
  de exportación que usa la pregunta (PN38784BM), y además admite que leyó la página «mediante una herramienta que la
  resume». Es el error típico de la web: una cifra real, pero de otra serie.
- **Web, `referencia_set26`:** «no sabe». Encontró una nota que decía 4,25 % pero no pudo abrirla ni la nota del BCRP, y
  prefirió no responder.
- Las otras 8 las acertó, varias citando a la prensa (Andina, Forbes, El Comercio) en vez de al BCRP, y tardando más del
  doble que el MCP.

## Dos cifras comprobadas a mano en la web del BCRP

| Cifra del MCP | Serie y periodo | Valor en la web | Tabla |
|---|---|---|---|
| Exportaciones FOB, 10,815.4 millones US$ | PN38714BM, agosto 2026 | 10,815 | [Balanza comercial - Exportaciones](https://estadisticas.bcrp.gob.pe/estadisticas/series/mensuales/resultados/PN38714BM/html/2026-6/2026-9/) |
| Oro LME, 4,411.15 US$ por onza troy | PN01654XM, agosto 2026 | 4,411 | [Cotizaciones - Oro LME](https://estadisticas.bcrp.gob.pe/estadisticas/series/mensuales/resultados/PN01654XM/html/2026-6/2026-9/) |

La web muestra las dos series sin decimales; el valor completo coincide con el de la API del BCRP.

## Conclusión

Sin herramientas Claude no sabe cifras recientes, y con la instrucción de no estimar lo reconoce en vez de inventar. La
búsqueda web acierta la mayoría, pero tarda más del doble y puede tomar la serie equivocada o citar prensa en lugar de la
fuente oficial. El MCP acertó todo, más rápido, y siempre con el código de serie y el link. Vale la pena construir un MCP
cuando se consulta seguido la misma fuente estructurada y se necesita la cifra exacta y trazable; para una pregunta suelta
o sobre temas sin una base de datos oficial, basta la búsqueda web.
