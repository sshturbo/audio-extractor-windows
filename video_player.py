from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QSlider, QLabel, QStyle, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize 
from PyQt5.QtGui import QImage, QPixmap
import sys
import os
import time
import traceback
from pathlib import Path
from video_editor.vlc_player import VLCPlayer

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
        self.duration = 0
        
        # Carregar stylesheet
        self.setStyleSheet(load_stylesheet('video_player.css'))
        
        self.setup_ui()

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

    def load_video(self, video_path):
        try:
            print(f"Carregando vídeo: {video_path}")
            
            if self.player:
                self.player.stop()
                self.player.release()
            
            self.player = VLCPlayer(self.video_widget)
            success = self.player.load(video_path)
            
            if success:
                # Obter duração do vídeo
                self.duration = self.player.get_length() / 1000.0  # ms para segundos
                
                # Configurar slider
                self.position_slider.setRange(0, int(self.duration * 1000))
                self.position_slider.setSingleStep(1000)
                self.position_slider.setPageStep(5000)
                
                # Atualizar label de duração
                self.time_label.setText(f"00:00 / {self.format_time(self.duration * 1000)}")
                
                # Reconectar sinais
                self.play_button.clicked.connect(self.toggle_play)
                self.stop_button.clicked.connect(self.stop)
                self.position_slider.sliderMoved.connect(self.set_position)
                self.volume_slider.valueChanged.connect(self.set_volume)
                
                # Configurar volume inicial
                initial_volume = 50
                self.volume_slider.setValue(initial_volume)
                self.set_volume(initial_volume)
                
                # Definir taxa de reprodução padrão
                self.player.set_rate(1.0)
                
                # Habilitar controles
                self.play_button.setEnabled(True)
                self.stop_button.setEnabled(True)
                self.position_slider.setEnabled(True)
                self.volume_slider.setEnabled(True)
                
                # Inicializar estado
                self.is_playing = False
                
                return True
            
            print("Erro ao carregar vídeo")
            return False
                
        except Exception as e:
            print(f"Erro ao carregar vídeo: {e}")
            traceback.print_exc()
            return False

    def toggle_play(self):
        if not self.player:
            return
            
        try:
            if self.is_playing:
                self.player.pause()
                self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            else:
                self.player.play()
                self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            
            self.is_playing = not self.is_playing
            
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
            
            # Voltar ao início
            self.player.set_time(0)
            
            # Forçar atualização da posição
            self.position_slider.setValue(0)
            self.update_time_label(0)
            
        except Exception as e:
            print(f"Erro ao parar reprodução: {e}")
            traceback.print_exc()

    def set_position(self, position):
        if not self.player or self.duration <= 0:
            return
            
        try:
            time_ms = position
            self.player.set_time(time_ms)
            self.update_time_label(position)
            
        except Exception as e:
            print(f"Erro ao definir posição: {e}")
            traceback.print_exc()

    def set_volume(self, value):
        if self.player:
            try:
                # Usar diretamente o método do VLCPlayer
                self.player.player.audio_set_volume(value)
                # Atualizar ícone do botão mudo
                self.mute_button.setIcon(
                    self.style().standardIcon(
                        QStyle.SP_MediaVolumeMuted if value == 0 else QStyle.SP_MediaVolume
                    )
                )
            except Exception as e:
                print(f"Erro ao definir volume: {e}")

    def toggle_mute(self):
        if self.player:
            try:
                current_volume = self.volume_slider.value()
                if current_volume > 0:
                    self.last_volume = current_volume
                    self.volume_slider.setValue(0)
                    self.mute_button.setIcon(self.style().standardIcon(QStyle.SP_MediaVolumeMuted))
                else:
                    restore_volume = getattr(self, 'last_volume', 50)
                    self.volume_slider.setValue(restore_volume)
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

    def update_time_label(self, position):
        if not self.player:
            return
        try:
            current_time = position
            total_time = int(self.duration * 1000)
            current = self.format_time(current_time)
            total = self.format_time(total_time)
            self.time_label.setText(f"{current} / {total}")
        except Exception as e:
            print(f"Erro ao atualizar label de tempo: {e}")

    def format_time(self, ms):
        """Converte milissegundos em formato MM:SS"""
        try:
            ms = float(ms) if ms else 0
            s = int(ms // 1000)
            m = int(s // 60)
            s = int(s % 60)
            return f"{int(m):02d}:{int(s):02d}"
        except Exception as e:
            print(f"Erro ao formatar tempo: {e}")
            return "00:00"
