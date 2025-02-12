import time
import os
import psutil
import torch
import shutil
from pathlib import Path
import logging
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('maintenance.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ServerMaintenance:
    def __init__(self):
        self.cache_dir = Path(os.getenv('CACHE_DIR', 'cache'))
        self.upload_dir = Path(os.getenv('UPLOAD_DIR', 'uploads'))
        self.results_dir = Path(os.getenv('RESULTS_DIR', 'results'))
        self.max_cache_size = int(os.getenv('MAX_CACHE_SIZE', 2048))  # MB
        self.max_memory_percent = int(os.getenv('MAX_MEMORY_PERCENT', 90))
        self.clear_cache_interval = int(os.getenv('CLEAR_CACHE_INTERVAL', 300))

    def clear_gpu_memory(self):
        """Limpa memória GPU se disponível"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("Memória GPU liberada")

    def clear_old_files(self, directory: Path, max_age_hours: int = 24):
        """Remove arquivos mais antigos que max_age_hours"""
        if not directory.exists():
            return

        current_time = time.time()
        for file in directory.iterdir():
            if file.is_file():
                file_age = current_time - file.stat().st_mtime
                if file_age > (max_age_hours * 3600):
                    try:
                        file.unlink()
                        logger.info(f"Arquivo removido: {file}")
                    except Exception as e:
                        logger.error(f"Erro ao remover arquivo {file}: {e}")

    def check_directory_size(self, directory: Path) -> float:
        """Retorna o tamanho do diretório em MB"""
        total_size = 0
        for dirpath, _, filenames in os.walk(directory):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size / (1024 * 1024)  # Converter para MB

    def maintain_cache(self):
        """Mantém o cache dentro do limite configurado"""
        if not self.cache_dir.exists():
            return

        cache_size = self.check_directory_size(self.cache_dir)
        if cache_size > self.max_cache_size:
            logger.info(f"Cache excedeu limite ({cache_size:.2f}MB). Limpando...")
            try:
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(exist_ok=True)
                logger.info("Cache limpo com sucesso")
            except Exception as e:
                logger.error(f"Erro ao limpar cache: {e}")

    def check_system_resources(self):
        """Verifica recursos do sistema"""
        memory = psutil.virtual_memory()
        if memory.percent > self.max_memory_percent:
            logger.warning(f"Uso de memória alto: {memory.percent}%")
            self.clear_gpu_memory()
            self.maintain_cache()

    def run_maintenance(self):
        """Executa rotina de manutenção"""
        while True:
            try:
                logger.info("Iniciando manutenção do servidor...")
                
                # Verificar recursos
                self.check_system_resources()
                
                # Limpar arquivos antigos
                self.clear_old_files(self.upload_dir, max_age_hours=1)  # Uploads temporários
                self.clear_old_files(self.results_dir, max_age_hours=24)  # Resultados
                
                # Manter cache
                self.maintain_cache()
                
                # Limpar GPU
                self.clear_gpu_memory()
                
                logger.info("Manutenção concluída")
                
            except Exception as e:
                logger.error(f"Erro durante manutenção: {e}")
            
            time.sleep(self.clear_cache_interval)

if __name__ == "__main__":
    maintenance = ServerMaintenance()
    maintenance.run_maintenance()