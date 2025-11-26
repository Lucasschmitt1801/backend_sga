from pydantic import BaseModel, EmailStr
from datetime import datetime

# --- LOGIN ---
class LoginInput(BaseModel):
    email: EmailStr
    senha: str

class TokenOutput(BaseModel):
    access_token: str
    token_type: str
    perfil: str

# --- VEÍCULOS ---
class VeiculoCreate(BaseModel):
    placa: str
    modelo: str
    chassi: str | None = None
    ano_fabricacao: int | None = None
    cor: str | None = None
    status: str = "PATIO"

class VeiculoResponse(VeiculoCreate):
    id: int
    class Config:
        from_attributes = True

# --- FOTOS ---
class FotoResponse(BaseModel):
    id: int
    url_arquivo: str
    tipo: str
    class Config:
        from_attributes = True

# --- ABASTECIMENTOS ---
class AbastecimentoCreate(BaseModel):
    id_veiculo: int
    valor_total: float
    quilometragem: int | None = None
    litros: float | None = None
    nome_posto: str | None = None
    gps_lat: float | None = None
    gps_long: float | None = None

# O que o Admin envia para Aprovar/Reprovar
class AbastecimentoReview(BaseModel):
    status: str 
    justificativa: str | None = None

class AbastecimentoResponse(AbastecimentoCreate):
    id: int
    data_hora: datetime
    status: str
    id_usuario: int
    justificativa_revisao: str | None = None
    fotos: list[FotoResponse] = [] 

    class Config:
        from_attributes = True