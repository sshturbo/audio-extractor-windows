import torch
import numpy as np
import soundfile as sf
import warnings
from pathlib import Path

def save_audio_segment(wav_data, sr, output_path):
    """Salva segmento de áudio em arquivo WAV"""
    try:
        sf.write(output_path, wav_data, sr)
    except Exception as e:
        print(f"Erro ao salvar segmento de áudio: {str(e)}")

def diarize_audio(audio_path, segments_dir):
    try:
        # Configurações
        warnings.filterwarnings('ignore')
        torch.set_num_threads(1)
        
        # Carregar áudio
        wav, sr = sf.read(audio_path)
        wav = wav.astype(np.float32)
        
        if len(wav.shape) > 1:
            wav = wav[:, 0]
        
        # Parâmetros de segmentação
        segment_length = 16000  # 1 segundo em 16kHz
        min_segment_length = 3 * 16000  # 3 segundos
        max_segment_length = 20 * 16000  # 20 segundos
        
        # Detectar silêncio usando energia
        energy = np.abs(wav)
        threshold = np.mean(energy) * 0.5
        
        # Encontrar segmentos
        segments = []
        start = 0
        is_speech = False
        
        for i in range(0, len(wav), segment_length):
            chunk = wav[i:i+segment_length]
            if len(chunk) < segment_length:
                break
                
            chunk_energy = np.mean(np.abs(chunk))
            
            if chunk_energy > threshold and not is_speech:
                start = i
                is_speech = True
            elif chunk_energy <= threshold and is_speech:
                end = i
                if end - start >= min_segment_length:
                    segments.append({
                        'start': start / sr,
                        'end': end / sr,
                        'duration': (end - start) / sr
                    })
                is_speech = False
        
        # Processar segmentos
        results = []
        for i, segment in enumerate(segments):
            start_sample = int(segment['start'] * sr)
            end_sample = int(segment['end'] * sr)
            
            if end_sample - start_sample > max_segment_length:
                continue
                
            # Extrair segmento
            audio_segment = wav[start_sample:end_sample]
            
            # Nome do arquivo
            segment_filename = f'segment_{i:03d}_{segment["duration"]:.1f}s.wav'
            segment_path = Path(segments_dir) / segment_filename
            
            # Salvar segmento
            sf.write(str(segment_path), audio_segment, sr)
            
            segment['audio_file'] = segment_filename
            results.append(segment)
        
        return results
        
    except Exception as e:
        print(f"Erro na diarização: {str(e)}")
        return []

def extract_enhanced_features(audio_segment, sr):
    """Extrai características melhoradas do áudio"""
    try:
        if len(audio_segment) < sr * 0.1:  # Ignorar segmentos muito curtos
            return None
            
        # Características básicas
        energy = np.mean(audio_segment**2)
        zcr = np.mean(np.abs(np.diff(np.signbit(audio_segment))))
        
        # Características espectrais
        spectrum = np.abs(np.fft.rfft(audio_segment))
        spectral_centroid = np.sum(spectrum * np.arange(len(spectrum))) / np.sum(spectrum)
        spectral_rolloff = np.percentile(spectrum, 85)
        
        # Combinar características
        features = np.array([
            energy,
            zcr,
            spectral_centroid,
            spectral_rolloff
        ])
        
        # Normalizar
        features = (features - np.mean(features)) / (np.std(features) + 1e-6)
        return features
        
    except Exception as e:
        print(f"Erro na extração de características: {str(e)}")
        return None

def smooth_speaker_labels(labels, min_segments=3):
    """Suaviza as alternâncias de locutor"""
    smoothed = labels.copy()
    n_segments = len(labels)
    
    for i in range(1, n_segments - 1):
        # Verifica janela de 3 segmentos
        if smoothed[i-1] == smoothed[i+1] and smoothed[i] != smoothed[i-1]:
            smoothed[i] = smoothed[i-1]
    
    return smoothed

def extract_features(wav, speech_timestamps):
    try:
        if not speech_timestamps:
            return np.array([], dtype=np.float32)
            
        features = []
        for timestamp in speech_timestamps:
            start = int(timestamp['start'])
            end = int(timestamp['end'])
            
            if start >= len(wav) or end > len(wav):
                continue
                
            segment = wav[start:end]
            if len(segment) > 0:
                # Características simplificadas
                energy = np.mean(segment**2)
                zero_crossing_rate = np.mean(np.abs(np.diff(np.signbit(segment))))
                features.append([float(energy), float(zero_crossing_rate)])
                
        if not features:
            return np.array([], dtype=np.float32)
            
        return np.array(features, dtype=np.float32)
        
    except Exception as e:
        print(f"Erro na extração de características: {str(e)}")
        return np.array([], dtype=np.float32)
