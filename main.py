from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from database import get_db, engine
from dotenv import load_dotenv
import models, schemas, auth
import shutil
import storage_client
import re
import os
import uuid
import ocr_service
from datetime import datetime, timedelta

# Carrega variáveis de ambiente
load_dotenv()

# Cria as tabelas no banco se não existirem
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SGA - Sistema de Gestão de Abastecimento")

# Configuração de CORS (Permite acesso do Frontend)
origins = ["*"] 
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração de Pasta de Uploads Temporários
os.makedirs("uploads", exist_ok=True)
app.mount("/fotos", StaticFiles(directory="uploads"), name="fotos")

# Segurança (OAuth2)
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

# --- ROTAS DE AUTENTICAÇÃO ---

@app.post("/auth/login", response_model=schemas.TokenOutput)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.email == form_data.username).first()
    if not usuario or not auth.verificar_senha(form_data.password, usuario.senha_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha incorretos")
    token_acesso = auth.criar_token_acesso(data={"sub": usuario.email, "role": usuario.perfil})
    return {"access_token": token_acesso, "token_type": "bearer", "perfil": usuario.perfil}

# --- ROTAS DE SETORES ---

@app.post("/setores/", response_model=schemas.SetorResponse)
def criar_setor(setor: schemas.SetorCreate, db: Session = Depends(get_db), usuario_atual: models.Usuario = Depends(get_usuario_atual)):
    if usuario_atual.perfil != "ADMIN": raise HTTPException(403, detail="Apenas Admin pode criar setores")
    
    if db.query(models.Setor).filter(models.Setor.nome == setor.nome).first():
        raise HTTPException(400, detail="Setor já existe")
    
    novo = models.Setor(nome=setor.nome)
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo

@app.get("/setores/", response_model=list[schemas.SetorResponse])
def listar_setores(db: Session = Depends(get_db)):
    return db.query(models.Setor).all()

@app.delete("/setores/{id}")
def deletar_setor(id: int, db: Session = Depends(get_db), usuario_atual: models.Usuario = Depends(get_usuario_atual)):
    if usuario_atual.perfil != "ADMIN": raise HTTPException(403, detail="Apenas Admin pode excluir setores")
    
    s = db.query(models.Setor).filter(models.Setor.id == id).first()
    if not s: raise HTTPException(404, detail="Setor não encontrado")
    
    db.delete(s)
    db.commit()
    return {"mensagem": "Deletado"}

# --- ROTAS DE VEÍCULOS (ATUALIZADA COM VALIDAÇÕES) ---

@app.get("/veiculos/", response_model=list[schemas.VeiculoResponse])
def listar_veiculos(db: Session = Depends(get_db)):
    # Limpeza automática: Apaga carros vendidos há mais de 48h
    limite = datetime.utcnow() - timedelta(hours=48)
    expirados = db.query(models.Veiculo).filter(
        models.Veiculo.status == "VENDIDO",
        models.Veiculo.data_venda < limite
    ).all()
    
    if expirados:
        for c in expirados:
            print(f"🗑️ Limpeza Automática: Removendo {c.placa} (Vendido +48h)")
            db.delete(c)
        db.commit()

    return db.query(models.Veiculo).all()

@app.post("/veiculos/", response_model=schemas.VeiculoResponse)
def criar_veiculo(veiculo: schemas.VeiculoCreate, db: Session = Depends(get_db)):
    # 1. Verifica Placa Duplicada
    if db.query(models.Veiculo).filter(models.Veiculo.placa == veiculo.placa).first():
        raise HTTPException(status_code=400, detail="Erro: Esta PLACA já está cadastrada.")
    
    # 2. Verifica Chassi Duplicado (apenas se foi informado)
    if veiculo.chassi:
        if db.query(models.Veiculo).filter(models.Veiculo.chassi == veiculo.chassi).first():
            raise HTTPException(status_code=400, detail="Erro: Este CHASSI já está cadastrado.")
    
    novo = models.Veiculo(**veiculo.dict())
    if novo.status == "VENDIDO": 
        novo.data_venda = datetime.utcnow()
        
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo

@app.put("/veiculos/{veiculo_id}", response_model=schemas.VeiculoResponse)
def atualizar_veiculo(veiculo_id: int, dados: schemas.VeiculoUpdate, db: Session = Depends(get_db)):
    veiculo = db.query(models.Veiculo).filter(models.Veiculo.id == veiculo_id).first()
    if not veiculo: 
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    
    # Atualiza campos básicos
    if dados.modelo: veiculo.modelo = dados.modelo
    if dados.fabricante: veiculo.fabricante = dados.fabricante
    if dados.cor: veiculo.cor = dados.cor
    if dados.id_setor: veiculo.id_setor = dados.id_setor
    
    # Verifica Chassi na edição (se mudou e já existe em outro carro)
    if dados.chassi and dados.chassi != veiculo.chassi:
        if db.query(models.Veiculo).filter(models.Veiculo.chassi == dados.chassi).first():
            raise HTTPException(status_code=400, detail="Erro: Este CHASSI já pertence a outro veículo.")
        veiculo.chassi = dados.chassi

    # Regra de Status e Data de Venda
    if dados.status:
        veiculo.status = dados.status
        if dados.status == "VENDIDO":
            veiculo.data_venda = datetime.utcnow() # Inicia contagem de 48h
        else:
            veiculo.data_venda = None # Cancela contagem se voltou pro estoque
            
    db.commit()
    db.refresh(veiculo)
    return veiculo

@app.delete("/veiculos/{veiculo_id}")
def deletar_veiculo(veiculo_id: int, db: Session = Depends(get_db)):
    veiculo = db.query(models.Veiculo).filter(models.Veiculo.id == veiculo_id).first()
    if not veiculo: raise HTTPException(status_code=404, detail="Veículo não encontrado")
    db.delete(veiculo)
    db.commit()
    return {"mensagem": "Veículo removido"}

# --- ROTAS DE INTELIGÊNCIA ARTIFICIAL (IA) ---

def limpar_placa(texto): return texto.replace("-", "").replace(" ", "").upper()

@app.post("/identificar_veiculo/", response_model=schemas.VeiculoResponse)
def identificar_veiculo(arquivo: UploadFile = File(...), db: Session = Depends(get_db), usuario_atual: models.Usuario = Depends(get_usuario_atual)):
    extensao = arquivo.filename.split(".")[-1]
    nome_arquivo = f"temp_search_{uuid.uuid4().hex}.{extensao}"
    caminho = f"uploads/{nome_arquivo}"
    with open(caminho, "wb") as b: shutil.copyfileobj(arquivo.file, b)

    texto_ocr = ocr_service.ler_texto_imagem(caminho)
    if os.path.exists(caminho): os.remove(caminho) 
    if not texto_ocr: raise HTTPException(status_code=404, detail="Placa ilegível")

    padrao = re.compile(r'[A-Z]{3}[0-9][0-9A-Z][0-9]{2}')
    match = padrao.search(limpar_placa(texto_ocr))
    candidata = match.group(0) if match else limpar_placa(texto_ocr)

    veiculo = db.query(models.Veiculo).filter(models.Veiculo.placa == candidata).first()
    
    # BLOQUEIO IA: Não identificar se estiver vendido
    if veiculo: 
        if veiculo.status == "VENDIDO":
             raise HTTPException(status_code=400, detail="BLOQUEADO: Veículo consta como VENDIDO.")
        return veiculo
    
    for v in db.query(models.Veiculo).all():
        if limpar_placa(v.placa) in limpar_placa(texto_ocr): 
             if v.status == "VENDIDO":
                 raise HTTPException(status_code=400, detail="BLOQUEADO: Veículo consta como VENDIDO.")
             return v
    
    raise HTTPException(status_code=404, detail="Veículo não encontrado na frota.")

@app.post("/assistente/ler_km/")
def assistente_ler_km(arquivo: UploadFile = File(...), db: Session = Depends(get_db), usuario_atual: models.Usuario = Depends(get_usuario_atual)):
    extensao = arquivo.filename.split(".")[-1]
    nome = f"temp_km_{uuid.uuid4().hex}.{extensao}"
    caminho = f"uploads/{nome}"
    with open(caminho, "wb") as b: shutil.copyfileobj(arquivo.file, b)
    try: km = ocr_service.ler_km_imagem(caminho)
    finally: 
        if os.path.exists(caminho): os.remove(caminho)
    if km is None: raise HTTPException(404, detail="Nenhum número de KM encontrado.")
    return {"km": km}

# --- ROTAS DE ABASTECIMENTOS ---

@app.post("/abastecimentos/", response_model=schemas.AbastecimentoResponse)
def registrar_abastecimento(dados: schemas.AbastecimentoCreate, db: Session = Depends(get_db), usuario_atual: models.Usuario = Depends(get_usuario_atual)):
    veiculo = db.query(models.Veiculo).filter(models.Veiculo.id == dados.id_veiculo).first()
    
    if not veiculo: raise HTTPException(404, detail="Veículo não encontrado")
    
    # BLOQUEIO: Se status for VENDIDO, rejeita o abastecimento manual
    if veiculo.status == "VENDIDO":
        raise HTTPException(status_code=400, detail="BLOQUEADO: Veículo VENDIDO não pode abastecer.")
    
    novo = models.Abastecimento(id_usuario=usuario_atual.id, **dados.dict(), status="PENDENTE_VALIDACAO")
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo

@app.get("/abastecimentos/", response_model=list[schemas.AbastecimentoResponse])
def listar_abastecimentos(db: Session = Depends(get_db)):
    return db.query(models.Abastecimento).order_by(models.Abastecimento.data_hora.desc()).all()

@app.patch("/abastecimentos/{id_abastecimento}/revisar", response_model=schemas.AbastecimentoResponse)
def revisar(id_abastecimento: int, review: schemas.AbastecimentoReview, db: Session = Depends(get_db), usuario_atual: models.Usuario = Depends(get_usuario_atual)):
    abastecimento = db.query(models.Abastecimento).filter(models.Abastecimento.id == id_abastecimento).first()
    if not abastecimento: raise HTTPException(404, detail="Abastecimento não encontrado")
    abastecimento.status = review.status
    if review.justificativa: abastecimento.justificativa_revisao = review.justificativa
    db.commit()
    return abastecimento

@app.post("/abastecimentos/{id_abastecimento}/fotos/")
def upload_foto(id_abastecimento: int, tipo_foto: str = Form(...), arquivo: UploadFile = File(...), db: Session = Depends(get_db), usuario_atual: models.Usuario = Depends(get_usuario_atual)):
    abastecimento = db.query(models.Abastecimento).filter(models.Abastecimento.id == id_abastecimento).first()
    if not abastecimento: raise HTTPException(404, detail="Abastecimento não encontrado")

    extensao = arquivo.filename.split(".")[-1]
    nome = f"{id_abastecimento}_{tipo_foto}_{uuid.uuid4().hex}.{extensao}"
    caminho = f"uploads/{nome}"
    with open(caminho, "wb") as b: shutil.copyfileobj(arquivo.file, b)

    alerta = ""
    try:
        if tipo_foto == "PLACA":
            txt = ocr_service.ler_texto_imagem(caminho)
            v = db.query(models.Veiculo).filter(models.Veiculo.id == abastecimento.id_veiculo).first()
            if txt and v.placa.replace("-","") not in txt.replace("-",""): alerta = "Alerta: Placa divergente na foto."
        elif tipo_foto == "PAINEL":
            km = ocr_service.ler_km_imagem(caminho)
            if km and abastecimento.quilometragem and km < abastecimento.quilometragem: alerta = f"Alerta: KM Foto ({km}) < Input ({abastecimento.quilometragem})"
        
        if alerta:
            abastecimento.justificativa_revisao = (abastecimento.justificativa_revisao or "") + " " + alerta
            db.add(abastecimento)

        with open(caminho, "rb") as f: bytes_arq = f.read()
        url = storage_client.upload_arquivo(bytes_arq, nome, arquivo.content_type)
        
        nova = models.FotoAbastecimento(id_abastecimento=id_abastecimento, tipo=tipo_foto, url_arquivo=url)
        db.add(nova)
        db.commit()
        
        if os.path.exists(caminho): os.remove(caminho)
        return {"mensagem": "Sucesso", "url": url, "analise": alerta}
    except Exception as e:
        if os.path.exists(caminho): os.remove(caminho)
        raise HTTPException(500, detail=str(e))

# --- ROTAS DE USUÁRIOS ---

@app.post("/usuarios/", response_model=schemas.TokenOutput)
def criar_usuario(novo: schemas.UsuarioCreate, db: Session = Depends(get_db), usuario_atual: models.Usuario = Depends(get_usuario_atual)):
    if usuario_atual.perfil != "ADMIN": raise HTTPException(403, detail="Acesso negado")
    if db.query(models.Usuario).filter(models.Usuario.email == novo.email).first(): raise HTTPException(400, detail="Email já cadastrado")
    
    user = models.Usuario(nome=novo.nome, email=novo.email, senha_hash=auth.get_password_hash(novo.senha), perfil=novo.perfil)
    db.add(user)
    db.commit()
    return {"access_token": "", "token_type": "", "perfil": user.perfil}

@app.get("/usuarios/")
def listar_usuarios(db: Session = Depends(get_db), usuario_atual: models.Usuario = Depends(get_usuario_atual)):
    if usuario_atual.perfil != "ADMIN": raise HTTPException(403, detail="Acesso negado")
    return [{"id": u.id, "nome": u.nome, "email": u.email, "perfil": u.perfil} for u in db.query(models.Usuario).all()]

@app.delete("/usuarios/{uid}")
def deletar_usuario(uid: int, db: Session = Depends(get_db), usuario_atual: models.Usuario = Depends(get_usuario_atual)):
    if usuario_atual.perfil != "ADMIN": raise HTTPException(403, detail="Acesso negado")
    u = db.query(models.Usuario).filter(models.Usuario.id == uid).first()
    if u: 
        db.delete(u)
        db.commit()
    return {"msg": "Deletado"}