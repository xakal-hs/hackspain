"""Cifra y descifra context/, notebooks/, research/ y analysis/.

La clave vive en .env (DECRYPT_KEY) y no se versiona.

    python3 scripts/vault.py encrypt
    python3 scripts/vault.py decrypt
    python3 scripts/vault.py status
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import tarfile
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "vault"
ENV_PATH = ROOT / ".env"
MAGIC = b"XRAYENC1"

FOLDERS = ("context", "notebooks", "research", "analysis")
SKIP_DIRS = {".venv", "__pycache__", ".pytest_cache", ".git"}
SKIP_NAMES = {".DS_Store"}
SKIP_SUFFIXES = {".pyc", ".duckdb"}


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key, value = key.strip(), value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def fernet() -> Fernet:
    load_env(ENV_PATH)
    raw = os.environ.get("DECRYPT_KEY", "").strip()
    if not raw:
        sys.exit("Falta DECRYPT_KEY en .env")
    try:
        return Fernet(raw.encode() if isinstance(raw, str) else raw)
    except ValueError as exc:
        sys.exit(f"DECRYPT_KEY no es una clave Fernet válida: {exc}")


def skip_dir(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def derived_skip(rel: Path) -> bool:
    posix = rel.as_posix()
    if posix.startswith("research/data/") and rel.name != "events_export.parquet":
        return True
    if posix.startswith("research/artifacts/"):
        return True
    if posix.startswith("research/reports/") and (
        rel.suffix == ".parquet" or rel.name.startswith("log_")
    ):
        return True
    return False


def iter_files(folder: str) -> list[Path]:
    root = ROOT / folder
    if not root.is_dir():
        return []
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if skip_dir(rel):
            continue
        if path.name in SKIP_NAMES or path.suffix in SKIP_SUFFIXES:
            continue
        if derived_skip(rel):
            continue
        files.append(path)
    return sorted(files)


def pack(folder: str) -> bytes:
    buffer = io.BytesIO()
    files = iter_files(folder)
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for path in files:
            tar.add(path, arcname=str(path.relative_to(ROOT)), recursive=False)
    return buffer.getvalue()


def encrypt_folder(cipher: Fernet, folder: str) -> Path:
    VAULT.mkdir(parents=True, exist_ok=True)
    payload = pack(folder)
    token = cipher.encrypt(payload)
    dest = VAULT / f"{folder}.enc"
    dest.write_bytes(MAGIC + token)
    return dest


def decrypt_folder(cipher: Fernet, folder: str) -> int:
    source = VAULT / f"{folder}.enc"
    if not source.is_file():
        sys.exit(f"No está el paquete cifrado: {source.relative_to(ROOT)}")
    raw = source.read_bytes()
    if not raw.startswith(MAGIC):
        sys.exit(f"{source.name} no tiene cabecera XRAYENC1")
    try:
        payload = cipher.decrypt(raw[len(MAGIC) :])
    except InvalidToken:
        sys.exit("Clave incorrecta o paquete corrupto")
    buffer = io.BytesIO(payload)
    count = 0
    with tarfile.open(fileobj=buffer, mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            dest = (ROOT / member.name).resolve()
            if ROOT not in dest.parents and dest != ROOT:
                sys.exit(f"Ruta fuera del repo: {member.name}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            dest.write_bytes(extracted.read())
            os.utime(dest, (member.mtime, member.mtime))
            count += 1
    return count


def cmd_encrypt() -> None:
    cipher = fernet()
    for folder in FOLDERS:
        files = iter_files(folder)
        dest = encrypt_folder(cipher, folder)
        print(f"{folder}: {len(files)} ficheros → {dest.relative_to(ROOT)} ({dest.stat().st_size:,} bytes)")


def cmd_decrypt() -> None:
    cipher = fernet()
    for folder in FOLDERS:
        n = decrypt_folder(cipher, folder)
        print(f"{folder}: {n} ficheros restaurados")


def cmd_status() -> None:
    load_env(ENV_PATH)
    has_key = bool(os.environ.get("DECRYPT_KEY", "").strip())
    print(f".env: {'sí' if ENV_PATH.exists() else 'no'}  DECRYPT_KEY: {'sí' if has_key else 'no'}")
    for folder in FOLDERS:
        enc = VAULT / f"{folder}.enc"
        local = len(iter_files(folder))
        enc_s = f"{enc.stat().st_size:,} bytes" if enc.is_file() else "ausente"
        print(f"  {folder}: {local} ficheros locales, vault {enc_s}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("encrypt", "decrypt", "status"))
    args = parser.parse_args()
    if args.command == "encrypt":
        cmd_encrypt()
    elif args.command == "decrypt":
        cmd_decrypt()
    else:
        cmd_status()


if __name__ == "__main__":
    main()
