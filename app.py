import os
import random
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from flask import Flask, jsonify, request, Response

import disparador
from config import UAZAPI_URL, OPTOUT_FILE, LOG_FILE, FALHAS_FILE

app = Flask(__name__)
PAINEL_SENHA = os.environ.get("PAINEL_SENHA", "")
TOTAL = {"valor": 0}


def linhas(path):
    p = Path(path)
    return [l.split("\t") for l in p.read_text(encoding="utf-8").splitlines() if l] if p.exists() else []


def autorizado():
    return not PAINEL_SENHA or request.args.get("k") == PAINEL_SENHA


NOMES_DEMO = [
    "Ana Paula Souza", "José Carlos Lima", "Maria das Graças Oliveira", "Antônio Pereira",
    "Francisca Alves", "João Batista Rocha", "Luzia Martins", "Sebastião Costa",
    "Raimunda Ferreira", "Pedro Henrique Dias", "Terezinha Gomes", "Manoel Ribeiro",
    "Conceição Barbosa", "Francisco Nunes", "Aparecida Teixeira", "Geraldo Moreira",
]


JANELAS_DEMO = [((9, 30), (13, 0)), ((14, 30), None)]


def stats_demo():
    agora = datetime.now(disparador.BRT)
    rnd = random.Random(agora.date().toordinal())
    ts, proximo = [], None
    for (hi, mi), fim_hm in JANELAS_DEMO:
        inicio = agora.replace(hour=hi, minute=mi, second=0, microsecond=0)
        fim = agora if fim_hm is None else min(agora, agora.replace(hour=fim_hm[0], minute=fim_hm[1], second=0, microsecond=0))
        n = max(int((fim - inicio).total_seconds() / 120), 0)
        ts += [inicio + timedelta(seconds=120 * i + 60 + rnd.uniform(-25, 25)) for i in range(n)]
        if fim_hm is None and agora > inicio:
            proximo = int((inicio + timedelta(seconds=120 * n + 60) - agora).total_seconds())
    total, optout, sem_wa = 10631, 2, 9
    return {
        "demo": True,
        "total": total,
        "enviados": len(ts),
        "optout": optout,
        "sem_whatsapp": sem_wa,
        "pendentes": total - len(ts) - optout - sem_wa,
        "ultima_hora": sum(1 for x in ts if agora - x < timedelta(hours=1)),
        "hoje": len(ts),
        "ultimo_envio": ts[-1].isoformat() if ts else None,
        "status": "aguardando" if proximo else "pausado",
        "atual": None,
        "proximo_em": max(proximo, 1) if proximo else None,
        "recentes": [{"numero": "", "nome": rnd.choice(NOMES_DEMO), "hora": x.isoformat()} for x in ts[-15:][::-1]],
    }


@app.get("/api/stats")
def stats():
    if not autorizado():
        return jsonify({"erro": "não autorizado"}), 401
    if request.args.get("demo"):
        return jsonify(stats_demo())
    enviados = linhas(LOG_FILE)
    agora = datetime.now(disparador.BRT)
    ts = [datetime.fromisoformat(l[-1]) for l in enviados if len(l) >= 3]
    ultima_hora = sum(1 for t in ts if agora - t < timedelta(hours=1))
    hoje = sum(1 for t in ts if t.date() == agora.date())
    n_env, n_opt, n_falha = len(enviados), len(linhas(OPTOUT_FILE)), len(linhas(FALHAS_FILE))
    total = TOTAL["valor"]
    e = disparador.estado
    return jsonify({
        "total": total,
        "enviados": n_env,
        "optout": n_opt,
        "sem_whatsapp": n_falha,
        "pendentes": max(total - n_env - n_opt - n_falha, 0),
        "ultima_hora": ultima_hora,
        "hoje": hoje,
        "ultimo_envio": ts[-1].isoformat() if ts else None,
        "status": e["status"],
        "atual": e["atual"],
        "proximo_em": max(int(e["proximo_em"] - time.time()), 0) if e["proximo_em"] else None,
        "recentes": [{"numero": l[0], "nome": l[1], "hora": l[-1]} for l in enviados[-15:][::-1]],
    })


@app.post("/webhook")
def webhook():
    data = request.get_json(silent=True) or {}
    msg = data.get("message") or data.get("data") or data
    if msg.get("fromMe"):
        return jsonify(ok=True)
    texto = " ".join(str(msg.get(k) or "") for k in ("text", "body", "content", "buttonOrListid")).lower()
    numero = str(msg.get("chatid") or msg.get("sender") or msg.get("from") or "").split("@")[0]
    if numero and ("sair" in texto or "não tenho interesse" in texto or "nao tenho interesse" in texto):
        if numero not in disparador.ler_numeros(OPTOUT_FILE):
            disparador.anexar(OPTOUT_FILE, numero)
            disparador.post("/send/text", {
                "number": numero,
                "text": "Tudo bem! Você não vai mais receber nossas mensagens. 🙏",
            })
            print(f"OPT-OUT {numero}", flush=True)
    return jsonify(ok=True)


@app.get("/")
def painel():
    if not autorizado():
        return Response("não autorizado", 401)
    return Response(Path(__file__).with_name("painel.html").read_text(encoding="utf-8"), mimetype="text/html")


def rodar_disparo():
    TOTAL["valor"] = len(disparador.carregar_contatos())
    disparador.main()


if __name__ == "__main__":
    threading.Thread(target=rodar_disparo, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
