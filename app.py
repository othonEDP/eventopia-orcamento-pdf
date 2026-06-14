# -*- coding: utf-8 -*-
"""
Micro-serviço HTTP de geração de orçamentos Eventopia.
POST /orcamento  (JSON) -> devolve o PDF (application/pdf)
GET  /health     -> {"status":"ok"}

Protegido por chave de API simples no header  X-API-Key  (env API_KEY).
Pensado para ser chamado pelo n8n (nó HTTP Request).
"""
import os
import datetime
from flask import Flask, request, jsonify, Response
from orcamento_core import gerar_pdf_bytes, _eur

app = Flask(__name__)
API_KEY = os.environ.get("API_KEY", "")  # se vazio, não exige chave


def _auth_ok(req):
    if not API_KEY:
        return True
    return req.headers.get("X-API-Key") == API_KEY


@app.get("/health")
def health():
    return jsonify(status="ok", service="eventopia-orcamento-pdf")


@app.post("/orcamento")
def orcamento():
    if not _auth_ok(request):
        return jsonify(error="unauthorized"), 401
    try:
        dados = request.get_json(force=True)
    except Exception as e:
        return jsonify(error=f"json inválido: {e}"), 400

    # Validação mínima
    if not dados.get("itens"):
        return jsonify(error="campo 'itens' em falta ou vazio"), 400
    if not dados.get("cliente", {}).get("nome"):
        return jsonify(error="cliente.nome em falta"), 400

    # Defaults úteis
    hoje = datetime.date.today()
    dados.setdefault("data", hoje.strftime("%d/%m/%Y"))
    dados.setdefault("validade", (hoje + datetime.timedelta(days=30)).strftime("%d/%m/%Y"))
    dados.setdefault("numero", f"ORC-{hoje.year}-{hoje.strftime('%m%d%H%M')}")
    dados.setdefault("markup_pct", 15)

    try:
        pdf_bytes, calc = gerar_pdf_bytes(dados)
    except Exception as e:
        return jsonify(error=f"falha ao gerar PDF: {e}"), 500

    filename = f"Orcamento_{dados['numero']}.pdf".replace("/", "-")
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Orcamento-Total": _eur(calc["total"]),
            "X-Orcamento-Numero": str(dados["numero"]),
        },
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
