from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from database import get_db, engine
import models, schemas, auth
import shutil
import storage_client
import re
import os
import uuid
import ocr_service 

# Cria tabelas
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SGA - Sistema de Gestão de Abastecimento")

# Configuração CORS 
origins = ["*"] 
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

# IDENTIFICAR VEÍCULO (IA)
# Função auxiliar para padronizar o texto (Remove traços e espaços)
def limpar_placa(texto):
    return texto.replace("-", "").replace(" ", "").upper()

@app.post("/identificar_veiculo/", response_model=schemas.VeiculoResponse)
def identificar_veiculo(
    arquivo: UploadFile = File(...), 
    db: Session = Depends(get_db), 
    usuario_atual: models.Usuario = Depends(get_usuario_atual)
):
    # 1. Salvar arquivo temporariamente
    extensao = arquivo.filename.split(".")[-1]
    nome_arquivo = f"temp_search_{uuid.uuid4().hex}.{extensao}"
    caminho_completo = f"uploads/{nome_arquivo}"
    
    with open(caminho_completo, "wb") as buffer:
        shutil.copyfileobj(arquivo.file, buffer)

    print(f"🔍 Buscando veículo na foto: {nome_arquivo}")
    
    # 2. Ler OCR
    texto_ocr = ocr_service.ler_texto_imagem(caminho_completo)
    
    # Limpa temp
    if os.path.exists(caminho_completo):
        os.remove(caminho_completo) 

    if not texto_ocr:
        raise HTTPException(status_code=404, detail="Não foi possível ler nenhum texto na imagem.")

    # 3. Lógica Inteligente (Regex)
    # Procura padrões: 3 Letras + 1 Num + 1 Letra/Num + 2 Num
    # Cobre: AAA-1234 (Antiga) e AAA1B23 (Mercosul)
    padrao_placa = re.compile(r'[A-Z]{3}[0-9][0-9A-Z][0-9]{2}')
    
    texto_limpo = limpar_placa(texto_ocr)
    match = padrao_placa.search(texto_limpo)
    
    # Se achou um padrão de placa, usa ele. Se não, usa o texto bruto limpo.
    candidata = match.group(0) if match else texto_limpo
    print(f"🎯 OCR Bruto: {texto_ocr} | Candidata filtrada: {candidata}")

    # 4. Busca no Banco de Dados
    
    # Tenta busca EXATA primeiro (Muito mais rápido e preciso)
    veiculo = db.query(models.Veiculo).filter(models.Veiculo.placa == candidata).first()
    if veiculo:
        return veiculo
        
    # Se não achar exato, tenta a busca "CONTÉM" (Fallback para leituras parciais)
    # Ex: OCR leu "BRABC1234" (pegou o BR da placa), mas no banco é "ABC1234"
    todos_veiculos = db.query(models.Veiculo).all()
    for v in todos_veiculos:
        placa_v = limpar_placa(v.placa)
        # Verifica se a placa do banco está contida no texto lido
        if placa_v in texto_limpo: 
            return v
    
    raise HTTPException(status_code=404, detail=f"Veículo não identificado. Texto lido: {texto_limpo}")


# REGISTRAR ABASTECIMENTO
@app.post("/abastecimentos/", response_model=schemas.AbastecimentoResponse)
def registrar_abastecimento(dados: schemas.AbastecimentoCreate, db: Session = Depends(get_db), usuario_atual: models.Usuario = Depends(get_usuario_atual)):
    if not db.query(models.Veiculo).filter(models.Veiculo.id == dados.id_veiculo).first():
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    
    novo = models.Abastecimento(id_usuario=usuario_atual.id, **dados.dict(), status="PENDENTE_VALIDACAO")
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo

@app.get("/abastecimentos/", response_model=list[schemas.AbastecimentoResponse])
def listar_abastecimentos(db: Session = Depends(get_db)):
    return db.query(models.Abastecimento).order_by(models.Abastecimento.data_hora.desc()).all()

