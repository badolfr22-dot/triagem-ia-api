from types import SimpleNamespace

import pytest

from app.classificador import classificar, classificar_por_regras


@pytest.mark.parametrize(
    "texto, categoria, urgencia",
    [
        ("Quero agendar um horário para sábado", "agendamento", "media"),
        ("Quanto custa a progressiva?", "orcamento", "baixa"),
        ("Fui cobrado errado, isso é um absurdo", "reclamacao", "alta"),
        ("Vocês aceitam cartão?", "duvida", "baixa"),
        ("Bom dia!", "outro", "baixa"),
        ("Preciso remarcar HOJE, é urgente", "agendamento", "alta"),
    ],
)
def test_regras_classificam_casos_comuns(texto, categoria, urgencia):
    resultado = classificar_por_regras(texto)
    assert resultado["categoria"] == categoria
    assert resultado["urgencia"] == urgencia
    assert resultado["classificado_por"] == "regras"


def test_resumo_longo_e_cortado():
    resultado = classificar_por_regras("palavra " * 100)
    assert len(resultado["resumo"]) <= 120


class ClienteFalso:
    """Imita o cliente da Anthropic sem chamar a internet."""

    def __init__(self, resposta: str | Exception):
        self.resposta = resposta
        self.messages = self

    def create(self, **_):
        if isinstance(self.resposta, Exception):
            raise self.resposta
        return SimpleNamespace(content=[SimpleNamespace(text=self.resposta)])


def test_usa_resposta_da_ia_quando_valida():
    cliente = ClienteFalso('{"categoria": "orcamento", "urgencia": "baixa", "resumo": "Pede preço de corte."}')
    resultado = classificar("qualquer texto", cliente_ia=cliente)
    assert resultado == {"categoria": "orcamento", "urgencia": "baixa",
                         "resumo": "Pede preço de corte.", "classificado_por": "ia"}


def test_cai_para_regras_se_ia_responde_fora_do_padrao():
    cliente = ClienteFalso('{"categoria": "inventada", "urgencia": "baixa", "resumo": "x"}')
    assert classificar("Quero agendar", cliente_ia=cliente)["classificado_por"] == "regras"


def test_cai_para_regras_se_ia_da_erro():
    cliente = ClienteFalso(TimeoutError("sem resposta"))
    resultado = classificar("Quero agendar", cliente_ia=cliente)
    assert resultado["classificado_por"] == "regras"
    assert resultado["categoria"] == "agendamento"
