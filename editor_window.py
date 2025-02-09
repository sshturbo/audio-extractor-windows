from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QPushButton, QSlider, QLabel, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtMultimedia import QMediaPlayer
import vlc
import ffmpeg
import sys  # Adicionar esta linha
from pathlib import Path

class VideoEditor(QMainWindow):
    def __init__(self, video_file, audio_file):
        super().__init__()
        self.video_file = video_file
        self.audio_file = audio_file
        self.audio_offset = 0  # Offset em milissegundos
        self.setup_ui()
        self.setup_players()

    def setup_ui(self):
        self.setWindowTitle("Editor de Vídeo/Áudio")
        self.setGeometry(100, 100, 1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Área do player de vídeo
        self.video_widget = QWidget()
        self.video_widget.setStyleSheet("background-color: black;")
        layout.addWidget(self.video_widget)

        # Controles de sincronização
        sync_layout = QHBoxLayout()
        
        self.offset_slider = QSlider(Qt.Horizontal)
        self.offset_slider.setRange(-5000, 5000)  # ±5 segundos
        self.offset_slider.valueChanged.connect(self.update_audio_sync)
        
        self.offset_label = QLabel("Offset: 0.0s")
        sync_layout.addWidget(QLabel("Sincronização:"))
        sync_layout.addWidget(self.offset_slider)
        sync_layout.addWidget(self.offset_label)
        
        layout.addLayout(sync_layout)

        # Controles de playback
        controls_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("⏵")
        self.play_btn.clicked.connect(self.toggle_playback)
        
        self.import_audio_btn = QPushButton("Importar Áudio")
        self.import_audio_btn.clicked.connect(self.import_new_audio)
        
        self.export_btn = QPushButton("Exportar")
        self.export_btn.clicked.connect(self.export_video)

        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.import_audio_btn)
        controls_layout.addWidget(self.export_btn)
        
        layout.addLayout(controls_layout)

    def setup_players(self):
        if not hasattr(self, 'vlc_instance'):
            self.vlc_instance = vlc.Instance()
        
        # Player de vídeo
        self.video_player = self.vlc_instance.media_player_new()
        self.video_player.set_hwnd(self.video_widget.winId())
        video_media = self.vlc_instance.media_new(self.video_file)
        self.video_player.set_media(video_media)
        
        # Player de áudio
        self.audio_player = self.vlc_instance.media_player_new()
        audio_media = self.vlc_instance.media_new(self.audio_file)
        self.audio_player.set_media(audio_media)

    def toggle_playback(self):
        if self.video_player.is_playing():
            self.video_player.pause()
            self.audio_player.pause()
            self.play_btn.setText("⏵")
        else:
            self.video_player.play()
            self.audio_player.play()
            self.play_btn.setText("⏸")

    def update_audio_sync(self, value):
        self.audio_offset = value
        self.offset_label.setText(f"Offset: {value/1000:.1f}s")
        if self.audio_player.is_playing():
            current_time = self.video_player.get_time()
            self.audio_player.set_time(current_time + self.audio_offset)

    def import_new_audio(self):
        file_name, _ = QFileDialog.getOpenFileName(self,
            "Selecionar Arquivo de Áudio",
            "",
            "Arquivos de Áudio (*.wav *.mp3 *.aac);;Todos os Arquivos (*)"
        )
        
        if file_name:
            self.audio_file = file_name
            audio_media = self.vlc_instance.media_new(self.audio_file)
            self.audio_player.set_media(audio_media)

    def export_video(self):
        try:
            output_file, _ = QFileDialog.getSaveFileName(self,
                "Salvar Vídeo",
                "",
                "Arquivo de Vídeo (*.mp4)"
            )
            
            if output_file:
                # Calcular offset em segundos
                offset_sec = self.audio_offset / 1000.0
                
                # Configurar streams
                video = ffmpeg.input(self.video_file)
                audio = ffmpeg.input(self.audio_file)
                
                # Aplicar offset se necessário
                if offset_sec != 0:
                    if offset_sec > 0:
                        audio = ffmpeg.filter(audio, 'adelay', f'{int(offset_sec*1000)}|{int(offset_sec*1000)}')
                    else:
                        video = ffmpeg.filter(video, 'setpts', f'PTS+{abs(offset_sec)}/TB')
                
                # Combinar streams
                stream = ffmpeg.output(video, audio, output_file,
                                    acodec='aac',
                                    vcodec='copy')
                
                ffmpeg.run(stream, overwrite_output=True)
                QMessageBox.information(self, "Sucesso", "Vídeo exportado com sucesso!")
                
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao exportar vídeo: {str(e)}")
