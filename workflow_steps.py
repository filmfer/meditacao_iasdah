#!/usr/bin/env python3
"""Passo utilitário do workflow: alinhar a execução com as 07:23 locais.

O cron é fixo em UTC (06:23) e os Açores alternam UTC+1 (verão) / UTC+0
(inverno). No inverno este script dorme 1h para publicar às 07:23 locais;
no verão não espera. Teto de 90 min. Nunca falha por estar fora de uma
janela — dorme apenas ou publica de imediato.

Segurança de tokens: nenhum passo valida formato ou comprimento do
GITHUB_TOKEN — compatível com o novo formato stateless de tokens de
GitHub App (`ghs_...`, ~520 chars).
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

ALVO = (4, 23)          # 07:23 locais
TETO_ESPERA_S = 5400    # 90 min
TZ_ACORES = ZoneInfo("Atlantic/Azores")


def aguardar() -> None:
    """Dorme até às 07:23 locais nos Açores."""
    agora = datetime.now(TZ_ACORES)
    alvo = agora.replace(hour=ALVO[0], minute=ALVO[1], second=0, microsecond=0)

    if agora < alvo:
        espera = (alvo - agora).total_seconds()
        if espera <= TETO_ESPERA_S:
            print(f"A esperar {int(espera)}s para publicar às 07:23 locais (Açores)...")
            time.sleep(espera)
        else:
            print(f"Aviso: desvio de {int(espera)}s além do teto de 90 min; a publicar de imediato.")
    else:
        print(f"Hora local {agora:%H:%M} — a publicar de imediato.")


if __name__ == "__main__":
    aguardar()
