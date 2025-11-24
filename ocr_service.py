import requests
import base64
import os

def ler_texto_imagem(caminho_arquivo):
    api_key = os.getenv("GOOGLE_API_KEY") 
    
    if not api_key:
        print("⚠️ ERRO CRÍTICO: API Key não encontrada nas variáveis.")
        return None

    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"

    try:
        print("📡 Preparando envio para o Google...")
        with open(caminho_arquivo, "rb") as image_file:
            content = base64.b64encode(image_file.read()).decode("utf-8")

        payload = {
            "requests": [{
                "image": {"content": content},
                "features": [{"type": "TEXT_DETECTION"}]
            }]
        }

        response = requests.post(url, json=payload)
        print(f"📡 Google respondeu com Status: {response.status_code}")
        
        dados = response.json()

        # VERIFICAÇÃO DE ERROS DO GOOGLE (O Pulo do Gato)
        if "error" in dados:
            print(f"❌ ERRO DO GOOGLE: {dados['error']}")
            return None
            
        if "responses" in dados and len(dados["responses"]) > 0:
            resp = dados["responses"][0]
            
            # Se houver erro dentro da resposta específica
            if "error" in resp:
                print(f"❌ ERRO NA ANÁLISE: {resp['error']}")
                return None

            if "fullTextAnnotation" in resp:
                texto = resp["fullTextAnnotation"]["text"]
                return texto.upper().replace("-", "").replace(" ", "")
            else:
                print("⚠️ AVISO: O Google não encontrou NENHUM texto na imagem.")
                return ""
        
        return ""

    except Exception as e:
        print(f"❌ ERRO DE CONEXÃO/CÓDIGO: {e}")
        return None