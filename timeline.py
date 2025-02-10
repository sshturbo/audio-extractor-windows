from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                           QSlider, QLabel, QFrame)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QUrl, QRect
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

class TimelineSegment(QFrame):
    clicked = pyqtSignal(object)
    
    def __init__(self, start_time, duration, label=""):
        super().__init__()
        self.start_time = start_time
        self.duration = duration
        self.label = label
        self.setStyleSheet("""
            QFrame {
                background-color: #4CAF50;
                border-radius: 4px;
                min-height: 40px;
            }
            QFrame:hover {
                background-color: #45a049;
            }
        """)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self)

class Timeline(QWidget):
    timeChanged = pyqtSignal(float)
    clipSelected = pyqtSignal(str)  # Novo sinal para clips selecionados
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_time = 0
        self.duration = 0
        self.segments = []
        self.selected_segment = None
        self.media_player = QMediaPlayer()
        self.media_player.positionChanged.connect(self.update_position)
        self.media_player.durationChanged.connect(self.set_duration)
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Área da timeline
        self.timeline_area = QFrame()
        self.timeline_area.setMinimumHeight(100)
        self.timeline_area.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 4px;
            }
        """)
        
        # Controles de playback
        controls_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("⏵")
        self.stop_btn = QPushButton("⏹")
        self.split_btn = QPushButton("✂️ Dividir")
        
        for btn in [self.play_btn, self.stop_btn, self.split_btn]:
            btn.setFixedWidth(80)
            controls_layout.addWidget(btn)
        
        # Slider e tempo
        self.time_slider = QSlider(Qt.Horizontal)
        self.time_label = QLabel("00:00 / 00:00")
        
        controls_layout.addWidget(self.time_slider)
        controls_layout.addWidget(self.time_label)
        
        layout.addWidget(self.timeline_area)
        layout.addLayout(controls_layout)
        
        # Conectar sinais
        self.play_btn.clicked.connect(self.toggle_playback)
        self.stop_btn.clicked.connect(self.stop)
        self.split_btn.clicked.connect(self.split_at_current_time)
        self.time_slider.valueChanged.connect(self.seek)
        
        # Timer para atualização
        self.update_timer = QTimer()
        self.update_timer.setInterval(100)  # 100ms
        self.update_timer.timeout.connect(self.update_time)
        
    def set_media(self, file_path):
        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
            
    def toggle_playback(self):
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.play_btn.setText("⏵")
            self.update_timer.stop()
        else:
            self.media_player.play()
            self.play_btn.setText("⏸")
            self.update_timer.start()
            
    def stop(self):
        self.media_player.stop()
        self.play_btn.setText("⏵")
        self.update_timer.stop()
        
    def seek(self, value):
        self.media_player.setPosition(value)
            
    def update_position(self, position):
        if not self.time_slider.isSliderDown():
            self.time_slider.setValue(position)
        self.update_time_label(position)
                
    def set_duration(self, duration):
        self.time_slider.setRange(0, duration)
        self.duration = duration
        self.update_time_label(self.media_player.position())
        
    def update_time_label(self, position):
        current = self.format_time(position)
        total = self.format_time(self.duration)
        self.time_label.setText(f"{current} / {total}")

    def format_time(self, ms):
        s = ms // 1000
        m = s // 60
        s = s % 60
        return f"{m:02d}:{s:02d}"
        
    def add_segment(self, start_time, duration, filepath=""):
        segment = {
            'start_time': start_time,
            'duration': duration,
            'filepath': filepath
        }
        self.segments.append(segment)
        self.update()
        
    def split_at_current_time(self):
        if self.media_player:
            current_time = self.media_player.position()
            # Emitir sinal para criar novo segmento
            self.timeChanged.emit(current_time / 1000.0)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Encontrar segmento clicado com validação
            clicked_segment = None
            for segment in self.segments:
                if not isinstance(segment, dict):
                    continue
                    
                try:
                    x = int(segment['start_time'] * self.width() / max(self.duration, 1))
                    width = int(segment['duration'] * self.width() / max(self.duration, 1))
                    if event.x() >= x and event.x() <= x + width:
                        clicked_segment = segment
                        break
                except (KeyError, TypeError, ZeroDivisionError):
                    continue

            # Atualizar seleção e emitir sinal apenas se houver mudança
            if clicked_segment != self.selected_segment:
                self.selected_segment = clicked_segment
                if clicked_segment and 'filepath' in clicked_segment:
                    print(f"Emitindo sinal clipSelected: {clicked_segment['filepath']}")
                    self.clipSelected.emit(clicked_segment['filepath'])
                self.update()

        super().mousePressEvent(event)

    def load_video(self, video_path):
        """Carrega um vídeo na timeline"""
        # Primeiro limpar segmentos existentes
        self.segments.clear()
        self.selected_segment = None  # Resetar seleção
        
        # Obter duração do vídeo
        try:
            import ffmpeg
            probe = ffmpeg.probe(video_path)
            duration = float(probe['streams'][0]['duration'])
            
            # Adicionar como um segmento completo
            self.add_segment(0, duration, video_path)
            self.duration = duration
            
            # Atualizar UI
            self.time_slider.setRange(0, int(duration * 1000))  # Converter para ms
            self.update_time_label(0)
            self.update()
            
            print(f"Vídeo carregado na timeline: {video_path}")
            return True
            
        except Exception as e:
            print(f"Erro ao carregar vídeo na timeline: {e}")
            return False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Desenhar fundo
        painter.fillRect(self.rect(), QColor("#1E1E1E"))

        # Desenhar segmentos
        for segment in self.segments:
            x = int(segment['start_time'] * self.width() / max(self.duration, 1))
            width = int(segment['duration'] * self.width() / max(self.duration, 1))
            
            # Cor diferente para segmento selecionado
            if segment == self.selected_segment:
                color = QColor("#0078D4")  # Azul para selecionado
            else:
                color = QColor("#333333")  # Cinza para não selecionado
                
            rect = QRect(x, 0, width, self.height())
            painter.fillRect(rect, color)
            
            # Borda para segmento selecionado
            if segment == self.selected_segment:
                pen = QPen(QColor("#00A6FF"), 2)
                painter.setPen(pen)
                painter.drawRect(rect)
