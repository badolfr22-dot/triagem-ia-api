"""Classificação de mensagens de clientes.

Dois modos:
- Com a variável ANTHROPIC_API_KEY definida, usa a IA (Claude) para entender
  o texto e devolver categoria, urgência e um resumo curto.
- Sem a chave (ou se a IA falhar), usa regras por palavras-chave. Assim o
  sistema nunca para de funcionar e os testes rodam sem custo.
"""

import json
import os
import unicodedata

CATEGORIAS = ["agendamento", "orcamento", "reclamacao", "duvida", "outro"]
URGENCIAS = ["baixa", "media", "alta"]

MODELO_PADRAO = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5")

PROMPT = """Você faz a triagem de mensagens que clientes enviam para um pequeno negócio.
Leia a mensagem e responda SOMENTE com um JSON neste formato:
{{"categoria": "...", "urgencia": "...", "resumo": "..."}}

Regras:
- categoria: uma de {categorias}
- urgencia: uma de {urgencias} ("alta" para reclamações graves, cobranças indevidas ou prazos de hoje)
- resumo: uma frase de até 20 palavras, em português, sem inventar informação

Mensagem do cliente:
\"\"\"{texto}\"\"\"
"""

PALAVRAS_CHAVE = {
    "reclamacao": ["reclam", "pessim", "horrivel", "absurdo", "nao funciona", "quebrou",
                   "atras", "cobrado errado", "cobranca indevida", "devolu", "reembolso", "procon"],
    "agendamento": ["agendar", "agenda", "marcar", "horario", "disponibilidade", "remarcar", "desmarcar"],
    "orcamento": ["orcamento", "quanto custa", "preco", "valor", "cotacao", "tabela"],
    "duvida": ["duvida", "como funciona", "voces fazem", "aceita", "onde fica", "funciona"],
}

PALAVRAS_URGENTES = ["urgente", "hoje", "agora", "imediat", "procon", "advogado", "cobrado errado",
                     "cobranca indevida", "nao funciona", "absurdo"]


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


def classificar_por_regras(texto: str) -> dict:
    normalizado = _normalizar(texto)

    categoria = "outro"
    for nome, palavras in PALAVRAS_CHAVE.items():  # ordem do dicionário = prioridade
        if any(p in normalizado for p in palavras):
            categoria = nome
            break

    if any(p in normalizado for p in PALAVRAS_URGENTES):
        urgencia = "alta"
    elif categoria in ("reclamacao", "agendamento"):
        urgencia = "media"
    else:
        urgencia = "baixa"

    resumo = " ".join(texto.split())
    if len(resumo) > 120:
        resumo = resumo[:117].rstrip() + "..."

    return {"categoria": categoria, "urgencia": urgencia, "resumo": resumo,
            "classificado_por": "regras"}


def _validar_resposta_ia(bruto: str) -> dict:
    inicio, fim = bruto.find("{"), bruto.rfind("}")
    dados = json.loads(bruto[inicio:fim + 1])
    if dados.get("categoria") not in CATEGORIAS or dados.get("urgencia") not in URGENCIAS:
        raise ValueError(f"Resposta fora do padrão: {dados}")
    resumo = str(dados.get("resumo", "")).strip()
    if not resumo:
        raise ValueError("Resumo vazio")
    return {"categoria": dados["categoria"], "urgencia": dados["urgencia"],
            "resumo": resumo, "classificado_por": "ia"}


def classificar_com_ia(texto: str, cliente_ia=None) -> dict:
    if cliente_ia is None:
        import anthropic  # importado só quando necessário

        cliente_ia = anthropic.Anthropic()

    resposta = cliente_ia.messages.create(
        model=MODELO_PADRAO,
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": PROMPT.format(categorias=CATEGORIAS, urgencias=URGENCIAS, texto=texto),
        }],
    )
    return _validar_resposta_ia(resposta.content[0].text)


def classificar(texto: str, cliente_ia=None) -> dict:
    """Tenta a IA; se não houver chave ou der erro, cai para as regras."""
    if cliente_ia is not None or os.getenv("ANTHROPIC_API_KEY"):
        try:
            return classificar_com_ia(texto, cliente_ia)
        except Exception:
            pass
    return classificar_por_regras(texto)
