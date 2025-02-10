import vlc
from PyQt5.QtWidgets import QFrame, QWidget
from PyQt5.QtCore import Qt
import sys

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
            self.player.set_rate(rate)
            return True
        except Exception as e:
            print(f"Erro ao definir velocidade: {e}")
            return False

    def get_rate(self):
        """Obtém a velocidade atual de reprodução"""
        return self.player.get_rate()

    def get_length(self):
        """Obtém a duração total em milissegundos"""
        return self.player.get_length()

    def get_time(self):
        """Obtém o tempo atual em milissegundos"""
        return self.player.get_time()

    def set_time(self, time_ms):
        """Define o tempo atual em milissegundos"""
        self.player.set_time(time_ms)

    def is_playing(self):
        """Verifica se está reproduzindo"""
        return self.player.is_playing()

    def release(self):
        """Libera os recursos do player"""
        self.player.release()