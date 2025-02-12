# Servidor de Legendas

Este é o servidor de processamento de legendas que utiliza Whisper e tradução automática.

## Requisitos

- Python 3.8 ou superior
- FFmpeg instalado no sistema
- CUDA (opcional, mas recomendado para melhor performance)

## Instalação

1. Clone este repositório
2. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Configuração

1. Copie o arquivo `.env.example` para `.env`:
```bash
cp .env.example .env
```

2. Ajuste as configurações no arquivo `.env` conforme necessário:
- `HOST`: endereço IP do servidor (padrão: 0.0.0.0)
- `PORT`: porta do servidor (padrão: 8000)
- `WHISPER_MODEL`: modelo do Whisper a ser usado (padrão: large-v3)

## Uso

### Iniciar o Servidor

Windows:
```bash
start_server.bat
```

Linux/Mac:
```bash
python main.py
```

O servidor estará disponível em `http://localhost:8000`

### Endpoints da API

- `POST /transcribe/`: Enviar áudio para transcrição
  - Parâmetros:
    - `file`: arquivo de áudio (wav, mp3, etc)
    - `source_language`: idioma de origem (padrão: "auto")
    - `target_language`: idioma de destino (padrão: "pt-br")

- `GET /status/{task_id}`: Verificar status da transcrição
  - Retorna o status atual e, se completo, as legendas

- `GET /health`: Verificar status do servidor

### Exemplo de Uso com Python

```python
from src.api.subtitle_client import SubtitleAPIClient

client = SubtitleAPIClient("http://localhost:8000")
task_id = client.submit_transcription("audio.wav", target_lang="pt-br")
result = client.wait_for_completion(task_id)
```

## Estrutura de Diretórios

- `uploads/`: Arquivos de áudio temporários
- `models/whisper/`: Modelos do Whisper
- `results/`: Resultados das transcrições

## Logs

Os logs são salvos em `subtitle_server.log` e também exibidos no console.