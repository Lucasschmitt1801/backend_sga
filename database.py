from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import urllib.parse
import os

# Tenta pegar a URL da nuvem
DATABASE_URL = os.getenv("DATABASE_URL")

# Se não tiver na nuvem (ou for vazio), usa o local
if not DATABASE_URL:
    print("⚠️ AVISO: Usando Banco de Dados LOCAL (localhost)")
    user = "postgres"
    password = urllib.parse.quote_plus("@Schmitt")
    host = "localhost"
    db_name = "sga_db"
    DATABASE_URL = f"postgresql://{user}:{password}@{host}/{db_name}"
else:
    print("✅ Usando Banco de Dados da NUVEM")
    # Correção para o Render (postgres:// -> postgresql://)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Cria a engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()