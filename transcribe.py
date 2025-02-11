import whisper
import torch
import json
from pathlib import Path
import os
from tqdm import tqdm
from models_handler import load_whisper_model, ModelManager
import concurrent.futures
import numpy as np
import psutil
import sys
import time

def save_transcript(transcript_data, output_path):
    """Salva transcrição em arquivo JSON"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, ensure_ascii=False, indent=2)

class MemoryManager:
    def __init__(self):
        self.gc_enabled = False
    
    def __enter__(self):
        # Ativar garbage collector
        import gc
        gc.enable()
        self.gc_enabled = True
        
        # Limpar memória no início
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch._C._cuda_clearCublasWorkspaces()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Limpar memória ao finalizar
        import gc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch._C._cuda_clearCublasWorkspaces()

def process_chunk(chunk_data):
    """Processa um chunk de áudio usando CPU ou GPU baseado na disponibilidade"""
    with MemoryManager():
        try:
            chunk, model_name, options = chunk_data
            
            # Fazer uma cópia do chunk para evitar problemas de memória
            chunk = np.array(chunk, copy=True)
            
            # Determina qual dispositivo usar para este chunk
            if torch.cuda.is_available():
                device = "cuda"
                model = whisper.load_model(model_name, device=device)
                model = model.half()
            else:
                device = "cpu"
                model = whisper.load_model(model_name, device=device)
            
            # Ajusta as opções para melhorar a tradução
            chunk_options = options.copy()
            chunk_options['temperature'] = max(0.0, min(1.0, chunk_options.get('temperature', 0.7)))
            chunk_options['no_speech_threshold'] = 0.6
            
            try:
                with torch.cuda.device(device) if device == "cuda" else torch.device("cpu"):
                    result = model.transcribe(chunk, **chunk_options)
                    text = result['text'].strip()
                    return text
            finally:
                # Garantir limpeza de memória
                del chunk
                del model
                if device == "cuda":
                    torch.cuda.empty_cache()
                    
        except Exception as e:
            print(f"Erro no processamento do chunk: {str(e)}")
            return ""

class TranscriptionPool:
    def __init__(self, model_name="small"):
        with MemoryManager():
            self.model_name = model_name
            self.has_gpu = torch.cuda.is_available()
            self.cpu_count = os.cpu_count() or 1
            self.device_managers = []
            
            # Configurar workers com base na memória disponível
            available_memory = MemoryMonitor.get_available_memory()
            
            if self.has_gpu:
                self.device_managers.append(("cuda", 1))
            
            # Ajustar número de workers CPU baseado na memória disponível
            if available_memory < 4:  # Menos de 4GB
                cpu_workers = 1
            elif available_memory < 8:  # Menos de 8GB
                cpu_workers = max(1, int(self.cpu_count * 0.15))  # 15% dos cores
            else:
                cpu_workers = max(1, int(self.cpu_count * 0.2))  # 20% dos cores
                
            self.device_managers.append(("cpu", cpu_workers))
            self.total_workers = sum(workers for _, workers in self.device_managers)
            print(f"Configurado com {self.total_workers} workers ({cpu_workers} CPU + {1 if self.has_gpu else 0} GPU)")
    
    def process_chunks(self, chunks, options):
        with MemoryManager():
            results = []
            futures = []
            previous_text = ""
            batch_size = 1  # Processa 1 chunk por vez
            max_retries = 3  # Número máximo de tentativas por chunk
            
            for batch_start in range(0, len(chunks), batch_size):
                with MemoryManager():
                    batch_end = min(batch_start + batch_size, len(chunks))
                    current_batch = chunks[batch_start:batch_end]
                    
                    with concurrent.futures.ThreadPoolExecutor(max_workers=self.total_workers) as executor:
                        chunk_index = batch_start
                        
                        for device, num_workers in self.device_managers:
                            for _ in range(num_workers):
                                while chunk_index < batch_end:
                                    chunk = chunks[chunk_index]
                                    
                                    # Criar uma cópia do chunk para cada worker
                                    chunk_copy = np.array(chunk, copy=True)
                                    
                                    chunk_options = options.copy()
                                    if previous_text and chunk_index > 0:
                                        chunk_options['initial_prompt'] = f"{options.get('initial_prompt', '')} Contexto anterior: {previous_text[-50:]}"
                                    
                                    futures.append((
                                        chunk_index,
                                        executor.submit(self._process_chunk_with_retry, 
                                                      (chunk_copy, self.model_name, chunk_options),
                                                      max_retries)
                                    ))
                                    chunk_index += 1
                                    
                                    if device == "cuda":
                                        break
                        
                        with tqdm(total=len(current_batch), 
                                desc=f"Lote {batch_start//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size}") as pbar:
                            for chunk_idx, future in sorted(futures, key=lambda x: x[0]):
                                try:
                                    text = future.result(timeout=300)  # 5 minutos de timeout
                                    if text:  # Só adiciona e atualiza o contexto se houver texto
                                        results.append(text)
                                        previous_text = text
                                    else:
                                        results.append("")
                                    pbar.update(1)
                                except concurrent.futures.TimeoutError:
                                    print(f"\nTimeout no chunk {chunk_idx}")
                                    results.append("")
                                    pbar.update(1)
                                except Exception as e:
                                    print(f"\nErro no chunk {chunk_idx}: {str(e)}")
                                    results.append("")
                                    pbar.update(1)
                
                # Limpar recursos após cada lote
                futures.clear()
                torch.cuda.empty_cache() if self.has_gpu else None
                
                # Forçar coleta de lixo após cada lote
                import gc
                gc.collect()
            
            return results
    
    def _process_chunk_with_retry(self, chunk_data, max_retries):
        """Processa um chunk com tentativas em caso de falha"""
        last_error = None
        for attempt in range(max_retries):
            try:
                return process_chunk(chunk_data)
            except Exception as e:
                last_error = e
                print(f"\nTentativa {attempt + 1} falhou: {str(e)}")
                # Espera um pouco antes de tentar novamente
                time.sleep(1)
                continue
        
        print(f"\nTodas as {max_retries} tentativas falharam: {str(last_error)}")
        return ""

JAPANESE_TO_PT_TERMS = {
    # Honoríficos
    "-san": "",
    "-kun": "",
    "-chan": "",
    "-sama": "senhor",
    "-senpai": "veterano",
    "-sensei": "professor",
    
    # Termos comuns em anime/mangá
    "hunter": "caçador",
    "raid": "incursão",
    "dungeon": "masmorra",
    "gate": "portal",
    "skill": "habilidade",
    "level": "nível",
    "boss": "chefe",
    "quest": "missão",
    "party": "grupo",
    "guild": "guilda",
    "mana": "mana",
    "healing": "cura",
    "healer": "curandeiro",
    "tank": "tanque",
    "warrior": "guerreiro",
    "sword": "espada",
    "shield": "escudo",
    "magic": "magia",
    "spell": "feitiço",
    
    # Expressões específicas
    "weakness": "fraqueza",
    "strength": "força",
    "power": "poder",
    "battle": "batalha",
    "fight": "luta",
    "monster": "monstro",
    "demon": "demônio",
    "angel": "anjo",
    "god": "deus",
    "devil": "diabo",
    
    # Termos específicos de Solo Leveling
    "shadow": "sombra",
    "arise": "surgir",
    "hunter association": "associação de caçadores",
    "s-rank": "rank-s",
    "e-rank": "rank-e",
    "gate": "portal",
    "dungeon break": "ruptura de masmorra",
}

def format_portuguese_text(text):
    """Formata e corrige problemas comuns na tradução para português"""
    # Aplicar dicionário de termos
    for jp_term, pt_term in JAPANESE_TO_PT_TERMS.items():
        # Procurar por variações maiúsculas/minúsculas
        text = text.replace(jp_term.lower(), pt_term)
        text = text.replace(jp_term.capitalize(), pt_term.capitalize())
        text = text.replace(jp_term.upper(), pt_term.upper())
    
    # Corrigir espaçamentos duplos
    text = ' '.join(text.split())
    
    # Corrigir pontuação
    text = text.replace(' ,', ',')
    text = text.replace(' .', '.')
    text = text.replace(' !', '!')
    text = text.replace(' ?', '?')
    
    return text

def setup_memory_optimization():
    """Configurações para otimizar uso de memória"""
    # Limitar uso de memória do PyTorch
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    
    # Definir limite de alocação de memória para CUDA
    if torch.cuda.is_available():
        torch.cuda.set_per_process_memory_fraction(0.7)  # Usar no máximo 70% da memória GPU
    
    # Configurar garbage collector para ser mais agressivo
    import gc
    gc.enable()
    
    # Reduzir cache de kernels CUDA
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch._C._cuda_clearCublasWorkspaces()

class MemoryMonitor:
    @staticmethod
    def get_memory_usage():
        """Retorna o uso atual de memória em porcentagem"""
        process = psutil.Process()
        return process.memory_percent()

    @staticmethod
    def get_available_memory():
        """Retorna a quantidade de memória disponível em GB"""
        return psutil.virtual_memory().available / (1024 * 1024 * 1024)

    @staticmethod
    def should_reduce_batch():
        """Verifica se deve reduzir o tamanho do batch baseado no uso de memória"""
        return MemoryMonitor.get_memory_usage() > 75 or MemoryMonitor.get_available_memory() < 2

def get_optimal_chunk_size():
    """Determina o tamanho ideal do chunk baseado na memória disponível"""
    available_memory = MemoryMonitor.get_available_memory()
    if available_memory < 4:  # Menos de 4GB disponível
        return 10  # 10 segundos
    elif available_memory < 8:  # Menos de 8GB disponível
        return 15  # 15 segundos
    else:
        return 20  # 20 segundos

def transcribe_audio(audio_file, target_language="pt", transcripts_dir=None, chunk_size=None):
    try:
        # Configurar tamanho do chunk baseado na memória disponível
        if chunk_size is None:
            chunk_size = get_optimal_chunk_size()
            print(f"Tamanho do chunk otimizado para: {chunk_size} segundos")

        # Aplicar otimizações de memória
        setup_memory_optimization()
        
        with MemoryManager():
            print("Inicializando pool de transcrição...")
            pool = TranscriptionPool(model_name="small")
            
            # Carregar áudio em chunks para economizar memória
            print("Carregando áudio...")
            audio = whisper.load_audio(audio_file)
            duration = len(audio) / whisper.audio.SAMPLE_RATE
            print(f"Duração total: {duration/60:.2f} minutos")

            # Monitorar uso de memória e ajustar parâmetros
            if MemoryMonitor.should_reduce_batch():
                print("Alto uso de memória detectado, reduzindo parâmetros...")
                transcribe_options = {
                    "task": "translate",
                    "language": "ja",
                    "beam_size": 2,
                    "best_of": 1,
                    "fp16": pool.has_gpu,
                    "condition_on_previous_text": True,
                    "initial_prompt": "Traduzir para português do Brasil:",
                    "temperature": 0.7,
                    "word_timestamps": False,
                }
            else:
                pt_prompts = ["Traduzir para português do Brasil de forma natural."]
                transcribe_options = {
                    "task": "translate",
                    "language": "ja",
                    "beam_size": 3,
                    "best_of": 1,
                    "fp16": pool.has_gpu,
                    "condition_on_previous_text": True,
                    "initial_prompt": pt_prompts[0],
                    "temperature": 0.7,
                    "word_timestamps": False,
                }

            print(f"Idioma alvo: {target_language}")

            # Processar em chunks menores
            if duration > chunk_size:
                print("Preparando chunks de áudio...")
                chunks = []
                num_chunks = int(duration / chunk_size) + 1
                
                # Criar chunks sem modificar o array original
                for i in range(num_chunks):
                    start = int(i * chunk_size * whisper.audio.SAMPLE_RATE)
                    end = int(min(len(audio), (i + 1) * chunk_size * whisper.audio.SAMPLE_RATE))
                    # Criar uma cópia do chunk
                    chunk = np.array(audio[start:end], copy=True)
                    chunks.append(chunk)
                    
                    if i % 5 == 0:  # Limpar cache a cada 5 chunks
                        torch.cuda.empty_cache() if torch.cuda.is_available() else None
                
                # Liberar memória do áudio original
                del audio
                torch.cuda.empty_cache() if torch.cuda.is_available() else None
                
                print(f"Processando {len(chunks)} chunks...")
                transcription = pool.process_chunks(chunks, transcribe_options)
                final_text = " ".join(filter(None, transcription))
                
                # Limpar chunks após processamento
                del chunks
                torch.cuda.empty_cache() if torch.cuda.is_available() else None
            else:
                print("Transcrevendo áudio completo...")
                result = process_chunk((audio, "small", transcribe_options))
                final_text = result
                del audio
        
            # Aplicar formatação com menor uso de memória
            final_text = format_portuguese_text(final_text)
        
            # Preparar dados da transcrição
            transcript_data = {
                'audio_file': os.path.basename(audio_file),
                'target_language': target_language,
                'transcription': final_text,
                'duration_minutes': duration/60
            }
        
            # Salvar transcrição se diretório fornecido
            if transcripts_dir:
                output_path = Path(transcripts_dir) / f"{Path(audio_file).stem}.json"
                save_transcript(transcript_data, output_path)
                print(f"\nTranscrição salva em: {output_path}")
        
            return final_text, ""
        
    except Exception as e:
        print(f"Erro ao transcrever áudio: {e}")
        return "", str(e)
    finally:
        # Limpar memória
        ModelManager.clear_cache()
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
