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
import ocr_service # Importa o módulo da IA

# Cria tabelas
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SGA - Sistema de Gestão de Abastecimento")

# Configuração CORS (Para o Site e App funcionarem)
origins = ["*"] # Permite todos para facilitar o teste com App
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração de Fotos
os.makedirs("uploads", exist_ok=True)
app.mount("/fotos", StaticFiles(directory="uploads"), name="fotos")

# Configuração de Segurança
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
    novo = models.Veiculo(**veiculo.dict())
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo

@app.get("/veiculos/", response_model=list[schemas.VeiculoResponse])
def listar_veiculos(db: Session = Depends(get_db)):
    return db.query(models.Veiculo).all()

@app.post("/abastecimentos/", response_model=schemas.AbastecimentoResponse)
def registrar_abastecimento(dados: schemas.AbastecimentoCreate, db: Session = Depends(get_db), usuario_atual: models.Usuario = Depends(get_usuario_atual)):
    if not db.query(models.Veiculo).filter(models.Veiculo.id == dados.id_veiculo).first():
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    
    novo_abastecimento = models.Abastecimento(
        id_usuario=usuario_atual.id,
        id_veiculo=dados.id_veiculo,
        valor_total=dados.valor_total,
        litros=dados.litros,
        nome_posto=dados.nome_posto,
        status="PENDENTE_VALIDACAO",
        # --- SALVAR GPS ---
        gps_lat=dados.gps_lat,
        gps_long=dados.gps_long
    )
    db.add(novo_abastecimento)
    db.commit()
    db.refresh(novo_abastecimento)
    return novo_abastecimento

@app.get("/abastecimentos/", response_model=list[schemas.AbastecimentoResponse])
def listar_abastecimentos(db: Session = Depends(get_db)):
    # Traz os dados e ordena por data (mais recente primeiro)
    return db.query(models.Abastecimento).order_by(models.Abastecimento.data_hora.desc()).all()

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
# ... (imports anteriores)

# --- ROTA NOVA: IDENTIFICAR VEÍCULO POR FOTO (IA) ---
@app.post("/identificar_veiculo/", response_model=schemas.VeiculoResponse)
def identificar_veiculo(
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    # 1. Salva a foto temporariamente
    extensao = arquivo.filename.split(".")[-1]
    nome_arquivo = f"temp_search_{uuid.uuid4().hex}.{extensao}"
    caminho_completo = f"uploads/{nome_arquivo}"

    with open(caminho_completo, "wb") as buffer:
        shutil.copyfileobj(arquivo.file, buffer)

    # 2. Chama a IA para ler o texto
    print(f"🔍 Buscando veículo na foto: {nome_arquivo}")
    texto_ia = ocr_service.ler_texto_imagem(caminho_completo)
    
    # Remove o arquivo temporário para não encher o servidor
    os.remove(caminho_completo)

    if not texto_ia:
        raise HTTPException(status_code=404, detail="Não foi possível ler a placa na imagem.")

    print(f"🤖 Texto encontrado: {texto_ia}")

    # 3. Procura no Banco de Dados
    # Vamos limpar o texto da IA (remover espaços/hifens) para comparar
    texto_limpo = texto_ia.replace("-", "").replace(" ", "").upper()

    # Pega todos os veículos ativos
    todos_veiculos = db.query(models.Veiculo).all()

    veiculo_encontrado = None
    for veiculo in todos_veiculos:
        placa_limpa = veiculo.placa.replace("-", "").replace(" ", "").upper()
        
        # Se a placa do carro estiver DENTRO do texto que a IA leu
        if placa_limpa in texto_limpo:
            veiculo_encontrado = veiculo
            break
    
    if veiculo_encontrado:
        return veiculo_encontrado
    else:
        raise HTTPException(status_code=404, detail="Nenhum veículo cadastrado foi encontrado nesta foto.")
# --- ROTA DE UPLOAD COM INTELIGÊNCIA ARTIFICIAL ---
@app.post("/abastecimentos/{id_abastecimento}/fotos/")
def upload_foto(
    id_abastecimento: int,
    tipo_foto: str = Form(...),
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    abastecimento = db.query(models.Abastecimento).filter(models.Abastecimento.id == id_abastecimento).first()
    if not abastecimento: raise HTTPException(status_code=404, detail="Abastecimento não encontrado")

    # 1. Salva o arquivo
    extensao = arquivo.filename.split(".")[-1]
    nome_arquivo = f"{id_abastecimento}_{tipo_foto}_{uuid.uuid4().hex}.{extensao}"
    caminho_completo = f"uploads/{nome_arquivo}"

    with open(caminho_completo, "wb") as buffer:
        shutil.copyfileobj(arquivo.file, buffer)

    # 2. CHAMA A IA SE FOR FOTO DA PLACA 🤖
    if tipo_foto == "PLACA":
        print(f"🔍 IA Analisando: {nome_arquivo}")
        texto_ia = ocr_service.ler_texto_imagem(caminho_completo)
        
        if texto_ia:
            print(f"🤖 IA Leu: {texto_ia}")
            
            # Busca a placa original do carro
            veiculo = db.query(models.Veiculo).filter(models.Veiculo.id == abastecimento.id_veiculo).first()
            placa_real = veiculo.placa.upper().replace("-", "").replace(" ", "")
            
            # Compara
            if placa_real in texto_ia:
                print("✅ Placa Validada!")
                # Poderíamos auto-aprovar aqui, mas vamos só logar por enquanto
            else:
                print("❌ Placa Divergente!")
                abastecimento.justificativa_revisao = f"[ALERTA IA] Placa lida '{texto_ia}' difere de '{placa_real}'"
                db.add(abastecimento)
                db.commit()

    # 3. Registra a foto no banco
    nova_foto = models.FotoAbastecimento(id_abastecimento=id_abastecimento, tipo=tipo_foto, url_arquivo=nome_arquivo)
    db.add(nova_foto)
    db.commit()
    
    return {"mensagem": "Sucesso", "url": f"/fotos/{nome_arquivo}"}