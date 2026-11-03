import pytest

from app import database


@pytest.fixture
def banco(tmp_path):
    caminho = str(tmp_path / "teste.db")
    database.criar_tabelas(caminho)
    return caminho


def _nova(banco, **extra):
    dados = {"cliente": "Ana", "canal": "site", "texto": "oi", "categoria": "duvida",
             "urgencia": "baixa", "resumo": "oi", "classificado_por": "regras", **extra}
    return database.inserir_mensagem(dados, banco)


def test_inserir_e_buscar(banco):
    criada = _nova(banco)
    assert criada["id"] == 1
    assert criada["status"] == "aberta"
    assert database.buscar_mensagem(1, banco)["cliente"] == "Ana"


def test_filtros(banco):
    _nova(banco, categoria="reclamacao", urgencia="alta")
    _nova(banco, categoria="duvida")
    assert len(database.listar_mensagens(categoria="reclamacao", caminho=banco)) == 1
    assert len(database.listar_mensagens(caminho=banco)) == 2


def test_filtro_nao_aceita_sql_injection(banco):
    _nova(banco)
    assert database.listar_mensagens(categoria="x' OR '1'='1", caminho=banco) == []


def test_relatorio(banco):
    _nova(banco, categoria="reclamacao", urgencia="alta")
    _nova(banco, categoria="reclamacao", urgencia="alta")
    _nova(banco, categoria="agendamento", urgencia="media")
    database.atualizar_status(1, "resolvida", banco)

    relatorio = database.gerar_relatorio(banco)
    assert relatorio["total"] == 3
    assert relatorio["por_categoria"] == {"reclamacao": 2, "agendamento": 1}
    assert relatorio["urgentes_em_aberto"] == 1
