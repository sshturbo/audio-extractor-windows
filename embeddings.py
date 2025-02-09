import numpy as np

def extract_embeddings(vad_segments):
    """
    Versão simplificada que retorna características básicas dos segmentos
    """
    embeddings = []
    for segment in vad_segments:
        # Criar um embedding simplificado baseado no tempo do segmento
        embedding = np.array([segment['start'], segment['end']])
        embeddings.append(embedding)
    return embeddings
