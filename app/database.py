"""Acesso ao banco de dados SQLite.

Uso SQL puro (módulo sqlite3 da biblioteca padrão) para deixar as consultas
visíveis e fáceis de entender. Trocar para PostgreSQL depois exige mudar só
este arquivo.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

CAMINHO_PADRAO = os.getenv("DATABASE_PATH", "triagem.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS mensagens (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente     TEXT    NOT NULL,
    canal       TEXT    NOT NULL,
    texto       TEXT    NOT NULL,
    categoria   TEXT    NOT NULL,
    urgencia    TEXT    NOT NULL,
    resumo      TEXT    NOT NULL,
    classificado_por TEXT NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'aberta',
    criado_em   TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mensagens_categoria ON mensagens (categoria);
CREATE INDEX IF NOT EXISTS idx_mensagens_status    ON mensagens (status);
"""


@contextmanager
def conectar(caminho: str | None = None):
    conexao = sqlite3.connect(caminho or CAMINHO_PADRAO)
    conexao.row_factory = sqlite3.Row
    try:
        yield conexao
        conexao.commit()
    finally:
        conexao.close()


def criar_tabelas(caminho: str | None = None) -> None:
    with conectar(caminho) as conexao:
        conexao.executescript(SCHEMA)


def inserir_mensagem(dados: dict, caminho: str | None = None) -> dict:
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conectar(caminho) as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO mensagens
                (cliente, canal, texto, categoria, urgencia, resumo,
                 classificado_por, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dados["cliente"],
                dados["canal"],
                dados["texto"],
                dados["categoria"],
                dados["urgencia"],
                dados["resumo"],
                dados["classificado_por"],
                agora,
            ),
        )
        novo_id = cursor.lastrowid
    return buscar_mensagem(novo_id, caminho)


def buscar_mensagem(mensagem_id: int, caminho: str | None = None) -> dict | None:
    with conectar(caminho) as conexao:
        linha = conexao.execute(
            "SELECT * FROM mensagens WHERE id = ?", (mensagem_id,)
        ).fetchone()
    return dict(linha) if linha else None


def listar_mensagens(
    categoria: str | None = None,
    urgencia: str | None = None,
    status: str | None = None,
    limite: int = 50,
    caminho: str | None = None,
) -> list[dict]:
    filtros, valores = [], []
    for coluna, valor in (("categoria", categoria), ("urgencia", urgencia), ("status", status)):
        if valor:
            filtros.append(f"{coluna} = ?")  # nome da coluna vem do código, não do usuário
            valores.append(valor)

    sql = "SELECT * FROM mensagens"
    if filtros:
        sql += " WHERE " + " AND ".join(filtros)
    sql += " ORDER BY id DESC LIMIT ?"
    valores.append(limite)

    with conectar(caminho) as conexao:
        linhas = conexao.execute(sql, valores).fetchall()
    return [dict(linha) for linha in linhas]


def atualizar_status(mensagem_id: int, status: str, caminho: str | None = None) -> dict | None:
    with conectar(caminho) as conexao:
        conexao.execute(
            "UPDATE mensagens SET status = ? WHERE id = ?", (status, mensagem_id)
        )
    return buscar_mensagem(mensagem_id, caminho)


def gerar_relatorio(caminho: str | None = None) -> dict:
    with conectar(caminho) as conexao:
        total = conexao.execute("SELECT COUNT(*) FROM mensagens").fetchone()[0]
        por_categoria = conexao.execute(
            "SELECT categoria, COUNT(*) AS qtd FROM mensagens GROUP BY categoria ORDER BY qtd DESC"
        ).fetchall()
        por_urgencia = conexao.execute(
            "SELECT urgencia, COUNT(*) AS qtd FROM mensagens GROUP BY urgencia"
        ).fetchall()
        abertas_alta = conexao.execute(
            "SELECT COUNT(*) FROM mensagens WHERE urgencia = 'alta' AND status = 'aberta'"
        ).fetchone()[0]
    return {
        "total": total,
        "por_categoria": {l["categoria"]: l["qtd"] for l in por_categoria},
        "por_urgencia": {l["urgencia"]: l["qtd"] for l in por_urgencia},
        "urgentes_em_aberto": abertas_alta,
    }
