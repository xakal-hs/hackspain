"""De la nota a la decisión: prestar / vigilar / no prestar.

La nota ordena el riesgo; **no decide**. Encima de ella van los vetos (`docs/eventos.md:19`),
que son hechos de HOY y mandan sobre cualquier nota:

    nota 78 «sano» + este mes no ha salido la nómina que paga todos los meses  ->  NO PRESTAR

Por qué separar las dos capas en vez de meter los vetos en el score:

  - Un veto es **verificable y discutible**: el CFO puede enseñarte el justificante y se cae.
    Un peso dentro de una media ponderada, no.
  - Un veto es **asimétrico**: nunca mejora la decisión, solo la bloquea. Meterlo en la nota
    obligaría a que su ausencia sumase puntos, que es justo lo que pasaba al sumar la póliza
    a la liquidez: premiar a quien ya está endeudado.
  - La nota mira a 6 meses; el veto mira a este mes. Son preguntas distintas.

Y la calidad de dato no es un veto: es `sin_nota`. No puntuamos lo que no vemos.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import preprocessing as pre

# veto -> (etiqueta, explicación para quien presta)
VETOS = {
    "veto_caja_negativa": (
        "Cuenta en negativo",
        "La cuenta lleva dos meses o más en negativo: eso ya no es un descuadre de fechas, es un "
        "desfase. No se presta deuda nueva; solo con colateral (facturas identificables o garantía "
        "del grupo)."),
    "veto_nomina_ausente": (
        "Nómina habitual ausente",
        "Este mes no ha salido la nómina que paga todos los meses. Es la primera evidencia de un "
        "impago y llega antes que la caja negativa. No prestar hasta ver la siguiente."),
    "veto_ss_ausente": (
        "Seguridad Social ausente",
        "Deja de pagar una Seguridad Social que venía pagando con regularidad: deuda con un acreedor "
        "privilegiado que va por delante del banco."),
    "veto_iva_ausente": (
        "IVA ausente",
        "Se salta la liquidación de IVA de un trimestre que venía pagando. Hacienda cobra antes que tú."),
    "veto_cuota_ausente": (
        "Cuota de deuda ausente",
        "Deja de pagar una cuota regular. Sin calendario de cuotas no es verificable al 100 % — puede "
        "ser un vencimiento o un cambio de periodicidad — así que bloquea pero se puede levantar con "
        "el cuadro de amortización."),
    "veto_poliza_agotada": (
        "Póliza agotada con caja corta",
        "Más del 90 % de la póliza dispuesta y menos de medio mes de caja propia: la liquidez que se "
        "le ve es prestada y ya está gastada. No ampliar; convertir la póliza en préstamo a plazo si "
        "la cuota lo permite."),
    "veto_grupo_en_estres": (
        "El grupo también está seco",
        "La caja agregada del grupo está por debajo de 0,25 meses de su gasto: el argumento de «si pasa "
        "algo la matriz responde» no se sostiene. Diagnóstico, no sustituye a la nota de la entidad."),
}
# Veto que se puede levantar con un documento, frente a los que no.
LEVANTABLES = {"veto_cuota_ausente", "veto_iva_ausente"}

# No todos se ganan el puesto: `veto_report()` mide el lift de cada uno (tensión futura de
# las filas vetadas / tasa base). Dos bajan a aviso — mueven a «vigilar», no bloquean:
#   veto_grupo_en_estres  lift 1,67, pero veta el 31 % del panel; eventos.md lo llama diagnóstico
#   veto_cuota_ausente    lift 0,98: las filas que bloquea no acaban peor que la media
BLOQUEAN = {"veto_caja_negativa", "veto_nomina_ausente", "veto_ss_ausente",
            "veto_iva_ausente", "veto_poliza_agotada"}
AVISAN = {"veto_grupo_en_estres", "veto_cuota_ausente"}

ACCIONES = {"prestar": "Prestar", "vigilar": "Vigilar", "no_prestar": "No prestar", "sin_nota": "Sin nota"}
MIN_TX, MAX_DORMANT, MIN_CONFIDENCE = 5, 2, 0.30
LEND_BAND = "sano"


def decide(row: pd.Series) -> dict:
    """Una fila de panel + nota -> decisión, con sus motivos en lenguaje de quien presta.

    Orden: (1) ¿se ve la empresa? (2) ¿hay veto? (3) la nota.
    """
    razones = []

    # 1 · ¿se ve la empresa? La falta de observabilidad es cobertura, no salud.
    ciegas = []
    for flag, txt in [("dq_cash_sentinel", "saldo centinela del generador"),
                      ("dq_cash_implausible", "caja implausible frente a su flujo"),
                      ("has_drift", "la reconstrucción del saldo no cierra")]:
        if bool(row.get(flag, False)):
            ciegas.append(txt)
    dorm = int(row.get("months_since_last_tx") or 0)
    n_tx = int(row.get("n_tx") or 0)
    if dorm >= MAX_DORMANT:
        ciegas.append(f"{dorm} meses sin movimientos bancarios")
    elif n_tx < MIN_TX:
        ciegas.append(f"solo {n_tx} movimientos en el mes")
    if ciegas:
        return {"accion": "sin_nota", "accion_label": ACCIONES["sin_nota"], "vetos": [],
                "razones": [{"codigo": "D0", "etiqueta": "No se ve la empresa", "texto":
                             "No se puntúa: " + "; ".join(ciegas) + ". Se pide el dato, no se inventa la nota."}],
                "importe_max_meses": None}

    # 2 · vetos: hechos de hoy, mandan sobre la nota
    activos = [v for v in pre.VETOS if bool(row.get(v, False))]
    for v in activos:
        etiqueta, texto = VETOS[v]
        razones.append({"codigo": v, "etiqueta": etiqueta, "texto": texto,
                        "bloquea": v in BLOQUEAN, "levantable": v in LEVANTABLES})
    bloqueantes = [v for v in activos if v in BLOQUEAN]
    avisos = [v for v in activos if v in AVISAN]
    if bloqueantes:
        return {"accion": "no_prestar", "accion_label": ACCIONES["no_prestar"], "vetos": bloqueantes,
                "avisos": avisos, "razones": razones, "importe_max_meses": None}

    # 3 · la nota, y solo entonces
    score, band = float(row["score"]), row["band"]
    conf = float(row.get("confidence") or 0)
    if avisos:
        accion = "vigilar"
    elif conf < MIN_CONFIDENCE:
        razones.append({"codigo": "D1", "etiqueta": "Confianza baja", "texto":
                        f"La nota es {score:.0f} pero la confianza es {conf:.2f} (poca historia, huecos de datos "
                        "o valores fuera de rango): vigilar y pedir el dato antes de ampliar."})
        accion = "vigilar"
    elif band == LEND_BAND:
        accion = "prestar"
        razones.append({"codigo": "D2", "etiqueta": "Nota sana", "texto":
                        f"Nota {score:.0f}: banda sana y sin vetos. Prestar."})
    elif band == "vigilar":
        accion = "vigilar"
        razones.append({"codigo": "D3", "etiqueta": "Nota intermedia", "texto":
                        f"Nota {score:.0f}: ni sano ni riesgo. Prestar poco y con covenant de liquidez, o esperar."})
    else:
        accion = "no_prestar"
        razones.append({"codigo": "D4", "etiqueta": "Nota en riesgo", "texto":
                        f"Nota {score:.0f}: banda de riesgo. No prestar sin colateral."})

    # el importe se recorta por observabilidad, no por salud: lo que no vemos no se financia
    meses = 1.0 if accion == "prestar" else 0.5 if accion == "vigilar" else 0.0
    recortes = []
    if not bool(row.get("has_erp", False)):
        recortes.append("sin ERP: no se ven facturas ni clientes")
    if float(row.get("uncat_share") or 0) > 0.5:
        recortes.append("más de la mitad de los cobros sin categorizar")
    if int(row.get("month_idx") or 0) < 3:
        recortes.append("menos de 3 meses de historia")
    if recortes:
        meses *= 0.5
        razones.append({"codigo": "D5", "etiqueta": "Importe recortado por cobertura", "texto":
                        "Se reduce el importe a la mitad, no la nota: " + "; ".join(recortes) + "."})
    return {"accion": accion, "accion_label": ACCIONES[accion], "vetos": [], "avisos": avisos,
            "razones": razones, "importe_max_meses": round(meses, 2) if meses else None}


def decide_panel(scored: pd.DataFrame, panel: pd.DataFrame) -> pd.DataFrame:
    """Decisión para cada empresa-mes. Devuelve acción, vetos y número de vetos."""
    cols = ["company_id", "month", *pre.VETOS, "n_tx", "has_erp", "uncat_share", "month_idx",
            "dq_cash_sentinel", "dq_cash_implausible", "has_drift", "months_since_last_tx"]
    p = panel[[c for c in cols if c in panel.columns]]
    m = scored[["company_id", "month", "score", "band", "confidence"]].merge(p, on=["company_id", "month"])
    out = [decide(r) for _, r in m.iterrows()]
    m["accion"] = [o["accion"] for o in out]
    m["vetos"] = [",".join(o["vetos"]) for o in out]
    m["avisos"] = [",".join(o.get("avisos", [])) for o in out]
    m["n_vetos"] = [len(o["vetos"]) for o in out]
    # la primera razón es la que manda (el veto bloqueante, o la banda): es la frase que
    # se enseña como acción, para que la interfaz no tenga que inventarse el motivo
    m["razon"] = [o["razones"][0]["texto"] if o.get("razones") else "" for o in out]
    return m


def veto_report(panel: pd.DataFrame, scored: pd.DataFrame | None = None) -> pd.DataFrame:
    """Cuántas filas veta cada regla y qué tasa de tensión futura tienen.

    Un veto solo se gana el sitio si las filas que bloquea acaban peor que la media.
    `lift` = tasa de tensión de las vetadas / tasa base. Por debajo de 1 el veto estorba.
    """
    e = "tension_np_raw_6m"
    rows = []
    base = panel[e].mean()
    for v in pre.VETOS:
        if v not in panel.columns:
            continue
        m = panel[v].astype(bool)
        tasa = panel.loc[m, e].mean()
        r = {"veto": v, "filas": int(m.sum()), "empresas": int(panel.loc[m, "company_id"].nunique()),
             "tasa_tension": tasa, "lift": tasa / base if base else np.nan}
        if scored is not None:
            s = scored.merge(panel[["company_id", "month", v]], on=["company_id", "month"])
            r["nota_media_vetada"] = s.loc[s[v].astype(bool), "score"].mean()
            r["sanas_vetadas"] = int(((s[v].astype(bool)) & (s.band == "sano")).sum())
        rows.append(r)
    out = pd.DataFrame(rows).set_index("veto")
    out.attrs["tasa_base"] = base
    return out


if __name__ == "__main__":
    import predict as prd

    d = pre.build()
    sc = prd.fit(d, pre.labels(d))
    s = prd.score_panel(sc, d)
    rep = veto_report(d, s)
    print(f"tasa base de tensión = {rep.attrs['tasa_base']:.3f}\n")
    print(rep.round(3).to_string())
    dec = decide_panel(s, d)
    print("\nacciones:", dec.accion.value_counts().to_dict())
    print("filas con algún veto:", int((dec.n_vetos > 0).sum()))
    print("\nejemplo:", decide(dec.iloc[0]))
