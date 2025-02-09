import os
import torch
from pathlib import Path
import shutil
import requests
from zipfile import ZipFile
import urllib.request

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
    if silero_dir.exists():
        return str(silero_dir)
    
    # Criar diretório para o Silero
    silero_dir.mkdir(exist_ok=True)
    
    # URL do modelo
    url = "https://github.com/snakers4/silero-vad/archive/master.zip"
    zip_path = silero_dir / "silero_vad.zip"
    
    # Download do arquivo
    print("Baixando modelo Silero VAD...")
    urllib.request.urlretrieve(url, zip_path)
    
    # Extrair arquivo
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
    
    return str(silero_dir)
