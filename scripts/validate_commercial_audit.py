#!/usr/bin/env python3
"""Fail fast when the jury-facing commercial claims drift from their sources."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def require(text: str, needle: str, source: str) -> None:
    if needle not in text:
        raise AssertionError(f"{source}: falta {needle!r}")


def main() -> None:
    metrics = json.loads(read("research/reports/metrics_v7.json"))
    metrics_app = json.loads(read("research/reports/metrics_app.json"))
    monetization = read("analysis/monetizacion.html")
    monetization_brief = read("context/monetizacion.md")
    monetization_html = read("context/monetizacion.html")
    audit_md = read("context/auditoria_comercial.md")
    audit_html = read("context/auditoria_comercial.html")
    readme = read("README.md")

    expected_metrics = {
        "auc_deterioro": 0.7252489043698701,
        "auc_mejora": 0.7297037573476389,
        "auc_level_vs_tension_6m": 0.657282348303363,
        "mae_h3": 10.848491563244492,
    }
    for key, expected in expected_metrics.items():
        if metrics.get(key) != expected:
            raise AssertionError(f"metrics_v7.json: {key} cambió ({metrics.get(key)!r})")

    require(monetization, "Ingreso central corregido</small><strong>4,2 M€", "analysis/monetizacion.html")
    require(monetization, "Excedente real</small><strong>344 M€", "analysis/monetizacion.html")
    require(monetization, "370 empresas", "analysis/monetizacion.html")

    for source, text in {
        "context/monetizacion.md": monetization_brief,
        "context/auditoria_comercial.md": audit_md,
        "README.md": readme,
    }.items():
        require(text, "4,2 M€", source)
        require(text, "344 M€", source)
        require(text, "370 empresas", source)

    require(monetization_brief, "antecedente descartado", "context/monetizacion.md")
    require(audit_md, "Embat es el comprador", "context/auditoria_comercial.md")
    require(audit_md, "fixtures", "context/auditoria_comercial.md")
    require(read("frontend/README.md"), "fictional EUR fixtures", "frontend/README.md")

    for source, html in {
        "context/auditoria_comercial.html": audit_html,
        "context/monetizacion.html": monetization_html,
    }.items():
        if re.search(r"<(script|link)[^>]+(?:src|href)=[\"']https?://", html, re.I):
            raise AssertionError(f"{source} no es autocontenido")
        require(html.lower(), "<!doctype html>", source)
    for section in ("veredicto", "producto", "evidencia", "riesgos", "demo", "objeciones", "roadmap"):
        require(audit_html, f'id="{section}"', "context/auditoria_comercial.html")

    if metrics_app["iterations"][-1]["tag"] != "v7":
        raise AssertionError("metrics_app.json: la iteración final no es v7")
    require(
        json.dumps(metrics_app["final"], ensure_ascii=False),
        "AUC caída ≥15 a 3m (modelo v7)",
        "research/reports/metrics_app.json",
    )
    require(
        read("research/reports/decisions.json"),
        "capa de decisión de Embat para el CFO",
        "research/reports/decisions.json",
    )

    print("OK · cifras, versión v7, frontera de demo y HTML autocontenido verificados")


if __name__ == "__main__":
    main()
