#!/usr/bin/env python3

import argparse
import shutil
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

SESSION_DIR = Path("whatsapp_auth")

DEFAULT_SESSION = SESSION_DIR / "session" / "Default"
LEVELDB = DEFAULT_SESSION / "Local Storage" / "leveldb"
INDEXEDDB = DEFAULT_SESSION / "IndexedDB"

ARTEFACTO = Path("whatsapp-session.tar.gz")

AUTH_MARKER = SESSION_DIR / ".autenticado"
READY_MARKER = SESSION_DIR / ".ready"
INVALID_MARKER = SESSION_DIR / ".invalido"
BACKUP_DIR = Path("whatsapp_auth_backup")

SINGLETONS = [
    "session/SingletonSocket",
    "session/SingletonLock",
    "session/SingletonCookie",
]

CACHES = [
    "session/Default/Cache",
    "session/Default/Code Cache",
    "session/Default/GPUCache",
    "session/Default/Crashpad",
]

ARTEFACTO_RETENCAO_DIAS = 90


def _listar_artefacts_disponiveis():
    return sorted(Path(".").glob("whatsapp-session*.tar.gz"))


def _fazer_backup_sessao():
    if not SESSION_DIR.exists():
        return None
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"whatsapp_auth_{ts}"
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copytree(SESSION_DIR, backup_path, dirs_exist_ok=True)
        print("Backup da sessão criado em:", backup_path)
        return backup_path
    except Exception as e:
        print("Nao foi possivel criar backup da sessao:", e)
        return None


def _extrair_arquivo(arquivo, destino=Path(".")):
    with tarfile.open(arquivo, "r:gz") as tar:
        tar.extractall(path=destino)


# ------------------------------------------------------------
# Validação (tolerante — preserva sessões válidas mesmo que marginais)
# ------------------------------------------------------------

def session_valida(forcar=False):
    problemas = []

    if not SESSION_DIR.exists():
        problemas.append("pasta whatsapp_auth inexistente")

    if not DEFAULT_SESSION.exists():
        problemas.append("pasta session/Default não encontrada")

    if INVALID_MARKER.exists() and not forcar:
        problemas.append("marcador .invalido presente")

    if not AUTH_MARKER.exists():
        problemas.append("marcador .autenticado inexistente")

    if READY_MARKER.exists():
        print("READY marker encontrado.")

    if LEVELDB.exists():
        leveldb_files = list(LEVELDB.glob("*.ldb")) + list(LEVELDB.glob("*.log"))
        if not leveldb_files:
            problemas.append("LevelDB vazio (sem .ldb nem .log)")
    else:
        problemas.append("Local Storage/leveldb inexistente")

    if INDEXEDDB.exists():
        indexed_files = [p for p in INDEXEDDB.rglob("*") if p.is_file()]
        if not indexed_files:
            problemas.append("IndexedDB vazio")
    else:
        problemas.append("IndexedDB inexistente")

    if problemas:
        print("Sessão invalida:")
        for p in problemas:
            print("   -", p)
        return False

    total_leveldb = 0
    if LEVELDB.exists():
        total_leveldb = sum(p.stat().st_size for p in LEVELDB.rglob("*") if p.is_file())
    total_indexeddb = 0
    if INDEXEDDB.exists():
        total_indexeddb = sum(p.stat().st_size for p in INDEXEDDB.rglob("*") if p.is_file())

    print("Sessão valida (LevelDB=", f"{total_leveldb / 1024:.1f} KB, IndexedDB={total_indexeddb / 1024:.1f} KB)")
    return True


def health():
    return 0 if session_valida() else 1


# ------------------------------------------------------------
# Restauração (com recuperação de artefacto anterior)
# ------------------------------------------------------------

def restaurar(artefato=ARTEFACTO, forcar=False):
    candidatos = []

    if artefato.exists():
        candidatos.append(artefato)

    for cand in _listar_artefacts_disponiveis():
        if cand.name != artefato.name and cand not in candidatos:
            candidatos.append(cand)

    if not candidatos:
        print("Nenhum artefacto de sessao encontrado.")
        if SESSION_DIR.exists():
            print("   Mantendo sessao local existente (nao removida).")
        return 0

    ultimo_erro = None

    for cand in candidatos:
        print("A tentar restaurar sessao de:", cand.name)
        _fazer_backup_sessao()

        if SESSION_DIR.exists():
            shutil.rmtree(SESSION_DIR)

        try:
            _extrair_arquivo(cand)
            cand.unlink()
        except Exception as e:
            print("Falha ao extrair", cand.name, ":", e)
            ultimo_erro = e
            continue

        if session_valida(forcar=forcar):
            print("Sessao restaurada e validada a partir de", cand.name)
            return 0

        print("Sessao de", cand.name, "nao passou na validacao.")
        ultimo_erro = Exception("validacao falhou")

        if SESSION_DIR.exists():
            shutil.rmtree(SESSION_DIR)

    print("Nenhum artefacto conseguiu restaurar uma sessao valida.")
    if ultimo_erro:
        print("   Ultimo erro:", ultimo_erro)
    return 1


def restore():
    return restaurar(ARTEFACTO)


