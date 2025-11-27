from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- TOKENS ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenOutput(BaseModel):
    access_token: str
    token_type: str
    perfil: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

# --- USUÁRIOS ---
class UsuarioBase(BaseModel):
    email: str

class UsuarioCreate(UsuarioBase):
    nome: str
    senha: str
    perfil: str = "EXECUTOR" # ADMIN ou EXECUTOR

class UsuarioLogin(UsuarioBase):
    senha: str

# --- VEÍCULOS ---
class VeiculoBase(BaseModel):
    placa: str
    modelo: str
    cor: Optional[str] = None
    ano_fabricacao: Optional[int] = None
    chassi: Optional[str] = None

class VeiculoCreate(VeiculoBase):
    pass

class VeiculoResponse(VeiculoBase):
    id: int
    status: str
    class Config:
        orm_mode = True

# --- FOTOS ---
class FotoResponse(BaseModel):
    id: int
    tipo: str
    url_arquivo: str
    class Config:
        orm_mode = True

# --- ABASTECIMENTOS ---
class AbastecimentoBase(BaseModel):
    id_veiculo: int
    valor_total: float
    litros: Optional[float] = None
    nome_posto: Optional[str] = None
    quilometragem: Optional[int] = None
    gps_lat: Optional[float] = None
    gps_long: Optional[float] = None

class AbastecimentoCreate(AbastecimentoBase):
    pass

class AbastecimentoReview(BaseModel):
    status: str # APROVADO, REPROVADO
    justificativa: Optional[str] = None

class AbastecimentoResponse(AbastecimentoBase):
    id: int
    id_usuario: int
    data_hora: datetime
    status: str
    justificativa_revisao: Optional[str] = None
    fotos: List[FotoResponse] = []
    
    class Config:
        orm_mode = True