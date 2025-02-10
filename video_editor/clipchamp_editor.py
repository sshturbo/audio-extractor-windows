from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QPushButton, QLabel, QFrame, QSplitter, QScrollArea,
                           QToolBar, QAction, QFileDialog, QDockWidget, QListWidget,
                           QMenuBar, QMenu, QSizeGrip, QSizePolicy)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QColor
from .timeline_widget import MultiTrackTimeline
from .preview_widget import PreviewWidget
from .media_bin import MediaBin
from pathlib import Path

class ClipchampEditor(QMainWindow):
    def __init__(self, project_data=None):
        super().__init__()
        self.project_data = project_data
        self.setWindowTitle("Editor de Vídeo")
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1E1E1E;
            }
            QMenuBar {
                background-color: #333333;
                color: white;
                padding: 5px;
                font-size: 12px;
            }
            QMenuBar::item {
                padding: 5px 10px;
                margin-right: 5px;
                background-color: transparent;
            }
            QMenuBar::item:selected {
                background-color: #404040;
                border-radius: 4px;
            }
            QMenu {
                background-color: #333333;
                color: white;
                border: 1px solid #404040;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #404040;
            }
        """)
        self.setup_ui()
        self.create_menu_bar()

    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # Menu Arquivo
        file_menu = menubar.addMenu('&Arquivo')
        file_menu.addAction('Novo Projeto', self.new_project)
        file_menu.addAction('Abrir Projeto', self.open_project)
        file_menu.addSeparator()
        file_menu.addAction('Importar Mídia', self.import_media)
        file_menu.addAction('Exportar Vídeo', self.export_video)
        
        # Menu Editar
        edit_menu = menubar.addMenu('&Editar')
        edit_menu.addAction('Desfazer', lambda: None)  # TODO: Implementar
        edit_menu.addAction('Refazer', lambda: None)  # TODO: Implementar
        edit_menu.addSeparator()
        edit_menu.addAction('Cortar', self.cut_clip)
        edit_menu.addAction('Dividir', self.split_clip)
        
        # Menu Exibir
        view_menu = menubar.addMenu('&Exibir')
        view_menu.addAction('Zoom In', lambda: self.timeline.zoom_in())
        view_menu.addAction('Zoom Out', lambda: self.timeline.zoom_out())

    def setup_ui(self):
        self.setMinimumSize(1280, 720)
        
        # Inicializar componentes
        self.media_bin = MediaBin()
        self.preview = PreviewWidget()
        self.timeline = MultiTrackTimeline()
        
        # Widget central com splitters
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Splitter horizontal principal
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # Painéis
        left_panel = self.create_left_panel()
        center_splitter = QSplitter(Qt.Vertical)
        
        # Preview
        preview_container = QFrame()
        preview_container.setStyleSheet("""
            QFrame {
                background-color: #1A1A1A;
                border: 1px solid #333333;
                border-radius: 8px;
            }
        """)
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(10, 10, 10, 10)
        preview_layout.setSpacing(0)
        preview_layout.addWidget(self.preview)
        
        # Timeline
        timeline_container = QFrame()
        timeline_layout = QVBoxLayout(timeline_container)
        timeline_layout.addWidget(self.timeline)
        
        # Adicionar ao splitter vertical
        center_splitter.addWidget(preview_container)
        center_splitter.addWidget(timeline_container)
        
        # Proporções dos splitters
        center_splitter.setStretchFactor(0, 2)  # Preview
        center_splitter.setStretchFactor(1, 1)  # Timeline
        
        self.main_splitter.addWidget(left_panel)
        self.main_splitter.addWidget(center_splitter)
        self.main_splitter.setStretchFactor(0, 1)  # Painel esquerdo
        self.main_splitter.setStretchFactor(1, 4)  # Área central
        
        main_layout.addWidget(self.main_splitter)
        
        # Barra de ferramentas
        self.create_toolbar()
        
        # Carregar projeto se fornecido
        if self.project_data:
            self.load_project(self.project_data)

    def create_left_panel(self):
        left_panel = QWidget()
        left_panel.setFixedWidth(280)
        left_panel.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border-radius: 8px;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)
        
        # Media Browser com título mais visível
        media_title = QLabel("MÍDIA")
        media_title.setStyleSheet("color: #0078D4; font-size: 14px; margin-top: 10px;")
        left_layout.addWidget(media_title)
        left_layout.addWidget(self.media_bin)
        
        # Efeitos com título destacado
        effects_title = QLabel("EFEITOS")
        effects_title.setStyleSheet("color: #0078D4; font-size: 14px; margin-top: 20px;")
        left_layout.addWidget(effects_title)
        self.effects_list = QListWidget()
        self.effects_list.addItems([
            "🎨 Filtros de Cor",
            "🔄 Transições",
            "✨ Efeitos Visuais",
            "🎵 Efeitos de Áudio",
            "📝 Textos e Títulos"
        ])
        left_layout.addWidget(self.effects_list)
        
        return left_panel

    def create_toolbar(self):
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(32, 32))
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #333333;
                border: none;
                spacing: 10px;
                padding: 5px;
            }
            QToolButton {
                background-color: transparent;
                border: none;
                padding: 5px;
                border-radius: 4px;
            }
            QToolButton:hover {
                background-color: #404040;
            }
        """)
        
        # Ações
        actions = [
            ("Importar", "import.png", self.import_media),
            ("Cortar", "cut.png", self.cut_clip),
            ("Dividir", "split.png", self.split_clip),
            ("Exportar", "export.png", self.export_video)
        ]
        
        for name, icon, callback in actions:
            action = QAction(QIcon(f"icons/{icon}"), name, self)
            action.triggered.connect(callback)
            toolbar.addAction(action)
        
        self.addToolBar(toolbar)
        
    def load_project(self, project_data):
        try:
            video_file = project_data.get('original_video')
            if video_file and Path(video_file).exists():
                print(f"Carregando projeto com vídeo: {video_file}")
                self.preview.load_video(video_file)
                self.media_bin.add_media(video_file)
                
                # Adicionar à timeline
                self.timeline.add_clip(video_file, 0, 0)  # tempo 0, trilha 0
                print("Projeto carregado com sucesso")
        except Exception as e:
            print(f"Erro ao carregar projeto: {e}")
            import traceback
            traceback.print_exc()

    def import_media(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Importar Mídia",
            "",
            "Arquivos de Mídia (*.mp4 *.avi *.mkv *.mov *.mp3 *.wav)"
        )
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

    def new_project(self):
        # TODO: Implementar novo projeto
        pass

    def open_project(self):
        # TODO: Implementar abrir projeto
        pass
