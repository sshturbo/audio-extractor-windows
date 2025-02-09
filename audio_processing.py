import ffmpeg
import os
from pathlib import Path
import uuid

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
    
    # Copiar vídeo original
    video_path = Path(video_file)
    original_video = original_dir / video_path.name
    
    if not original_video.exists():
        from shutil import copy2
        copy2(video_file, original_video)
    
    return str(segments_dir), str(transcripts_dir), str(original_video), project_id

def extract_audio(video_file):
    try:
        # Criar diretórios do projeto
        segments_dir, transcripts_dir, original_video, project_id = create_project_dirs(video_file)
        
        # Definir caminhos de saída
        base_dir = Path(segments_dir).parent
        audio_file = str(Path(segments_dir) / 'full_audio.wav')
        video_without_audio = str(base_dir / 'original' / 'video_no_audio.mp4')
        
        try:
            # Extrair áudio
            stream_audio = ffmpeg.input(video_file)
            stream_audio = ffmpeg.output(
                stream_audio,
                audio_file,
                acodec='pcm_s16le',
                ac=1,
                ar='16k',
                vn=None,
                loglevel='error'
            )
            ffmpeg.run(stream_audio, overwrite_output=True)
            
            # Extrair vídeo sem áudio
            stream_video = ffmpeg.input(video_file)
            stream_video = ffmpeg.output(
                stream_video,
                video_without_audio,
                an=None,  # Remove áudio
                c='copy',  # Copiar codec de vídeo
                loglevel='error'
            )
            ffmpeg.run(stream_video, overwrite_output=True)
            
            # Excluir vídeo original após o processamento bem-sucedido
            if original_video != video_without_audio:  # Garantir que não exclua o vídeo sem áudio
                Path(original_video).unlink()
            
        except ffmpeg.Error as e:
            raise Exception(f"Erro FFmpeg: {e.stderr.decode()}")
        
        return {
            'audio_file': audio_file,
            'video_file': video_without_audio,
            'segments_dir': segments_dir,
            'transcripts_dir': transcripts_dir,
            'project_id': project_id,
            'original_dir': str(Path(video_without_audio).parent)
        }
        
    except Exception as e:
        raise Exception(f"Erro ao processar vídeo: {str(e)}")
