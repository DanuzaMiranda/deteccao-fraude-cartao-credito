"""Carrega a base fictícia e calcula a ficha que a Vera pode citar."""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ / "data"

ALIASES_CATEGORIA = {
    "alimentacao": ["alimentacao", "comida"],
    "moradia": ["moradia", "aluguel", "conta de luz"],
    "transporte": ["transporte", "uber", "combustivel"],
    "saude": ["saude", "farmacia", "academia"],
    "lazer": ["lazer", "netflix"],
    "compras": ["compras"],
    "receita": ["receita", "salario"],
}

BUSCA_DESCRICAO = [
    ("supermercado", "Supermercado Extra"),
    ("netflix", "Netflix"),
    ("farmacia", "Farmácia"),
    ("restaurante", "Restaurante"),
    ("uber", "Uber"),
    ("shopping", "Loja Aurora Shopping"),
    ("aluguel", "Aluguel"),
    ("conta de luz", "Conta de luz"),
    ("academia", "Academia"),
    ("combustivel", "Combustível"),
    ("salario", "Salário"),
    ("eletronicos", "Eletrônicos Online INT"),
]


def normalizar(texto: str) -> str:
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", texto)


def tem_termo(texto: str, termo: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(termo)}(?!\w)", texto) is not None


def brl(valor: float) -> str:
    negativo = valor < 0
    centavos = int(round(abs(valor) * 100))
    inteiro, frac = divmod(centavos, 100)
    corpo = f"{inteiro:,}".replace(",", ".")
    prefixo = "-" if negativo else ""
    return f"{prefixo}R$ {corpo},{frac:02d}"


def data_br(iso: str) -> str:
    ano, mes, dia = iso.split("-")
    return f"{dia}/{mes}/{ano}"


def _ler_json(nome: str):
    return json.loads((PASTA_DADOS / nome).read_text(encoding="utf-8"))


