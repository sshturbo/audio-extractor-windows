from PyQt5.QtCore import QThread, pyqtSignal
from pathlib import Path
import logging
import time
from src.video_editor.subtitle_extractor import SubtitleExtractor

class SubtitleExtractionWorker(QThread):
    progressChanged = pyqtSignal(int)
    statusChanged = pyqtSignal(str)
    finished = pyqtSignal(str)  # Emite o caminho do arquivo de legendas
    error = pyqtSignal(str)
    logMessage = pyqtSignal(str)  # Novo sinal para logs

    def __init__(self, video_path: str, output_dir: Path, target_language: str = "pt-BR"):
        super().__init__()
        self.video_path = video_path
        self.output_dir = output_dir
        self.extractor = SubtitleExtractor()
        # Define o idioma alvo
        self.extractor.set_language(source_lang="auto", dest_lang=target_language)
        
        # Configurar handler de log personalizado
        self.log_handler = QtLogHandler(self.logMessage)
        self.log_handler.setLevel(logging.DEBUG)
        logging.getLogger('src.video_editor.subtitle_extractor').addHandler(self.log_handler)

    def run(self):
        try:
            self.statusChanged.emit(f"Iniciando extração de legendas em {self.extractor.dest_lang}...")
            self.progressChanged.emit(0)
            
            # Configurar diretório de saída
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Mostrar progresso inicial
            self.progressChanged.emit(10)
            self.statusChanged.emit("Extraindo áudio do vídeo...")
            
            # Extrair legendas
            subtitles = self.extractor.extract_subtitles(
                self.video_path,
                self.output_dir
            )
            
            if not subtitles:
                raise Exception("Nenhuma legenda foi extraída. Verifique o áudio do vídeo.")
            
            # Emitir caminho do arquivo JSON
            json_file = self.output_dir / "extracted_subtitles.json"
            self.progressChanged.emit(100)
            self.statusChanged.emit("Legendas extraídas com sucesso!")
            self.finished.emit(str(json_file))
            
        except Exception as e:
            self.error.emit(str(e))
        finally:
            # Remover o handler de log
            logging.getLogger('src.video_editor.subtitle_extractor').removeHandler(self.log_handler)

class QtLogHandler(logging.Handler):
    """Handler personalizado para enviar logs para a interface Qt"""
    def __init__(self, signal):
        super().__init__()
        self.signal = signal
        # Configurar formatação dos logs
        formatter = logging.Formatter('%(message)s')
        self.setFormatter(formatter)

    def emit(self, record):
        try:
            msg = self.format(record)
            # Se a mensagem contiver "transcrição", atualizar o progresso
            if "Iniciando transcrição" in msg:
                self.signal.emit("Iniciando transcrição do áudio... (pode demorar alguns minutos)")
            else:
                self.signal.emit(msg)
        except Exception:
            pass