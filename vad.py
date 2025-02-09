import torch
import numpy as np
import soundfile as sf
import warnings
import os
from models_handler import download_silero_model

def detect_voice_activity(audio_file):
    # Silenciar avisos
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    
    try:
        # Configurar torch para usar apenas 1 thread
        torch.set_num_threads(1)
        
        # Usar modelo local
        model_path = download_silero_model()
        
        # Carregar modelo com configurações específicas
        model, utils = torch.hub.load(
            repo_or_dir=model_path,
            model='silero_vad',
            source='local',
            force_reload=False,
            trust_repo=True,
            onnx=False
        )
        
        # Desempacotar utilidades
        get_speech_timestamps, _, read_audio, *_ = utils
        
        # Carregar e processar áudio
        wav = read_audio(audio_file, sampling_rate=16000)
        
        if len(wav.shape) > 1:
            wav = wav[:, 0]
        
        # Usar float32 consistentemente
        wav = wav.float()
        model = model.float()
        
        # Configurar para CPU
        model = model.to('cpu')
        wav = wav.to('cpu')
        
        # Obter timestamps
        speech_timestamps = get_speech_timestamps(
            wav, 
            model,
            sampling_rate=16000,
            return_seconds=True,
            threshold=0.5,
            min_speech_duration_ms=250,
            min_silence_duration_ms=150
        )
        
        return speech_timestamps
        
    except Exception as e:
        print(f"Erro no VAD: {str(e)}")
        return []
