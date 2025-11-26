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
```

2.  **Rode o script apontando para a Nuvem:**
    No PowerShell (`backend_sga`), rode aquele comando mágico (com o link do Render):
    ```powershell
    $env:DATABASE_URL = "SUA_EXTERNAL_URL_DO_RENDER"; python fix_km.py