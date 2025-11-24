import requests
import base64
import os

# Função para ler texto de uma imagem usando Google Vision API
def ler_texto_imagem(caminho_arquivo):
    api_key = os.getenv("GOOGLE_API_KEY") # Vamos configurar isso no Render depois
    
    if not api_key:
        print("⚠️ ERRO: API Key do Google não configurada.")
        return None

    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"

    # 1. Ler o arquivo da imagem e converter para Base64 (formato que o Google aceita)
    with open(caminho_arquivo, "rb") as image_file:
        content = base64.b64encode(image_file.read()).decode("utf-8")

    # 2. Montar o pedido (Payload)
    payload = {
        "requests": [
            {
                "image": {"content": content},
                "features": [{"type": "TEXT_DETECTION"}] # Queremos ler texto
            }
        ]
    }

    # 3. Enviar para o Google
    try:
        response = requests.post(url, json=payload)
        dados = response.json()
        
        # 4. Extrair o texto da resposta
        # O Google devolve muita coisa, queremos o "fullTextAnnotation"
        if "responses" in dados and len(dados["responses"]) > 0:
            primeira_resposta = dados["responses"][0]
            if "fullTextAnnotation" in primeira_resposta:
                texto_completo = primeira_resposta["fullTextAnnotation"]["text"]
                return texto_completo.upper() # Retorna tudo em MAIÚSCULO para facilitar comparação
            else:
                return "" # Não achou texto nenhum
        return ""
        
    except Exception as e:
        print(f"Erro na IA: {e}")
        return None