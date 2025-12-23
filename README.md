# SGA - Backend (API)

O **SGA (Sistema de Gestão de Abastecimento)** é uma solução robusta para controle de frotas e detecção de fraudes em abastecimentos. Esta API foi desenvolvida em **Python (FastAPI)** e é responsável por toda a regra de negócio, persistência de dados e processamento de imagens via OCR.

## 🚀 Tecnologias Utilizadas

* **Python 3.10+**
* **FastAPI:** Framework de alta performance para construção de APIs.
* **PostgreSQL:** Banco de dados relacional.
* **SQLAlchemy (ORM) & Alembic:** Para manipulação de dados e migrações.
* **Google Cloud Vision API:** Para OCR (leitura automática de notas fiscais).
* **Docker:** (Opcional) Para containerização da aplicação.

## ⚙️ Pré-requisitos

Antes de começar, certifique-se de ter instalado:
* [Python 3.10+](https://www.python.org/)
* [PostgreSQL](https://www.postgresql.org/)
* Uma conta de serviço ativa na [Google Cloud Platform](https://console.cloud.google.com/) com a Vision API habilitada.

## 🔧 Instalação e Configuração

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/seu-usuario/sga-backend.git](https://github.com/seu-usuario/sga-backend.git)
   cd sga-backend
