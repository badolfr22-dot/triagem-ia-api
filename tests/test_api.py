import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setattr("app.database.CAMINHO_PADRAO", str(tmp_path / "api.db"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_saude(cliente):
    assert cliente.get("/saude").json() == {"status": "ok"}


def test_fluxo_completo(cliente):
    r = cliente.post("/mensagens", json={"cliente": "Bruno", "canal": "whatsapp",
                                         "texto": "Fui cobrado errado, quero reembolso"})
    assert r.status_code == 201
    mensagem = r.json()
    assert mensagem["categoria"] == "reclamacao"
    assert mensagem["urgencia"] == "alta"

    r = cliente.get("/mensagens", params={"urgencia": "alta"})
    assert [m["id"] for m in r.json()] == [mensagem["id"]]

    r = cliente.patch(f"/mensagens/{mensagem['id']}/status", json={"status": "resolvida"})
    assert r.json()["status"] == "resolvida"

    assert cliente.get("/relatorio").json()["urgentes_em_aberto"] == 0


def test_validacao_de_entrada(cliente):
    assert cliente.post("/mensagens", json={"cliente": "", "texto": "oi"}).status_code == 422
    assert cliente.post("/mensagens", json={"cliente": "A", "texto": "ok ok", "canal": "fax"}).status_code == 422


def test_mensagem_inexistente(cliente):
    assert cliente.get("/mensagens/999").status_code == 404
