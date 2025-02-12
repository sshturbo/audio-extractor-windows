import os
import sys
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt, QCoreApplication
from src.gui.gui import MainWindow
from src.models.models_handler import download_silero_model
from src.worker import init as init_dirs
import signal

def signal_handler(signum, frame):
    """Manipula sinais de interrupção"""
    QApplication.quit()

def check_vlc():
    try:
        import vlc
        return True
    except ImportError:
        QMessageBox.critical(None, "Erro de Dependência",
                           "VLC não encontrado. Por favor, instale o VLC media player e o python-vlc:\n"
                           "1. Instale o VLC de https://www.videolan.org/\n"
                           "2. Execute: pip install python-vlc")
        return False

def main():
    if not check_vlc():
        sys.exit(1)

    # Inicializar estrutura de diretórios
    init_dirs()

    # Garantir que o modelo está baixado antes de iniciar
    download_silero_model()
    
    try:
        # Configurar manipulador de sinais
        signal.signal(signal.SIGINT, signal_handler)
        
        # Configurar ambiente
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
        
        app = QApplication(sys.argv)
        
        # Configurar encerramento limpo
        app.aboutToQuit.connect(app.deleteLater)
        
        # Iniciar aplicação
        window = MainWindow()
        window.show()
        
        return app.exec_()
    except KeyboardInterrupt:
        print("\nEncerrando aplicação...")
        app.quit()
    except Exception as e:
        print(f"Erro ao iniciar aplicativo: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

def load_previous_project(self, project_item):
    try:
        if isinstance(project_item, Path):
            project_dir = project_item
        else:
            project_dir = Path(__file__).parent / 'projects' / project_item.text()

        if not project_dir.exists():
            raise Exception("Diretório do projeto não encontrado")

        # Procurar arquivos necessários
        original_dir = project_dir / 'original'
        segments_dir = project_dir / 'segments'
        video_no_audio_dir = project_dir / 'video_no_audio'
        
        # Procurar vídeo sem áudio e áudio completo
        video_file = list(video_no_audio_dir.glob('video_no_audio.mp4'))[0]
        audio_file = segments_dir / 'full_audio.wav'

        if not video_file.exists() or not audio_file.exists():
            raise Exception("Arquivos de vídeo ou áudio não encontrados")

        self.current_project = {
            'video_file': str(video_file),
            'audio_file': str(audio_file),
            'segments_dir': str(segments_dir),
            'transcripts_dir': str(project_dir / 'transcripts'),
            'original_dir': str(original_dir),
            'video_no_audio_dir': str(video_no_audio_dir),
            'project_id': project_dir.name
        }

        self.selected_video = str(video_file)
        self.file_label.setText(f"Projeto carregado: {project_dir.name}")
        self.load_project_data()
        self.show_viewer()
        QMessageBox.information(self, "Sucesso", "Projeto carregado com sucesso!")

    except Exception as e:
        QMessageBox.warning(self, "Erro", f"Erro ao carregar projeto: {str(e)}")
