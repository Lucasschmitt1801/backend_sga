# backend_sga/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import urllib.parse
import os # Importante para ler variáveis da nuvem

# 1. Tenta pegar a URL do banco da nuvem (Render/Railway)
DATABASE_URL = os.getenv("DATABASE_URL")

# 2. Se não tiver na nuvem, usa o seu local (Fallback)
if not DATABASE_URL:
    user = "postgres"
    password = urllib.parse.quote_plus("@Schmitt") # Sua senha local
    host = "localhost"
    db_name = "sga_db"
    DATABASE_URL = f"postgresql://{user}:{password}@{host}/{db_name}"

# 3. Correção para o Render (ele usa 'postgres://' antigo, o SQLAlchemy quer 'postgresql://')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()