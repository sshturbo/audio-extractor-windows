import vlc
from PyQt5.QtWidgets import QFrame, QWidget
from PyQt5.QtCore import Qt
import sys
import time
from typing import Optional
import ctypes

class VLCPlayer:
    def __init__(self, widget):
        """Inicializa o player VLC com configurações otimizadas"""
        # Configuração com software decoding como fallback
        params = [
            '--no-video-deco',          # Desabilitar decorações de vídeo
            '--no-snapshot-preview',     # Desabilitar preview de snapshot
            '--no-video-title-show',     # Não mostrar título do vídeo
            '--no-embedded-video',       # Não usar embedded video
            '--avcodec-hw=d3d11va,none', # Tentar D3D11 primeiro, fallback para software
            '--no-audio-time-stretch',   # Desabilitar time stretching
            '--quiet',                   # Suprimir mensagens de log do VLC
        ]
        
        self.instance = vlc.Instance(params)
        self.player = self.instance.media_player_new()
        self.widget = widget
        
        if sys.platform.startswith('linux'):  # Linux
            self.player.set_xwindow(widget.winId())
        elif sys.platform == "win32":  # Windows
            if not isinstance(widget.winId(), int):
                hwnd = int(widget.winId())
            else:
                hwnd = widget.winId()
            if hwnd == 0:
                raise Exception("Invalid window handle")
            
            if not ctypes.windll.user32.IsWindow(hwnd):
                raise Exception("Invalid window handle")
                
            # Configurar opções de vídeo antes de definir a janela
            self.player.video_set_key_input(False)
            self.player.video_set_mouse_input(False)
            self.player.set_hwnd(hwnd)
        elif sys.platform == "darwin":  # macOS
            self.player.set_nsobject(int(widget.winId()))

    def load(self, file_path: str) -> bool:
        """Carrega um arquivo de mídia"""
        try:
            # Criar media com opções otimizadas
            media = self.instance.media_new(file_path)
            media.add_option('input-repeat=0')  # Não repetir
            media.add_option('avcodec-hw=d3d11va,none')  # Tentar hardware decoding, fallback para software
            media.add_option('quiet')  # Suprimir mensagens de log
            
            # Configurar media
            self.player.set_media(media)
            return True
        except Exception as e:
            print(f"Erro ao carregar mídia: {e}")
            return False

    def play(self) -> None:
        """Inicia a reprodução"""
        self.player.play()

    def pause(self) -> None:
        """Pausa a reprodução"""
        self.player.pause()

    def stop(self) -> None:
        """Para a reprodução com limpeza adequada"""
        try:
            if self.player:
                # Parar reprodução
                self.player.stop()
                
                # Pequeno delay para garantir que o vídeo pare completamente
                time.sleep(0.1)
                
                # Limpar tracks de vídeo
                if self.player.get_media():
                    self.player.get_media().release()
                
                # Limpar o media atual
                self.player.set_media(None)
                
                # Forçar atualização da janela de vídeo
                if sys.platform == "win32" and self.widget:
                    try:
                        self.widget.update()
                    except Exception:
                        pass
                        
        except Exception as e:
            print(f"Erro ao parar reprodução: {e}")

    def set_time(self, ms: int) -> None:
        """Define a posição atual em milissegundos"""
        self.player.set_time(ms)

    def get_time(self) -> int:
        """Obtém a posição atual em milissegundos"""
        return self.player.get_time()

    def get_length(self) -> int:
        """Obtém a duração total em milissegundos"""
        return self.player.get_length()

    def set_volume(self, volume: int) -> None:
        """Define o volume (0-100)"""
        self.player.audio_set_volume(volume)

    def get_volume(self) -> int:
        """Obtém o volume atual (0-100)"""
        return self.player.audio_get_volume()

    def is_playing(self) -> bool:
        """Verifica se está reproduzindo"""
        return self.player.is_playing()

    def set_rate(self, rate: float) -> bool:
        """Define a velocidade de reprodução"""
        return self.player.set_rate(rate)

    def get_rate(self) -> float:
        """Obtém a velocidade de reprodução atual"""
        return self.player.get_rate()

    def set_mute(self, muted: bool) -> None:
        """Define o estado mudo"""
        self.player.audio_set_mute(muted)

    def is_muted(self) -> bool:
        """Verifica se está mudo"""
        return self.player.audio_get_mute()

    def release(self) -> None:
        """Libera os recursos do player com limpeza adequada"""
        try:
            if self.player:
                # Garantir que a reprodução pare primeiro
                self.stop()
                
                # Liberar o player
                self.player.release()
                self.player = None
                
                # Atualizar widget se possível
                if self.widget:
                    try:
                        self.widget.update()
                    except Exception:
                        pass
                
            if self.instance:
                self.instance.release()
                self.instance = None
                
        except Exception as e:
            print(f"Erro ao liberar recursos: {e}")
            
        finally:
            # Garantir que as referências sejam limpas
            self.player = None
            self.instance = None
            self.widget = None