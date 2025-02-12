@echo off
echo Iniciando servidor de legendas otimizado...

:: Verificar se Python está instalado
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python não encontrado. Por favor, instale o Python e tente novamente.
    pause
    exit /b 1
)

:: Criar e ativar ambiente virtual se não existir
if not exist ".venv" (
    echo Criando ambiente virtual...
    python -m venv .venv
)

:: Ativar ambiente virtual
call .venv\Scripts\activate.bat

:: Configurar ambiente CUDA
set CUDA_VISIBLE_DEVICES=0
set OMP_NUM_THREADS=4
set MKL_NUM_THREADS=4

:: Limpar cache antigo
if exist "cache" rmdir /s /q "cache"
if exist "uploads" rmdir /s /q "uploads"
mkdir cache
mkdir uploads
mkdir results

:: Instalar dependências se necessário
pip install -r requirements.txt

:: Iniciar processo de manutenção em background
start /b pythonw maintenance.py

:: Iniciar servidor com configurações otimizadas
python main.py

:: Desativar ambiente virtual ao fechar (opcional, já que o script termina aqui)
deactivate