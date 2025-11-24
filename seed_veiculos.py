from database import SessionLocal, engine
from models import Base, Veiculo

def criar_frota_inicial():
    db = SessionLocal()
    
    # Lista de carros para inserir
    frota = [
        {"placa": "ABC-1234", "modelo": "Fiat Strada Endurance", "cor": "Branca", "ano_fabricacao": 2023},
        {"placa": "XYZ-9876", "modelo": "Jeep Compass Longitude", "cor": "Preto", "ano_fabricacao": 2024},
        {"placa": "SGA-2025", "modelo": "Fiat Toro Volcano", "cor": "Vermelho", "ano_fabricacao": 2023},
        {"placa": "TEST-001", "modelo": "VW Gol (Uso Interno)", "cor": "Prata", "ano_fabricacao": 2020},
        {"placa": "BMW-5555", "modelo": "BMW X1 (Diretoria)", "cor": "Azul", "ano_fabricacao": 2024},
    ]

    print("🚀 Iniciando cadastro da frota...")

    for carro in frota:
        # Verifica se já existe para não duplicar
        existe = db.query(Veiculo).filter(Veiculo.placa == carro["placa"]).first()
        if not existe:
            novo = Veiculo(
                placa=carro["placa"],
                modelo=carro["modelo"],
                cor=carro["cor"],
                ano_fabricacao=carro["ano_fabricacao"],
                status="PATIO"
            )
            db.add(novo)
            print(f"✅ Criado: {carro['modelo']} ({carro['placa']})")
        else:
            print(f"⚠️ Já existe: {carro['placa']}")

    db.commit()
    db.close()
    print("🏁 Frota cadastrada com sucesso!")

if __name__ == "__main__":
    criar_frota_inicial()