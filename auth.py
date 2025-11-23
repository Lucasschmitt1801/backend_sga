# auth.py
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

# CONFIGURAÇÕES (Em produção, isto vem de variáveis de ambiente .env)
SECRET_KEY = "sua_chave_secreta_super_dificil" # Troque isto!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # Token dura 24 horas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Função para verificar se a senha batida corresponde ao hash no banco
def verificar_senha(senha_pura, senha_hash):
    return pwd_context.verify(senha_pura, senha_hash)

# Função para gerar o hash (usada no seed_admin.py)
def get_password_hash(senha):
    return pwd_context.hash(senha)

# Função para criar o Token JWT
def criar_token_acesso(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt