import vlc
from PyQt5.QtWidgets import QFrame, QWidget
from PyQt5.QtCore import Qt
import sys

class VLCPlayer:
    def __init__(self, display_widget):
        # Configurações adicionais para melhor performance
        self.instance = vlc.Instance([
            '--no-xlib',  # Reduzir latência
            '--quiet',    # Reduzir logs
            '--audio-pitch-compensation',  # Manter o pitch do áudio constante
            '--clock-synchro=0',  # Sincronização precisa
            '--no-snapshot-preview',  # Desabilitar preview
            '--live-caching=50',  # Reduzir buffer live
            '--network-caching=50',  # Reduzir buffer de rede
            '--file-caching=50',  # Reduzir buffer de arquivo
            '--disc-caching=50',  # Reduzir buffer de disco
            '--sout-mux-caching=50',  # Reduzir buffer de muxing
            '--vout-filter=deinterlace',  # Melhorar qualidade
            '--deinterlace-mode=blend',  # Modo de desentrelaçamento
            '--preferred-resolution=-1',  # Resolução nativa
            '--avcodec-threads=0',  # Threads automático
            '--avcodec-hw=any',  # Usar qualquer aceleração de hardware
            '--high-priority',  # Alta prioridade
        ])
        self.player = self.instance.media_player_new()
        
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
            # Configurar opções de mídia para melhor performance
            if sys.platform == "win32":
                # Otimizações específicas para Windows
                media.add_option(':avcodec-hw=dxva2')  # DirectX Video Acceleration
                media.add_option(':d3d11-hw-device=1')  # Direct3D 11
            else:
                media.add_option(':avcodec-hw=any')

            # Otimizações gerais
            media.add_option(':avcodec-fast')    # Decodificação rápida
            media.add_option(':avcodec-dr')      # Direct rendering
            media.add_option(':audio-pitch-compensation')  # Manter pitch do áudio
            media.add_option(':audio-time-stretch')  # Esticar áudio sem mudar pitch
            media.add_option(':clock-jitter=0')   # Reduzir jitter
            media.add_option(':clock-synchro=0')  # Sincronização precisa
            media.add_option(':vout-filter=deinterlace')  # Desentrelaçamento
            media.add_option(':deinterlace-mode=blend')  # Modo de desentrelaçamento
            media.add_option(':live-caching=50')  # Reduzir buffer
            media.add_option(':network-caching=50')  # Reduzir buffer de rede
            media.add_option(':sout-mux-caching=50')  # Reduzir buffer de muxing
            
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
        """Define a velocidade de reprodução mantendo o pitch"""
        try:
            if rate != 1.0:
                # Configurar compensação de pitch antes de alterar a velocidade
                media = self.player.get_media()
                media.add_option(':audio-pitch-compensation')
                media.add_option(':audio-time-stretch')
                
                # Otimizar parâmetros para diferentes velocidades
                if rate < 1.0:
                    # Configurações para reprodução lenta
                    self.player.set_rate(rate)
                else:
                    # Configurações para reprodução rápida
                    self.player.set_rate(rate)
            else:
                # Resetar para configurações normais
                self.player.set_rate(1.0)
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