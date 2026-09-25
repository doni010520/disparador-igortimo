import re
import time
import random
from datetime import datetime
from pathlib import Path

import openpyxl
import requests

from config import (
    UAZAPI_URL, UAZAPI_TOKEN, AUDIO_URL,
    MENSAGEM_BOTOES, BOTAO_1, BOTAO_2,
    DELAY_ENTRE_MSGS, DELAY_MIN, DELAY_MAX,
    PLANILHA, OPTOUT_FILE, LOG_FILE, FALHAS_FILE,
)

HEADERS = {"token": UAZAPI_TOKEN, "Content-Type": "application/json"}

estado = {"status": "iniciando", "atual": None, "proximo_em": None}


def limpar_telefone(raw) -> str | None:
    digits = re.sub(r"\D", "", str(raw or ""))
    if not digits or "00000" in digits:
        return None
    digits = digits.lstrip("0")
    if not digits.startswith("55"):
        digits = "55" + digits
    if len(digits) not in (12, 13):
        return None
    return digits


def ler_numeros(path: str) -> set:
    p = Path(path)
    if not p.exists():
        return set()
    return {l.split("\t")[0] for l in p.read_text(encoding="utf-8").splitlines() if l}


def anexar(path: str, *campos):
    with open(path, "a", encoding="utf-8") as f:
        f.write("\t".join([*campos, datetime.now().isoformat(timespec="seconds")]) + "\n")


def carregar_contatos() -> list[tuple[str, str]]:
    ws = openpyxl.load_workbook(PLANILHA, read_only=True).active
    vistos, contatos = set(), []
    for row in ws.iter_rows(min_row=2, values_only=True):
        tel = limpar_telefone(row[1])
        if tel and tel not in vistos:
            vistos.add(tel)
            contatos.append((tel, str(row[0] or "").strip()))
    return contatos


def post(endpoint: str, payload: dict) -> requests.Response:
    return requests.post(f"{UAZAPI_URL}{endpoint}", json=payload, headers=HEADERS, timeout=60)


def bloqueio() -> str | None:
    """Retorna o motivo para não enviar agora, ou None se está liberado."""
    try:
        r = requests.get(f"{UAZAPI_URL}/instance/status", headers=HEADERS, timeout=30)
        if r.json().get("instance", {}).get("status") != "connected":
            return "instância desconectada"
        r = requests.get(f"{UAZAPI_URL}/instance/wa_messages_limits", headers=HEADERS, timeout=30)
        d = r.json()
        if d.get("can_send_new_messages") is False:
            ate = (d.get("reachout_timelock") or {}).get("until", "")
            return f"WhatsApp restringiu novas conversas até {ate}"
        return None
    except Exception as e:
        return f"erro ao checar instância: {e}"


def enviar(numero: str) -> tuple[bool, str]:
    r = post("/send/media", {"number": numero, "type": "ptt", "file": AUDIO_URL, "delay": 0})
    if r.status_code != 200:
        return False, f"audio {r.status_code} {r.text[:150]}"
    time.sleep(DELAY_ENTRE_MSGS)
    r = post("/send/menu", {
        "number": numero, "type": "button",
        "text": MENSAGEM_BOTOES, "choices": [BOTAO_1, BOTAO_2], "delay": 0,
    })
    if r.status_code != 200:
        return False, f"botoes {r.status_code} {r.text[:150]}"
    return True, ""


def main():
    contatos = carregar_contatos()
    feitos = ler_numeros(LOG_FILE) | ler_numeros(FALHAS_FILE) | ler_numeros(OPTOUT_FILE)
    pendentes = [(t, n) for t, n in contatos if t not in feitos]
    print(f"Contatos válidos: {len(contatos)} | pendentes: {len(pendentes)}", flush=True)

    for numero, nome in pendentes:
        while motivo := bloqueio():
            estado.update(status=f"pausado: {motivo}", atual=None, proximo_em=None)
            print(f"Pausado ({motivo}), checando de novo em 10 min", flush=True)
            time.sleep(600)

        if numero in ler_numeros(OPTOUT_FILE):
            continue

        estado.update(status="enviando", atual=f"{nome} ({numero})")
        try:
            ok, erro = enviar(numero)
        except requests.RequestException as e:
            ok, erro = False, f"rede: {e}"

        if ok:
            anexar(LOG_FILE, numero, nome)
            print(f"OK   {numero} {nome}", flush=True)
        elif "not on WhatsApp" in erro:
            anexar(FALHAS_FILE, numero, nome, "sem whatsapp")
            print(f"SEM  {numero} {nome}", flush=True)
            continue
        else:
            print(f"ERRO {numero} {nome}: {erro}", flush=True)

        delay = random.uniform(DELAY_MIN, DELAY_MAX)
        estado.update(status="aguardando", proximo_em=time.time() + delay)
        time.sleep(delay)

    estado.update(status="concluído", atual=None, proximo_em=None)
    print("Disparo concluído.", flush=True)


if __name__ == "__main__":
    main()
