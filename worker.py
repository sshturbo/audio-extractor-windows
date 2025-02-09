from PyQt5.QtCore import QThread, pyqtSignal
from vad import detect_voice_activity
from diarization import diarize_audio
from transcribe import transcribe_audio
from audio_processing import extract_audio
import os

class AudioProcessingWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, video_file, language):
        super().__init__()
        self.video_file = video_file
        self.language = language

    def run(self):
        try:
            # 1. Extrair áudio e vídeo
            self.progress.emit(10, "Processando vídeo...")
            results = extract_audio(self.video_file)
            
            # 2. Diarização
            self.progress.emit(30, "Detectando segmentos de fala...")
            segments = diarize_audio(results['audio_file'], results['segments_dir'])
            
            if not segments:
                self.error.emit("Nenhum segmento de fala detectado")
                return
            
            # 3. Transcrição
            self.progress.emit(50, "Iniciando transcrição...")
            transcription, translation = transcribe_audio(
                results['audio_file'],
                self.language,
                results['transcripts_dir']
            )
            
            if not transcription:
                self.error.emit("Falha na transcrição")
                return
                
            self.progress.emit(90, "Finalizando...")
            
            # 4. Retornar resultados
            results['segments'] = segments
            results['transcription'] = transcription
            
            self.finished.emit(results)
            
        except Exception as e:
            self.error.emit(str(e))
