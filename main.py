import os
import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt, QCoreApplication
from gui import MainWindow
from models_handler import download_silero_model
from vlc_config import setup_vlc_path

def check_vlc_installation():
    """Verifica se o VLC está instalado e acessível"""
    vlc_paths = [
        r"C:\Program Files\VideoLAN\VLC",
        r"C:\Program Files (x86)\VideoLAN\VLC",
    ]
    
    for path in vlc_paths:
        if os.path.exists(path):
            return True
    return False

def main():
    # Configurar VLC antes de importar outros módulos
    if not setup_vlc_path():
        print("Erro: VLC não encontrado. Por favor, instale o VLC e tente novamente.")
        print("Download: https://www.videolan.org/vlc/")
        return
        
    # Garantir que o modelo está baixado antes de iniciar
    download_silero_model()
    
    try:
        # Configurar ambiente
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
        
        app = QApplication(sys.argv)
        
        # Verificar VLC
        if not check_vlc_installation():
            QMessageBox.warning(None, "VLC não encontrado",
                "O VLC Media Player não foi encontrado no sistema.\n"
                "Algumas funcionalidades estarão indisponíveis.\n"
                "Por favor, instale o VLC de https://www.videolan.org/vlc/")
        
        # Iniciar aplicação
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Erro ao iniciar aplicativo: {str(e)}")

if __name__ == "__main__":
    main()
