# fix_abastecimento.py
from database import engine
from sqlalchemy import text

def corrigir_tabela():
    with engine.connect() as connection:
        try:
            # Adiciona a coluna 'justificativa_revisao' na tabela 'abastecimentos'
            comando = text("ALTER TABLE abastecimentos ADD COLUMN justificativa_revisao VARCHAR;")
            connection.execute(comando)
            connection.commit()
            print("✅ Coluna 'justificativa_revisao' adicionada com sucesso!")
        except Exception as e:
            print(f"❌ Erro (talvez a coluna já exista?): {e}")

if __name__ == "__main__":
    corrigir_tabela()