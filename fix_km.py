from database import engine
from sqlalchemy import text

def adicionar_km():
    with engine.connect() as connection:
        try:
            # Adiciona coluna de Quilometragem
            connection.execute(text("ALTER TABLE abastecimentos ADD COLUMN quilometragem INTEGER;"))
            connection.commit()
            print("✅ Coluna 'quilometragem' adicionada com sucesso!")
        except Exception as e:
            print(f"⚠️ Erro (talvez já exista): {e}")

if __name__ == "__main__":
    adicionar_km()