"""Publica los perfiles operativos ya inferidos por analysis/cluster_sector.py.

El perfil describe cómo opera una empresa; no interviene en el Health Score.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "processed" / "company_sector.csv"
VERSION = "cluster-sector-v1"


def as_number(value: str | None):
    return None if not value else float(value)


def build(source: Path, as_of_month: str) -> list[dict]:
    with source.open(newline="", encoding="utf-8") as handle:
        profiles = []
        for row in csv.DictReader(handle):
            sectors = [s.strip() for s in (row.get("sector_set") or "").split("|") if s.strip()]
            profiles.append({
                "company_id": row["company_id"], "group_id": row["group_id"],
                "business_kind": row.get("business_kind") or None,
                "sector_set": json.dumps(sectors, ensure_ascii=False),
                "top_sector": row.get("top_sector") or None,
                "top_sector_score": as_number(row.get("top_sector_score")),
                "regime_id": int(row["regime_id"]) if row.get("regime_id") else None,
                "regime_label": row.get("regime_label") or None,
                "profile_confidence": as_number(row.get("confidence")),
                "tenor": row.get("tenor") or None, "product_fit": row.get("product_fit") or None,
                "as_of_month": as_of_month, "profile_version": VERSION,
            })
    return profiles


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(SOURCE))
    parser.add_argument("--out", default=str(ROOT / "supabase" / "export" / "company_business_profile.csv"))
    parser.add_argument("--as-of-month", default="2026-08-01")
    args = parser.parse_args()
    rows = build(Path(args.source), args.as_of_month)
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys()); writer.writeheader(); writer.writerows(rows)
    print(f"{len(rows)} perfiles operativos -> {out}")


if __name__ == "__main__":
    main()
