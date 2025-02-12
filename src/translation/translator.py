import requests
from typing import Optional
import time
from functools import lru_cache

class GoogleTranslator:
    """Classe para tradução usando a API do Google Translate"""
    
    BASE_URL = "https://translate.googleapis.com/translate_a/single"
    
    def __init__(self):
        self.session = requests.Session()
        # Configurar headers para simular um navegador
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    @lru_cache(maxsize=1000)  # Cache para evitar traduções repetidas
    def translate(self, text: str, target_lang: str, source_lang: Optional[str] = 'auto') -> str:
        """
        Traduz o texto usando a API do Google Translate
        
        Args:
            text: Texto para traduzir
            target_lang: Código do idioma alvo (ex: 'pt', 'en', 'es')
            source_lang: Código do idioma fonte (default: 'auto' para detecção automática)
            
        Returns:
            str: Texto traduzido
        """
        try:
            # Parâmetros da requisição
            params = {
                'client': 'gtx',
                'sl': source_lang,
                'tl': target_lang,
                'dt': 't',
                'q': text
            }
            
            # Fazer a requisição
            response = self.session.get(self.BASE_URL, params=params)
            response.raise_for_status()
            
            # Parse da resposta
            result = response.json()
            
            if not result or not result[0]:
                return text
            
            # Juntar todas as partes traduzidas
            translated_text = ''.join(part[0] for part in result[0] if part[0])
            
            # Aguardar um pouco para não sobrecarregar a API
            time.sleep(0.5)
            
            return translated_text
            
        except Exception as e:
            print(f"Erro na tradução: {str(e)}")
            return text  # Retorna texto original em caso de erro
    
    def translate_batch(self, texts: list[str], target_lang: str, source_lang: Optional[str] = 'auto') -> list[str]:
        """
        Traduz uma lista de textos em lote
        
        Args:
            texts: Lista de textos para traduzir
            target_lang: Código do idioma alvo
            source_lang: Código do idioma fonte (default: 'auto')
            
        Returns:
            list[str]: Lista de textos traduzidos
        """
        translated = []
        for text in texts:
            translated_text = self.translate(text, target_lang, source_lang)
            translated.append(translated_text)
            # Pequena pausa entre traduções para não sobrecarregar
            time.sleep(0.2)
        return translated