# ------------------------------------------------------------
# Recuperação de sessão validada recentemente
# ------------------------------------------------------------

def recuperar_sessao_validada():
    candidatos = _listar_artefacts_disponiveis()

    if not candidatos:
        print("Nenhum artefacto de sessao disponível para recuperacao.")
        return 1

    print("A procurar sessao valida entre", len(candidatos), "artefacto(s)...")

    for cand in sorted(candidatos, key=lambda p: p.stat().st_mtime, reverse=True):
        print("   A testar:", cand.name)
        tmp_dir = Path(f".tmp_restore_{cand.stem}")
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)

        try:
            _extrair_arquivo(cand, tmp_dir)
            tmp_session = tmp_dir / "whatsapp_auth"
            if tmp_session.exists():
                if (tmp_session / "session" / "Default").exists() and \
                   (tmp_session / ".autenticado").exists():
                    print("Artefacto", cand.name, "contem sessao potencialmente valida.")
                    if SESSION_DIR.exists():
                        shutil.rmtree(SESSION_DIR)
                    shutil.copytree(tmp_session, SESSION_DIR)
                    cand.unlink()
                    if session_valida():
                        print("Sessao recuperada com sucesso.")
                        return 0
                    else:
                        print("Sessao copiada mas nao passou na validacao completa.")
                else:
                    print("   ", cand.name, "nao contem estrutura de sessao completa.")
            else:
                print("   ", cand.name, "nao contem pasta whatsapp_auth.")
        except Exception as e:
            print("   Erro ao testar", cand.name, ":", e)
        finally:
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)

    print("Nao foi possivel recuperar nenhuma sessao valida dos artefactos.")
    return 1


# ------------------------------------------------------------
# Compactação (sem destruir a sessão antes)
# ------------------------------------------------------------

def compress():
    if not SESSION_DIR.exists():
        print("ERRO: pasta whatsapp_auth inexistente. Nada a compactar.")
        return 1

    if not session_valida():
        print("ERRO: sessao WhatsApp nao passou na validacao pré-compress.")
        return 1

    if ARTEFACTO.exists():
        ARTEFACTO.unlink()

    with tarfile.open(ARTEFACTO, "w:gz") as tar:
        tar.add(SESSION_DIR, arcname="whatsapp_auth")

    tamanho_mb = ARTEFACTO.stat().st_size / 1024 / 1024
    print("Tarball criado:", ARTEFACTO.name, f"({tamanho_mb:.1f} MB)")

    with tarfile.open(ARTEFACTO, "r:gz") as tar:
        for member in tar.getmembers()[:40]:
            print("   ", member.name)

    return 0


# ------------------------------------------------------------
# Limpeza (apenas quando solicitada explicitamente)
# ------------------------------------------------------------

def clean():
    _fazer_backup_sessao()
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

    print("Removidos", removed, "elementos de cache/singleton (backup feito em whatsapp_auth_backup/).")
    return 0


def clear():
    _fazer_backup_sessao()
    if SESSION_DIR.exists():
        shutil.rmtree(SESSION_DIR)
        print("Sessao removida:", SESSION_DIR)
    else:
        print("Nenhuma sessao para remover.")
    return 0


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Gestão da sessão WhatsApp (meditacao_iasdah)"
    )

    sub = parser.add_subparsers(dest="comando", required=True)

    p_clean = sub.add_parser("clean", help="Limpar caches e singletons (destrutivo)")
    p_clean.add_argument("--forcar", action="store_true", help="Ignorar avisos")

    sub.add_parser("clear", help="Remover sessao local")

    p_compress = sub.add_parser("compress", help="Compactar sessao para artefacto")
    p_compress.add_argument("--forcar", action="store_true", help="Compactar mesmo com avisos de validacao")

    p_restore = sub.add_parser("restore", help="Restaurar sessao a partir do artefacto")
    p_restore.add_argument("--forcar", action="store_true", help="Ignorar .invalido e avisos de validacao")

    p_recuperar = sub.add_parser("recuperar", help="Recuperar sessao valida de artefactos antigos")
    p_recuperar.add_argument("--forcar", action="store_true", help="Ignorar avisos de validacao")

    p_health = sub.add_parser("health", help="Validar integridade da sessao")
    p_health.add_argument("--forcar", action="store_true", help="Ignorar .invalido e validar mesmo assim")

    args = parser.parse_args()

    if args.comando == "clean":
        return clean()
    if args.comando == "clear":
        return clear()
    if args.comando == "compress":
        if args.forcar:
            if not SESSION_DIR.exists():
                print("ERRO: pasta whatsapp_auth inexistente. Nada a compactar.")
                return 1
            if ARTEFACTO.exists():
                ARTEFACTO.unlink()
            with tarfile.open(ARTEFACTO, "w:gz") as tar:
                tar.add(SESSION_DIR, arcname="whatsapp_auth")
            print("Tarball criado (forcado):", ARTEFACTO.name)
            return 0
        return compress()
    if args.comando == "restore":
        return restaurar(ARTEFACTO, forcar=args.forcar)
    if args.comando == "recuperar":
        return recuperar_sessao_validada()
    if args.comando == "health":
        return 0 if session_valida(forcar=args.forcar) else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())