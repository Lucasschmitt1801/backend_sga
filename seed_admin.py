# seed_admin.py
from database import SessionLocal, engine
from models import Base, Usuario # Vamos assumir que você já criou o models.py com a classe Usuario
from passlib.context import CryptContext

# Configuração de Hashing de senha (segurança)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def criar_admin_inicial():
    db = SessionLocal()
    
    # 1. Verifica se já existe alguém (para não criar duplicado)
    usuario_existente = db.query(Usuario).filter(Usuario.email == "admin@sga.com").first()
    if usuario_existente:
        print("Admin já existe!")
        return

    # 2. Cria o Hash da senha
    senha_pura = "admin123" # A senha que você vai digitar no login
    senha_hash = pwd_context.hash(senha_pura)

    # 3. Cria o objeto Usuário
    novo_admin = Usuario(
        nome="Administrador Mestre",
        email="admin@sga.com",
        senha_hash=senha_hash,
        perfil="ADMIN",
        id_setor=None # Admin geral não tem setor fixo
    )

    # 4. Salva no banco
    db.add(novo_admin)
    db.commit()
    print("✅ Admin criado com sucesso! Login: admin@sga.com / Senha: admin123")
    db.close()

if __name__ == "__main__":
    # Garante que as tabelas existem antes de inserir
    # Base.metadata.create_all(bind=engine) 
    criar_admin_inicial()