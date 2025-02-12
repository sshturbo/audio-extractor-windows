import whisper
import torch
import os
from pathlib import Path

def test_whisper():
    print("=== Teste de Download e Transcrição do Whisper ===")
    
    # 1. Verificar GPU
    print("\nVerificando disponibilidade de GPU...")
    if torch.cuda.is_available():
        print(f"GPU disponível: {torch.cuda.get_device_name(0)}")
        print(f"Memória GPU total: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    else:
        print("GPU não disponível, usando CPU")
    
    # 2. Tentar carregar modelo
    print("\nTentando carregar modelo small...")
    try:
        model = whisper.load_model("small")
        print("Modelo carregado com sucesso!")
    except Exception as e:
        print(f"Erro ao carregar modelo: {e}")
        return
    
    # 3. Verificar caminhos
    print("\nVerificando diretórios...")
    cache_dir = Path.home() / ".cache" / "whisper"
    print(f"Diretório de cache: {cache_dir}")
    if cache_dir.exists():
        print("Arquivos no cache:")
        for f in cache_dir.glob("*"):
            print(f"- {f.name}: {f.stat().st_size / 1024**2:.2f} MB")
    
    print("\nTeste concluído!")

if __name__ == "__main__":
    test_whisper()