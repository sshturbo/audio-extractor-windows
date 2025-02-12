from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
                           QSlider, QLabel, QSizePolicy, QStyle)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize, QUrl
from PyQt5.QtGui import QImage, QPalette, QColor
from pathlib import Path
from src.video_editor.vlc_player import VLCPlayer
import traceback

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
        self.selected_video = None
        
        # Timer para atualizar a posição
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(100)
        self.update_timer.timeout.connect(self.update_position)
        
        # Configurar widget antes do setup da UI
        self.setup_video_widget()
        self.setup_ui()

    def setup_video_widget(self):
        """Configura o widget de vídeo para garantir janela dedicada"""
        self.video_widget = QFrame()
        self.video_widget.setAutoFillBackground(True)
        
        # Configurar paleta para fundo preto
        palette = self.video_widget.palette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0))
        self.video_widget.setPalette(palette)
        
        # Definir política de tamanho
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_widget.setMinimumSize(640, 360)  # 16:9 aspect ratio

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Adicionar widget de vídeo
        layout.addWidget(self.video_widget)
        
        # Controles
        controls = QFrame()
        controls.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.7);
                border-radius: 10px;
                padding: 5px;
            }
        """)
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(10, 5, 10, 5)
        
        # Progress bar e tempo
        time_layout = QHBoxLayout()
        
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #666;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #fff;
                border: 2px solid #666;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #3498db;
                border-radius: 2px;
            }
        """)
        
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: white;")
        
        time_layout.addWidget(self.position_slider)
        time_layout.addWidget(self.time_label)
        
        controls_layout.addLayout(time_layout)
        
        # Botões de controle
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.play_button = QPushButton()
        self.stop_button = QPushButton()
        self.mute_button = QPushButton()
        
        button_size = QSize(32, 32)
        for button in [self.play_button, self.stop_button, self.mute_button]:
            button.setFixedSize(button_size)
            button.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.1);
                    border: none;
                    border-radius: 16px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.2);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.15);
                }
            """)
        
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.mute_button.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume))
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #666;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #fff;
                border: 2px solid #666;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::sub-page:horizontal {
                background: #3498db;
                border-radius: 2px;
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.mute_button)
        button_layout.addWidget(self.volume_slider)
        button_layout.addStretch()
        
        controls_layout.addLayout(button_layout)
        layout.addWidget(controls)
        
        # Conectar eventos
        self.play_button.clicked.connect(self.toggle_play)
        self.stop_button.clicked.connect(self.stop)
        self.position_slider.sliderMoved.connect(self.set_position)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.mute_button.clicked.connect(self.toggle_mute)

    def load_video(self, video_path):
        try:
            print(f"Carregando vídeo: {video_path}")
            
            if self.player:
                self.player.stop()
                self.player = None
            
            # Criar novo player
            self.player = VLCPlayer(self.video_widget)
            success = self.player.load(video_path)
            
            if success:
                # Configurar player
                self.duration = self.player.get_length()
                self.position_slider.setRange(0, self.duration)
                self.update_time_label(0)
                
                # Habilitar controles
                self.play_button.setEnabled(True)
                self.stop_button.setEnabled(True)
                self.position_slider.setEnabled(True)
                self.volume_slider.setEnabled(True)
                self.mute_button.setEnabled(True)
                
                # Iniciar timer de atualização
                self.update_timer.start()
                
                print("Vídeo carregado com sucesso")
                return True
            
            print("Erro ao carregar vídeo")
            return False
                
        except Exception as e:
            print(f"Erro ao carregar vídeo: {e}")
            traceback.print_exc()
            return False

    def play(self):
        """Inicia reprodução do vídeo"""
        if not self.player:
            # Se não há player mas tem vídeo selecionado, carrega primeiro
            if self.selected_video:
                if self.load_video(self.selected_video):
                    self.toggle_play()
            return
        
        self.toggle_play()

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
            # Parar timer de atualização primeiro
            self.update_timer.stop()
            
            # Parar player e realizar limpeza
            self.player.stop()
            self.is_playing = False
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.position_slider.setValue(0)
            self.update_time_label(0)
            
            # Desabilitar controles até que um novo vídeo seja carregado
            self.play_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.position_slider.setEnabled(False)
            
        except Exception as e:
            print(f"Erro ao parar reprodução: {e}")
            traceback.print_exc()

    def closeEvent(self, event):
        """Chamado quando o widget é fechado"""
        try:
            if self.player:
                self.update_timer.stop()
                self.player.stop()
                self.player.release()
                self.player = None
        except Exception as e:
            print(f"Erro ao liberar recursos: {e}")
        super().closeEvent(event)

    def set_position(self, position):
        if not self.player:
            return
            
        try:
            self.player.set_time(position)
            self.update_time_label(position)
            
        except Exception as e:
            print(f"Erro ao definir posição: {e}")
            traceback.print_exc()

    def update_position(self):
        if not self.player or not self.is_playing:
            return
            
        try:
            position = self.player.get_time()
            if position >= 0 and not self.position_slider.isSliderDown():
                self.position_slider.setValue(position)
                self.update_time_label(position)
                
        except Exception as e:
            print(f"Erro ao atualizar posição: {e}")
            traceback.print_exc()

    def set_volume(self, value):
        if not self.player:
            return
            
        try:
            self.player.set_volume(value)
            self.mute_button.setIcon(
                self.style().standardIcon(
                    QStyle.SP_MediaVolumeMuted if value == 0 else QStyle.SP_MediaVolume
                )
            )
        except Exception as e:
            print(f"Erro ao definir volume: {e}")
            traceback.print_exc()

    def toggle_mute(self):
        if not self.player:
            return
            
        try:
            current_volume = self.volume_slider.value()
            if current_volume > 0:
                self.last_volume = current_volume
                self.volume_slider.setValue(0)
            else:
                self.volume_slider.setValue(getattr(self, 'last_volume', 100))
                
        except Exception as e:
            print(f"Erro ao alternar mudo: {e}")
            traceback.print_exc()

    def update_time_label(self, position):
        try:
            current = self.format_time(position)
            total = self.format_time(self.duration)
            self.time_label.setText(f"{current} / {total}")
        except Exception as e:
            print(f"Erro ao atualizar label de tempo: {e}")

    def format_time(self, ms):
        """Converte milissegundos em formato MM:SS"""
        try:
            s = int(ms / 1000)
            m = int(s / 60)
            s = s % 60
            return f"{m:02d}:{s:02d}"
        except Exception as e:
            print(f"Erro ao formatar tempo: {e}")
            return "00:00"
