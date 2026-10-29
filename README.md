# MCP del BCRP

Trabajo de la sesión 04 (MCP y Claude Code). Es un servidor MCP hecho con FastMCP que le da a Claude acceso a las
series estadísticas del Banco Central de Reserva del Perú, para que responda con la cifra oficial en vez de adivinar.

La pregunta que quería responder era simple: si le pregunto a Claude por la inflación, el tipo de cambio o las
exportaciones de un mes reciente, ¿inventa un número? ¿Y qué cambia cuando tiene el servidor conectado?

El análisis completo está en [informe.md](informe.md). En resumen: sin herramientas no acierta ninguna de las 10
preguntas (aunque tampoco inventa, responde que no sabe), con búsqueda web acierta 8 y con el MCP acierta las 10.
Repetí la corrida tres veces y el MCP acertó 30 de 30.

![Aciertos por modo](grafico.png)

## Qué tiene el servidor

| Herramienta | Para qué |
|---|---|
| `buscar_series` | Encontrar el código de una serie por palabras (el catálogo tiene más de 17 mil) |
| `serie` | Bajar los datos entre dos fechas, con el link a la fuente |
| `resumen` | Primero, último, variación, promedio, máximo y mínimo, calculados en Python |
| `valor_actual` | La que agregué yo: el dato más reciente publicado y su variación contra el año anterior |

Además tiene un recurso, `bcrp://serie/{codigo}`, con la ficha de cada serie, y un prompt, `informe(tema)`.

## Cómo correrlo

Se necesita [uv](https://docs.astral.sh/uv/) y Claude Code con la sesión iniciada.

```bash
uv run pytest -q          # 8 pruebas con datos reales del BCRP
uv run evaluar.py         # le hace las preguntas a Claude sin herramientas y con el MCP
uv run grafico.py         # genera grafico.png a partir de resultados.csv
uv run evaluar.py --sin-salida --modos memoria --salida resultados_sin_salida.csv   # experimento extra
```

Al abrir `claude` en esta carpeta se cargan los servidores `bcrp` y `fetch` desde `.mcp.json`. La primera vez se baja
el catálogo del BCRP a `datos/` (unos 7 MB), que no se sube al repositorio.

## Archivos

- `server.py`: el servidor MCP.
- `test_server.py`: las pruebas del curso, sin cambios.
- `preguntas.csv`: las 10 preguntas con su cifra oficial; las dos últimas (exportaciones y oro) son mías.
- `evaluar.py`: la evaluación con `claude -p`.
- `resultados_base.csv`: la corrida memoria contra MCP. `resultados.csv`: la corrida con memoria, web y MCP.
- `resultados_sin_salida.csv`: memoria sin la opción de decir «no sé». `resultados_rep2.csv` y `resultados_rep3.csv`:
  las repeticiones de la corrida base.
- `candidatos.py`: el script que usé para buscar las series de mis dos preguntas.
- `grafico.py` y `grafico.png`: la figura del informe.
