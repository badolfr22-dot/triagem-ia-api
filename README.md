# Triagem IA API

![testes](https://github.com/badolfr22-dot/triagem-ia-api/actions/workflows/testes.yml/badge.svg)

API em **Python (FastAPI)** que recebe mensagens de clientes, usa **IA (Claude)** para classificar cada uma e guarda tudo num banco **SQL**. O objetivo é que um pequeno negócio saiba na hora o que é urgente, sem precisar ler mensagem por mensagem.

## O problema

Barbearias, clínicas e escritórios recebem pedidos pelo WhatsApp, site, e-mail e Instagram. Tudo chega misturado: quem quer agendar, quem pede preço, quem está reclamando de uma cobrança. As reclamações graves acabam esperando junto com o "bom dia".

## A solução

```
Mensagem do cliente ──▶ POST /mensagens ──▶ Classificador ──▶ Banco SQLite
                                              │
                                ┌─────────────┴─────────────┐
                                │ IA (Claude)               │  se houver chave de API
                                │ regras por palavra-chave  │  plano B: se não houver chave ou a IA falhar
                                └───────────────────────────┘
```

Para cada mensagem a API devolve:

| Campo | Valores |
|---|---|
| `categoria` | agendamento, orcamento, reclamacao, duvida, outro |
| `urgencia` | baixa, media, alta |
| `resumo` | uma frase curta gerada pela IA |
| `status` | aberta, em_andamento, resolvida |

## Endpoints

| Método | Rota | O que faz |
|---|---|---|
| `POST` | `/mensagens` | Recebe e classifica uma mensagem |
| `GET` | `/mensagens?categoria=&urgencia=&status=` | Lista com filtros |
| `GET` | `/mensagens/{id}` | Detalhe de uma mensagem |
| `PATCH` | `/mensagens/{id}/status` | Atualiza o andamento do atendimento |
| `GET` | `/relatorio` | Totais por categoria e urgentes em aberto |
| `GET` | `/saude` | Verificação de funcionamento |

A documentação interativa (Swagger) fica em `/docs` quando a API está rodando.

### Exemplo

```bash
curl -X POST http://localhost:8000/mensagens \
  -H "Content-Type: application/json" \
  -d '{"cliente": "Bruno", "canal": "whatsapp", "texto": "Fui cobrado errado, quero reembolso"}'
```

```json
{
  "id": 1,
  "cliente": "Bruno",
  "canal": "whatsapp",
  "categoria": "reclamacao",
  "urgencia": "alta",
  "resumo": "Cliente relata cobrança indevida e pede reembolso.",
  "classificado_por": "ia",
  "status": "aberta",
  "criado_em": "2026-11-03T14:00:00+00:00"
}
```

## Como rodar

```bash
git clone https://github.com/badolfr22-dot/triagem-ia-api.git
cd triagem-ia-api
python -m venv .venv && source .venv/bin/activate   # no Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env    # opcional: coloque sua ANTHROPIC_API_KEY
uvicorn app.main:app --reload
```

Depois é só abrir http://localhost:8000/docs.

Com Docker:

```bash
docker build -t triagem-ia-api .
docker run -p 8000:8000 -e ANTHROPIC_API_KEY=sua_chave triagem-ia-api
```

## Testes

```bash
pytest -v
```

Os testes não chamam a IA de verdade. Um cliente falso simula as respostas, inclusive respostas fora do padrão e erros de conexão, para garantir que o plano B entra em ação. Os testes rodam automaticamente no GitHub Actions a cada envio de código.

## Decisões técnicas

- **Plano B sem IA:** se a chave não existir, a IA demorar ou responder algo fora do formato, a API classifica por regras e marca `classificado_por: "regras"`. O atendimento não para.
- **Validação da resposta da IA:** a resposta só é aceita se a categoria e a urgência estiverem na lista permitida. Isso evita que um texto inesperado da IA quebre o sistema.
- **SQL puro com parâmetros (`?`):** as consultas ficam visíveis e protegidas contra SQL injection, o que é coberto por teste. Para trocar por PostgreSQL basta mudar o arquivo `app/database.py`.
- **Índices** em `categoria` e `status`, os campos mais usados nos filtros.

## Estrutura

```
app/
  main.py           # rotas da API e validação de entrada (Pydantic)
  classificador.py  # IA + regras de plano B
  database.py       # SQL e acesso ao SQLite
tests/              # pytest: classificador, banco e API
```

## Próximos passos

- Integrar com o **n8n** para receber mensagens do WhatsApp e do formulário do site automaticamente
- Painel simples para a equipe acompanhar os atendimentos
- Autenticação por chave de API

---

Feito por **Matheus Paulino** · [Portfólio](https://badolfr22-dot.github.io) · [LinkedIn](https://www.linkedin.com/in/matheus-paulino-a9a313444)
