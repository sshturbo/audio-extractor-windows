from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QPushButton, QSlider, QLabel, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtMultimedia import QMediaPlayer
from .timeline import Timeline  # Corrigindo o import para usar caminho relativo
import vlc
import ffmpeg
import sys
from pathlib import Path

class VideoEditor(QMainWindow):
    def __init__(self, video_file=None, audio_file=None):
        super().__init__()
        self.video_file = None  # Inicialmente nenhum vídeo carregado
        self.audio_file = audio_file
        self.audio_offset = 0
        self.setup_ui()
        # Conectar sinais da timeline
        self.timeline.clipSelected.connect(self.on_clip_selected)

    def setup_ui(self):
        self.setWindowTitle("Editor de Vídeo/Áudio")
        self.setGeometry(100, 100, 1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Área do player de vídeo (inicialmente vazia)
        self.video_widget = QWidget()
        self.video_widget.setStyleSheet("background-color: black;")
        layout.addWidget(self.video_widget)

        # Área da timeline
        self.timeline = Timeline()  # Usar a classe Timeline que modificamos
        layout.addWidget(self.timeline)

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
        
        self.import_video_btn = QPushButton("Importar Vídeo")
        self.import_video_btn.clicked.connect(self.import_video)
        controls_layout.insertWidget(0, self.import_video_btn)  # Adicionar no início

        self.play_btn = QPushButton("⏵")
        self.play_btn.clicked.connect(self.toggle_playback)
        self.play_btn.setEnabled(False)  # Desabilitar até que um vídeo seja selecionado

        self.import_audio_btn = QPushButton("Importar Áudio")
        self.import_audio_btn.clicked.connect(self.import_new_audio)
        
        self.export_btn = QPushButton("Exportar")
        self.export_btn.clicked.connect(self.export_video)

        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.import_audio_btn)
        controls_layout.addWidget(self.export_btn)
        
        layout.addLayout(controls_layout)

    def on_clip_selected(self, filepath):
        """Chamado quando um clip é selecionado na timeline"""
        print(f"Carregando vídeo no player: {filepath}")
        if hasattr(self, 'video_player'):
            self.video_player.stop()
            self.video_player.release()
        
        # Configurar novo player
        self.setup_video_player(filepath)
        # Atualizar controles
        self.play_btn.setEnabled(True)

    def setup_video_player(self, video_file):
        """Configura o player de vídeo com um arquivo específico"""
        if not hasattr(self, 'vlc_instance'):
            self.vlc_instance = vlc.Instance()
        
        self.video_player = self.vlc_instance.media_player_new()
        self.video_player.set_hwnd(self.video_widget.winId())
        video_media = self.vlc_instance.media_new(video_file)
        self.video_player.set_media(video_media)

    def setup_audio_player(self):
        """Configura o player de áudio"""
        if not hasattr(self, 'vlc_instance'):
            self.vlc_instance = vlc.Instance()
        
        self.audio_player = self.vlc_instance.media_player_new()
        audio_media = self.vlc_instance.media_new(self.audio_file)
        self.audio_player.set_media(audio_media)

    def setup_players(self):
        """Agora só configura o player de áudio"""
        if not hasattr(self, 'vlc_instance'):
            self.vlc_instance = vlc.Instance()
        
        # Player de áudio
        self.audio_player = self.vlc_instance.media_player_new()
        audio_media = self.vlc_instance.media_new(self.audio_file)
        self.audio_player.set_media(audio_media)

    def toggle_playback(self):
        """Atualizado para checar se o player existe"""
        if not hasattr(self, 'video_player'):
            QMessageBox.warning(self, "Aviso", "Por favor, selecione um vídeo na timeline primeiro")
            return
            
        if self.video_player.is_playing():
            self.video_player.pause()
            if hasattr(self, 'audio_player'):
                self.audio_player.pause()
            self.play_btn.setText("⏵")
        else:
            self.video_player.play()
            if hasattr(self, 'audio_player'):
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

    def import_video(self):
        """Importa um novo vídeo para a timeline"""
        file_name, _ = QFileDialog.getOpenFileName(self,
            "Selecionar Arquivo de Vídeo",
            "",
            "Arquivos de Vídeo (*.mp4 *.avi *.mkv);;Todos os Arquivos (*)"
        )
        
        if file_name:
            # Apenas carregar na timeline, não no player
            if self.timeline.load_video(file_name):
                self.video_file = file_name
                print(f"Vídeo importado para timeline: {file_name}")
            else:
                QMessageBox.warning(self, "Erro", "Falha ao carregar vídeo na timeline")

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
