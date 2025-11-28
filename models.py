from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from database import Base
import datetime

# --- TABELA NOVA: SETORES ---
class Setor(Base):
    __tablename__ = "setores"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, nullable=False)

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    perfil = Column(String, default="EXECUTOR") 
    ativo = Column(Boolean, default=True)
    id_setor = Column(Integer, nullable=True)

class Veiculo(Base):
    __tablename__ = "veiculos"
    id = Column(Integer, primary_key=True, index=True)
    placa = Column(String, unique=True, index=True, nullable=False)
    modelo = Column(String, nullable=False)
    
    # CAMPOS NOVOS E ANTIGOS
    fabricante = Column(String, nullable=True)
    ano_fabricacao = Column(Integer, nullable=True)
    cor = Column(String, nullable=True)
    chassi = Column(String, nullable=True)
    id_setor = Column(Integer, nullable=True)
    
    # LÓGICA DE VENDAS
    status = Column(String, default="ESTOQUE") 
    data_venda = Column(DateTime, nullable=True)

class Abastecimento(Base):
    __tablename__ = "abastecimentos"
    id = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id"))
    id_veiculo = Column(Integer, ForeignKey("veiculos.id"))
    data_hora = Column(DateTime, default=datetime.datetime.utcnow)
    valor_total = Column(Float, nullable=False)
    litros = Column(Float, nullable=True)
    nome_posto = Column(String, nullable=True)
    status = Column(String, default="PENDENTE_VALIDACAO") 
    justificativa_revisao = Column(String, nullable=True)
    gps_lat = Column(Float, nullable=True)
    gps_long = Column(Float, nullable=True)
    quilometragem = Column(Integer, nullable=True)
    
    usuario = relationship("Usuario")
    veiculo = relationship("Veiculo")
    fotos = relationship("FotoAbastecimento", back_populates="abastecimento")

class FotoAbastecimento(Base):
    __tablename__ = "fotos_abastecimento"
    id = Column(Integer, primary_key=True, index=True)
    id_abastecimento = Column(Integer, ForeignKey("abastecimentos.id"))
    tipo = Column(String) 
    url_arquivo = Column(String) 
    abastecimento = relationship("Abastecimento", back_populates="fotos")