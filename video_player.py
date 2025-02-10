from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QSlider, QLabel, QStyle, QFrame, QSizePolicy, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import QImage, QPixmap
from pathlib import Path
import time
import sys
import os
import ctypes
import traceback  # Added traceback import

def initialize_vlc():
    """Initialize VLC with proper path handling"""
    try:
        # Common VLC installation paths for Windows
        vlc_paths = [
            'C:/Program Files/VideoLAN/VLC',
            'C:/Program Files (x86)/VideoLAN/VLC',
        ]
        
        # Add VLC path to system PATH
        vlc_found = False
        for vlc_path in vlc_paths:
            if os.path.exists(vlc_path):
                # Verificar se libvlc.dll existe
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

# Try to initialize VLC
vlc = initialize_vlc()

def load_stylesheet(filename):
    """Carrega arquivo CSS"""
    css_file = Path(__file__).parent / 'assets' / 'css' / filename
    if css_file.exists():
        with open(css_file, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

class VideoPlayer(QFrame):
    frame_ready = pyqtSignal(QImage)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.player = None
        self.is_playing = False
        
        if (vlc is None):
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
        
        # Carregar stylesheet
        self.setStyleSheet(load_stylesheet('video_player.css'))
        
        self.setup_ui()
        
        # Timer para atualização do vídeo
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_progress)
        self.update_timer.setInterval(30)  # ~30 FPS

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Widget de vídeo com borda arredondada
        video_container = QFrame()
        video_container.setProperty('class', 'video-container')
        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_widget = QLabel()
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_widget.setProperty('class', 'video-widget')
        video_layout.addWidget(self.video_widget)
        
        layout.addWidget(video_container)
        
        # Controles modernos
        controls = QFrame()
        controls.setProperty('class', 'controls-frame')
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(15, 10, 15, 10)
        controls_layout.setSpacing(10)
        
        # Progress bar e tempo com design moderno
        time_layout = QHBoxLayout()
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setProperty('class', 'position-slider')
        
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setProperty('class', 'time-label')
        
        time_layout.addWidget(self.position_slider)
        time_layout.addWidget(self.time_label)
        
        # Container único para todos os controles
        controls_container = QHBoxLayout()
        controls_container.setSpacing(20)
        controls_container.setContentsMargins(10, 0, 10, 0)
        
        # Adicionar stretch para centralizar
        controls_container.addStretch()
        
        # Botões de controle
        self.play_button = QPushButton()
        self.stop_button = QPushButton()
        
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        
        self.play_button.setProperty('class', 'control-button')
        self.stop_button.setProperty('class', 'control-button')
        
        controls_container.addWidget(self.play_button)
        controls_container.addWidget(self.stop_button)
        
        # Volume (agora apenas uma vez)
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(5)
        
        self.mute_button = QPushButton()
        self.mute_button.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume))
        self.mute_button.setFixedSize(30, 30)
        self.mute_button.setProperty('class', 'control-button')
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setProperty('class', 'volume-slider')
        
        volume_layout.addWidget(self.mute_button)
        volume_layout.addWidget(self.volume_slider)
        
        controls_container.addLayout(volume_layout)
        
        # Adicionar stretch para centralizar
        controls_container.addStretch()
        
        # Configurar tamanhos consistentes para todos os botões
        button_size = 35  # Tamanho padrão para todos os botões
        icon_size = int(button_size * 0.6)  # 60% do tamanho do botão
        
        # Definir tamanhos fixos para os botões
        self.play_button.setFixedSize(button_size, button_size)
        self.stop_button.setFixedSize(button_size, button_size)
        self.mute_button.setFixedSize(button_size, button_size)
        
        # Ajustar o tamanho dos ícones de forma consistente
        for btn in [self.play_button, self.stop_button, self.mute_button]:
            btn.setIconSize(QSize(icon_size, icon_size))
        
        # Ajustar volume layout
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(8)  # Espaçamento consistente
        volume_layout.setContentsMargins(0, 0, 0, 0)
        
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setFixedHeight(button_size)  # Mesma altura dos botões
        
        # Adicionar ao layout principal
        controls_layout.addLayout(time_layout)
        controls_layout.addLayout(controls_container)
        layout.addWidget(controls)
        
        # Conectar sinais
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.mute_button.clicked.connect(self.toggle_mute)

    def show_vlc_error(self):
        """Show error message when VLC is not available"""
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

    def load_video(self, video_path):
        try:
            print(f"Carregando vídeo: {video_path}")
            
            if self.player:
                self.player.stop()
                self.player.release()
                
            media = self.vlc_instance.media_new(str(video_path))
            self.player = self.vlc_instance.media_player_new()
            self.player.set_media(media)
            
            # Configurar o player para usar o widget de display
            if sys.platform.startswith('linux'):
                self.player.set_xwindow(self.video_widget.winId())
            elif sys.platform == "win32":
                self.player.set_hwnd(self.video_widget.winId())
            elif sys.platform == "darwin":
                self.player.set_nsobject(int(self.video_widget.winId()))
            
            # Otimizações para melhor performance usando opções de mídia
            media.add_option(':avcodec-hw=any')  # Usar aceleração de hardware
            media.add_option(':avcodec-fast')    # Modo rápido de decodificação
            media.add_option(':avcodec-dr')      # Direct rendering
            media.add_option(':audio-pitch-compensation')  # Manter pitch do áudio
            media.add_option(':audio-time-stretch')  # Esticar áudio sem mudar pitch
            media.add_option(':clock-jitter=0')   # Reduzir jitter
            media.add_option(':clock-synchro=0')  # Sincronização precisa
            media.add_option(':no-snapshot-preview')  # Desabilitar preview
            media.add_option(':live-caching=50')  # Reduzir buffer
            media.add_option(':network-caching=50')  # Reduzir buffer de rede
            media.add_option(':sout-mux-caching=50')  # Reduzir buffer de muxing
            
            # Obter duração do vídeo
            media.parse()
            self.duration = media.get_duration() / 1000.0  # Converter ms para segundos
            
            # Configurar slider
            self.position_slider.setRange(0, int(self.duration * 1000))
            self.position_slider.setSingleStep(1000)  # 1 segundo por step
            self.position_slider.setPageStep(5000)    # 5 segundos por page
            
            # Atualizar label de duração
            self.time_label.setText(f"00:00 / {self.format_time(self.duration)}")
            
            # Desconectar sinais antigos se existirem
            try:
                self.play_button.clicked.disconnect()
                self.stop_button.clicked.disconnect()
            except:
                pass
            
            # Reconectar sinais
            self.play_button.clicked.connect(self.toggle_play)
            self.stop_button.clicked.connect(self.stop)
            self.position_slider.sliderMoved.connect(self.set_position)
            
            # Habilitar controles
            self.play_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            
            # Inicializar estado
            self.is_playing = False
            
            print("Vídeo carregado com sucesso")
            
        except Exception as e:
            print(f"Erro ao carregar vídeo: {e}")
            import traceback
            traceback.print_exc()
            self.duration = 0
            self.position_slider.setRange(0, 0)

    def update_progress(self):
        if self.player and self.player.is_playing():
            current_time = self.player.get_time() / 1000.0  # Converter ms para segundos
            if not self.position_slider.isSliderDown():
                self.position_slider.setValue(int(current_time * 1000))
                self.time_label.setText(f"{self.format_time(current_time)} / {self.format_time(self.duration)}")

    def toggle_play(self):
        if not self.player:
            return
            
        try:
            if self.is_playing:
                print("Pausando...")
                self.player.pause()
                self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
                self.update_timer.stop()
            else:
                print("Reproduzindo...")
                self.player.play()
                self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
                self.update_timer.start()
            
            self.is_playing = not self.is_playing
            print(f"Estado de reprodução: {'Reproduzindo' if self.is_playing else 'Pausado'}")
            
        except Exception as e:
            print(f"Erro ao alternar reprodução: {e}")
            traceback.print_exc()

    def stop(self):
        if not self.player:
            return
            
        try:
            self.player.stop()
            self.is_playing = False
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.update_timer.stop()
            
            # Voltar ao início
            self.player.set_time(0)
            time.sleep(0.1)  # Pequena pausa para garantir que o seek foi completado
            
            # Forçar atualização da posição
            self.position_slider.setValue(0)
            self.time_label.setText(f"00:00 / {self.format_time(self.duration)}")
            
            print("Reprodução parada e resetada")
        except Exception as e:
            print(f"Erro ao parar reprodução: {e}")
            traceback.print_exc()

    def set_position(self, position):
        if not self.player or self.duration <= 0:
            return
            
        try:
            # Converter milissegundos para proporção (0-1)
            pos_ratio = position / (self.duration * 1000)
            
            # Garantir que a posição está dentro dos limites
            pos_ratio = max(0, min(pos_ratio, 1))
            
            # Pausar temporariamente
            was_playing = self.is_playing
            if was_playing:
                self.player.pause()
            
            # Aplicar seek
            self.player.set_position(pos_ratio)
            
            # Atualizar interface
            current_time = position / 1000.0
            self.time_label.setText(f"{self.format_time(current_time)} / {self.format_time(self.duration)}")
            
            # Retomar reprodução se estava reproduzindo
            if was_playing:
                self.player.play()
            
        except Exception as e:
            print(f"Erro ao definir posição: {e}")
            traceback.print_exc()

    def set_volume(self, value):
        if self.player:
            try:
                # VLC espera volume entre 0 e 100
                self.player.audio_set_volume(value)
            except Exception as e:
                print(f"Erro ao definir volume: {e}")

    def toggle_mute(self):
        if self.player:
            try:
                is_muted = self.player.audio_get_mute()
                self.player.audio_set_mute(not is_muted)
                if not is_muted:
                    self.mute_button.setIcon(self.style().standardIcon(QStyle.SP_MediaVolumeMuted))
                else:
                    self.mute_button.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume))
            except Exception as e:
                print(f"Erro ao alternar mudo: {e}")
                traceback.print_exc()

    def closeEvent(self, event):
        if self.player:
            try:
                self.player.stop()
                self.player.release()
            except Exception as e:
                print(f"Erro ao fechar player: {e}")
        super().closeEvent(event)

    def format_time(self, seconds):
        """Converte segundos em formato MM:SS"""
        try:
            m = int(seconds // 60)
            s = int(seconds % 60)
            return f"{m:02d}:{s:02d}"
        except Exception as e:
            print(f"Erro ao formatar tempo: {e}")
            return "00:00"

    def set_playback_speed(self, speed):
        if self.player:
            try:
                media = self.player.get_media()
                # Configurar compensação de pitch antes de alterar a velocidade
                media.add_option(':audio-pitch-compensation')
                media.add_option(':audio-time-stretch')
                self.player.set_rate(speed)
            except Exception as e:
                print(f"Erro ao definir velocidade: {e}")
