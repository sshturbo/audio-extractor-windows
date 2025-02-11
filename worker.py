from PyQt5.QtCore import QThread, pyqtSignal
import traceback
from audio_processing import extract_audio
from transcribe import transcribe_audio
import os

class AudioProcessingWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, video_file, target_language):
        super().__init__()
        self.video_file = video_file
        self.target_language = target_language

    def run(self):
        try:
            # Extrair áudio
            self.progress.emit(20, "Extraindo áudio do vídeo...")
            project_data = extract_audio(self.video_file)
            
            # Transcrever e traduzir áudio
            self.progress.emit(40, "Detectando idioma e transcrevendo áudio...")
            transcription, error = transcribe_audio(
                project_data['audio_file'],
                target_language=self.target_language,
                transcripts_dir=project_data['transcripts_dir']
            )
            
            if error:
                self.error.emit(error)
                return
            
            self.progress.emit(100, "Processamento concluído!")
            self.finished.emit(project_data)
            
        except Exception as e:
            traceback.print_exc()
            self.error.emit(str(e))
