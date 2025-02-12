from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QScrollArea, QLabel, QFrame,
                           QMenu, QApplication)
from PyQt5.QtCore import Qt, QMimeData, QByteArray, pyqtSignal, QRect
from PyQt5.QtGui import QPainter, QColor, QPen, QLinearGradient
import json
from pathlib import Path

MIME_TYPE = "application/x-timeline-clip"

def create_clip_data(filepath, duration, media_type):
    return {
        'filepath': str(filepath),
        'duration': float(duration),
        'type': str(media_type),
        'has_audio': media_type == 'video',
        'is_audio_only': media_type == 'audio'
    }

def create_mime_data(clip_data):
    mime = QMimeData()
    data = json.dumps(clip_data).encode('utf-8')
    mime.setData(MIME_TYPE, QByteArray(data))
    return mime

class TimelineTrack(QFrame):
    clip_selected = pyqtSignal(str)
    clip_deleted = pyqtSignal(int)
    audio_ungroup = pyqtSignal(dict)

    def __init__(self, track_type="video"):
        super().__init__()
        self.track_type = track_type
        self.clips = []
        self.selected_clip = None
        self.drop_indicator_pos = None
        self.setAcceptDrops(True)
        self.setMinimumHeight(80)
        self.scale_factor = 100  # Pixels por segundo
        
        self.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #333333;
                border-radius: 8px;
                margin: 3px;
            }
            QFrame[accepting_drop="true"] {
                background-color: #2A2A2B;
                border: 1px solid #0078D4;
            }
        """)

    def contextMenuEvent(self, event):
        """Exibe menu de contexto ao clicar com botão direito"""
        clicked_clip = None
        for clip in self.clips:
            x = int(clip['start_time'] * self.scale_factor)  # Usar scale_factor local
            width = int(clip['duration'] * self.scale_factor)  # Usar scale_factor local
            if event.x() >= x and event.x() <= x + width:
                clicked_clip = clip
                break

        if clicked_clip:
            self.selected_clip = clicked_clip
            self.update()
            
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #252526;
                    color: #E0E0E0;
                    border: 1px solid #404040;
                    border-radius: 6px;
                    padding: 8px;
                }
                QMenu::item {
                    padding: 8px 25px 8px 15px;
                    border-radius: 4px;
                    margin: 2px 4px;
                }
                QMenu::item:selected {
                    background-color: #404040;
                }
            """)

            # Ações do menu
            cut_action = menu.addAction("✂️ Cortar")
            split_action = menu.addAction("🔪 Dividir")
            duplicate_action = menu.addAction("📑 Duplicar")
            menu.addSeparator()
            
            if self.track_type == "video" and clicked_clip.get('has_audio', True):
                remove_audio = menu.addAction("🔇 Remover Áudio")
                ungroup_audio = menu.addAction("↕️ Desagrupar Áudio")
                menu.addSeparator()
                
            delete_action = menu.addAction("🗑️ Excluir")
            
            # Executar ação selecionada
            action = menu.exec_(event.globalPos())
            
            if action == cut_action:
                clip_index = self.clips.index(clicked_clip)
                self.cut_clip(clip_index)
            elif action == split_action:
                clip_index = self.clips.index(clicked_clip)
                split_pos = event.pos().x()
                self.split_clip(clip_index, split_pos)
            elif action == duplicate_action:
                clip_index = self.clips.index(clicked_clip)
                self.duplicate_clip(clip_index)
            elif action == delete_action:
                clip_index = self.clips.index(clicked_clip)
                self.delete_clip(clip_index)
            elif self.track_type == "video":
                if action == remove_audio:
                    clicked_clip['has_audio'] = False
                    self.update()
                elif action == ungroup_audio:
                    clip_index = self.clips.index(clicked_clip)
                    self.ungroup_audio_from_clip(clip_index)

    def mousePressEvent(self, event):
        """Manipula eventos de clique do mouse na timeline"""
        if event.button() == Qt.LeftButton:
            old_selected = self.selected_clip
            clicked_clip = None
            
            # Procura por clip na posição do clique usando scale_factor local
            for clip in self.clips:
                x = int(clip['start_time'] * self.scale_factor)
                width = int(clip['duration'] * self.scale_factor)
                if event.x() >= x and event.x() <= x + width:
                    clicked_clip = clip
                    break
            
            # Atualiza a seleção apenas se houve mudança
            if old_selected != clicked_clip:
                self.selected_clip = clicked_clip
                if clicked_clip:
                    self.clip_selected.emit(clicked_clip['filepath'])
                self.update()  # Redesenha apenas se houve mudança na seleção
                
            # Propagar o evento para permitir o drag
            super().mousePressEvent(event)

    def dragEnterEvent(self, event):
        """Aceita o drag and drop na timeline"""
        if event.mimeData().hasFormat(MIME_TYPE):
            try:
                data = bytes(event.mimeData().data(MIME_TYPE))
                clip_data = json.loads(data.decode('utf-8'))
                
                # Verificar compatibilidade do tipo
                if clip_data['type'] == self.track_type or (
                    self.track_type == 'audio' and clip_data.get('is_audio_only', False)
                ):
                    self.setProperty("accepting_drop", True)
                    self.style().unpolish(self)
                    self.style().polish(self)
                    event.acceptProposedAction()
                    return
                    
            except Exception as e:
                print(f"Erro no dragEnter: {e}")
                
        event.ignore()
        self.setProperty("accepting_drop", False)
        self.style().unpolish(self)
        self.style().polish(self)
        self.drop_indicator_pos = None
        self.update()

    def dragMoveEvent(self, event):
        """Atualiza o feedback visual durante o drag"""
        if event.mimeData().hasFormat(MIME_TYPE):
            try:
                data = bytes(event.mimeData().data(MIME_TYPE))
                clip_data = json.loads(data.decode('utf-8'))
                drop_time = event.pos().x() / self.scale_factor  # Usar scale_factor local
                
                if not self.check_clip_overlap(drop_time, clip_data['duration']):
                    event.acceptProposedAction()
                    self.drop_indicator_pos = event.pos().x()
                    self.update()
                    return
                    
            except Exception as e:
                print(f"Erro no dragMove: {e}")
                
        event.ignore()
        self.drop_indicator_pos = None
        self.update()

    def dropEvent(self, event):
        """Processa o drop na timeline"""
        if event.mimeData().hasFormat(MIME_TYPE):
            try:
                data = bytes(event.mimeData().data(MIME_TYPE))
                clip_data = json.loads(data.decode('utf-8'))
                drop_time = event.pos().x() / self.scale_factor  # Usar scale_factor local
                
                if not self.check_clip_overlap(drop_time, clip_data['duration']):
                    new_clip = {
                        'filepath': str(clip_data['filepath']),
                        'start_time': float(drop_time),
                        'duration': float(clip_data['duration']),
                        'type': str(clip_data['type']),
                        'has_audio': bool(clip_data.get('has_audio', True))
                    }
                    
                    insert_index = self.get_insert_position(drop_time)
                    self.clips.insert(insert_index, new_clip)
                    self.drop_indicator_pos = None
                    self.update()
                    event.acceptProposedAction()
                    return
                    
            except Exception as e:
                print(f"Erro no drop: {e}")
                import traceback
                traceback.print_exc()
                
        event.ignore()
        self.drop_indicator_pos = None
        self.update()

    def check_clip_overlap(self, start_time, duration):
        """
        Verifica se há sobreposição com outros clips na trilha.
        
        Args:
            start_time: Tempo inicial do novo clip
            duration: Duração do novo clip
            
        Returns:
            bool: True se houver sobreposição, False caso contrário
        """
        end_time = start_time + duration
        
        for clip in self.clips:
            clip_start = clip['start_time']
            clip_end = clip_start + clip['duration']
            
            # Verifica sobreposição
            if not (end_time <= clip_start or start_time >= clip_end):
                return True
                
        return False

    def get_insert_position(self, time_pos):
        """
        Determina a posição de inserção correta para um novo clip.
        
        Args:
            time_pos: Posição temporal onde o clip será inserido
            
        Returns:
            int: Índice onde o clip deve ser inserido
        """
        for i, clip in enumerate(self.clips):
            if time_pos < clip['start_time']:
                return i
        return len(self.clips)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Desenhar clipes
        for clip in self.clips:
            x = int(clip['start_time'] * self.scale_factor)  # Usar scale_factor local
            width = int(clip['duration'] * self.scale_factor)  # Usar scale_factor local
            
            # Escolher cor baseado no tipo e seleção
            if clip == self.selected_clip:
                color = QColor("#0078D4")  # Azul para selecionado
            else:
                color = QColor("#333333") if self.track_type == "video" else QColor("#2D4B2D")
                
            rect = QRect(x, 0, width, self.height())
            painter.fillRect(rect, color)
            
            if clip == self.selected_clip:
                pen = QPen(QColor("#00A6FF"), 2)
                painter.setPen(pen)
                painter.drawRect(rect)

        # Desenhar indicador de drop se houver
        if self.drop_indicator_pos is not None:
            painter.setPen(QPen(QColor("#0078D4"), 2))
            painter.drawLine(self.drop_indicator_pos, 0, self.drop_indicator_pos, self.height())

