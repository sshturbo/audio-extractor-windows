from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QScrollArea, QFrame,
                           QHBoxLayout, QPushButton, QLabel)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QRect
from PyQt5.QtGui import QPainter, QColor, QPen
from pathlib import Path  # Adicionar importação do Path

class TimelineTrack(QFrame):
    clip_dropped = pyqtSignal(str, float)  # filepath, position
    
    def __init__(self, track_type="video"):
        super().__init__()
        self.track_type = track_type
        self.clips = []
        self.setAcceptDrops(True)
        self.setMinimumHeight(60)
        self.setStyleSheet("""
            QFrame {
                background-color: #2D2D2D;
                border: 1px solid #404040;
                border-radius: 4px;
                margin: 2px;
            }
            QFrame:hover {
                border-color: #0078D4;
            }
        """)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-clip"):
            event.accept()
            
    def dropEvent(self, event):
        pos = event.pos()
        time_pos = pos.x() / self.width()  # Normalizado 0-1
        self.clip_dropped.emit(event.mimeData().text(), time_pos)

class TimelineClip(QFrame):
    def __init__(self, filepath, duration):
        super().__init__()
        self.filepath = filepath
        self.duration = duration
        self.setFixedHeight(48)
        self.setStyleSheet("""
            QFrame {
                background-color: #4CAF50;
                border-radius: 4px;
            }
            QFrame:hover {
                background-color: #45a049;
            }
        """)

class MultiTrackTimeline(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
            }
            QScrollArea {
                border: none;
            }
            QPushButton {
                background-color: #0078D4;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-size: 12px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #1084D9;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
                font-weight: bold;
                padding: 5px;
            }
        """)
        self.clips = []  # Lista de clips na timeline
        self.current_time = 0
        self.scale_factor = 100  # pixels por segundo
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Área rolável para as trilhas
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        
        # Container para as trilhas
        tracks_widget = QWidget()
        self.tracks_layout = QVBoxLayout(tracks_widget)
        
        # Adicionar trilhas iniciais
        self.video_track = TimelineTrack("video")
        self.audio_track = TimelineTrack("audio")
        
        self.tracks_layout.addWidget(QLabel("Vídeo"))
        self.tracks_layout.addWidget(self.video_track)
        self.tracks_layout.addWidget(QLabel("Áudio"))
        self.tracks_layout.addWidget(self.audio_track)
        
        scroll_area.setWidget(tracks_widget)
        
        # Controles
        controls = QHBoxLayout()
        
        add_video_track = QPushButton("+ Trilha de Vídeo")
        add_audio_track = QPushButton("+ Trilha de Áudio")
        
        add_video_track.clicked.connect(lambda: self.add_track("video"))
        add_audio_track.clicked.connect(lambda: self.add_track("audio"))
        
        controls.addWidget(add_video_track)
        controls.addWidget(add_audio_track)
        controls.addStretch()
        
        layout.addLayout(controls)
        layout.addWidget(scroll_area)
        
    def add_track(self, track_type):
        label = QLabel("Vídeo" if track_type == "video" else "Áudio")
        track = TimelineTrack(track_type)
        
        self.tracks_layout.addWidget(label)
        self.tracks_layout.addWidget(track)
        
    def add_clip(self, filepath, start_time, track_index):
        """Adiciona um novo clip à timeline"""
        clip = {
            'filepath': filepath,
            'start_time': start_time,
            'track': track_index,
            'duration': self.get_clip_duration(filepath)
        }
        self.clips.append(clip)
        self.update()
        
    def get_clip_duration(self, filepath):
        """Obtém a duração do clip em segundos"""
        try:
            import av
            container = av.open(filepath)
            duration = float(container.duration) / av.time_base
            container.close()
            return duration
        except Exception as e:
            print(f"Erro ao obter duração: {e}")
            return 10.0  # duração padrão
            
    def paintEvent(self, event):
        """Desenha a timeline"""
        painter = QPainter(self)
        
        # Desenhar trilhas
        track_height = 50
        for i in range(3):  # 3 trilhas
            y = i * (track_height + 5)
            painter.fillRect(0, y, self.width(), track_height, QColor("#2D2D2D"))
            
        # Desenhar clips
        for clip in self.clips:
            # Converter valores float para int antes de desenhar
            x = int(clip['start_time'] * self.scale_factor)
            y = int(clip['track'] * (track_height + 5))
            width = int(clip['duration'] * self.scale_factor)
            
            # Criar QRect para o clip
            clip_rect = QRect(x, y, width, track_height)
            painter.fillRect(clip_rect, QColor("#4CAF50"))
            
            # Nome do arquivo
            clip_name = Path(clip['filepath']).name
            painter.setPen(Qt.white)
            painter.drawText(x + 5, y + 25, clip_name)
        
    def zoom_in(self):
        """Aumenta o zoom da timeline"""
        self.scale_factor *= 1.2
        self.update()
        
    def zoom_out(self):
        """Diminui o zoom da timeline"""
        self.scale_factor /= 1.2
        self.update()
        
    def cut_selected_clip(self):
        # Implementar lógica de corte
        pass
        
    def split_at_playhead(self):
        # Implementar lógica de divisão
        pass
        
    def export_timeline(self, output_file):
        # Implementar lógica de exportação
        pass
