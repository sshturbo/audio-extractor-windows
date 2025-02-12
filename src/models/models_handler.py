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
import time
import socket  # Adicionando importação do socket
import logging

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

def check_internet_speed(test_url="https://www.google.com", num_tests=3):
    """Verifica a velocidade da conexão com múltiplos testes"""
    try:
        speeds = []
        test_urls = [
            "https://www.google.com",
            "https://www.cloudflare.com",
            "https://www.microsoft.com"
        ]
        
        print("Realizando teste de velocidade...")
        for i in range(num_tests):
            start_time = time.time()
            response = requests.get(test_urls[i % len(test_urls)], stream=True)
            chunk = next(response.iter_content(chunk_size=8192))
            end_time = time.time()
            
            # Calcular velocidade em MB/s
            duration = end_time - start_time
            speed = (len(chunk) / duration) / 1024 / 1024
            speeds.append(speed)
        
        avg_speed = sum(speeds) / len(speeds)
        print(f"Velocidade média detectada: {avg_speed:.2f} MB/s")
        
        # Configurações otimizadas para 600Mbps
        if avg_speed > 50:  # Conexão muito rápida (>400Mbps)
            return {
                'chunk_size': 32 * 1024 * 1024,  # 32MB chunks
                'num_chunks': 16,  # Mais chunks paralelos
                'buffer_size': 4 * 1024 * 1024,  # 4MB buffer
                'max_retries': 5,
                'timeout': 15,
                'concurrent_downloads': 4
            }
        elif avg_speed > 25:  # Conexão rápida (>200Mbps)
            return {
                'chunk_size': 16 * 1024 * 1024,  # 16MB chunks
                'num_chunks': 8,
                'buffer_size': 2 * 1024 * 1024,  # 2MB buffer
                'max_retries': 4,
                'timeout': 30,
                'concurrent_downloads': 2
            }
        else:  # Conexão mais lenta
            return {
                'chunk_size': 8 * 1024 * 1024,  # 8MB chunks
                'num_chunks': 4,
                'buffer_size': 1024 * 1024,  # 1MB buffer
                'max_retries': 3,
                'timeout': 60,
                'concurrent_downloads': 1
            }
    except Exception as e:
        print(f"Erro no teste de velocidade: {e}")
        # Configuração padrão otimizada
        return {
            'chunk_size': 16 * 1024 * 1024,
            'num_chunks': 8,
            'buffer_size': 2 * 1024 * 1024,
            'max_retries': 3,
            'timeout': 30,
            'concurrent_downloads': 2
        }

