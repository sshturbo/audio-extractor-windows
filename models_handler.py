import os
import torch
from pathlib import Path
import shutil
import requests
from zipfile import ZipFile
import urllib.request
import whisper
import hashlib
from urllib.request import urlretrieve
import json
from tqdm import tqdm
import threading
from functools import lru_cache
import time  # Adicionando importação do time

class DownloadProgressBar:
    def __init__(self):
        self.pbar = None

    def __call__(self, block_num, block_size, total_size):
        if not self.pbar:
            self.pbar = tqdm(total=total_size, unit='iB', unit_scale=True)
        downloaded = block_num * block_size
        self.pbar.update(block_size)
        if downloaded >= total_size:
            self.pbar.close()

def download_with_progress(url, output_path, method='urlretrieve'):
    """Download file with progress bar using either urlretrieve or requests"""
    try:
        if method == 'urlretrieve':
            print("\nIniciando download com urlretrieve...")
            progress_bar = DownloadProgressBar()
            urlretrieve(url, output_path, reporthook=progress_bar)
            return True
        else:
            print("\nIniciando download com requests...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            
            # Aumentando o tamanho do buffer para melhor performance
            chunk_size = 1024 * 1024  # 1MB chunks
            
            with open(output_path, 'wb') as file, tqdm(
                desc="Downloading",
                total=total_size,
                unit='MB',
                unit_scale=True,
                unit_divisor=1024*1024,
                ascii=True,  # Usar caracteres ASCII para melhor compatibilidade
                ncols=100,  # Largura fixa para a barra de progresso
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
            ) as pbar:
                for data in response.iter_content(chunk_size=chunk_size):
                    size = file.write(data)
                    pbar.update(size)
            print("\nDownload concluído!")
            return True
    except Exception as e:
        print(f"\nErro durante o download: {str(e)}")
        return False

def get_models_dir():
    """Retorna o diretório de modelos local"""
    models_dir = Path(__file__).parent / 'models'
    models_dir.mkdir(exist_ok=True)
    return models_dir

def download_silero_model():
    """Download e configuração do modelo Silero VAD"""
    models_dir = get_models_dir()
    silero_dir = models_dir / 'silero_vad'
    
    # Se já existe, retorna o caminho
    if (silero_dir.exists()):
        return str(silero_dir)
    
    # Criar diretório para o Silero
    silero_dir.mkdir(exist_ok=True)
    
    # URL do modelo
    url = "https://github.com/snakers4/silero-vad/archive/master.zip"
    zip_path = silero_dir / "silero_vad.zip"
    
    # Download do arquivo com barra de progresso
    print("Baixando modelo Silero VAD...")
    if not download_with_progress(url, zip_path, method='requests'):
        raise Exception("Failed to download Silero VAD model")
    
    # Extrair arquivo com barra de progresso
    print("\nExtraindo arquivos...")
    with ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(silero_dir)
    
    # Remover arquivo zip
    zip_path.unlink()
    
    # Mover arquivos para o diretório correto
    source_dir = silero_dir / "silero-vad-master"
    for item in source_dir.iterdir():
        shutil.move(str(item), str(silero_dir / item.name))
    
    # Remover diretório temporário
    shutil.rmtree(str(source_dir))
    
    print("Download e configuração do Silero VAD concluídos!")
    return str(silero_dir)

def get_cache_dir():
    """Get the cache directory for models"""
    try:
        # Criar diretório de cache no diretório do projeto em vez de .cache global
        cache_dir = Path(__file__).parent / 'cache' / 'whisper'
        
        # Tentar criar o diretório com permissões explícitas
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Cache directory created/verified: {cache_dir}")
        print(f"Cache directory exists: {cache_dir.exists()}")
        print(f"Cache directory is writable: {os.access(cache_dir, os.W_OK)}")
        
        return cache_dir
    except Exception as e:
        print(f"Error creating cache directory: {str(e)}")
        raise

def get_model_info(name):
    """Get model info including URL and SHA256"""
    models = {
        "large-v2": {
            "url": "https://openaipublic.azureedge.net/main/whisper/models/81f7c96c852ee8fc832187b0132e569d6c3065a3252ed18e56effd0b6a73e524/large-v2.pt",
            "sha256": "81f7c96c852ee8fc832187b0132e569d6c3065a3252ed18e56effd0b6a73e524"
        },
        "large-v3": {
            "url": "https://openaipublic.azureedge.net/main/whisper/models/1f1e0f6c980bb76940fb5d3110466c16d07b8c0c0c056377bd9bb8235db99536/large-v3.pt",
            "sha256": "1f1e0f6c980bb76940fb5d3110466c16d07b8c0c0c056377bd9bb8235db99536"
        },
        "medium": {
            "url": "https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt",
            "sha256": "345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1"
        }
    }
    return models.get(name)

def verify_model(model_path, expected_sha256):
    """Verify model file integrity"""
    sha256_hash = hashlib.sha256()
    with open(model_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest() == expected_sha256

def download_model(name="large-v2", force=False):
    """Download and cache the model"""
    try:
        cache_dir = get_cache_dir()
        model_path = cache_dir / f"{name}.pt"
        info_path = cache_dir / f"{name}.json"
        
        print(f"Cache directory: {cache_dir}")
        print(f"Model path: {model_path}")
        
        # Check if model info exists
        model_info = get_model_info(name)
        if not model_info:
            raise ValueError(f"Model {name} not found in model info dictionary")
            
        print(f"Model URL: {model_info['url']}")
        
        # If model exists and force is False, verify it
        if model_path.exists() and not force:
            print("Model file exists, verifying integrity...")
            if verify_model(model_path, model_info['sha256']):
                print("Model verification successful")
                return str(model_path)
            else:
                print("Model verification failed, will re-download")
        
        # Try downloading with urlretrieve first
        print(f"Downloading model {name}...")
        try:
            if not download_with_progress(model_info['url'], model_path, method='urlretrieve'):
                print("urlretrieve failed, trying with requests...")
                if not download_with_progress(model_info['url'], model_path, method='requests'):
                    raise Exception("Both download methods failed")
        except Exception as e:
            print(f"Download error: {str(e)}")
            raise
        
        # Verify downloaded model
        print("\nVerifying downloaded model...")
        if not verify_model(model_path, model_info['sha256']):
            model_path.unlink()
            raise RuntimeError("Model verification failed after download")
            
        print("Model verification successful")
        
        # Save model info
        with open(info_path, 'w') as f:
            json.dump({
                'name': name,
                'sha256': model_info['sha256'],
                'download_date': str(Path(model_path).stat().st_mtime)
            }, f)
            
        return str(model_path)
    except Exception as e:
        print(f"Error in download_model: {str(e)}")
        raise

class ModelManager:
    _instance = None
    _lock = threading.Lock()
    _models = {}
    _last_used = {}
    _max_cached_models = 1  # Reduzido para apenas 1 modelo em cache
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ModelManager, cls).__new__(cls)
        return cls._instance
    
    @staticmethod
    def _cleanup_old_models():
        """Remove modelos antigos do cache se exceder o limite"""
        while len(ModelManager._models) > ModelManager._max_cached_models:
            # Encontrar o modelo menos usado recentemente
            oldest_key = min(ModelManager._last_used.items(), key=lambda x: x[1])[0]
            del ModelManager._models[oldest_key]
            del ModelManager._last_used[oldest_key]
            torch.cuda.empty_cache() if torch.cuda.is_available() else None
    
    @staticmethod
    def get_model(name, device):
        """Get or load a model for the specified device"""
        key = f"{name}_{device}"
        current_time = time.time()
        
        with ModelManager._lock:
            # Limpar modelos antigos primeiro
            ModelManager._cleanup_old_models()
            
            if key not in ModelManager._models:
                print(f"Carregando modelo {name} para {device}...")
                model = whisper.load_model(name, device=device)
                if device == "cuda":
                    model = model.half()  # Usar precisão reduzida para GPU
                ModelManager._models[key] = model
            
            ModelManager._last_used[key] = current_time
            return ModelManager._models[key]
    
    @staticmethod
    def clear_cache():
        """Clear model cache and free memory"""
        with ModelManager._lock:
            ModelManager._models.clear()
            ModelManager._last_used.clear()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

def load_whisper_model(name="small", device=None):  # Mudando para modelo small por padrão
    """Load whisper model with proper caching"""
    try:
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
        cache_dir = get_cache_dir()
        print(f"Loading model {name} for {device} from cache directory: {cache_dir}")
        
        # Configurar threads da CPU para usar menos memória
        if device == "cpu":
            torch.set_num_threads(2)  # Reduzido para 2 threads
            
        # Limpar memória antes de carregar novo modelo
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
        
        try:
            model_path = download_model(name)
            print(f"Model path: {model_path}")
        except Exception as download_error:
            print(f"Custom download failed: {download_error}")
            print("Falling back to whisper's default download mechanism...")
        
        # Usar o ModelManager para gerenciar os modelos
        model = ModelManager().get_model(name, device)
            
        return model
    except Exception as e:
        print(f"Detailed error loading model: {str(e)}")
        raise Exception(f"Error loading model: {str(e)}")
    finally:
        # Garantir limpeza de memória
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
