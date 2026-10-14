#!/usr/bin/env python3

import argparse
import shutil
import sys
import tarfile

from pathlib import Path

SESSION_DIR = Path("whatsapp_auth")

DEFAULT_SESSION = SESSION_DIR / "session" / "Default"

LEVELDB = DEFAULT_SESSION / "Local Storage" / "leveldb"

INDEXEDDB = DEFAULT_SESSION / "IndexedDB"

ARTEFACTO = Path("whatsapp-session.tar.gz")

AUTH_MARKER = SESSION_DIR / ".autenticado"
READY_MARKER = SESSION_DIR / ".ready"
INVALID_MARKER = SESSION_DIR / ".invalido"

SINGLETONS = [
    "session/SingletonSocket",
    "session/SingletonLock",
    "session/SingletonCookie",
]

#
# IMPORTANTE:
# NÃO remover Service Workers.
# O WhatsApp Web moderno depende deles.
#
CACHES = [
    "session/Default/Cache",
    "session/Default/Code Cache",
    "session/Default/GPUCache",
    "session/Default/Crashpad",
]


def clean():
    removed = 0

    for rel in SINGLETONS:
        p = SESSION_DIR / rel

        if p.exists():
            try:
                p.unlink()
                removed += 1
            except Exception:
                pass

    for rel in CACHES:
        p = SESSION_DIR / rel

        if p.exists():
            try:
                shutil.rmtree(p)
                removed += 1
            except Exception:
                pass

    print(f"Removidos {removed} elementos de cache/singleton.")

    return 0


def session_valida():

    if not DEFAULT_SESSION.exists():
        print("Sessão inválida: pasta Default não encontrada.")
        return False

    if INVALID_MARKER.exists():
        print("Sessão inválida: marcador .invalido encontrado.")
        return False

    if not AUTH_MARKER.exists():
        print("Sessão inválida: marcador .autenticado inexistente.")
        return False

    if not READY_MARKER.exists():
        print("Sessão inválida: marcador .ready inexistente.")
        return False

    if not LEVELDB.exists():
        print("Sessão inválida: Local Storage/leveldb inexistente.")
        return False

    leveldb_files = list(LEVELDB.glob("*.ldb"))
    log_files = list(LEVELDB.glob("*.log"))

    if not leveldb_files and not log_files:
        print("Sessão inválida: LevelDB vazio.")
        return False

    total_leveldb = sum(
        p.stat().st_size
        for p in LEVELDB.rglob("*")
        if p.is_file()
    )

    if total_leveldb < 10240:
        print(
            f"Sessão inválida: LevelDB demasiado pequeno "
            f"({total_leveldb} bytes)."
        )
        return False

    if not INDEXEDDB.exists():
        print("Sessão inválida: IndexedDB inexistente.")
        return False

    indexed_files = [
        p
        for p in INDEXEDDB.rglob("*")
        if p.is_file()
    ]

    if not indexed_files:
        print("Sessão inválida: IndexedDB vazio.")
        return False

    total_indexeddb = sum(
        p.stat().st_size
        for p in indexed_files
    )

    if total_indexeddb < 10240:
        print(
            f"Sessão inválida: IndexedDB demasiado pequeno "
            f"({total_indexeddb} bytes)."
        )
        return False

    print(
        f"Sessão válida "
        f"(LevelDB={total_leveldb/1024:.1f} KB, "
        f"IndexedDB={total_indexeddb/1024:.1f} KB)"
    )

    return True


def health():

    print("=== Health Check WhatsApp Session ===")

    if not session_valida():
        print("ERRO: sessão não está saudável.")
        return 1

    total_leveldb = sum(
        f.stat().st_size
        for f in LEVELDB.rglob("*")
        if f.is_file()
    )

    total_indexeddb = sum(
        f.stat().st_size
        for f in INDEXEDDB.rglob("*")
        if f.is_file()
    )

    print()
    print(
        f"HEALTH OK | "
        f"LevelDB={total_leveldb/1024:.1f} KB | "
        f"IndexedDB={total_indexeddb/1024:.1f} KB"
    )

    return 0


def restore():

    if not ARTEFACTO.exists():
        print(
            "Aviso: tarball não encontrado. "
            "Será necessário pareamento via QR Code."
        )
        return 0

    with tarfile.open(ARTEFACTO, "r:gz") as tar:
        tar.extractall(path=".")

    ARTEFACTO.unlink()

    print("Sessão restaurada com sucesso.")

    if not session_valida():

        print()
        print(
            "AVISO: a sessão restaurada não passou "
            "na validação de integridade."
        )

        if SESSION_DIR.exists():
            shutil.rmtree(SESSION_DIR)

        print(
            "Sessão descartada para permitir "
            "novo pareamento seguro."
        )

        return 1

    print("Sessão restaurada e validada.")

    return 0


def clear():

    if SESSION_DIR.exists():
        shutil.rmtree(SESSION_DIR)
        print(f"Sessão removida: {SESSION_DIR}")
    else:
        print("Nenhuma sessão para remover.")

    return 0


def compress():

    if not session_valida():
        print(
            "ERRO: sessão WhatsApp inválida."
        )
        return 1

    if ARTEFACTO.exists():
        ARTEFACTO.unlink()

    with tarfile.open(
        ARTEFACTO,
        "w:gz"
    ) as tar:

        tar.add(
            SESSION_DIR,
            arcname="whatsapp_auth"
        )

    print(
        f"Tarball criado: {ARTEFACTO.name} "
        f"({ARTEFACTO.stat().st_size / 1024 / 1024:.1f} MB)"
    )

    with tarfile.open(
        ARTEFACTO,
        "r:gz"
    ) as tar:

        for member in tar.getmembers()[:30]:
            print(f"  {member.name}")

    return 0


def main():

    parser = argparse.ArgumentParser(
        description="Gestão da sessão WhatsApp"
    )

    sub = parser.add_subparsers(
        dest="comando",
        required=True
    )

    sub.add_parser(
        "clean",
        help="Limpar caches"
    )

    sub.add_parser(
        "clear",
        help="Remover sessão"
    )

    sub.add_parser(
        "compress",
        help="Compactar sessão"
    )

    sub.add_parser(
        "restore",
        help="Restaurar sessão"
    )

    sub.add_parser(
        "health",
        help="Validar integridade da sessão"
    )

    args = parser.parse_args()

    if args.comando == "clean":
        return clean()

    elif args.comando == "clear":
        return clear()

    elif args.comando == "compress":
        return compress()

    elif args.comando == "restore":
        return restore()

    elif args.comando == "health":
        return health()

    return 1


if __name__ == "__main__":
    sys.exit(main())
