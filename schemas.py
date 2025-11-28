from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- SETORES (NOVO) ---
class SetorBase(BaseModel):
    nome: str

class SetorCreate(SetorBase):
    pass

class SetorResponse(SetorBase):
    id: int
    class Config:
        orm_mode = True

# --- TOKENS ---
class TokenOutput(BaseModel):
    access_token: str
    token_type: str
    perfil: str

# --- USUÁRIOS ---
class UsuarioCreate(BaseModel):
    nome: str
    email: str
    senha: str
    perfil: str = "EXECUTOR"
    cargo: Optional[str] = None
    setor: Optional[str] = None

# --- VEÍCULOS ---
class VeiculoBase(BaseModel):
    placa: str
    modelo: str
    fabricante: Optional[str] = None
    cor: Optional[str] = None
    ano_fabricacao: Optional[int] = None
    chassi: Optional[str] = None
    id_setor: Optional[int] = None
    status: str = "ESTOQUE"

class VeiculoCreate(VeiculoBase):
    pass

class VeiculoUpdate(BaseModel):
    modelo: Optional[str] = None
    fabricante: Optional[str] = None
    cor: Optional[str] = None
    status: Optional[str] = None
    id_setor: Optional[int] = None
    chassi: Optional[str] = None

class VeiculoResponse(VeiculoBase):
    id: int
    class Config:
        orm_mode = True

# --- ABASTECIMENTOS ---
class AbastecimentoCreate(BaseModel):
    id_veiculo: int
    valor_total: float
    litros: Optional[float] = None
    nome_posto: Optional[str] = None
    quilometragem: Optional[int] = None
    gps_lat: Optional[float] = None
    gps_long: Optional[float] = None

class AbastecimentoReview(BaseModel):
    status: str
    justificativa: Optional[str] = None

class FotoResponse(BaseModel):
    id: int
    tipo: str
    url_arquivo: str
    class Config:
        orm_mode = True

class AbastecimentoResponse(AbastecimentoCreate):
    id: int
    id_usuario: int
    data_hora: datetime
    status: str
    justificativa_revisao: Optional[str] = None
    fotos: List[FotoResponse] = []
    class Config:
        orm_mode = True