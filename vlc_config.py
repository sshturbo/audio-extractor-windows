import os
import sys
import platform

def setup_vlc_path():
    """Configura o caminho do VLC no PATH do sistema"""
    
    # Caminhos comuns do VLC
    VLC_PATHS = [
        r"C:\Program Files\VideoLAN\VLC",
        r"C:\Program Files (x86)\VideoLAN\VLC",
        # Adicione outros caminhos possíveis aqui
    ]
    
    # Determinar arquitetura do sistema
    is_64bits = platform.architecture()[0] == '64bit'
    
    for vlc_path in VLC_PATHS:
        if not os.path.exists(vlc_path):
            continue
            
        # Verificar compatibilidade de arquitetura
        if is_64bits and 'Program Files (x86)' in vlc_path:
            continue  # Pular VLC 32-bit em sistema 64-bit
        if not is_64bits and 'Program Files' in vlc_path and '(x86)' not in vlc_path:
            continue  # Pular VLC 64-bit em sistema 32-bit
            
        # Adicionar ao PATH se não estiver
        if vlc_path not in os.environ['PATH']:
            os.environ['PATH'] = vlc_path + os.pathsep + os.environ['PATH']
            
        # Adicionar também o caminho para plugins do VLC
        plugins_path = os.path.join(vlc_path, 'plugins')
        if os.path.exists(plugins_path) and plugins_path not in os.environ['PATH']:
            os.environ['PATH'] = plugins_path + os.pathsep + os.environ['PATH']
            
        print(f"VLC configurado em: {vlc_path}")
        return True
        
    print("VLC não encontrado!")
    return False
