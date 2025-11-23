# fix_db.py
from database import engine
from sqlalchemy import text

def corrigir_tabela():
    with engine.connect() as connection:
        try:
            # O comando SQL que adiciona a coluna que falta
            comando = text("ALTER TABLE usuarios ADD COLUMN id_setor INTEGER;")
            connection.execute(comando)
            connection.commit()
            print("✅ Coluna 'id_setor' adicionada com sucesso!")
        except Exception as e:
            print(f"❌ Erro (talvez a coluna já exista?): {e}")

if __name__ == "__main__":
    corrigir_tabela()