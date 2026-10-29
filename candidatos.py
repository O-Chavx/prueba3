"""Script que usé para armar mis 2 preguntas: busca la serie, baja el dato y da el link de la web del BCRP.

    uv run candidatos.py

El valor final de cada pregunta lo revisé en la tabla de la web del BCRP antes de pasarlo a preguntas.csv.
"""
from server import buscar_series, serie

PEDIDOS = [  # (id, texto para buscar, frecuencia, periodo, pregunta, tolerancia)
    ("expo_ago26", "exportaciones", "Mensual", "2026-08",
     "¿Cuánto sumaron las exportaciones totales del Perú en agosto de 2026 según el BCRP, en millones de US$?", 5),
    ("oro_ago26", "cotizaciones oro", "Mensual", "2026-08",
     "¿Cuál fue el precio promedio del oro en agosto de 2026 según el BCRP, en US$ por onza troy?", 5),
]

for id_, texto, frec, periodo, pregunta, tol in PEDIDOS:
    print(f"\n=== {id_}: buscar «{texto}» ===")
    candidatas = buscar_series(texto, frecuencia=frec, limite=5)
    for c in candidatas:
        print(f"  {c['codigo']}  {c['nombre']}")
    if not candidatas:
        print("  sin resultados: cambien el texto en PEDIDOS")
        continue
    s = serie(candidatas[0]["codigo"], periodo, periodo)
    valor = s["datos"][0]["valor"]
    print(f"  -> usando {s['codigo']}: {valor} en {periodo}")
    print(f"  revisen en la web: {s['fuente']}")
    print(f'  fila: {id_},"{pregunta}",{valor},{tol},{s["codigo"]},{periodo}')
