import requests
import base64
import os
import re # Biblioteca para expressões regulares (achar números)

def ler_texto_imagem(caminho_arquivo):
    api_key = os.getenv("GOOGLE_API_KEY") 
    if not api_key: return None

    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"

    try:
        with open(caminho_arquivo, "rb") as image_file:
            content = base64.b64encode(image_file.read()).decode("utf-8")

        payload = {
            "requests": [{
                "image": {"content": content},
                "features": [{"type": "TEXT_DETECTION"}]
            }]
        }

        response = requests.post(url, json=payload)
        dados = response.json()
        
        if "responses" in dados and len(dados["responses"]) > 0:
            resp = dados["responses"][0]
            if "fullTextAnnotation" in resp:
                texto = resp["fullTextAnnotation"]["text"]
                return texto.upper().replace("-", "").replace(" ", "")
        return ""
    except Exception as e:
        print(f"Erro OCR: {e}")
        return None

# --- NOVA FUNÇÃO ESPECIALIZADA EM NÚMEROS ---
def ler_km_imagem(caminho_arquivo):
    texto_bruto = ler_texto_imagem(caminho_arquivo)
    if not texto_bruto:
        return None
    
    # Procura apenas dígitos no texto
    # Ex: "Total 15400 km" -> "15400"
    numeros = re.findall(r'\d+', texto_bruto)
    
    if numeros:
        # Pega o maior número encontrado (geralmente o KM total é o maior número no painel)
        # Convertendo para inteiro para comparar
        maior_numero = max([int(n) for n in numeros], default=0)
        return maior_numero
    
    return None

    # 2. LÓGICA DE IA 🤖
    if tipo_foto == "PLACA":
        # ... (Lógica da Placa que já existia) ...
        pass 

    elif tipo_foto == "PAINEL":
        print(f"🔍 IA Analisando Hodômetro: {nome_arquivo}")
        km_lido = ocr_service.ler_km_imagem(caminho_completo)
        
        if km_lido:
            print(f"🤖 IA Leu KM: {km_lido}")
            km_registrado = abastecimento.quilometragem
            
            if km_registrado:
                # Tolerância de erro ou divergência
                if km_lido < km_registrado:
                    print("❌ KM Inconsistente (Foto menor que registro)!")
                    abastecimento.justificativa_revisao = f"[ALERTA IA] KM na foto ({km_lido}) é MENOR que o digitado ({km_registrado})"
                    db.add(abastecimento)
                elif km_lido > (km_registrado + 100): # Se for muito maior também é estranho
                    abastecimento.justificativa_revisao = f"[ALERTA IA] Divergência grande de KM: Foto={km_lido} vs Input={km_registrado}"
                    db.add(abastecimento)
                else:
                    print("✅ KM Validado!")
            else:
                # Se o usuário não digitou KM, salvamos o da IA como sugestão no log
                abastecimento.justificativa_revisao = f"[IA] KM Detectado na foto: {km_lido}"
                db.add(abastecimento)
            
            db.commit()