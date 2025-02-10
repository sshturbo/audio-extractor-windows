from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QLabel, QListWidget,
                           QListWidgetItem, QGraphicsOpacityEffect, QApplication)
from PyQt5.QtCore import Qt, QPoint, QRect, QPropertyAnimation, QByteArray, QMimeData
from PyQt5.QtGui import QDrag, QIcon, QPixmap, QPainter, QLinearGradient, QPainterPath, QPen, QColor
import json
from pathlib import Path
from .timeline_widget import create_clip_data, create_mime_data, MIME_TYPE

class MediaListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setDragEnabled(True)
        self.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.setHorizontalScrollMode(QListWidget.ScrollPerPixel)
        self.viewport().setAcceptDrops(False)
        self.drag_start_position = None
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
            
        if not self.drag_start_position:
            return
            
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
            
        try:
            item = self.itemAt(self.drag_start_position)
            if not item:
                return
                
            # Obter dados do arquivo
            filepath = str(item.data(Qt.UserRole))
            duration = self.parent().get_media_duration(filepath)
            media_type = self.parent().get_media_type(filepath)
            
            # Criar clip data
            clip_data = {
                'filepath': filepath,
                'duration': duration,
                'type': media_type,
                'has_audio': media_type == 'video',
                'is_audio_only': media_type == 'audio'
            }
            
            # Criar mime data diretamente
            mime_data = QMimeData()
            json_str = json.dumps(clip_data, ensure_ascii=False)
            byte_data = json_str.encode('utf-8')
            mime_data.setData("application/x-timeline-clip", QByteArray(byte_data))
            
            # Criar drag
            drag = QDrag(self)
            drag.setMimeData(mime_data)
            
            # Criar preview
            pixmap = self.parent().create_drag_preview(item)
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(pixmap.width()//2, pixmap.height()//2))
            
            # Executar drag de forma síncrona
            result = drag.exec_(Qt.CopyAction)
            
            # Limpar estado
            self.drag_start_position = None
            
        except Exception as e:
            print(f"Erro ao iniciar drag: {e}")
            import traceback
            traceback.print_exc()

    def dragMoveEvent(self, event):
        """Atualiza o feedback visual durante o drag"""
        if event.mimeData().hasFormat(MIME_TYPE):
            try:
                data = bytes(event.mimeData().data(MIME_TYPE))
                clip_data = json.loads(data.decode('utf-8'))
                # Usar scale_factor da timeline
                timeline = self.parent().timeline
                drop_time = event.pos().x() / timeline.scale_factor if timeline else 0
                
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

class MediaBin(QFrame):
    def __init__(self):
        super().__init__()
        self.drag_start_position = None
        self.pressed_item = None
        self.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #404040;
                border-radius: 10px;
            }
            QLabel {
                color: #E0E0E0;
                font-size: 13px;
                font-weight: bold;
                padding: 8px;
            }
            QListWidget {
                background-color: transparent;
                border: none;
                border-radius: 8px;
                padding: 5px;
            }
            QListWidget::item {
                background-color: #2D2D2D;
                color: #E0E0E0;
                border-radius: 6px;
                margin: 3px;
                padding: 10px;
            }
            QListWidget::item:hover {
                background-color: #323233;
                border: 1px solid #0078D4;
            }
            QListWidget::item:selected {
                background-color: rgba(0, 120, 212, 0.2);
                color: #FFFFFF;
                border: 1px solid #0078D4;
            }
            QListWidget::item:drag {
                background-color: #2B88D9;
                color: white;
                border: 1px solid #0078D4;
            }
        """)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        title = QLabel("Biblioteca de Mídia")
        title.setStyleSheet("""
            QLabel {
                color: #0078D4;
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
                border-bottom: 2px solid #0078D4;
            }
        """)
        
        self.list_widget = MediaListWidget()
        
        layout.addWidget(title)
        layout.addWidget(self.list_widget)
        
    def add_media(self, filepath):
        item = QListWidgetItem()
        item.setText(Path(filepath).name)
        item.setData(Qt.UserRole, filepath)
        item.setIcon(self.get_media_icon(filepath))
        self.list_widget.addItem(item)
        
        # Efeito de fade in ao adicionar novo item
        effect = QGraphicsOpacityEffect()
        item.setData(Qt.UserRole + 1, effect)
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(300)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.start()
        
    def get_media_icon(self, filepath):
        ext = Path(filepath).suffix.lower()
        if ext in ['.mp4', '.avi', '.mkv', '.mov']:
            return QIcon.fromTheme("video-x-generic")
        elif ext in ['.mp3', '.wav']:
            return QIcon.fromTheme("audio-x-generic")
        return QIcon.fromTheme("text-x-generic")
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
            self.pressed_item = self.list_widget.itemAt(event.pos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
            
        if not self.drag_start_position:
            return
            
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return
            
        if self.pressed_item:
            self.list_widget.startDrag(self.pressed_item, event)
            self.drag_start_position = None
            self.pressed_item = None

    def get_media_duration(self, filepath):
        """Obtém a duração do arquivo de mídia"""
        try:
            import av
            container = av.open(filepath)
            duration = float(container.duration) / av.time_base
            container.close()
            return duration
        except Exception as e:
            print(f"Erro ao obter duração: {e}")
            # Tentar método alternativo com FFmpeg
            try:
                import ffmpeg
                probe = ffmpeg.probe(filepath)
                duration = float(probe['streams'][0]['duration'])
                return duration
            except:
                print("Usando duração padrão")
                return 10.0  # duração padrão

    def get_media_type(self, filepath):
        """Determina o tipo de mídia baseado na extensão"""
        ext = Path(filepath).suffix.lower()
        if ext in ['.mp4', '.avi', '.mkv', '.mov']:
            return 'video'
        elif ext in ['.mp3', '.wav']:
            return 'audio'
        return 'unknown'

    def create_drag_preview(self, item):
        """Cria uma preview visual melhorada para o drag and drop"""
        width = 220
        height = 45
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Adicionar sombra suave
        shadow_color = QColor(0, 0, 0, 30)
        for i in range(4):
            shadow_rect = QRect(2 + i, 2 + i, width - (4 + i), height - (4 + i))
            painter.fillRect(shadow_rect, shadow_color)
        
        # Desenhar fundo com gradiente mais atraente
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor("#2B88D9"))
        gradient.setColorAt(0.5, QColor("#0078D4"))
        gradient.setColorAt(1, QColor("#006CBE"))
        
        path = QPainterPath()
        path.addRoundedRect(0, 0, width - 2, height - 2, 8, 8) 
        painter.fillPath(path, gradient)
        
        # Adicionar borda brilhante
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.drawPath(path)
        
        # Adicionar ícone com sombra
        icon = item.icon()
        icon_rect = QRect(8, 7, 30, 30)
        
        # Desenhar sombra do ícone
        shadow_rect = icon_rect.adjusted(1, 1, 1, 1)
        icon.paint(painter, shadow_rect, Qt.AlignCenter, QIcon.Disabled)
        
        # Desenhar ícone principal
        icon.paint(painter, icon_rect, Qt.AlignCenter)
        
        # Adicionar texto com sombra e estilo melhorado
        painter.setPen(QColor(0, 0, 0, 100))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(9)
        painter.setFont(font)
        
        text_rect = QRect(45, 0, width - 55, height)
        text = painter.fontMetrics().elidedText(
            item.text(), Qt.ElideMiddle, text_rect.width()
        )
        
        # Sombra do texto
        painter.drawText(text_rect.adjusted(1, 1, 1, 1), Qt.AlignVCenter | Qt.AlignLeft, text)
        
        # Texto principal
        painter.setPen(Qt.white)
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, text)
        
        painter.end()
        return pixmap
