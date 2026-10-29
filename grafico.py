"""La figura del informe: aciertos, errores y «no sé» por modo, a partir de resultados.csv.

    uv run grafico.py                                  # resultados.csv -> grafico.png
    uv run grafico.py resultados_base.csv base.png     # otra corrida
"""
import sys
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

AQUI = Path(__file__).parent
entrada = Path(sys.argv[1]) if len(sys.argv) > 1 else AQUI / "resultados.csv"
salida = Path(sys.argv[2]) if len(sys.argv) > 2 else AQUI / "grafico.png"

res = pd.read_csv(entrada)
orden = [m for m in ["memoria", "web", "mcp"] if m in set(res.modo)]
tabla = (res.groupby("modo").resultado.value_counts().unstack(fill_value=0)
         .reindex(index=orden, columns=["acierta", "se equivoca", "no sabe"], fill_value=0))
segundos = res.groupby("modo").segundos.mean().reindex(orden)
n = tabla.sum(axis=1)

fig, ax = plt.subplots(figsize=(7, 4))
izq = pd.Series(0, index=orden)
for col, color in zip(tabla.columns, ["#2e7d32", "#c62828", "#9e9e9e"]):
    ax.barh(orden, tabla[col], left=izq, color=color, label=col)
    for i, m in enumerate(orden):
        if tabla.loc[m, col]:
            ax.text(izq[m] + tabla.loc[m, col] / 2, i, int(tabla.loc[m, col]), ha="center", va="center", color="white")
    izq += tabla[col]
for i, m in enumerate(orden):
    ax.text(n[m] + 0.15, i, f"{segundos[m]:.1f} s", va="center", fontsize=9)
ax.invert_yaxis()
ax.set_xlim(0, n.max() + 1.5)
ax.set_xlabel(f"Preguntas (de {int(n.max())})")
ax.set_title("¿Acierta Claude las cifras del BCRP? Memoria, web y MCP")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3, frameon=False, fontsize=9)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(salida, dpi=150)
print(f"{salida.name}: {tabla.to_dict('index')}")