def _ler_csv(nome: str) -> list[dict]:
    with (PASTA_DADOS / nome).open(encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


@dataclass
class Base:
    perfil: dict
    transacoes: list[dict]
    historico: list[dict]
    produtos: list[dict]
    regras: dict
    faq: list[dict]
    cents_conhecidos: set[int] = field(default_factory=set)

    @property
    def saidas(self) -> list[dict]:
        return [t for t in self.transacoes if t["tipo"] == "saida"]

    @property
    def entradas(self) -> list[dict]:
        return [t for t in self.transacoes if t["tipo"] == "entrada"]

    @property
    def alerta(self) -> dict:
        achados = [t for t in self.transacoes if t["status"] == "alerta"]
        if len(achados) != 1:
            raise ValueError("A base deste protótipo espera um alerta.")
        return achados[0]

    @property
    def total_saidas(self) -> float:
        return sum(t["valor"] for t in self.saidas)

    @property
    def total_entradas(self) -> float:
        return sum(t["valor"] for t in self.entradas)

    @property
    def saidas_sem_alerta(self) -> float:
        return self.total_saidas - self.alerta["valor"]

    @property
    def falta_reserva(self) -> float:
        return self.perfil["reserva_emergencia_meta"] - self.perfil["reserva_emergencia_atual"]

    def por_categoria(self, categoria: str) -> list[dict]:
        return [t for t in self.transacoes if t["categoria"] == categoria]

    def soma_categoria(self, categoria: str) -> float:
        return sum(t["valor"] for t in self.por_categoria(categoria))

    def maior_saida_confirmada(self) -> dict:
        confirmadas = [
            t for t in self.saidas if t["status"] == "confirmada"
        ]
        return max(confirmadas, key=lambda t: t["valor"])

    def maior_compra_confirmada(self) -> dict:
        confirmadas = [
            t
            for t in self.saidas
            if t["status"] == "confirmada" and t["categoria"] == "compras"
        ]
        return max(confirmadas, key=lambda t: t["valor"])

    def alerta_em_aberto(self, memoria: dict | None) -> bool:
        decisao = (memoria or {}).get("decisao")
        return decisao != "reconhecida"

    def resumo_alerta(self) -> str:
        item = self.alerta
        return (
            f"{item['descricao']}, {brl(item['valor'])}, "
            f"em {data_br(item['data'])} às {item['hora']}, "
            f"no cartão final {item['final_cartao']}"
        )

    def motivos_alerta(self) -> str:
        maior = self.maior_saida_confirmada()
        compra = self.maior_compra_confirmada()
        return (
            f"{brl(self.alerta['valor'])} é maior do que qualquer saída confirmada "
            f"de outubro de 2025. A maior foi {maior['descricao']}, {brl(maior['valor'])}. "
            f"Entre as compras confirmadas, a maior foi {compra['descricao']}, "
            f"{brl(compra['valor'])}. A hora registrada é {self.alerta['hora']}."
        )

    def peso_na_renda(self) -> str:
        renda = self.perfil["renda_mensal"]
        percentual = (self.alerta["valor"] / renda) * 100
        return f"{percentual:.0f}%"

    def produtos_risco(self, risco: str) -> list[dict]:
        return [p for p in self.produtos if p.get("risco") == risco]

    def produto_por_nome(self, consulta: str) -> dict | None:
        consulta_n = normalizar(consulta)
        for produto in self.produtos:
            if normalizar(produto["nome"]) in consulta_n:
                return produto
        return None

    def ficha(self) -> str:
        linhas = [
            f"Cliente: {self.perfil['nome']}, {self.perfil['idade']} anos, {self.perfil['profissao']}.",
            f"Renda mensal: {brl(self.perfil['renda_mensal'])}.",
            f"Perfil de investidor: {self.perfil['perfil_investidor']}. Aceita risco alto: não.",
            f"Cartão final {self.perfil['cartao']['final']}, status {self.perfil['cartao']['status']}.",
            f"Reserva atual: {brl(self.perfil['reserva_emergencia_atual'])}.",
            f"Meta da reserva: {brl(self.perfil['reserva_emergencia_meta'])}.",
            f"Falta para a reserva: {brl(self.falta_reserva)}.",
            f"Entradas em outubro de 2025: {brl(self.total_entradas)}.",
            f"Saídas em outubro de 2025: {brl(self.total_saidas)}.",
            f"Saídas sem a compra em alerta: {brl(self.saidas_sem_alerta)}.",
            f"Alerta: {self.resumo_alerta()}.",
            self.motivos_alerta(),
            f"A compra em alerta equivale a {self.peso_na_renda()} da renda mensal.",
            (
                "Prazo para contestar: "
                f"{self.regras['contestacao']['prazo_cliente_dias_corridos']} dias corridos. "
                f"{self.regras['contestacao']['contagem']}"
            ),
            (
                "Análise da contestação: até "
                f"{self.regras['contestacao']['analise_dias_uteis']} dias úteis. "
                "Estorno garantido: não."
            ),
            f"Canal oficial: {self.regras['canal_oficial']}.",
        ]
        for categoria in ["alimentacao", "moradia", "transporte", "saude", "lazer", "compras"]:
            linhas.append(
                f"Categoria {categoria}: {brl(self.soma_categoria(categoria))}."
            )
        return "\n".join(linhas)

    def contexto_completo(self) -> str:
        return "\n\n".join(
            [
                "FICHA",
                self.ficha(),
                "PERFIL",
                json.dumps(self.perfil, ensure_ascii=False, indent=2),
                "REGRAS",
                json.dumps(self.regras, ensure_ascii=False, indent=2),
                "PRODUTOS",
                json.dumps(self.produtos, ensure_ascii=False, indent=2),
                "TRANSACOES",
                json.dumps(self.transacoes, ensure_ascii=False, indent=2),
                "HISTORICO",
                json.dumps(self.historico, ensure_ascii=False, indent=2),
                "FAQ",
                json.dumps(self.faq, ensure_ascii=False, indent=2),
            ]
        )


def carregar() -> Base:
    transacoes = []
    for linha in _ler_csv("transacoes.csv"):
        transacoes.append(
            {
                "data": linha["data"],
                "descricao": linha["descricao"],
                "categoria": linha["categoria"],
                "valor": float(linha["valor"]),
                "tipo": linha["tipo"],
                "status": linha["status"],
                "hora": linha["hora"],
                "final_cartao": linha["final_cartao"],
            }
        )
    base = Base(
        perfil=_ler_json("perfil_cliente.json"),
        transacoes=transacoes,
        historico=_ler_csv("historico_atendimento.csv"),
        produtos=_ler_json("produtos_financeiros.json"),
        regras=_ler_json("regras_banco.json"),
        faq=_ler_json("faq_seguranca.json"),
    )
    valores = [
        base.total_saidas,
        base.total_entradas,
        base.saidas_sem_alerta,
        base.falta_reserva,
        base.perfil["renda_mensal"],
        base.perfil["patrimonio_total"],
        base.perfil["reserva_emergencia_atual"],
        base.perfil["reserva_emergencia_meta"],
    ]
    valores.extend(item["valor"] for item in base.transacoes)
    valores.extend(base.soma_categoria(c) for c in ALIASES_CATEGORIA)
    valores.extend(float(p["aporte_minimo"]) for p in base.produtos if "aporte_minimo" in p)
    for meta in base.perfil["metas"]:
        valores.append(float(meta["valor_necessario"]))
    base.cents_conhecidos = {int(round(v * 100)) for v in valores}
    return base


def abertura(base: Base) -> str:
    return (
        "Oi, Marina. Eu sou a Vera. Eu te ajudo a entender o alerta do cartão "
        f"final {base.perfil['cartao']['final']} e a escolher o próximo passo.\n\n"
        f"Há uma compra em alerta: {base.resumo_alerta()}. {base.motivos_alerta()} "
        "Você reconhece essa compra?\n\n"
        "Fonte: transacoes.csv, regras_banco.json."
    )
