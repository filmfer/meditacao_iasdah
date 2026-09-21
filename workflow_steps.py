#!/usr/bin/env python3
"""Passos utilitários do workflow GitHub Actions.

Sub-comandos:
  dedup     — verifica se a meditação já foi publicada hoje (API de runs)
  aguardar  — alinha a execução com as 07:23 locais nos Açores (DST)

Segurança de tokens: o GITHUB_TOKEN é usado exclusivamente em cabeçalhos
HTTP, sem qualquer pressuposto de formato ou comprimento — compatível com
o novo formato stateless de tokens de GitHub App (`ghs_...`, ~520 chars).
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

WORKFLOW_FILE = "meditacao_diaria.yml"
API_URL = "https://api.github.com/repos/{repo}/actions/workflows/{workflow}/runs"
ALVO_HORA = 7
ALVO_MINUTO = 23
TETO_ESPERA_S = 5400  # 90 min


def dedup() -> int:
    """Escreve skip=true/false em $GITHUB_OUTPUT se já houve run de hoje.

    Falha aberta: em erro da API publica na mesma (é pior ficar um dia
    sem meditação do que arriscar um duplicado).
    """
    hoje = datetime.now(ZoneInfo("Atlantic/Azores")).strftime("%Y-%m-%d")
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ["GITHUB_REPOSITORY"]
    run_id = os.environ["GITHUB_RUN_ID"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        resp = requests.get(
            API_URL.format(repo=repo, workflow=WORKFLOW_FILE),
            headers=headers,
            params={"created": f">={hoje}", "per_page": 100},
            timeout=30,
        )
        resp.raise_for_status()
        runs = resp.json().get("workflow_runs", [])
    except requests.RequestException as exc:
        print(f"::warning::Deduplicação indisponível ({exc}); a prosseguir com a publicação.")
        ativos = 0
    else:
        # Runs de hoje concluídos com sucesso OU ainda por concluir
        # (fila/em curso), excluindo o run atual.
        ativos = sum(
            1
            for r in runs
            if str(r.get("id")) != run_id
            and (
                r.get("conclusion") == "success"
                or r.get("status") in ("queued", "in_progress", "waiting")
            )
        )

    print(f"Data de referência (Atlantic/Azores): {hoje}")
    print(f"Runs de hoje concluídos com sucesso ou em curso: {ativos}")

    skip = "true" if ativos > 0 else "false"
    out_path = os.environ.get("GITHUB_OUTPUT")
    if out_path:
        with open(out_path, "a", encoding="utf-8") as fh:
            fh.write(f"skip={skip}\n")
    return 0


def aguardar() -> int:
    """Dorme até às 07:23 locais nos Açores (no inverno o cron chega 1h cedo).

    Dorme apenas — nunca falha por estar fora de uma janela.
    """
    agora = datetime.now(ZoneInfo("Atlantic/Azores"))
    alvo = agora.replace(hour=ALVO_HORA, minute=ALVO_MINUTO, second=0, microsecond=0)

    if agora < alvo:
        espera = (alvo - agora).total_seconds()
        if espera <= TETO_ESPERA_S:
            print(f"A esperar {int(espera)}s para publicar às 07:23 locais (Açores)...")
            time.sleep(espera)
        else:
            print(f"Aviso: desvio de {int(espera)}s além do teto de 90 min; a publicar de imediato.")
    else:
        print(f"Hora local {agora:%H:%M} — já passou das 07:23; a publicar de imediato.")
    return 0


def main() -> int:
    comandos = {"dedup": dedup, "aguardar": aguardar}
    if len(sys.argv) != 2 or sys.argv[1] not in comandos:
        print(f"Uso: {sys.argv[0]} {{{'|'.join(comandos)}}}", file=sys.stderr)
        return 2
    return comandos[sys.argv[1]]()


if __name__ == "__main__":
    sys.exit(main())