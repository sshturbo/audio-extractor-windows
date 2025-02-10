from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QLabel, QPushButton, QFrame, QSplitter, QScrollArea,
                           QToolBar, QAction, QFileDialog, QDockWidget)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon
from .timeline_widget import MultiTrackTimeline
from .preview_widget import PreviewWidget
from .media_bin import MediaBin
from .effects_panel import EffectsPanel

class VideoEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Editor de Vídeo")
        self.setMinimumSize(1200, 800)
        self.setup_ui()
        
    def setup_ui(self):
        # Widget central com layout principal
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Criar barra de ferramentas
        self.create_toolbar()
        
        # Área principal dividida
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Painel esquerdo (Media bin e efeitos)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Media Bin
        self.media_bin = MediaBin()
        left_layout.addWidget(self.media_bin)
        
        # Efeitos
        self.effects_panel = EffectsPanel()
        left_layout.addWidget(self.effects_panel)
        
        # Preview e Timeline
        preview_timeline = QWidget()
        preview_layout = QVBoxLayout(preview_timeline)
        
        # Preview
        self.preview = PreviewWidget()
        preview_layout.addWidget(self.preview)
        
        # Timeline
        self.timeline = MultiTrackTimeline()
        preview_layout.addWidget(self.timeline)
        
        # Adicionar painéis ao splitter
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(preview_timeline)
        
        # Configurar proporções do splitter
        main_splitter.setStretchFactor(0, 1)  # Left panel
        main_splitter.setStretchFactor(1, 4)  # Preview/Timeline
        
        main_layout.addWidget(main_splitter)
        
    def create_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Ações do arquivo
        import_action = QAction(QIcon("icons/import.png"), "Importar Mídia", self)
        import_action.triggered.connect(self.import_media)
        toolbar.addAction(import_action)
        
        # Ações de edição
        cut_action = QAction(QIcon("icons/cut.png"), "Cortar", self)
        cut_action.triggered.connect(self.cut_clip)
        toolbar.addAction(cut_action)
        
        split_action = QAction(QIcon("icons/split.png"), "Dividir", self)
        split_action.triggered.connect(self.split_clip)
        toolbar.addAction(split_action)
        
        # Ações de exportação
        export_action = QAction(QIcon("icons/export.png"), "Exportar", self)
        export_action.triggered.connect(self.export_video)
        toolbar.addAction(export_action)
        
    def import_media(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Importar Mídia",
            "",
            "Arquivos de Mídia (*.mp4 *.avi *.mkv *.mov *.mp3 *.wav)"
        )
        if files:
            for file in files:
                self.media_bin.add_media(file)
                
    def cut_clip(self):
        self.timeline.cut_selected_clip()
        
    def split_clip(self):
        self.timeline.split_at_playhead()
        
    def export_video(self):
        output_file, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Vídeo",
            "",
            "Vídeo MP4 (*.mp4)"
        )
        if output_file:
            self.timeline.export_timeline(output_file)
