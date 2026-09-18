"""Convierte los CSV crudos a parquet (lectura rápida).

Busca los CSV en ../output (zip del reto descomprimido) y, si no, en ../data (repo, con Git LFS).
Si un CSV es un puntero LFS sin descargar, avisa: hay que ejecutar `git lfs pull` o descomprimir el zip en output/.
"""
from pathlib import Path
import polars as pl

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parents[1] / "data"


def _is_lfs_pointer(f: Path) -> bool:
    with open(f, "rb") as fh:
        return fh.read(40).startswith(b"version https://git-lfs")


def main():
    OUT.mkdir(exist_ok=True)
    names = {}
    for raw in (REPO / "output", REPO / "data"):
        for f in sorted(raw.glob("*.csv")) if raw.exists() else []:
            if f.stem not in names and not _is_lfs_pointer(f):
                names[f.stem] = f
    missing = {"transactions", "invoices", "balances", "companies", "banking_products", "debt_products"} - set(names)
    if missing:
        raise SystemExit(f"Faltan CSV reales (¿punteros LFS?): {sorted(missing)}. Ejecuta `git lfs pull` o descomprime el zip del reto en output/.")
    for stem, f in names.items():
        df = pl.read_csv(f, infer_schema_length=100000, try_parse_dates=True)
        df.write_parquet(OUT / f"{stem}.parquet")
        print(stem, df.shape, "←", f.relative_to(REPO))


if __name__ == "__main__":
    main()
