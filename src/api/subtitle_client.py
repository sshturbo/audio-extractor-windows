import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
import logging
import time
from typing import Dict

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