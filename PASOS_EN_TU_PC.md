# Correr el trabajo en tu PC (Windows, PowerShell)

Necesitas `uv` y Claude Code con tu sesión iniciada (`claude` debe abrir sin pedir login).

```powershell
cd ruta\a\mcp-bcrp
uv run pytest -q                      # meta: 8 passed. Si falla algo, copia el error completo
uv run candidatos.py                  # propone 2 preguntas propias con su link a la web del BCRP
```

Abre los dos links que imprime `candidatos.py`, comprueba el valor y pásame la salida (o pega las 2 filas al
final de `preguntas.csv`). Luego:

```powershell
uv run evaluar.py                                   # memoria contra mcp -> resultados.csv
Copy-Item resultados.csv resultados_base.csv
uv run grafico.py resultados_base.csv grafico.png   # figura del informe
uv run evaluar.py --modos memoria web mcp           # experimento extra -> resultados.csv
uv run grafico.py resultados.csv grafico_web.png
```

Pásame `resultados_base.csv`, `resultados.csv` y lo que imprimió `pytest`, y completo `informe.md`.
