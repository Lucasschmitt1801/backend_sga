import os
from supabase import create_client, Client

# Pegando as credenciais das variáveis de ambiente
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

# Validação simples para não quebrar se esquecer a env
if not url or not key:
    print("⚠️ AVISO: SUPABASE_URL ou SUPABASE_KEY não configurados!")
    supabase = None
else:
    supabase: Client = create_client(url, key)

def upload_arquivo(arquivo_bytes, nome_arquivo, content_type="image/jpeg"):
    """
    Sobe o arquivo para o bucket 'sga-fotos' e retorna a URL Pública.
    """
    if not supabase:
        raise Exception("Supabase não configurado.")

    bucket_name = "sga-fotos"
    
    try:
        # Faz o upload
        # file_options define o tipo do arquivo (opcional, mas bom pra navegador)
        res = supabase.storage.from_(bucket_name).upload(
            path=nome_arquivo,
            file=arquivo_bytes,
            file_options={"content-type": content_type}
        )
        
        # Gera a URL pública para salvar no banco
        public_url = supabase.storage.from_(bucket_name).get_public_url(nome_arquivo)
        return public_url
        
    except Exception as e:
        print(f"❌ Erro no Upload Supabase: {e}")
        raise e