@app.patch("/abastecimentos/{id_abastecimento}/revisar", response_model=schemas.AbastecimentoResponse)
def revisar_abastecimento(id_abastecimento: int, review: schemas.AbastecimentoReview, db: Session = Depends(get_db), usuario_atual: models.Usuario = Depends(get_usuario_atual)):
    abastecimento = db.query(models.Abastecimento).filter(models.Abastecimento.id == id_abastecimento).first()
    if not abastecimento: raise HTTPException(status_code=404, detail="Abastecimento não encontrado")
    abastecimento.status = review.status
    if review.justificativa: abastecimento.justificativa_revisao = review.justificativa
    db.commit()
    db.refresh(abastecimento)
    return abastecimento

# --- ROTA DE UPLOAD COM LÓGICA ANTIFRAUDE HISTÓRICA ---
# --- ROTA DE UPLOAD COM SUPABASE + IA ---
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

    # 1. Preparar arquivo temporário (Necessário para o OCR funcionar localmente)
    extensao = arquivo.filename.split(".")[-1]
    nome_arquivo = f"{id_abastecimento}_{tipo_foto}_{uuid.uuid4().hex}.{extensao}"
    caminho_temp = f"uploads/{nome_arquivo}"

    # Salva localmente primeiro (Buffer temporário)
    with open(caminho_temp, "wb") as buffer:
        shutil.copyfileobj(arquivo.file, buffer)

    # 2. LÓGICA DE IA (Roda no arquivo local)
    alerta_ia = ""
    
    try:
        if tipo_foto == "PLACA":
            texto_ia = ocr_service.ler_texto_imagem(caminho_temp)
            if texto_ia:
                veiculo = db.query(models.Veiculo).filter(models.Veiculo.id == abastecimento.id_veiculo).first()
                placa_real = veiculo.placa.upper().replace("-", "").replace(" ", "")
                if placa_real not in texto_ia:
                    alerta_ia = f"[ALERTA IA] Placa lida '{texto_ia[:15]}...' difere de '{placa_real}'"

        elif tipo_foto == "PAINEL":
            km_lido = ocr_service.ler_km_imagem(caminho_temp)
            if km_lido:
                # Validação Input
                km_input = abastecimento.quilometragem
                if km_input and km_lido < km_input:
                     alerta_ia = f"[ALERTA IA] KM Foto ({km_lido}) < KM Digitado ({km_input})"
                
                # Validação Histórica
                ultimo_registro = db.query(models.Abastecimento).filter(
                    models.Abastecimento.id_veiculo == abastecimento.id_veiculo,
                    models.Abastecimento.id != abastecimento.id,
                    models.Abastecimento.quilometragem != None
                ).order_by(models.Abastecimento.data_hora.desc()).first()

                if ultimo_registro:
                    km_anterior = ultimo_registro.quilometragem
                    if km_lido <= km_anterior:
                        alerta_ia = f"[ALERTA CRÍTICO] KM Regredido! Foto ({km_lido}) <= Último ({km_anterior})"
        
        # Atualiza justificativa se houver alerta
        if alerta_ia:
            print(f"❌ {alerta_ia}")
            msg_atual = abastecimento.justificativa_revisao or ""
            abastecimento.justificativa_revisao = (msg_atual + " " + alerta_ia).strip()
            db.add(abastecimento)

        # 3. UPLOAD PARA SUPABASE (Persistência Real)
        # Re-lê o arquivo do disco para enviar bytes
        with open(caminho_temp, "rb") as f:
            arquivo_bytes = f.read()
            
        url_publica = storage_client.upload_arquivo(arquivo_bytes, nome_arquivo, arquivo.content_type)

        # Salva no banco a URL da nuvem, não o caminho local!
        nova_foto = models.FotoAbastecimento(
            id_abastecimento=id_abastecimento, 
            tipo=tipo_foto, 
            url_arquivo=url_publica # <--- Agora é um link HTTPS
        )
        db.add(nova_foto)
        db.commit()

        # 4. Limpeza (Deleta o temporário local)
        if os.path.exists(caminho_temp):
            os.remove(caminho_temp)
        
        return {"mensagem": "Sucesso", "url": url_publica, "analise": alerta_ia}

    except Exception as e:
        # Se der erro, tenta limpar o temp para não acumular lixo
        if os.path.exists(caminho_temp):
            os.remove(caminho_temp)
        raise HTTPException(status_code=500, detail=f"Erro no processamento: {str(e)}")