import requests
import base64
import os

def ler_texto_imagem(caminho_arquivo):
    # Pega a chave que configuramos no Render
    api_key = os.getenv("GOOGLE_API_KEY") 
    
    if not api_key:
        print("⚠️ ERRO: API Key do Google não encontrada.")
        return None

    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"

    try:
        # Lê a foto e converte para o formato do Google
        with open(caminho_arquivo, "rb") as image_file:
            content = base64.b64encode(image_file.read()).decode("utf-8")

        payload = {
            "requests": [{
                "image": {"content": content},
                "features": [{"type": "TEXT_DETECTION"}] # Modo Leitura de Texto
            }]
        }

        # Envia
        response = requests.post(url, json=payload)
        dados = response.json()
        
        # Processa a resposta
        if "responses" in dados and len(dados["responses"]) > 0:
            resp = dados["responses"][0]
            if "fullTextAnnotation" in resp:
                texto = resp["fullTextAnnotation"]["text"]
                return texto.upper().replace("-", "").replace(" ", "") # Limpa o texto
        
        return "" # Nada encontrado

    except Exception as e:
        print(f"Erro na conexão com IA: {e}")
        return None