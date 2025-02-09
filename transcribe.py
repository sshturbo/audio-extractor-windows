import whisper
import torch
import json
from pathlib import Path
import os
from tqdm import tqdm

def save_transcript(transcript_data, output_path):
    """Salva transcrição em arquivo JSON"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(transcript_data, f, ensure_ascii=False, indent=2)

def transcribe_audio(audio_file, language="en", transcripts_dir=None, chunk_size=5*60):  # chunk de 5 minutos
    try:
        print("Inicializando modelo Whisper...")
        model = whisper.load_model("base")
        model = model.float()
        
        # Usar CUDA se disponível
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Usando dispositivo: {device}")
        model = model.to(device)

        # Carregar áudio e obter informações
        print("Carregando áudio...")
        audio = whisper.load_audio(audio_file)
        duration = len(audio) / whisper.audio.SAMPLE_RATE
        print(f"Duração total: {duration/60:.2f} minutos")

        # Processar em chunks se o áudio for longo
        if duration > chunk_size:
            print("Processando áudio em partes...")
            transcription = []
            chunks = int(duration / chunk_size) + 1
            
            for i in tqdm(range(chunks), desc="Transcrevendo"):
                start = i * chunk_size * whisper.audio.SAMPLE_RATE
                end = min(len(audio), (i + 1) * chunk_size * whisper.audio.SAMPLE_RATE)
                chunk = audio[start:end]
                
                result = model.transcribe(
                    chunk,
                    language=language,
                    fp16=False,
                    initial_prompt="Transcrição de áudio em português." if language == "pt" else None
                )
                transcription.append(result['text'])
        else:
            print("Transcrevendo áudio completo...")
            result = model.transcribe(
                audio_file,
                language=language,
                fp16=False,
                initial_prompt="Transcrição de áudio em português." if language == "pt" else None
            )
            transcription = [result['text']]

        # Juntar resultados
        final_text = " ".join(transcription)
        
        # Preparar dados da transcrição
        transcript_data = {
            'audio_file': os.path.basename(audio_file),
            'language': language,
            'transcription': final_text,
            'duration_minutes': duration/60
        }
        
        # Salvar transcrição se diretório fornecido
        if transcripts_dir:
            output_path = Path(transcripts_dir) / f"{Path(audio_file).stem}.json"
            save_transcript(transcript_data, output_path)
            print(f"Transcrição salva em: {output_path}")
        
        return final_text, ""
        
    except Exception as e:
        print(f"Erro ao transcrever áudio: {e}")
        return "", ""
