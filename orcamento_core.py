# -*- coding: utf-8 -*-
"""
Núcleo de geração de orçamentos Eventopia (FAÇANHA ÓBVIA, LDA).
Cálculo (IVA 23%/13% + markup) e template HTML→PDF. Usado pelo micro-serviço (app.py)
e pelo CLI local (cli.py). Padrão Portugal.
"""
import base64
import io
import os
from weasyprint import HTML

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.environ.get("EVENTOPIA_LOGO", os.path.join(BASE_DIR, "eventopia_logo.png"))
COR_MARCA = "#E2001A"

EMITENTE = {
    "firma": "FAÇANHA ÓBVIA, LDA",
    "nipc": "518 525 031",
    "morada": "Rua de Santana, Lote 535A, 1 A",
    "cp_local": "2750-832 Cascais",
    "telefone": "+351 964 802 511",
    "email": "comercial@eventopia.events",
    "site": "eventopia.events",
    "iban": "LT91 3250 0419 3562 5281",
    "bic": "REVOLT21",
    "banco": "Revolut",
}


def _eur(v):
    s = f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} €"


def _logo_data_uri():
    try:
        with open(LOGO_PATH, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return ""


def calcular(itens, markup_pct):
    linhas, subtotal_custo = [], 0.0
    for it in itens:
        qtd = float(it["quantidade"])
        pu = float(it["preco_unit"])
        total_linha = qtd * pu
        subtotal_custo += total_linha
        linhas.append({
            "descricao": it["descricao"], "quantidade": qtd, "preco_unit": pu,
            "iva_pct": float(it.get("iva_pct", 23)), "total_linha": total_linha,
        })
    markup_pct = float(markup_pct or 0)
    markup_valor = subtotal_custo * (markup_pct / 100.0)
    base_por_taxa = {}
    for ln in linhas:
        peso = (ln["total_linha"] / subtotal_custo) if subtotal_custo else 0
        base_linha = ln["total_linha"] + markup_valor * peso
        base_por_taxa.setdefault(ln["iva_pct"], 0.0)
        base_por_taxa[ln["iva_pct"]] += base_linha
    base_tributavel = subtotal_custo + markup_valor
    iva_por_taxa = {t: b * (t / 100.0) for t, b in base_por_taxa.items()}
    total_iva = sum(iva_por_taxa.values())
    return {
        "linhas": linhas, "subtotal_custo": subtotal_custo, "markup_pct": markup_pct,
        "markup_valor": markup_valor, "base_tributavel": base_tributavel,
        "iva_por_taxa": iva_por_taxa, "total_iva": total_iva,
        "total": base_tributavel + total_iva,
    }


def render_html(dados, calc):
    cliente = dados["cliente"]
    linhas_html = ""
    for i, ln in enumerate(calc["linhas"], 1):
        qtd_fmt = (f"{ln['quantidade']:.0f}" if float(ln["quantidade"]).is_integer()
                   else f"{ln['quantidade']:.2f}".replace(".", ","))
        linhas_html += f"""<tr><td class="c">{i}</td><td>{ln['descricao']}</td>
        <td class="c">{qtd_fmt}</td><td class="r">{_eur(ln['preco_unit'])}</td>
        <td class="c">{ln['iva_pct']:.0f}%</td><td class="r">{_eur(ln['total_linha'])}</td></tr>"""
    iva_rows = "".join(
        f'<tr><td class="lbl">IVA ({t:.0f}%)</td><td class="val">{_eur(calc["iva_por_taxa"][t])}</td></tr>'
        for t in sorted(calc["iva_por_taxa"]))
    markup_row = (f'<tr><td class="lbl">Comissão de gestão ({calc["markup_pct"]:.0f}%)</td>'
                  f'<td class="val">{_eur(calc["markup_valor"])}</td></tr>') if calc["markup_valor"] > 0 else ""
    cond_pag = dados.get("cond_pagamento", "50% na adjudicação, 50% até à data do evento.")
    assunto = f'<div style="margin-top:10px;font-size:9pt"><b>Assunto:</b> {dados["assunto"]}</div>' if dados.get("assunto") else ""

    return f"""<!DOCTYPE html><html lang="pt"><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 16mm 14mm 22mm 14mm;
  @bottom-center {{ content: "{EMITENTE['firma']} · NIPC {EMITENTE['nipc']} · {EMITENTE['morada']}, {EMITENTE['cp_local']} · {EMITENTE['email']}"; font-size: 7pt; color: #888; }}
  @bottom-right {{ content: "Pág. " counter(page) "/" counter(pages); font-size: 7pt; color: #888; }} }}
* {{ box-sizing: border-box; }}
body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #222; font-size: 9.5pt; margin: 0; }}
.top {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid {COR_MARCA}; padding-bottom: 10px; }}
.top img {{ height: 52px; }}
.doc-meta {{ text-align: right; }} .doc-meta h1 {{ color: {COR_MARCA}; font-size: 20pt; margin: 0 0 4px; letter-spacing: 1px; }}
.doc-meta table {{ font-size: 8.5pt; border-collapse: collapse; margin-left: auto; }}
.doc-meta td {{ padding: 1px 0 1px 8px; }} .doc-meta td.k {{ color: #777; text-align: right; }}
.parties {{ display: flex; gap: 18px; margin: 16px 0 6px; }}
.party {{ flex: 1; border: 1px solid #e3e3e3; border-radius: 6px; padding: 9px 11px; }}
.party h3 {{ margin: 0 0 5px; font-size: 8pt; text-transform: uppercase; letter-spacing: .6px; color: {COR_MARCA}; }}
.party .nm {{ font-weight: bold; font-size: 10pt; }} .party div {{ line-height: 1.35; }}
table.items {{ width: 100%; border-collapse: collapse; margin-top: 14px; }}
table.items th {{ background: #1a1a1a; color: #fff; font-size: 8pt; text-transform: uppercase; letter-spacing: .5px; padding: 7px 8px; text-align: left; }}
table.items td {{ padding: 7px 8px; border-bottom: 1px solid #ececec; vertical-align: top; }}
table.items td.c, table.items th.c {{ text-align: center; }} table.items td.r, table.items th.r {{ text-align: right; }}
table.items tr:nth-child(even) td {{ background: #fafafa; }}
.totais {{ width: 46%; margin-left: auto; margin-top: 12px; }} .totais table {{ width: 100%; border-collapse: collapse; }}
.totais td {{ padding: 4px 8px; font-size: 9pt; }} .totais td.lbl {{ color: #555; }} .totais td.val {{ text-align: right; }}
.totais tr.sub td {{ border-top: 1px solid #ddd; }}
.totais tr.tot td {{ background: {COR_MARCA}; color: #fff; font-weight: bold; font-size: 11pt; padding: 8px; }}
.cond {{ margin-top: 20px; font-size: 8.5pt; line-height: 1.5; }}
.cond h3 {{ font-size: 8.5pt; text-transform: uppercase; letter-spacing: .6px; color: {COR_MARCA}; margin: 0 0 4px; border-bottom: 1px solid #eee; padding-bottom: 3px; }}
.cond .pay {{ background: #f7f7f7; border-left: 3px solid {COR_MARCA}; padding: 7px 10px; margin-top: 6px; }}
.assin {{ margin-top: 26px; display: flex; justify-content: space-between; font-size: 8.5pt; }}
.assin .box {{ width: 42%; }} .assin .line {{ border-top: 1px solid #999; margin-top: 34px; padding-top: 3px; text-align: center; color: #666; }}
.nota {{ margin-top: 14px; font-size: 7.5pt; color: #999; font-style: italic; }}
</style></head><body>
  <div class="top"><img src="{_logo_data_uri()}" alt="Eventopia">
    <div class="doc-meta"><h1>ORÇAMENTO</h1><table>
      <tr><td class="k">Nº</td><td>{dados['numero']}</td></tr>
      <tr><td class="k">Data</td><td>{dados['data']}</td></tr>
      <tr><td class="k">Validade</td><td>{dados['validade']}</td></tr></table></div></div>
  <div class="parties">
    <div class="party"><h3>Emitente</h3><div class="nm">{EMITENTE['firma']}</div>
      <div>NIPC: {EMITENTE['nipc']}</div><div>{EMITENTE['morada']}</div>
      <div>{EMITENTE['cp_local']}</div><div>{EMITENTE['telefone']} · {EMITENTE['email']}</div></div>
    <div class="party"><h3>Cliente</h3><div class="nm">{cliente['nome']}</div>
      {f"<div>NIF: {cliente['nif']}</div>" if cliente.get('nif') else ""}
      {f"<div>{cliente['morada']}</div>" if cliente.get('morada') else ""}
      {f"<div>{cliente['cp_local']}</div>" if cliente.get('cp_local') else ""}
      {f"<div>{cliente['contacto']}</div>" if cliente.get('contacto') else ""}</div></div>
  {assunto}
  <table class="items"><thead><tr>
    <th class="c" style="width:5%">#</th><th style="width:48%">Descrição</th>
    <th class="c" style="width:9%">Qtd.</th><th class="r" style="width:15%">Preço Unit.</th>
    <th class="c" style="width:8%">IVA</th><th class="r" style="width:15%">Total</th>
  </tr></thead><tbody>{linhas_html}</tbody></table>
  <div class="totais"><table>
    <tr class="sub"><td class="lbl">Subtotal (s/IVA)</td><td class="val">{_eur(calc['subtotal_custo'])}</td></tr>
    {markup_row}
    <tr><td class="lbl">Base tributável</td><td class="val">{_eur(calc['base_tributavel'])}</td></tr>
    {iva_rows}
    <tr class="tot"><td>TOTAL</td><td style="text-align:right">{_eur(calc['total'])}</td></tr></table></div>
  <div class="cond"><h3>Condições</h3>
    <div><b>Validade:</b> proposta válida até {dados['validade']}.</div>
    <div><b>Pagamento:</b> {cond_pag}</div>
    <div class="pay"><b>Dados para pagamento</b><br>Beneficiário: {EMITENTE['firma']}<br>
      IBAN: {EMITENTE['iban']} &nbsp;·&nbsp; BIC: {EMITENTE['bic']} ({EMITENTE['banco']})</div></div>
  <div class="assin"><div class="box"><div class="line">A Eventopia</div></div>
    <div class="box"><div class="line">O Cliente (aceitação)</div></div></div>
  <div class="nota">Este documento constitui um orçamento e não serve de fatura. Valores em euros (EUR). IVA à taxa legal em vigor.</div>
</body></html>"""


def gerar_pdf_bytes(dados):
    """Recebe o dict de dados, devolve (pdf_bytes, calc). Robusto a campos em falta."""
    import datetime as _dt
    hoje = _dt.date.today()
    dados.setdefault("data", hoje.strftime("%d/%m/%Y"))
    dados.setdefault("validade", (hoje + _dt.timedelta(days=30)).strftime("%d/%m/%Y"))
    dados.setdefault("numero", f"ORC-{hoje.year}-{hoje.strftime('%m%d%H%M')}")
    dados.setdefault("markup_pct", 15)
    dados.setdefault("cliente", {})
    calc = calcular(dados["itens"], dados.get("markup_pct", 15))
    html = render_html(dados, calc)
    buf = io.BytesIO()
    HTML(string=html, base_url=BASE_DIR).write_pdf(buf)
    return buf.getvalue(), calc
