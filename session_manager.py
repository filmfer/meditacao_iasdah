#!/usr/bin/env python3
import argparse, shutil, sys, tarfile
from pathlib import Path

SESSION_DIR = Path('whatsapp_auth')
DEFAULT_SESSION = SESSION_DIR / 'session' / 'Default'
LEVELDB = DEFAULT_SESSION / 'Local Storage' / 'leveldb'
INDEXEDDB = DEFAULT_SESSION / 'IndexedDB'
ARTEFACTO = Path('whatsapp-session.tar.gz')

SINGLETONS = ['session/SingletonSocket', 'session/SingletonLock', 'session/SingletonCookie']

CACHES = [
    'session/Default/Cache', 'session/Default/Code Cache', 'session/Default/GPUCache',
    'session/Default/Service Worker/CacheStorage', 'session/Default/Service Worker/ScriptCache',
    'session/Default/GrShaderCache', 'session/Default/DawnCache', 'session/Default/Dictionaries',
    'session/Default/Crashpad', 'session/Default/component_crx_cache',
    'session/Default/Storage/ext', 'session/Default/blob_storage', 'session/Default/File System',
]

def clean():
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
    print(f'Removidos {removed} elementos de cache/singleton.')
    return 0

def session_valida():
    if not DEFAULT_SESSION.exists():
        return False
    lvl_current = LEVELDB / 'CURRENT'
    if LEVELDB.exists() and lvl_current.exists() and lvl_current.stat().st_size > 0:
        return True
    if INDEXEDDB.exists():
        if list(INDEXEDDB.rglob('*')):
            return True
    return False

def restore():
    if not ARTEFACTO.exists():
        print('Aviso: tarball nao encontrado. Sera necessario pareamento via QR Code.')
        return 0
    with tarfile.open(ARTEFACTO, 'r:gz') as tar:
        tar.extractall(path='.')
    ARTEFACTO.unlink()
    print('Sessao descompactada com sucesso.')
    if not session_valida():
        print('AVISO: Sessao restaurada nao e valida (provavelmente expirada ou revogada pelo WhatsApp).')
        print('Descartando sessao invalida para permitir novo pareamento via QR Code...')
        if SESSION_DIR.exists():
            shutil.rmtree(SESSION_DIR)
        print('Sessao invalida removida. Sera gerado novo QR Code para pareamento.')
        return 1
    print('Sessao valida confirmada.')
    return 0

def compress():
    if not session_valida():
        print('ERRO: Sessao WhatsApp nao encontrada.')
        return 1
    if ARTEFACTO.exists():
        ARTEFACTO.unlink()
    with tarfile.open(ARTEFACTO, 'w:gz') as tar:
        tar.add(SESSION_DIR, arcname='whatsapp_auth')
    print(f'Tarball criado: {ARTEFACTO.name} ({ARTEFACTO.stat().st_size / 1024 / 1024:.1f} MB)')
    with tarfile.open(ARTEFACTO, 'r:gz') as tar:
        for m in tar.getmembers()[:30]:
            print(f'  {m.name}')
    return 0

def main():
    parser = argparse.ArgumentParser(description='Gestao da sessao WhatsApp')
    sub = parser.add_subparsers(dest='comando', required=True)
    sub.add_parser('clean', help='Limpar caches da sessao')
    sub.add_parser('compress', help='Validar e compactar a sessao')
    sub.add_parser('restore', help='Restaurar sessao do artefacto')
    args = parser.parse_args()
    if args.comando == 'clean': return clean()
    elif args.comando == 'compress': return compress()
    elif args.comando == 'restore': return restore()
    return 1

if __name__ == '__main__':
    sys.exit(main())
