from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# Carrega as variáveis de ambiente
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ Erro: DATABASE_URL não encontrada no .env")
    exit()

# Ajuste para o Render (se necessário)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"🔌 Conectando ao banco...")
engine = create_engine(DATABASE_URL)

# Comandos SQL para atualizar a tabela
comandos_sql = [
    # Adiciona colunas novas na tabela VEICULOS
    "ALTER TABLE veiculos ADD COLUMN IF NOT EXISTS fabricante VARCHAR;",
    "ALTER TABLE veiculos ADD COLUMN IF NOT EXISTS ano_fabricacao INTEGER;",
    "ALTER TABLE veiculos ADD COLUMN IF NOT EXISTS cor VARCHAR;",
    "ALTER TABLE veiculos ADD COLUMN IF NOT EXISTS chassi VARCHAR;",
    "ALTER TABLE veiculos ADD COLUMN IF NOT EXISTS id_setor INTEGER;",
    "ALTER TABLE veiculos ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'ESTOQUE';",
    "ALTER TABLE veiculos ADD COLUMN IF NOT EXISTS data_venda TIMESTAMP;",
    
    # Cria a tabela SETORES se não existir
    """
    CREATE TABLE IF NOT EXISTS setores (
        id SERIAL PRIMARY KEY,
        nome VARCHAR NOT NULL UNIQUE
    );
    """
]

with engine.connect() as connection:
    for comando in comandos_sql:
        try:
            print(f"🔄 Executando: {comando[:40]}...")
            connection.execute(text(comando))
            connection.commit()
            print("✅ Sucesso!")
        except Exception as e:
            # Ignora erros se a coluna já existir
            print(f"⚠️ Aviso: {e}")

print("\n🚀 Banco de dados atualizado com sucesso!")