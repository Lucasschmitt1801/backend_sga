from database import engine
from sqlalchemy import text

def adicionar_gps():
    with engine.connect() as connection:
        try:
            # Adiciona colunas de Latitude e Longitude
            connection.execute(text("ALTER TABLE abastecimentos ADD COLUMN gps_lat FLOAT;"))
            connection.execute(text("ALTER TABLE abastecimentos ADD COLUMN gps_long FLOAT;"))
            connection.commit()
            print("✅ Colunas de GPS adicionadas com sucesso!")
        except Exception as e:
            print(f"⚠️ Erro (talvez já existam): {e}")

if __name__ == "__main__":
    adicionar_gps()