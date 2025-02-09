from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QListWidget, QLabel, QSplitter, QFrame, QMenu,
                           QListWidgetItem)
from PyQt5.QtCore import Qt, QMimeData, QPoint
from PyQt5.QtGui import QDrag
import soundfile as sf
import numpy as np
from pathlib import Path

class AudioSegmentWidget(QFrame):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = Path(file_path)
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(2)
        self.setMinimumHeight(60)
        self.setAcceptDrops(True)
        
        layout = QVBoxLayout(self)
        self.name_label = QLabel(self.file_path.name)
        self.duration_label = QLabel(self.get_duration())
        layout.addWidget(self.name_label)
        layout.addWidget(self.duration_label)
        
    def get_duration(self):
        try:
            with sf.SoundFile(self.file_path) as f:
                duration = len(f) / f.samplerate
                return f"Duração: {duration:.2f}s"
        except:
            return "Duração: N/A"
            
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(str(self.file_path))
            drag.setMimeData(mime_data)
            drag.exec_(Qt.MoveAction)

class SegmentEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        
        # Área de segmentos originais
        original_frame = QFrame()
        original_layout = QVBoxLayout(original_frame)
        original_layout.addWidget(QLabel("Segmentos Originais"))
        self.original_list = QListWidget()
        original_layout.addWidget(self.original_list)
        
        # Área de edição
        edit_frame = QFrame()
        edit_layout = QVBoxLayout(edit_frame)
        
        # Barra de ferramentas
        toolbar = QHBoxLayout()
        self.merge_btn = QPushButton("Mesclar Selecionados")
        self.split_btn = QPushButton("Dividir")
        self.delete_btn = QPushButton("Excluir")
        
        toolbar.addWidget(self.merge_btn)
        toolbar.addWidget(self.split_btn)
        toolbar.addWidget(self.delete_btn)
        edit_layout.addLayout(toolbar)
        
        # Área de drop para edição
        self.edit_area = QFrame()
        self.edit_area.setAcceptDrops(True)
        self.edit_area.setStyleSheet("QFrame { border: 2px dashed #999; }")
        self.edit_area_layout = QVBoxLayout(self.edit_area)
        edit_layout.addWidget(self.edit_area)
        
        # Configurar layout principal
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(original_frame)
        splitter.addWidget(edit_frame)
        layout.addWidget(splitter)
        
        # Conectar sinais
        self.merge_btn.clicked.connect(self.merge_segments)
        self.split_btn.clicked.connect(self.split_segment)
        self.delete_btn.clicked.connect(self.delete_segment)
        
    def load_segments(self, segments_dir):
        self.segments_dir = Path(segments_dir)
        self.original_list.clear()
        
        for segment_file in sorted(self.segments_dir.glob("*.wav")):
            # Criar item da lista
            list_item = QListWidgetItem()
            # Criar widget personalizado
            segment_widget = AudioSegmentWidget(segment_file)
            # Configurar tamanho do item baseado no widget
            list_item.setSizeHint(segment_widget.sizeHint())
            # Adicionar item à lista
            self.original_list.addItem(list_item)
            # Definir widget personalizado para o item
            self.original_list.setItemWidget(list_item, segment_widget)
    
    def merge_segments(self):
        # Implementar lógica de mesclagem
        pass
        
    def split_segment(self):
        # Implementar lógica de divisão
        pass
        
    def delete_segment(self):
        # Implementar lógica de exclusão
        pass
