from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from database import get_db, engine
import models, schemas, auth
import shutil
import os
import uuid

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SGA - Sistema de Gestão de Abastecimento")

# CORS
origins = ["http://localhost:5173", "http://localhost:3000"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# FOTOS
os.makedirs("uploads", exist_ok=True)
app.mount("/fotos", StaticFiles(directory="uploads"), name="fotos")

# AUTH
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_usuario_atual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None: raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError: raise HTTPException(status_code=401, detail="Token inválido")
    user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if user is None: raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return user

# --- ROTAS ---

@app.post("/auth/login", response_model=schemas.TokenOutput)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.email == form_data.username).first()
    if not usuario or not auth.verificar_senha(form_data.password, usuario.senha_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha incorretos")
    token_acesso = auth.criar_token_acesso(data={"sub": usuario.email, "role": usuario.perfil})
    return {"access_token": token_acesso, "token_type": "bearer", "perfil": usuario.perfil}

@app.post("/veiculos/", response_model=schemas.VeiculoResponse)
def criar_veiculo(veiculo: schemas.VeiculoCreate, db: Session = Depends(get_db)):
    if db.query(models.Veiculo).filter(models.Veiculo.placa == veiculo.placa).first():
        raise HTTPException(status_code=400, detail="Veículo já existe")
    novo_veiculo = models.Veiculo(**veiculo.dict())
    db.add(novo_veiculo)
    db.commit()
    db.refresh(novo_veiculo)
    return novo_veiculo

@app.get("/veiculos/", response_model=list[schemas.VeiculoResponse])
def listar_veiculos(db: Session = Depends(get_db)):
    return db.query(models.Veiculo).all()

@app.post("/abastecimentos/", response_model=schemas.AbastecimentoResponse)
def registrar_abastecimento(dados: schemas.AbastecimentoCreate, db: Session = Depends(get_db), usuario_atual: models.Usuario = Depends(get_usuario_atual)):
    if not db.query(models.Veiculo).filter(models.Veiculo.id == dados.id_veiculo).first():
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    novo_abastecimento = models.Abastecimento(id_usuario=usuario_atual.id, **dados.dict(), status="PENDENTE_VALIDACAO")
    db.add(novo_abastecimento)
    db.commit()
    db.refresh(novo_abastecimento)
    return novo_abastecimento

@app.get("/abastecimentos/", response_model=list[schemas.AbastecimentoResponse])
def listar_abastecimentos(db: Session = Depends(get_db)): # Removi verificação de token pra facilitar teste
    return db.query(models.Abastecimento).all()

@app.post("/abastecimentos/{id_abastecimento}/fotos/")
def upload_foto(id_abastecimento: int, tipo_foto: str = Form(...), arquivo: UploadFile = File(...), db: Session = Depends(get_db)):
    abastecimento = db.query(models.Abastecimento).filter(models.Abastecimento.id == id_abastecimento).first()
    if not abastecimento: raise HTTPException(status_code=404, detail="Abastecimento não encontrado")
    extensao = arquivo.filename.split(".")[-1]
    nome_arquivo = f"{id_abastecimento}_{tipo_foto}_{uuid.uuid4().hex}.{extensao}"
    caminho_completo = f"uploads/{nome_arquivo}"
    with open(caminho_completo, "wb") as buffer: shutil.copyfileobj(arquivo.file, buffer)
    nova_foto = models.FotoAbastecimento(id_abastecimento=id_abastecimento, tipo=tipo_foto, url_arquivo=nome_arquivo)
    db.add(nova_foto)
    db.commit()
    return {"mensagem": "Sucesso", "url": f"/fotos/{nome_arquivo}"}

# ROTA DE AUDITORIA (NOVA)
@app.patch("/abastecimentos/{id_abastecimento}/revisar", response_model=schemas.AbastecimentoResponse)
def revisar_abastecimento(id_abastecimento: int, review: schemas.AbastecimentoReview, db: Session = Depends(get_db), usuario_atual: models.Usuario = Depends(get_usuario_atual)):
    abastecimento = db.query(models.Abastecimento).filter(models.Abastecimento.id == id_abastecimento).first()
    if not abastecimento: raise HTTPException(status_code=404, detail="Abastecimento não encontrado")
    abastecimento.status = review.status
    if review.justificativa:
        abastecimento.justificativa_revisao = review.justificativa
    db.commit()
    db.refresh(abastecimento)
    return abastecimento