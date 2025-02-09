from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QSlider, QLabel, QStyle, QFrame)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPalette, QColor
import vlc
import sys

class VideoPlayer(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.player = None
        self.instance = None
        self.setup_ui()
        self.setup_player()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Widget de vídeo com fundo preto
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: black;")
        layout.addWidget(self.video_frame, stretch=1)
        
        # Controles
        controls = QFrame()
        controls.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 8px;
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
                border: 1px solid #999999;
                height: 8px;
                background: #4d4d4d;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4CAF50;
                border: 1px solid #5cd65f;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: #4CAF50;
                border-radius: 4px;
            }
        """)
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: white;")
        
        time_layout.addWidget(self.position_slider)
        time_layout.addWidget(self.time_label)
        
        # Botões de controle
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.play_button = QPushButton()
        self.stop_button = QPushButton()
        
        # Usar ícones do sistema
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        
        # Estilizar botões
        button_style = """
            QPushButton {
                background-color: #4CAF50;
                border: none;
                border-radius: 15px;
                padding: 8px;
                min-width: 30px;
                min-height: 30px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """
        self.play_button.setStyleSheet(button_style)
        self.stop_button.setStyleSheet(button_style)
        
        # Adicionar botões ao layout
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.play_button)
        buttons_layout.addWidget(self.stop_button)
        buttons_layout.addStretch()
        
        controls_layout.addLayout(time_layout)
        controls_layout.addLayout(buttons_layout)
        layout.addWidget(controls)
        
        # Conectar sinais
        self.play_button.clicked.connect(self.toggle_play)
        self.stop_button.clicked.connect(self.stop)
        self.position_slider.sliderMoved.connect(self.set_position)
        
        # Timer para atualizar a posição
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(100)
        self.update_timer.timeout.connect(self.update_ui)

    def setup_player(self):
        # Configurar instância VLC com parâmetros corretos e mínimos
        vlc_args = [
            '--no-audio',  # Desabilitar áudio
            '--quiet',     # Reduzir logs
            '--no-video-title-show',  # Não mostrar título do vídeo
            '--no-xlib'    # Evitar uso do X11
        ]
        
        try:
            self.instance = vlc.Instance(vlc_args)
            if self.instance:
                self.player = self.instance.media_player_new()
                if sys.platform == "win32":
                    self.player.set_hwnd(self.video_frame.winId())
                elif sys.platform == "darwin":
                    self.player.set_nsobject(int(self.video_frame.winId()))
                else:
                    self.player.set_xwindow(self.video_frame.winId())
                    
                # Configurar parâmetros adicionais do player
                self.player.video_set_deinterlace('disabled')
                
            else:
                print("Erro: Não foi possível criar instância do VLC")
                self.player = None
                
        except Exception as e:
            print(f"Erro ao configurar player VLC: {e}")
            self.instance = None
            self.player = None

    def load_video(self, video_path):
        if not self.instance or not self.player:
            print("Player VLC não inicializado corretamente")
            return
            
        try:
            media = self.instance.media_new(str(video_path))
            if media:
                # Configurar opções de mídia
                media.add_option(":no-audio")
                media.add_option(":quiet")
                self.player.set_media(media)
            else:
                print("Erro ao criar mídia VLC")
        except Exception as e:
            print(f"Erro ao carregar vídeo: {e}")

    def toggle_play(self):
        if not self.player:
            return
            
        try:
            if self.player.is_playing():
                self.player.pause()
                self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
                self.update_timer.stop()
            else:
                self.player.play()
                self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
                self.update_timer.start()
        except Exception as e:
            print(f"Erro ao alternar reprodução: {e}")

    def stop(self):
        if not self.player:
            return
            
        try:
            self.player.stop()
            self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.update_timer.stop()
            self.position_slider.setValue(0)
            self.time_label.setText("00:00 / 00:00")
        except Exception as e:
            print(f"Erro ao parar reprodução: {e}")

    def set_position(self, position):
        if not self.player:
            return
            
        try:
            self.player.set_position(position / 1000.0)
        except Exception as e:
            print(f"Erro ao definir posição: {e}")

    def update_ui(self):
        if not self.player:
            return
            
        try:
            media_pos = int(self.player.get_position() * 1000)
            self.position_slider.setValue(media_pos)
            
            # Atualizar label de tempo
            if self.player.get_length() > 0:
                current = self.format_time(self.player.get_time())
                total = self.format_time(self.player.get_length())
                self.time_label.setText(f"{current} / {total}")
        except Exception as e:
            print(f"Erro ao atualizar UI: {e}")

    def format_time(self, ms):
        s = ms // 1000
        m = s // 60
        s = s % 60
        return f"{m:02d}:{s:02d}"
