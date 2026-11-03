"""API de triagem de mensagens de clientes com IA."""

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from app import database
from app.classificador import classificar

Categoria = Literal["agendamento", "orcamento", "reclamacao", "duvida", "outro"]
Urgencia = Literal["baixa", "media", "alta"]
Status = Literal["aberta", "em_andamento", "resolvida"]


class NovaMensagem(BaseModel):
    cliente: str = Field(..., min_length=1, max_length=100, examples=["Ana Souza"])
    canal: Literal["whatsapp", "site", "email", "instagram"] = "site"
    texto: str = Field(..., min_length=3, max_length=2000,
                       examples=["Quero agendar um corte para sábado de manhã"])


class Mensagem(BaseModel):
    id: int
    cliente: str
    canal: str
    texto: str
    categoria: Categoria
    urgencia: Urgencia
    resumo: str
    classificado_por: Literal["ia", "regras"]
    status: Status
    criado_em: str


class MudarStatus(BaseModel):
    status: Status


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    database.criar_tabelas()
    yield


app = FastAPI(
    title="Triagem IA API",
    description="Recebe mensagens de clientes, classifica com IA e organiza o atendimento.",
    version="1.0.0",
    lifespan=ciclo_de_vida,
)


@app.get("/saude", tags=["infra"])
def saude():
    return {"status": "ok"}


@app.post("/mensagens", response_model=Mensagem, status_code=201, tags=["mensagens"])
def criar_mensagem(entrada: NovaMensagem):
    resultado = classificar(entrada.texto)
    return database.inserir_mensagem({**entrada.model_dump(), **resultado})


@app.get("/mensagens", response_model=list[Mensagem], tags=["mensagens"])
def listar(
    categoria: Categoria | None = None,
    urgencia: Urgencia | None = None,
    status: Status | None = None,
    limite: int = Query(50, ge=1, le=200),
):
    return database.listar_mensagens(categoria, urgencia, status, limite)


@app.get("/mensagens/{mensagem_id}", response_model=Mensagem, tags=["mensagens"])
def detalhar(mensagem_id: int):
    mensagem = database.buscar_mensagem(mensagem_id)
    if not mensagem:
        raise HTTPException(status_code=404, detail="Mensagem não encontrada")
    return mensagem


@app.patch("/mensagens/{mensagem_id}/status", response_model=Mensagem, tags=["mensagens"])
def mudar_status(mensagem_id: int, entrada: MudarStatus):
    if not database.buscar_mensagem(mensagem_id):
        raise HTTPException(status_code=404, detail="Mensagem não encontrada")
    return database.atualizar_status(mensagem_id, entrada.status)


@app.get("/relatorio", tags=["relatorios"])
def relatorio():
    return database.gerar_relatorio()
