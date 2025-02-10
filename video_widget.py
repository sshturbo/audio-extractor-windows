from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QMessageBox
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
import sys
import os
import time
from pathlib import Path

def initialize_vlc():
    """Initialize VLC with proper path handling"""
    try:
        vlc_paths = [
            'C:/Program Files/VideoLAN/VLC',
            'C:/Program Files (x86)/VideoLAN/VLC',
        ]
        
        vlc_found = False
        for vlc_path in vlc_paths:
            if os.path.exists(vlc_path):
                if os.path.exists(os.path.join(vlc_path, 'libvlc.dll')):
                    os.environ['PATH'] = vlc_path + ';' + os.environ['PATH']
                    if hasattr(os, 'add_dll_directory'):
                        os.add_dll_directory(vlc_path)
                    vlc_found = True
                    break

        if not vlc_found:
            raise Exception("VLC não encontrado. Por favor, instale o VLC em seu sistema.")

        import vlc
        return vlc
    except Exception as e:
        print(f"Erro ao inicializar VLC: {e}")
        return None

vlc = initialize_vlc()

class VideoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = None
        
        if vlc is None:
            self.show_vlc_error()
            return
            
        try:
            self.vlc_instance = vlc.Instance([
                '--no-xlib',
                '--quiet',
                '--no-audio-time-stretch',
                '--clock-synchro=0',
                '--no-snapshot-preview',
                '--live-caching=50',
                '--file-caching=50',
                '--disc-caching=50',
                '--network-caching=50',
                '--sout-mux-caching=50'
            ])
        except Exception as e:
            print(f"Erro ao criar instância VLC: {e}")
            self.show_vlc_error()
            return
            
        self.setup_ui()
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_frame)
        self.update_timer.setInterval(30)  # ~30 FPS

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_frame = QLabel()
        self.video_frame.setAlignment(Qt.AlignCenter)
        self.video_frame.setStyleSheet("background-color: black;")
        self.layout.addWidget(self.video_frame)

    def load_video(self, file_path):
        if Path(file_path).exists():
            try:
                if self.player:
                    self.player.stop()
                    self.player.release()
                
                media = self.vlc_instance.media_new(str(file_path))
                self.player = self.vlc_instance.media_player_new()
                self.player.set_media(media)
                
                # Configurar o player para usar o widget de display
                if sys.platform.startswith('linux'):
                    self.player.set_xwindow(self.video_frame.winId())
                elif sys.platform == "win32":
                    self.player.set_hwnd(self.video_frame.winId())
                elif sys.platform == "darwin":
                    self.player.set_nsobject(int(self.video_frame.winId()))
                
                # Otimizações para melhor performance usando opções de mídia
                media.add_option(':avcodec-hw=any')  # Usar aceleração de hardware
                media.add_option(':avcodec-fast')    # Modo rápido de decodificação
                media.add_option(':avcodec-dr')      # Direct rendering
                media.add_option(':no-audio-time-stretch')  # Desabilitar time stretch
                media.add_option(':clock-jitter=0')   # Reduzir jitter
                media.add_option(':clock-synchro=0')  # Sincronização precisa
                media.add_option(':no-snapshot-preview')  # Desabilitar preview
                media.add_option(':live-caching=50')  # Reduzir buffer
                media.add_option(':network-caching=50')  # Reduzir buffer de rede
                media.add_option(':sout-mux-caching=50')  # Reduzir buffer de muxing
                
                print("Vídeo carregado com sucesso")
                return True
            except Exception as e:
                print(f"Erro ao carregar vídeo: {e}")
                import traceback
                traceback.print_exc()
                self.show_error_message(str(e))
        return False

    def play(self):
        if self.player:
            self.player.play()
            self.update_timer.start()

    def pause(self):
        if self.player:
            self.player.pause()
            self.update_timer.stop()

    def stop(self):
        if self.player:
            self.player.stop()
            self.update_timer.stop()

    def set_position(self, position):
        """Set position in percentage (0-1)"""
        if self.player:
            self.player.set_position(position)

    def get_position(self):
        """Get current position in percentage (0-1)"""
        if self.player:
            return self.player.get_position()
        return 0

    def set_volume(self, volume):
        """Set volume (0-100)"""
        if self.player:
            self.player.audio_set_volume(volume)

    def update_frame(self):
        # O VLC atualiza o frame automaticamente
        pass

    def closeEvent(self, event):
        if self.player:
            self.player.stop()
            self.player.release()
        super().closeEvent(event)

    def show_vlc_error(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Erro - VLC não encontrado")
        msg.setText("O VLC Media Player não foi encontrado no sistema.")
        msg.setInformativeText("Por favor, siga os passos abaixo:\n\n"
                             "1. Baixe o VLC de videolan.org\n"
                             "2. Instale o VLC de 64 bits\n"
                             "3. Certifique-se de que a instalação foi concluída\n"
                             "4. Reinicie este aplicativo\n\n"
                             "Nota: Certifique-se de instalar a versão de 64 bits do VLC.")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
