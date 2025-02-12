from pathlib import Path

def init():
    """Inicializa a estrutura de diretórios necessária para o projeto"""
    base_dir = Path(__file__).parent.parent.parent
    
    # Criar diretórios necessários
    directories = [
        base_dir / 'projects',
        base_dir / 'assets' / 'css',
        base_dir / 'assets' / 'icons',  # Adicionando diretório de ícones
        base_dir / 'data' / 'models',
        base_dir / 'data' / 'cache' / 'translations'  # Adicionando diretório para cache de traduções
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)