def download_with_progress(url, output_path, method='requests', num_chunks=4):
    """Download file with progress bar using highly optimized methods"""
    try:
        print(f"\nIniciando download otimizado de {url}")
        print("Verificando velocidade da conexão...")
        
        # Obter configurações otimizadas baseadas na velocidade
        speed_config = check_internet_speed()
        
        # Configurar sessão otimizada
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            max_retries=speed_config['max_retries'],
            pool_connections=speed_config['num_chunks'] * 2,
            pool_maxsize=speed_config['num_chunks'] * 2
        )
        session.mount('https://', adapter)
        session.mount('http://', adapter)
        
        # Configurar timeouts e buffers
        socket.setdefaulttimeout(speed_config['timeout'])
        
        # Fazer pedido HEAD primeiro para obter o tamanho total
        head = session.head(url)
        total_size = int(head.headers.get('content-length', 0))
        
        if total_size == 0:
            print("Não foi possível determinar o tamanho do arquivo, usando download direto")
            response = session.get(url)
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True
        
        # Calcular ranges para download em paralelo
        chunk_size = total_size // speed_config['concurrent_downloads']
        ranges = []
        for i in range(speed_config['concurrent_downloads']):
            start = i * chunk_size
            end = start + chunk_size - 1 if i < speed_config['concurrent_downloads'] - 1 else total_size
            ranges.append((start, end))
        
        # Criar arquivo temporário para cada parte
        temp_files = []
        for i in range(speed_config['concurrent_downloads']):
            temp_files.append(output_path.parent / f"{output_path.name}.part{i}")
        
        print(f"Iniciando download em {speed_config['concurrent_downloads']} partes paralelas...")
        
        with tqdm(total=total_size, unit='B', unit_scale=True, desc="Download") as pbar:
            def download_part(session, url, start, end, temp_file):
                headers = {'Range': f'bytes={start}-{end}'}
                response = session.get(url, headers=headers, stream=True)
                with open(temp_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=speed_config['chunk_size']):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            
            # Criar threads para download paralelo
            threads = []
            for i, (start, end) in enumerate(ranges):
                thread = threading.Thread(
                    target=download_part,
                    args=(session, url, start, end, temp_files[i])
                )
                thread.start()
                threads.append(thread)
            
            # Aguardar todas as threads terminarem
            for thread in threads:
                thread.join()
        
        # Combinar todas as partes
        print("\nCombinando partes do arquivo...")
        with open(output_path, 'wb') as output:
            for temp_file in temp_files:
                with open(temp_file, 'rb') as input:
                    shutil.copyfileobj(input, output, length=speed_config['buffer_size'])
                temp_file.unlink()  # Remover arquivo temporário
        
        print("\nDownload concluído com sucesso!")
        return True
        
    except Exception as e:
        print(f"\nErro durante o download: {str(e)}")
        if os.path.exists(output_path):
            os.remove(output_path)
        for temp_file in temp_files:
            if temp_file.exists():
                temp_file.unlink()
        return False

def get_models_dir():
    """Retorna o diretório de modelos local"""
    root_dir = Path(__file__).parent.parent.parent
    models_dir = root_dir / 'data' / 'models'
    models_dir.mkdir(parents=True, exist_ok=True)
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
        # Criar diretório de cache dentro de data/cache
        root_dir = Path(__file__).parent.parent.parent
        cache_dir = root_dir / 'data' / 'cache' / 'whisper'
        
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
        "small": {
            "url": "https://openaipublic.azureedge.net/main/whisper/models/9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794/small.pt",
            "sha256": "9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794"
        },
        "medium": {
            "url": "https://openaipublic.azureedge.net/main/whisper/models/345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1/medium.pt",
            "sha256": "345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1"
        },
        "large-v2": {
            "url": "https://openaipublic.azureedge.net/main/whisper/models/81f7c96c852ee8fc832187b0132e569d6c3065a3252ed18e56effd0b6a73e524/large-v2.pt",
            "sha256": "81f7c96c852ee8fc832187b0132e569d6c3065a3252ed18e56effd0b6a73e524"
        }
    }
    
    if name not in models:
        print(f"Modelo {name} não encontrado, usando medium como fallback")
        name = "medium"
        
    return models.get(name)

