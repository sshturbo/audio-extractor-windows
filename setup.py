import subprocess
import sys
import os

def install_requirements():
    """Instala as dependências necessárias"""
    print("Instalando dependências...")
    
    try:
        # Atualizar pip
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        
        # Instalar dependências do requirements.txt
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        
        print("\nDependências instaladas com sucesso!")
        print("\nAgora você pode executar o programa com: python main.py")
        
    except subprocess.CalledProcessError as e:
        print(f"\nErro ao instalar dependências: {e}")
        sys.exit(1)

if __name__ == "__main__":
    install_requirements()