class MultiTrackTimeline(QWidget):
    clip_selected = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.clips = []
        self.current_time = 0
        self.scale_factor = 100  # Pixels por segundo
        self.setAcceptDrops(True)
        
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:horizontal {
                height: 12px;
                background: #252526;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background: #404040;
                min-width: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #4D4D4D;
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Criar scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setAcceptDrops(True)
        
        # Container das trilhas
        tracks_widget = QWidget()
        tracks_widget.setAcceptDrops(True)
        self.tracks_layout = QVBoxLayout(tracks_widget)
        self.tracks_layout.setSpacing(2)
        
        # Labels das trilhas
        video_label = QLabel("Vídeo")
        video_label.setStyleSheet("""
            QLabel {
                color: #0078D4;
                font-weight: bold;
                padding: 2px 8px;
                background: rgba(0, 120, 212, 0.1);
                border-radius: 4px;
                margin: 2px 0;
            }
        """)
        
        audio_label = QLabel("Áudio")
        audio_label.setStyleSheet("""
            QLabel {
                color: #4CAF50;
                font-weight: bold;
                padding: 2px 8px;
                background: rgba(76, 175, 80, 0.1);
                border-radius: 4px;
                margin: 2px 0;
            }
        """)
        
        # Criar trilhas
        self.video_track = TimelineTrack("video")
        self.audio_track = TimelineTrack("audio")
        
        # Inicializar scale_factor nas trilhas
        self.set_scale_factor(self.scale_factor)
        
        # Adicionar widgets ao layout
        self.tracks_layout.addWidget(video_label)
        self.tracks_layout.addWidget(self.video_track)
        self.tracks_layout.addWidget(audio_label)
        self.tracks_layout.addWidget(audio_label)
        self.tracks_layout.addWidget(self.audio_track)
        
        # Configurar scroll area
        self.scroll_area.setWidget(tracks_widget)
        layout.addWidget(self.scroll_area)
        
        # Conectar sinais
        self.video_track.audio_ungroup.connect(self.handle_audio_ungroup)
        self.video_track.clip_selected.connect(self.handle_clip_selection)
        self.audio_track.clip_selected.connect(self.handle_clip_selection)

    def handle_clip_selection(self, filepath):
        """Emite o sinal quando um clip é selecionado"""
        self.clip_selected.emit(filepath)

    def handle_audio_ungroup(self, audio_data):
        """Adiciona o áudio desagrupado à trilha de áudio"""
        try:
            # Criar clip de áudio
            audio_clip = {
                'filepath': audio_data['filepath'],
                'start_time': audio_data['start_time'],
                'duration': audio_data['duration'],
                'type': 'audio',
                'is_audio_only': True,
                'has_audio': True
            }
            
            # Verificar sobreposição
            if not self.audio_track.check_clip_overlap(audio_data['start_time'], audio_data['duration']):
                # Inserir na posição correta
                insert_index = self.audio_track.get_insert_position(audio_data['start_time'])
                self.audio_track.clips.insert(insert_index, audio_clip)
                self.audio_track.update()
                
        except Exception as e:
            print(f"Erro ao desagrupar áudio: {e}")
            import traceback
            traceback.print_exc()

    def set_scale_factor(self, value):
        """Define o fator de escala para todas as trilhas"""
        self.scale_factor = value
        if hasattr(self, 'video_track'):
            self.video_track.scale_factor = value
            self.video_track.update()
        if hasattr(self, 'audio_track'):
            self.audio_track.scale_factor = value
            self.audio_track.update()

    def zoom_in(self):
        """Aumenta o zoom da timeline"""
        new_scale = min(200, self.scale_factor * 1.2)
        self.set_scale_factor(new_scale)

    def zoom_out(self):
        """Diminui o zoom da timeline"""
        new_scale = max(50, self.scale_factor / 1.2)
        self.set_scale_factor(new_scale)

    def add_clip(self, filepath, start_time, track_index=0):
        """Adiciona um clip à timeline"""
        try:
            # Determinar o tipo de mídia
            ext = Path(filepath).suffix.lower()
            media_type = 'video' if ext in ['.mp4', '.avi', '.mkv', '.mov'] else 'audio'
            
            # Obter duração do arquivo
            duration = self._get_media_duration(filepath)
            
            # Criar dados do clip
            clip_data = {
                'filepath': str(filepath),
                'start_time': float(start_time),
                'duration': float(duration),
                'type': media_type,
                'has_audio': media_type == 'video'
            }
            
            # Adicionar à trilha apropriada
            if media_type == 'video':
                self.video_track.clips.append(clip_data)
            else:
                self.audio_track.clips.append(clip_data)
                
            # Atualizar visualização
            self.update()
            return True
            
        except Exception as e:
            print(f"Erro ao adicionar clip: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def _get_media_duration(self, filepath):
        """Obtém a duração do arquivo de mídia"""
        try:
            import av
            container = av.open(filepath)
            duration = float(container.duration) / av.time_base
            container.close()
            return duration
        except Exception as e:
            print(f"Erro ao obter duração: {e}")
            try:
                import ffmpeg
                probe = ffmpeg.probe(filepath)
                duration = float(probe['streams'][0]['duration'])
                return duration
            except:
                print("Usando duração padrão")
                return 10.0

    def export_timeline(self, output_file):
        """Exporta a timeline para um arquivo"""
        # TODO: Implementar exportação de vídeo
        pass
