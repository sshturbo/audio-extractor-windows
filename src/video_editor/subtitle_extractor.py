import os
from pathlib import Path
import json
import time
from typing import List, Dict, Optional
import subprocess
import logging
import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

class SubtitleAPIClient:
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url.rstrip('/')
        self.logger = logging.getLogger(__name__)
        
        # Configurar retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        
        self.session = requests.Session()
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def check_server_health(self) -> bool:
        """Verifica se o servidor está online"""
        try:
            response = self.session.get(f"{self.api_url}/health")
            response.raise_for_status()
            return response.json().get("status") == "healthy"
        except Exception as e:
            self.logger.error(f"Erro ao verificar servidor: {str(e)}")
            return False

    def submit_transcription(self, audio_file: str, source_lang: str = "auto", target_lang: str = "pt-br") -> str:
        """Envia o arquivo de áudio para transcrição"""
        if not self.check_server_health():
            raise ConnectionError("Servidor de transcrição não está disponível")
            
        try:
            with open(audio_file, 'rb') as f:
                files = {'file': f}
                data = {
                    'source_language': source_lang,
                    'target_language': target_lang
                }
                response = self.session.post(
                    f"{self.api_url}/transcribe/",
                    files=files,
                    data=data,
                    timeout=30  # 30 segundos para timeout
                )
                response.raise_for_status()
                return response.json()["task_id"]
        except Exception as e:
            self.logger.error(f"Erro ao enviar arquivo para transcrição: {str(e)}")
            raise

    def get_transcription_status(self, task_id: str) -> Dict:
        """Verifica o status de uma tarefa de transcrição"""
        try:
            response = self.session.get(
                f"{self.api_url}/status/{task_id}",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Erro ao verificar status da transcrição: {str(e)}")
            raise

    def wait_for_completion(self, task_id: str, check_interval: int = 5, timeout: int = 3600) -> Dict:
        """
        Aguarda a conclusão da transcrição com timeout
        timeout: tempo máximo de espera em segundos (padrão 1 hora)
        """
        start_time = time.time()
        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError("Tempo limite excedido aguardando transcrição")
                
            status = self.get_transcription_status(task_id)
            
            if status["status"] == "completed":
                return status
            elif status["status"] == "error":
                raise Exception(status.get("error", "Erro desconhecido na transcrição"))
            
            # Registrar progresso
            if "progress" in status:
                self.logger.info(f"Progresso: {status['progress']}%")
            
            time.sleep(check_interval)

from src.api.subtitle_client import SubtitleAPIClient

class SubtitleExtractor:
    LANGUAGE_CODES = {
        'ja': 'ja-JP',
        'ko': 'ko-KR',
        'zh': 'zh-CN',
        'pt': 'pt-BR',
        'en': 'en-US',
    }

    def __init__(self, api_url: str = None):
        self.source_lang = "auto"
        self.dest_lang = "pt-br"
        self.logger = logging.getLogger(__name__)
        
        # Se não fornecido, tenta ler do ambiente
        if api_url is None:
            api_url = os.getenv("SUBTITLE_API_URL", "http://localhost:8000")
        
        self.api_client = SubtitleAPIClient(api_url)

    def extract_subtitles(self, video_path: str, output_dir: Path, interval: float = None) -> List[Dict]:
        """
        Extrai legendas do vídeo usando o servidor de processamento remoto
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        srt_path = output_dir / "extracted_subtitles.srt"
        json_path = output_dir / "extracted_subtitles.json"
        
        self.logger.info(f"Iniciando extração de legendas do vídeo: {video_path}")
        
        # Extrai áudio do vídeo
        audio_path = str(output_dir / "temp_audio.wav")
        
        try:
            # Verificar conexão com servidor
            if not self.api_client.check_server_health():
                raise ConnectionError("Servidor de transcrição não está disponível")
            
            self.logger.info("Extraindo áudio do vídeo...")
            result = subprocess.run([
                'ffmpeg', '-i', video_path,
                '-ar', '16000',  # Formato esperado pelo Whisper
                '-ac', '1',      # Mono
                '-y', audio_path
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Erro ao extrair áudio: {result.stderr}")
            
            # Enviar para processamento remoto
            self.logger.info("Enviando áudio para processamento remoto...")
            task_id = self.api_client.submit_transcription(
                audio_path,
                source_lang=self.source_lang,
                target_lang=self.dest_lang
            )
            
            # Aguardar processamento
            self.logger.info(f"Aguardando processamento remoto (ID: {task_id})...")
            result = self.api_client.wait_for_completion(task_id)
            
            if result["status"] != "completed":
                raise Exception("Erro no processamento remoto")
            
            subtitles = result["subtitles"]
            
            # Salvar resultados
            if subtitles:
                self._save_results(subtitles, json_path)
                self._save_srt(subtitles, srt_path)
                self.logger.info(f"Legendas salvas com sucesso")
            else:
                self.logger.warning("Nenhuma legenda foi extraída")
            
            return subtitles
            
        except Exception as e:
            self.logger.error(f"Erro na extração de legendas: {str(e)}")
            raise
        finally:
            # Limpar arquivo temporário
            if os.path.exists(audio_path):
                os.remove(audio_path)

    def _save_srt(self, subtitles: List[Dict], output_file: Path) -> None:
        """Salva as legendas em formato SRT."""
        with open(output_file, 'w', encoding='utf-8') as f:
            for i, sub in enumerate(subtitles, 1):
                start_time = time.strftime('%H:%M:%S,000', time.gmtime(sub['timestamp']))
                end_time = time.strftime('%H:%M:%S,000', time.gmtime(sub['timestamp'] + 2.0))
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{sub['text']}\n\n")

    def _save_results(self, subtitles: List[Dict], output_file: Path) -> None:
        """Salva os resultados em formato JSON."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "subtitles": subtitles,
                "metadata": {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "source_language": self.source_lang,
                    "destination_language": self.dest_lang
                }
            }, f, ensure_ascii=False, indent=2)

    def set_language(self, source_lang: str = "auto", dest_lang: str = "pt-br") -> None:
        """
        Define os idiomas de origem e destino.
        """
        self.source_lang = source_lang
        self.dest_lang = dest_lang
