from PyQt5.QtCore import QThread, pyqtSignal
import traceback
import torch  # Adicionando importação do torch
from src.audio_processing.audio_processing import extract_audio
from src.audio_processing.transcribe import transcribe_audio
import os
import uuid
from pathlib import Path
import shutil
import subprocess  # Add subprocess import

class AudioProcessingWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)  # Mudando para emitir um dicionário com os resultados
    error = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, video_path, target_language):
        super().__init__()
        self.video_path = video_path
        self.target_language = target_language
        self.transcription_text = ""
        # Ajustando chunk_size para 2 minutos para combinar com a transcrição
        self.chunk_size = 120

    def run(self):
        try:
            # Etapa 1: Criar estrutura do projeto
            self.emit_status("Criando estrutura do projeto...", 5)
            project_id = self.create_project_id()
            project_dir = self.create_project_structure(project_id)
            print(f"Projeto criado em: {project_dir}")
            
            # Etapa 2: Extrair áudio
            self.emit_status("Extraindo áudio do vídeo...", 15)
            audio_path = self.extract_audio(project_dir)
            if not audio_path:
                raise Exception("Falha ao extrair áudio do vídeo")
            print(f"Áudio extraído para: {audio_path}")

            # Etapa 3: Preparar diretório de transcrição
            self.emit_status("Preparando transcrição...", 25)
            transcription_dir = project_dir / "transcripts"
            transcription_dir.mkdir(exist_ok=True)
            print(f"Diretório de transcrição: {transcription_dir}")

            # Etapa 4: Verificar modelo
            self.emit_status("Verificando modelo de transcrição...", 35)
            print("\nVerificando cache do Whisper...")
            cache_dir = Path.home() / ".cache" / "whisper"
            if cache_dir.exists():
                print("Arquivos no cache:")
                for f in cache_dir.glob("*"):
                    print(f"- {f.name}: {f.stat().st_size / 1024**2:.2f} MB")

            # Etapa 5: Iniciar transcrição
            self.emit_status("Iniciando transcrição do áudio...", 45)
            
            # Forçar coleta de lixo antes da transcrição
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            text, error = transcribe_audio(
                str(audio_path),
                target_language=self.target_language,
                transcripts_dir=str(transcription_dir),
                chunk_size=self.chunk_size
            )

            if error:
                raise Exception(f"Erro na transcrição: {error}")

            if not text:
                raise Exception("Nenhum texto foi gerado na transcrição")

            # Etapa 6: Finalização
            self.transcription_text = text
            self.emit_status("Transcrição concluída!", 100)
            
            # Preparar resultado com informações do projeto
            result = {
                'project_id': project_id,
                'original_video': str(project_dir / "original" / Path(self.video_path).name),
                'audio_file': str(audio_path),
                'segments_dir': str(project_dir / "segments"),
                'transcripts_dir': str(transcription_dir),
                'project_dir': str(project_dir),
                'transcription': text
            }
            
            # Forçar limpeza final
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.finished.emit(result)

        except Exception as e:
            error_msg = f"Erro durante o processamento: {str(e)}"
            print(f"\nERRO: {error_msg}")
            print("\nStack trace completo:")
            print(traceback.format_exc())
            self.error.emit(error_msg)
            
            # Garantir limpeza mesmo em caso de erro
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    
    def emit_status(self, message, progress):
        """Emite status e progresso juntos"""
        print(f"\n[{progress}%] {message}")
        self.status.emit(message)
        self.progress.emit(progress)

    def update_progress(self, current_step, total_steps, description=""):
        """Atualiza o progresso baseado nas etapas"""
        progress = int((current_step / total_steps) * 100)
        self.progress.emit(progress)
        if description:
            self.status.emit(description)

    def create_project_id(self):
        """Gera um ID único para o projeto"""
        return uuid.uuid4().hex[:8]

    def create_project_structure(self, project_id):
        """Cria a estrutura de diretórios do projeto"""
        projects_dir = Path("projects")
        projects_dir.mkdir(exist_ok=True)
        
        project_dir = projects_dir / project_id
        project_dir.mkdir(exist_ok=True)
        
        # Criar subdiretórios
        (project_dir / "original").mkdir(exist_ok=True)
        (project_dir / "segments").mkdir(exist_ok=True)
        (project_dir / "transcripts").mkdir(exist_ok=True)
        
        # Copiar arquivo original
        original_dir = project_dir / "original"
        video_filename = Path(self.video_path).name
        shutil.copy2(self.video_path, original_dir / video_filename)
        
        return project_dir

    def extract_audio(self, project_dir):
        """Extrai áudio do vídeo"""
        try:
            segments_dir = project_dir / "segments"
            output_path = segments_dir / "full_audio.wav"
            
            print(f"\nExtraindo áudio para: {output_path}")
            print(f"Vídeo fonte: {self.video_path}")
            
            # Use subprocess to call ffmpeg directly
            command = [
                'ffmpeg', '-i', str(self.video_path),
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # WAV format
                '-ac', '1',  # Mono
                '-ar', '16000',  # 16kHz
                '-y',  # Overwrite output
                str(output_path)
            ]
            
            # Execute ffmpeg command
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            if result.returncode != 0:
                print(f"Erro do FFmpeg: {result.stderr}")
                return None
            
            # Verify if file was created
            if output_path.exists():
                print(f"Áudio extraído com sucesso: {output_path}")
                print(f"Tamanho do arquivo: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
                return output_path
            else:
                print("Erro: Arquivo de áudio não foi criado")
                return None
            
        except Exception as e:
            print(f"Erro inesperado ao extrair áudio: {str(e)}")
            return None
