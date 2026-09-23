#!/usr/bin/env python3
"""
Gestão da sessão WhatsApp para o workflow GitHub Actions.

Sub-comandos:
  clean       — remove caches e ficheiros singleton da sessão
  compress    — valida e compacta a sessão para whatsapp-session.tar.gz
  restore     — descompacta o artefacto da sessão (se existir)

Compatibilidade com tokens GitHub App: nenhum código assume formato
ou comprimento de token. O GITHUB_TOKEN é usado exclusivamente via
as GitHub Actions oficiais (action-download-artifact, upload-artifact),
que recebem o token através de secrets — o GitHub gere a transição
para o formato stateless (ghs_...) automaticamente.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tarfile
from pathlib import Path

SESSION_DIR = Path("whatsapp_auth")
DEFAULT_SESSION = SESSION_DIR / "session" / "Default"
LEVELDB = DEFAULT_SESSION / "Local Storage" / "leveldb"
INDEXEDDB = DEFAULT_SESSION / "IndexedDB"
ARTEFACTO = Path("whatsapp-session.tar.gz")

SINGLETONS = [
    "session/SingletonSocket",
    "session/SingletonLock",
    "session/SingletonCookie",
]

CACHES = [
    "session/Default/Cache",
    "session/Default/Code Cache",
    "session/Default/GPUCache",
    "session/Default/Service Worker/CacheStorage",
    "session/Default/Service Worker/ScriptCache",
    "session/Default/GrShaderCache",
    "session/Default/DawnCache",
    "session/Default/Dictionaries",
    "session/Default/Crashpad",
    "session/Default/component_crx_cache",
    "session/Default/Storage/ext",
    "session/Default/blob_storage",
    "session/Default/File System",
]


def clean() -> int:
    """Remove caches e ficheiros singleton da sessão."""
    removed = 0
    for rel in SINGLETONS:
        p = SESSION_DIR / rel
        if p.exists():
            p.unlink()
            removed += 1
    for rel in CACHES:
        p = SESSION_DIR / rel
        if p.exists():
            shutil.rmtree(p)
            removed += 1
    print(f"Removidos {removed} elementos de cache/singleton.")
    tamanho = du_hr(SESSION_DIR)
    print(f"Tamanho da sessão após limpeza: {tamanho}")
    return 0


def session_valida() -> bool:
    """Verifica se existe uma sessão autenticada válida."""
    if not DEFAULT_SESSION.exists():
        return False
    lvl_current = LEVELDB / "CURRENT"
    if LEVELDB.exists() and lvl_current.exists() and lvl_current.stat().st_size > 0:
        return True
    if INDEXEDDB.exists():
        ficheiros = list(INDEXEDDB.rglob("*"))
        if ficheiros:
            return True
    return False


def compress() -> int:
    """Valida e compacta a sessão para o artefacto."""
    if not session_valida():
        print("ERRO: Sessão WhatsApp não encontrada (nem Local Storage/leveldb nem IndexedDB).")
        print("Diagnóstico da pasta whatsapp_auth:")
        if SESSION_DIR.exists():
            for p in SESSION_DIR.rglob("*"):
                if p.is_file():
                    print(f"  {p.relative_to(SESSION_DIR)}")
        else:
            print("  whatsapp_auth/ não existe")
        return 1

    if ARTEFACTO.exists():
        ARTEFACTO.unlink()

    with tarfile.open(ARTEFACTO, "w:gz") as tar:
        tar.add(SESSION_DIR, arcname="whatsapp_auth")

    tamanho_bytes = ARTEFACTO.stat().st_size
    print(f"Tarball criado: {ARTEFACTO.name} ({tamanho_bytes / 1024 / 1024:.1f} MB)")

    # Lista conteúdo (equivalente ao tar tzf | head -30)
    with tarfile.open(ARTEFACTO, "r:gz") as tar:
        membros = tar.getmembers()
        for m in membros[:30]:
            print(f"  {m.name}")
        if len(membros) > 30:
            print(f"  ... ({len(membros) - 30} mais)")

    return 0


def restore() -> int:
    """Descompacta o artefacto da sessão, se existir."""
    if not ARTEFACTO.exists():
        print("Aviso: tarball não encontrado. Será necessário pareamento via QR Code.")
        return 0

    with tarfile.open(ARTEFACTO, "r:gz") as tar:
        tar.extractall(path=".")

    ARTEFACTO.unlink()
    print("Sessão descompactada com sucesso.")
    return 0


def du_hr(p: Path) -> str:
    """Retorna o tamanho de um diretório em formato legível."""
    total = 0
    for entrada in p.rglob("*"):
        if entrada.is_file():
            total += entrada.stat().st_size
    if total < 1024:
        return f"{total} B"
    if total < 1024 * 1024:
        return f"{total / 1024:.0f} KB"
    return f"{total / 1024 / 1024:.1f} MB"


def main() -> int:
    parser = argparse.ArgumentParser(description="Gestão da sessão WhatsApp")
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("clean", help="Limpar caches da sessão")
    sub.add_parser("compress", help="Validar e compactar a sessão")
    sub.add_parser("restore", help="Restaurar sessão do artefacto")

    args = parser.parse_args()

    if args.comando == "clean":
        return clean()
    elif args.comando == "compress":
        return compress()
    elif args.comando == "restore":
        return restore()
    return 1


if __name__ == "__main__":
    sys.exit(main())
