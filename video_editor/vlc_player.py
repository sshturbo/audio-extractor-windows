import vlc
from PyQt5.QtWidgets import QFrame, QWidget
from PyQt5.QtCore import Qt
import sys
import time

class VLCPlayer:
    def __init__(self, display_widget):
        # Configurações simplificadas e atualizadas para compatibilidade
        self.instance = vlc.Instance([
            '--quiet',                 # Reduzir logs
            '--no-xlib',              # Reduzir latência
            '--audio-resampler=soxr',  # Resampler de alta qualidade
            '--clock-jitter=0',        # Reduzir jitter
            '--clock-synchro=0',       # Sincronização precisa
            '--live-caching=50',       # Reduzir buffer live
            '--network-caching=50',    # Reduzir buffer de rede
            '--file-caching=50',       # Reduzir buffer de arquivo
            '--disc-caching=50',       # Reduzir buffer de disco
            '--sout-mux-caching=50',   # Reduzir buffer de muxing
            '--high-priority',         # Alta prioridade
        ])
        
        if not self.instance:
            raise RuntimeError("Não foi possível inicializar o VLC")
            
        self.player = self.instance.media_player_new()
        if not self.player:
            raise RuntimeError("Não foi possível criar o media player")
        
        # Configurar o widget de exibição
        if isinstance(display_widget, (QFrame, QWidget)):
            if sys.platform.startswith('linux'):
                self.player.set_xwindow(display_widget.winId())
            elif sys.platform == "win32":
                self.player.set_hwnd(display_widget.winId())
            elif sys.platform == "darwin":
                self.player.set_nsobject(int(display_widget.winId()))

    def load(self, file_path):
        """Carrega um arquivo de mídia"""
        try:
            media = self.instance.media_new(str(file_path))
            
            # Configurações otimizadas e compatíveis
            options = [
                ':clock-jitter=0',
                ':clock-synchro=0',
                ':live-caching=50',
                ':network-caching=50',
                ':sout-mux-caching=50',
            ]
            
            # Adicionar otimizações específicas do Windows
            if sys.platform == "win32":
                options.extend([
                    ':avcodec-hw=any',
                    ':avcodec-threads=0'
                ])
            
            # Aplicar todas as opções
            for option in options:
                media.add_option(option)
            
            # Aplicar mídia ao player
            self.player.set_media(media)
            
            # Aguardar a mídia ser carregada
            time.sleep(0.5)
            
            # Verificar se a mídia foi carregada corretamente
            if self.player.get_length() <= 0:
                time.sleep(1)  # Tentar novamente após um tempo maior
            
            return True
            
        except Exception as e:
            print(f"Erro ao carregar mídia: {e}")
            return False

    def play(self):
        """Inicia a reprodução"""
        self.player.play()

    def pause(self):
        """Pausa a reprodução"""
        self.player.pause()

    def stop(self):
        """Para a reprodução"""
        self.player.stop()

    def set_position(self, position):
        """Define a posição da reprodução (0.0 a 1.0)"""
        self.player.set_position(position)

    def get_position(self):
        """Obtém a posição atual da reprodução (0.0 a 1.0)"""
        return self.player.get_position()

    def set_rate(self, rate):
        """Define a velocidade de reprodução"""
        try:
            # Validar o valor da velocidade
            rate = float(rate)
            if rate < 0.25:  # Limitar velocidade mínima
                rate = 0.25
            elif rate > 2.0:  # Limitar velocidade máxima
                rate = 2.0
            
            # Verificar estado da mídia e aguardar até que esteja pronto
            max_wait_time = 5  # Tempo máximo de espera em segundos
            start_time = time.time()
            while self.player.get_state() not in [vlc.State.Playing, vlc.State.Paused]:
                if time.time() - start_time > max_wait_time:
                    print("Tempo de espera excedido para o estado da mídia")
                    return False
                time.sleep(0.1)
            
            # Tentar definir a velocidade
            success = self.player.set_rate(rate)
            current_rate = self.player.get_rate()
            print(f"Tentando definir velocidade para: {rate:.2f}x, Velocidade atual: {current_rate:.2f}x")
            if success:
                print(f"Velocidade definida para: {rate:.2f}x")
                return True
            
            print(f"Falha ao definir velocidade: {rate:.2f}x")
            return False
            
        except Exception as e:
            print(f"Erro ao definir velocidade: {e}")
            return False

    def get_rate(self):
        """Obtém a velocidade atual de reprodução"""
        try:
            rate = self.player.get_rate()
            return float(rate) if rate is not None else 1.0
        except Exception as e:
            print(f"Erro ao obter velocidade: {e}")
            return 1.0

    def get_length(self):
        """Obtém a duração total em milissegundos"""
        try:
            length = self.player.get_length()
            if length <= 0:
                # Tentar obter a duração da mídia diretamente
                media = self.player.get_media()
                if (media):
                    media.parse()
                    length = media.get_duration()
            return max(0, length)
        except Exception as e:
            print(f"Erro ao obter duração: {e}")
            return 0

    def get_time(self):
        """Obtém o tempo atual em milissegundos"""
        try:
            time = self.player.get_time()
            return max(0, time if time is not None else 0)
        except Exception as e:
            print(f"Erro ao obter tempo atual: {e}")
            return 0

    def set_time(self, time_ms):
        """Define o tempo atual em milissegundos"""
        try:
            # Garantir que o tempo está dentro dos limites
            duration = self.get_length()
            time_ms = max(0, min(time_ms, duration))
            
            # Aplicar o tempo
            self.player.set_time(int(time_ms))
            
            # Pequena pausa para o seek completar
            time.sleep(0.05)
            
            return True
        except Exception as e:
            print(f"Erro ao definir tempo: {e}")
            return False

    def is_playing(self):
        """Verifica se está reproduzindo"""
        return self.player.is_playing()

    def release(self):
        """Libera os recursos do player"""
        self.player.release()