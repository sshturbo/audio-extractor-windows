import subprocess
import sys
import os
import platform

def install_tesseract():
    """Instala o Tesseract OCR no Windows com suporte a português"""
    if platform.system() == 'Windows':
        try:
            print("Instalando Tesseract OCR...")
            # Instala o Tesseract OCR com pacote de idioma português
            subprocess.check_call([
                'winget', 'install', 'UB-Mannheim.TesseractOCR',
                '--accept-source-agreements',
                '--accept-package-agreements'
            ])
            
            # Verificar instalação
            tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            if os.path.exists(tesseract_path):
                print("Tesseract OCR instalado com sucesso!")
                
                # Verificar se o português está instalado
                try:
                    result = subprocess.run([tesseract_path, '--list-langs'], 
                                         capture_output=True, text=True)
                    if 'por' not in result.stdout:
                        print("Instalando pacote de idioma português...")
                        # Baixar e instalar dados do português
                        lang_path = r'C:\Program Files\Tesseract-OCR\tessdata'
                        os.makedirs(lang_path, exist_ok=True)
                        subprocess.check_call([
                            'powershell',
                            '-Command',
                            f'Invoke-WebRequest -Uri "https://github.com/tesseract-ocr/tessdata/raw/main/por.traineddata" -OutFile "{lang_path}\\por.traineddata"'
                        ])
                        print("Pacote de idioma português instalado com sucesso!")
                except subprocess.CalledProcessError as e:
                    print(f"Erro ao verificar/instalar idioma português: {e}")
            else:
                print("Tesseract não encontrado no caminho padrão após instalação.")
                print("Por favor, instale manualmente em: https://github.com/UB-Mannheim/tesseract/wiki")
                
        except subprocess.CalledProcessError as e:
            print(f"Erro ao instalar Tesseract OCR: {e}")
            print("Por favor, instale manualmente em: https://github.com/UB-Mannheim/tesseract/wiki")
        except FileNotFoundError:
            print("Winget não encontrado. Por favor, instale o Tesseract OCR manualmente.")

def install_requirements():
    """Instala as dependências necessárias"""
    print("Instalando dependências...")
    
    try:
        # Atualizar pip
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        
        # Instalar dependências do requirements.txt
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        
        # Instalar Tesseract OCR no Windows
        install_tesseract()
        
        print("\nDependências instaladas com sucesso!")
        print("\nAgora você pode executar o programa com: python main.py")
        
    except subprocess.CalledProcessError as e:
        print(f"\nErro ao instalar dependências: {e}")
        sys.exit(1)

if __name__ == "__main__":
    install_requirements()
