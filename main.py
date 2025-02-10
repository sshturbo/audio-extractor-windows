import os
import sys
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt, QCoreApplication
from gui import MainWindow
from models_handler import download_silero_model
import signal

def signal_handler(signum, frame):
    """Manipula sinais de interrupção"""
    QApplication.quit()

def main():
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
