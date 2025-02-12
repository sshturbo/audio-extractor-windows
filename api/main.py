from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil
import whisper
import librosa
import soundfile as sf
import numpy as np
from deep_translator import GoogleTranslator
import logging
import os
import json
from typing import Dict, List
import uuid
from pydantic import BaseModel
from dotenv import load_dotenv
import torch
import gc
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import time
import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

# Carregar variáveis de ambiente
load_dotenv()

# Configuração de hardware
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
NUM_THREADS = psutil.cpu_count(logical=False)  # Usar número de cores físicos
BATCH_SIZE = 16  # Otimizado para 3GB VRAM
MAX_CONCURRENT_TASKS = 2  # Limitar número de tarefas simultâneas
TORCH_THREADS = 4  # Threads para processamento PyTorch

# Configurar sessão HTTP com retry
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Configurar PyTorch
torch.set_num_threads(TORCH_THREADS)
if DEVICE == "cuda":
    torch.backends.cudnn.benchmark = True
    torch.backends.cudnn.deterministic = False

# Configuração básica
UPLOAD_DIR = Path("uploads")
MODELS_DIR = Path("models/whisper")
RESULTS_DIR = Path("results")

for directory in [UPLOAD_DIR, MODELS_DIR, RESULTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('subtitle_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Inicialização do FastAPI
app = FastAPI(
    title="Subtitle Processing API",
    description="API para processamento de legendas com Whisper e tradução",
    version="1.0.0"
)

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sistema de fila para controlar processamento
task_queue = Queue()
processing_tasks = {}
task_status = {}
thread_pool = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_TASKS)

# Gerenciamento de Memória
def clear_gpu_memory():
    """Limpa memória GPU"""
    if DEVICE == "cuda":
        torch.cuda.empty_cache()
        gc.collect()

# Carregamento otimizado do modelo
class WhisperManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.model = None
            return cls._instance
    
    def get_model(self):
        if self.model is None:
            logger.info("Carregando modelo Whisper...")
            self.model = whisper.load_model(
                "large-v3",
                device=DEVICE,
                download_root=str(MODELS_DIR)
            )
        return self.model

def optimize_audio(audio_data: np.ndarray, sr: int) -> np.ndarray:
    """Otimiza o áudio para processamento"""
    # Redução de ruído
    y_cleaned = librosa.effects.preemphasis(audio_data)
    
    # Separação de voz usando decomposição harmônica-percussiva
    y_harmonic, _ = librosa.effects.hpss(y_cleaned)
    
    # Normalização
    y_normalized = librosa.util.normalize(y_harmonic)
    
    return y_normalized

def process_audio_chunk(chunk: np.ndarray, sr: int) -> np.ndarray:
    """Processa um chunk de áudio em paralelo"""
    return optimize_audio(chunk, sr)

def process_audio(audio_path: str) -> str:
    """Processa o áudio usando múltiplos threads"""
    logger.info("Processando áudio para melhorar qualidade...")
    
    # Carregar o áudio
    y, sr = librosa.load(audio_path, sr=16000)
    
    # Dividir em chunks para processamento paralelo
    chunk_size = len(y) // NUM_THREADS
    chunks = [y[i:i + chunk_size] for i in range(0, len(y), chunk_size)]
    
    # Processar chunks em paralelo
    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        processed_chunks = list(executor.map(
            lambda x: process_audio_chunk(x, sr),
            chunks
        ))
    
    # Combinar chunks processados
    y_processed = np.concatenate(processed_chunks)
    
    # Salvar áudio processado
    output_path = str(Path(audio_path).parent / "processed_audio.wav")
    sf.write(output_path, y_processed, sr)
    
    return output_path

async def process_transcription(
    file_path: str,
    task_id: str,
    source_lang: str,
    target_lang: str
):
    whisper_manager = WhisperManager()
    
    try:
        task_status[task_id] = {"status": "processing", "progress": 10}
        
        # Processar áudio
        processed_path = process_audio(file_path)
        task_status[task_id]["progress"] = 30
        
        # Carregar modelo
        model = whisper_manager.get_model()
        
        # Configurar opções de transcrição
        options = {
            "language": source_lang if source_lang != "auto" else None,
            "task": "transcribe",
            "fp16": True if DEVICE == "cuda" else False,
            "batch_size": BATCH_SIZE,
            "verbose": True
        }
        
        # Transcrição
        logger.info(f"Iniciando transcrição para task {task_id}")
        result = model.transcribe(processed_path, **options)
        task_status[task_id]["progress"] = 70
        
        # Limpar GPU após transcrição
        clear_gpu_memory()
        
        # Processar e traduzir em batches
        subtitles = []
        batch_size = 50  # Processar traduções em lotes
        
        segments = result["segments"]
        total_segments = len(segments)
        
        # Inicializar tradutor apenas se necessário
        translator = None
        if target_lang != source_lang and target_lang != "auto":
            translator = GoogleTranslator(source='auto', target=target_lang[:2])
        
        for i in range(0, total_segments, batch_size):
            batch = segments[i:i + batch_size]
            texts = [seg["text"].strip() for seg in batch]
            
            # Traduzir se necessário
            if translator:
                try:
                    translated_texts = [translator.translate(text) for text in texts]
                except Exception as e:
                    logger.warning(f"Erro na tradução em lote: {str(e)}")
                    translated_texts = texts
            else:
                translated_texts = texts
            
            # Adicionar à lista de legendas
            for seg, text in zip(batch, translated_texts):
                subtitles.append({
                    "timestamp": seg["start"],
                    "text": text
                })
            
            # Atualizar progresso
            progress = 70 + (i / total_segments) * 25
            task_status[task_id]["progress"] = min(95, progress)
        
        # Salvar resultado
        result_path = RESULTS_DIR / f"{task_id}_result.json"
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump({
                "task_id": task_id,
                "status": "completed",
                "subtitles": subtitles,
                "metadata": {
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "processing_device": DEVICE,
                    "model": "large-v3"
                }
            }, f, ensure_ascii=False, indent=2)
        
        task_status[task_id] = {"status": "completed", "progress": 100}
            
    except Exception as e:
        logger.error(f"Erro no processamento: {str(e)}")
        task_status[task_id] = {"status": "error", "error": str(e)}
        
        # Salvar erro
        with open(RESULTS_DIR / f"{task_id}_result.json", 'w', encoding='utf-8') as f:
            json.dump({
                "task_id": task_id,
                "status": "error",
                "error": str(e)
            }, f)
    finally:
        # Limpar arquivos temporários e memória
        try:
            os.remove(file_path)
            os.remove(processed_path)
            clear_gpu_memory()
        except:
            pass

class TranscriptionRequest(BaseModel):
    source_language: str = "auto"
    target_language: str = "pt-br"

@app.post("/transcribe/")
async def transcribe_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    request: TranscriptionRequest = TranscriptionRequest()
):
    task_id = str(uuid.uuid4())
    
    try:
        # Verificar uso de memória
        if psutil.virtual_memory().percent > 90:
            raise HTTPException(
                status_code=503,
                detail="Servidor sobrecarregado. Tente novamente mais tarde."
            )
        
        # Salvar arquivo recebido
        file_path = UPLOAD_DIR / f"{task_id}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Iniciar processamento em background
        background_tasks.add_task(
            process_transcription,
            str(file_path),
            task_id,
            request.source_language,
            request.target_language
        )
        
        return JSONResponse({
            "task_id": task_id,
            "status": "processing",
            "message": "Arquivo recebido e processamento iniciado"
        })
        
    except Exception as e:
        logger.error(f"Erro ao receber arquivo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in task_status:
        return JSONResponse({
            "task_id": task_id,
            "status": "not_found",
            "error": "Tarefa não encontrada"
        })
    
    status = task_status[task_id]
    if status["status"] == "completed":
        result_file = RESULTS_DIR / f"{task_id}_result.json"
        if result_file.exists():
            with open(result_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    return status

@app.get("/health")
async def health_check():
    system_info = {
        "status": "healthy",
        "version": "1.0.0",
        "device": DEVICE,
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": psutil.virtual_memory().percent,
        "gpu_memory": None
    }
    
    if DEVICE == "cuda":
        try:
            gpu_memory = torch.cuda.get_device_properties(0).total_memory
            gpu_memory_allocated = torch.cuda.memory_allocated(0)
            system_info["gpu_memory"] = {
                "total": gpu_memory,
                "allocated": gpu_memory_allocated,
                "available": gpu_memory - gpu_memory_allocated
            }
        except:
            pass
    
    return system_info

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    # Configurar uvicorn para usar múltiplos workers
    workers = min(NUM_THREADS, 4)  # Máximo de 4 workers
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,  # Desabilitar reload em produção
        workers=workers,
        limit_concurrency=100,  # Limite de conexões concorrentes
        timeout_keep_alive=30  # Timeout para conexões keep-alive
    )