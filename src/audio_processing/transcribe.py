import whisper
import torch
from pathlib import Path
import json
from src.models.models_handler import load_whisper_model
import logging
import psutil
import os
import numpy as np
import threading
from functools import wraps
from src.translation.translator import GoogleTranslator

def timeout(seconds):
    """Timeout decorator usando threading.Timer em vez de signal.SIGALRM"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = []
            error = []
            
            def target():
                try:
                    result.append(func(*args, **kwargs))
                except Exception as e:
                    error.append(e)
            
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(seconds)
            
            if thread.is_alive():
                thread.join(1)  # dar um pequeno tempo para limpar
                raise TimeoutError(f"Função {func.__name__} excedeu o limite de {seconds} segundos")
            
            if error:
                raise error[0]
            
            return result[0] if result else None
        return wrapper
    return decorator

def check_system_resources():
    """Verifica recursos do sistema antes da transcrição"""
    memory = psutil.virtual_memory()
    free_memory_gb = memory.available / (1024 * 1024 * 1024)
    print(f"\nRecursos do Sistema:")
    print(f"Memória Total: {memory.total / (1024**3):.1f} GB")
    print(f"Memória Disponível: {free_memory_gb:.1f} GB")
    print(f"CPU Cores: {os.cpu_count()}")
    # Reduzindo o requisito mínimo de memória já que processaremos em chunks
    if free_memory_gb < 2:
        raise Exception("Memória insuficiente para transcrição (mínimo 2GB necessário)")
    return True

def split_audio(audio, chunk_duration=300):
    """Divide o áudio em chunks de tamanho especificado (em segundos)"""
    sample_rate = whisper.audio.SAMPLE_RATE
    chunk_length = chunk_duration * sample_rate
    chunks = np.array_split(audio, max(1, len(audio) // chunk_length))
    # Converter chunks para float32
    return [chunk.astype(np.float32) for chunk in chunks]

def format_portuguese_text(text):
    """Formata o texto traduzido para melhor legibilidade"""
    # Remove espaços extras
    text = ' '.join(text.split())
    return text

@timeout(300)  # 5 minutos timeout
def load_model_with_timeout(model_size="small", target_language="pt"):
    """Carrega o modelo Whisper com timeout"""
    return load_whisper_model(model_size, target_language=target_language)

def transcribe_audio(audio_file, target_language="pt", transcripts_dir=None, chunk_size=300):
    """Função de transcrição com suporte a processamento em chunks e detecção automática de idioma"""
    try:
        print("\n=== Iniciando Transcrição ===")
        
        # 0. Verificar recursos do sistema
        check_system_resources()
        
        # 1. Verificar arquivo de áudio
        audio_path = Path(audio_file)
        if not audio_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {audio_file}")
        print(f"Arquivo de áudio: {audio_file} ({audio_path.stat().st_size / 1024 / 1024:.2f} MB)")
        
        # 2. Carregar modelo com timeout
        print("\nCarregando modelo Whisper...")
        try:
            model = load_model_with_timeout("small")
            print("✓ Modelo carregado com sucesso")
            print(f"Tipo do modelo: {type(model)}")
            print(f"Dispositivo do modelo: {next(model.parameters()).device}")
            
        except TimeoutError:
            raise Exception("Timeout ao carregar modelo (5 minutos)")
        except Exception as e:
            raise Exception(f"Erro ao carregar modelo: {e}")
        
        # 3. Carregar e processar áudio
        print("\nCarregando áudio...")
        try:
            # Carregar áudio
            full_audio = whisper.load_audio(str(audio_path))
            duration = len(full_audio) / whisper.audio.SAMPLE_RATE
            print(f"✓ Áudio carregado: {duration/60:.2f} minutos")
            
            # Detectar idioma do áudio usando a função do próprio Whisper
            print("\nDetectando idioma do áudio...")
            # Usar apenas os primeiros 30 segundos para detecção de idioma
            audio_sample = whisper.pad_or_trim(full_audio[:whisper.audio.SAMPLE_RATE * 30])
            # Converter para mel spectrograms
            mel = whisper.log_mel_spectrogram(audio_sample).to(model.device)
            
            # Detectar idioma usando a função dedicada do Whisper
            _, probs = model.detect_language(mel)
            audio_language = max(probs, key=probs.get)
            print(f"✓ Idioma detectado: {audio_language}")
            
            # Dividir em chunks menores
            audio_chunks = split_audio(full_audio, chunk_size)
            print(f"\nDividindo áudio em {len(audio_chunks)} chunks de {chunk_size} segundos cada")
            
        except Exception as e:
            raise Exception(f"Erro ao processar áudio: {e}")
        
        # 4. Configurar transcrição
        options = {
            "task": "transcribe",
            "language": audio_language,
            "temperature": [0.0, 0.2],
            "best_of": 2,
            "beam_size": 3,
            "patience": 1.0,
            "verbose": False,
            "fp16": False
        }
        print("\nConfigurações:", options)
        
        # 5. Realizar transcrição por chunks
        print("\nIniciando transcrição em chunks...")
        try:
            model.eval()
            transcribed_chunks = []
            
            with torch.no_grad():
                for i, chunk in enumerate(audio_chunks, 1):
                    print(f"\nProcessando chunk {i}/{len(audio_chunks)}...")
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    
                    # Usar a função transcribe diretamente no chunk de áudio
                    result = model.transcribe(chunk, **options)
                    
                    if result and result.get("text"):
                        transcribed_chunks.append(result["text"])
                    
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
            
            if not transcribed_chunks:
                raise Exception("A transcrição não gerou texto")
            
            # 6. Traduzir o texto transcrito
            original_text = " ".join(transcribed_chunks)
            translated_text = original_text
            
            if audio_language != target_language:
                print(f"\nTraduzindo de {audio_language} para {target_language}...")
                translator = GoogleTranslator()
                translated_chunks = translator.translate_batch(transcribed_chunks, 
                                                            target_lang=target_language,
                                                            source_lang=audio_language)
                translated_text = " ".join(translated_chunks)
            else:
                print("\nIdioma fonte igual ao alvo, pulando tradução...")
            
            print("\n✓ Processamento concluído com sucesso")
            print("\nPrimeiros 200 caracteres do texto processado:", translated_text[:200])
            
        except Exception as e:
            raise Exception(f"Erro durante processamento: {e}")
        
        # 7. Salvar resultado
        if transcripts_dir:
            try:
                output_path = Path(transcripts_dir) / f"{audio_path.stem}.json"
                transcript_data = {
                    'audio_file': audio_path.name,
                    'source_language': audio_language,
                    'target_language': target_language,
                    'original_text': original_text,
                    'translated_text': translated_text,
                    'duration_minutes': duration/60,
                    'configuration': options
                }
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(transcript_data, f, ensure_ascii=False, indent=2)
                print(f"\n✓ Resultado salvo em: {output_path}")
            except Exception as e:
                print(f"Aviso: Erro ao salvar resultado: {e}")
        
        return translated_text, ""
        
    except Exception as e:
        error_msg = f"Erro no processamento: {str(e)}"
        print(f"\n❌ {error_msg}")
        print("\nStack trace completo:")
        import traceback
        print(traceback.format_exc())
        return "", error_msg
        
    finally:
        print("\n=== Fim do Processamento ===")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()