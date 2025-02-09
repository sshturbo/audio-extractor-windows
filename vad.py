import torch
import numpy as np
import soundfile as sf
import warnings
import os
from models_handler import download_silero_model

def detect_voice_activity(audio_file):
    """Função simplificada que retorna um único segmento com todo o áudio"""
    try:
        # Criar um único segmento com todo o áudio
        import soundfile as sf
        with sf.SoundFile(audio_file) as f:
            duration = len(f) / f.samplerate
            
        return [{
            'start': 0,
            'end': duration,
            'duration': duration
        }]
        
    except Exception as e:
        print(f"Erro ao processar áudio: {str(e)}")
        return []
