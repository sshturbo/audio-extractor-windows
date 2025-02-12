import ffmpeg
import os
from pathlib import Path
import uuid
import subprocess

def create_project_dirs(video_file):
    """Cria estrutura de diretórios do projeto"""
    # Criar ID único para o projeto
    project_id = str(uuid.uuid4())[:8]
    
    # Diretório base do projeto
    base_dir = Path(__file__).parent / 'projects' / project_id
    
    # Criar diretórios
    segments_dir = base_dir / 'segments'
    transcripts_dir = base_dir / 'transcripts'
    original_dir = base_dir / 'original'
    
    for dir_path in [segments_dir, transcripts_dir, original_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # Copiar vídeo original mantendo o nome e o áudio
    video_path = Path(video_file)
    original_video = original_dir / video_path.name
    
    if not original_video.exists():
        from shutil import copy2
        copy2(video_file, original_video)  # Copia mantendo o áudio original
        
    return str(segments_dir), str(transcripts_dir), str(original_video), project_id

def extract_audio(video_file):
    try:
        # Criar diretórios do projeto
        segments_dir, transcripts_dir, original_video, project_id = create_project_dirs(video_file)
        
        # Definir caminhos de saída
        audio_file = str(Path(segments_dir) / 'full_audio.wav')
        
        try:
            # Usar subprocess diretamente para mais controle
            command = [
                'ffmpeg', '-i', video_file,
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # WAV format
                '-ac', '1',  # Mono
                '-ar', '16000',  # 16kHz
                '-y',  # Overwrite output
                audio_file
            ]
            
            # Executar comando ffmpeg
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg error: {result.stderr}")
            
        except Exception as e:
            raise Exception(f"Error extracting audio: {str(e)}")
        
        return {
            'audio_file': audio_file,
            'segments_dir': segments_dir,
            'transcripts_dir': transcripts_dir,
            'project_id': project_id,
            'original_dir': str(Path(original_video).parent),
            'original_video': original_video  # Caminho do vídeo original com áudio
        }
        
    except Exception as e:
        raise Exception(f"Erro ao processar vídeo: {str(e)}")