def verify_model(model_path, expected_sha256):
    """Verify model file integrity"""
    sha256_hash = hashlib.sha256()
    with open(model_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest() == expected_sha256

def download_model(name="medium", force=False):
    """Download and cache the model"""
    try:
        # Usar o diretório de cache local do projeto
        cache_dir = get_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        model_path = cache_dir / f"{name}.pt"
        info_path = cache_dir / f"{name}.json"
        
        print(f"Diretório de cache: {cache_dir}")
        print(f"Caminho do modelo: {model_path}")
        
        # Verificar informações do modelo
        model_info = get_model_info(name)
        if not model_info:
            raise ValueError(f"Modelo {name} não encontrado")
        
        # Verificar se já existe um modelo válido em cache
        if model_path.exists() and not force:
            print("Verificando modelo em cache...")
            
            # Verificar se temos informações salvas do modelo
            if info_path.exists():
                with open(info_path, 'r') as f:
                    cached_info = json.load(f)
                if cached_info.get('sha256') == model_info['sha256']:
                    print("Usando modelo em cache (SHA256 verificado)")
                    return str(model_path)
            
            # Se não tiver info ou SHA diferente, verificar o arquivo
            if verify_model(model_path, model_info['sha256']):
                print("Verificação do modelo em cache bem-sucedida")
                # Atualizar informações do cache
                with open(info_path, 'w') as f:
                    json.dump({
                        'name': name,
                        'sha256': model_info['sha256'],
                        'download_date': str(Path(model_path).stat().st_mtime)
                    }, f)
                return str(model_path)
            else:
                print("Modelo em cache corrompido ou inválido, realizando novo download")
                model_path.unlink()

        # Download necessário
        print(f"\nBaixando modelo {name}...")
        success = download_with_progress(
            model_info['url'], 
            model_path,
            method='requests',
            num_chunks=4
        )
        
        if not success:
            raise Exception("Falha no download do modelo")

        # Verificar modelo baixado
        print("\nVerificando integridade do download...")
        if not verify_model(model_path, model_info['sha256']):
            model_path.unlink()
            raise RuntimeError("Verificação do modelo falhou após download")
            
        print("Download e verificação concluídos com sucesso")
        
        # Salvar informações do cache
        with open(info_path, 'w') as f:
            json.dump({
                'name': name,
                'sha256': model_info['sha256'],
                'download_date': str(Path(model_path).stat().st_mtime)
            }, f)
            
        return str(model_path)
        
    except Exception as e:
        print(f"Erro em download_model: {str(e)}")
        if model_path.exists():
            model_path.unlink()
        raise

class ModelManager:
    _instance = None
    _lock = threading.Lock()
    _models = {}
    _last_used = {}
    _max_cached_models = 1
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ModelManager, cls).__new__(cls)
        return cls._instance
    
    @staticmethod
    def _cleanup_old_models():
        with ModelManager._lock:
            while len(ModelManager._models) > ModelManager._max_cached_models:
                oldest_key = min(ModelManager._last_used.items(), key=lambda x: x[1])[0]
                del ModelManager._models[oldest_key]
                del ModelManager._last_used[oldest_key]
                torch.cuda.empty_cache() if torch.cuda.is_available() else None
    
    @staticmethod
    def get_model(name, device, target_language="pt"):
        """Get or load a model for the specified device and language"""
        key = f"{name}_{device}_{target_language}"
        current_time = time.time()
        
        with ModelManager._lock:
            ModelManager._cleanup_old_models()
            
            if key not in ModelManager._models:
                print(f"Carregando modelo {name} para {device} (idioma alvo: {target_language})...")
                model = whisper.load_model(name, device=device)
                
                # Configurar modelo para português
                if target_language == "pt":
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        # Força o modelo a usar vocabulário português
                        model.tokenizer.language = "pt"
                        model.tokenizer.task = "translate"
                
                # Usar half precision apenas se estiver na GPU
                if device == "cuda":
                    model = model.half()  # FP16 apenas na GPU
                else:
                    model = model.float()  # FP32 na CPU
                
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

class MemoryManager:
    @staticmethod
    def clear_memory():
        """Limpa a memória do sistema antes de operações pesadas"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        import gc
        gc.collect()

def load_whisper_model(model_size="small", target_language=None):
    """Carrega o modelo Whisper com otimizações e suporte a detecção automática de idioma"""
    try:
        # Configurar device
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cpu":
            print("Usando CPU - o processamento pode ser mais lento")
        else:
            print(f"Usando GPU: {torch.cuda.get_device_name(0)}")

        # Carregar modelo com otimizações
        model = whisper.load_model(
            model_size,
            device=device,
            download_root=str(Path.home() / ".cache" / "whisper"),
            in_memory=True
        )
        
        # Otimizações gerais
        if device == "cpu":
            # Forçar o modelo para float32 para evitar problemas de precisão
            model = model.float()
            # Desabilitar gradient para economizar memória
            for param in model.parameters():
                param.requires_grad = False
            # Limpar cache CUDA
            torch.cuda.empty_cache()
        
        return model

    except Exception as e:
        logging.error(f"Erro ao carregar modelo Whisper: {e}")
        raise
