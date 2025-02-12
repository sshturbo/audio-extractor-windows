import unittest
import sys
import os
from pathlib import Path
import requests
from urllib3.util import Retry

# Adicionar diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.subtitle_client import SubtitleAPIClient
from src.video_editor.subtitle_extractor import SubtitleExtractor

class TestAPIConnection(unittest.TestCase):
    def setUp(self):
        self.api_url = "http://localhost:8000"
        self.client = SubtitleAPIClient(self.api_url)
        self.extractor = SubtitleExtractor(self.api_url)

    def test_api_health(self):
        """Testa se a API está online e respondendo"""
        try:
            is_healthy = self.client.check_server_health()
            self.assertTrue(is_healthy, "API deveria estar online")
        except Exception as e:
            self.fail(f"API não está respondendo: {str(e)}")

    def test_retry_configuration(self):
        """Verifica se a configuração de retry está correta"""
        self.assertIsInstance(
            self.client.session.get_adapter('http://').max_retries,
            Retry,
            "Retry strategy deveria estar configurado"
        )

if __name__ == '__main__':
    unittest.main()