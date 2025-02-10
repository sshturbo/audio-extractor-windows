from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QPushButton, QLabel, QFrame, QSplitter, QScrollArea,
                           QToolBar, QAction, QFileDialog, QDockWidget, QListWidget,
                           QMenuBar, QMenu, QSizeGrip, QSizePolicy, QActionGroup) 
from PyQt5.QtCore import Qt, QSize, QTimer 
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
        self.is_button_enabled = True  # Novo atributo para controlar o estado do botão
        self.button_timer = QTimer()  # Timer para reabilitar o botão
        self.button_timer.timeout.connect(self.enable_playback_button)
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
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #0078D4;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-size: 12px;
                min-width: 80px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #1084D9;
            }
            QPushButton:pressed {
                background-color: #006CBE;
            }
            QListWidget {
                background-color: #252526;
                color: white;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
                margin: 2px;
            }
            QListWidget::item:hover {
                background-color: #2D2D2D;
            }
            QListWidget::item:selected {
                background-color: #0078D4;
            }
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
        self.speed_menu = None  # Inicializar o menu de velocidade como None
        self.setup_ui()
        self.setup_connections()  # Nova chamada para configurar conexões
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
        
        # Inicializar componentes antes de usar
        self.media_bin = MediaBin()
        self.preview = PreviewWidget()
        self.timeline = MultiTrackTimeline()
        
        # Botões de controle
        self.rewind_btn = QPushButton("⏪")
        self.play_btn = QPushButton("⏵")
        self.stop_btn = QPushButton("⏹")
        self.forward_btn = QPushButton("⏩")
        
        # Widget central com splitters
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Splitter horizontal principal
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # 1. Painel Esquerdo (Media e Efeitos)
        left_panel = self.create_left_panel()
        
        # 2. Área Central com splitter vertical
        center_splitter = QSplitter(Qt.Vertical)
        
        # Preview com borda e controle de tamanho
        preview_container = self.create_preview_container()
        
        # Timeline
        timeline_container = QFrame()
        timeline_layout = QVBoxLayout(timeline_container)
        timeline_layout.addWidget(self.timeline)
        
        # Adicionar ao splitter vertical
        center_splitter.addWidget(preview_container)
        center_splitter.addWidget(timeline_container)
        
        # Definir proporções do splitter vertical
        center_splitter.setStretchFactor(0, 2)  # Preview
        center_splitter.setStretchFactor(1, 1)  # Timeline
        
        # Adicionar painéis ao splitter principal
        self.main_splitter.addWidget(left_panel)
        self.main_splitter.addWidget(center_splitter)
        
        # Definir proporções do splitter principal
        self.main_splitter.setStretchFactor(0, 1)  # Painel esquerdo
        self.main_splitter.setStretchFactor(1, 4)  # Área central
        
        main_layout.addWidget(self.main_splitter)
        
        # Barra de ferramentas
        self.create_toolbar()
        
        # Carregar projeto se fornecido
        if self.project_data:
            self.load_project(self.project_data)
            
        # Conectar sinais dos botões
        self.play_btn.clicked.connect(self.toggle_playback)
        self.stop_btn.clicked.connect(self.stop_playback)

        # Atualizar os botões com press and hold
        self.rewind_btn.pressed.connect(self.start_rewind)
        self.rewind_btn.released.connect(self.stop_fast_playback)
        
        self.forward_btn.pressed.connect(self.start_fast_forward)
        self.forward_btn.released.connect(self.stop_fast_playback)

    def setup_connections(self):
        """Configura todas as conexões de sinais e slots"""
        # Conectar controles de playback
        if hasattr(self, 'play_btn'):
            self.play_btn.clicked.connect(self.toggle_playback)
        if hasattr(self, 'stop_btn'):
            self.stop_btn.clicked.connect(self.stop_playback)
        if hasattr(self, 'rewind_btn'):
            self.rewind_btn.pressed.connect(self.start_rewind)
            self.rewind_btn.released.connect(self.stop_fast_playback)
        if hasattr(self, 'forward_btn'):
            self.forward_btn.pressed.connect(self.start_fast_forward)
            self.forward_btn.released.connect(self.stop_fast_playback)

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

    def create_preview_container(self):
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
        preview_layout.setSpacing(0)  # Reduzir espaçamento vertical
        
        # Container do preview
        preview_inner = QFrame()
        preview_inner.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        preview_inner_layout = QVBoxLayout(preview_inner)
        preview_inner_layout.setSpacing(0)  # Reduzir espaçamento vertical
        
        # Preview widget
        self.preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        preview_inner_layout.addWidget(self.preview)
        
        # Controles de playback
        controls = QHBoxLayout()
        controls.setContentsMargins(10, 5, 10, 5)
        controls.setSpacing(8)  # Espaçamento entre botões
        
        # Estilo comum para os botões
        button_style = """
            QPushButton {
                background-color: #333333;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #404040;
            }
            QPushButton:pressed {
                background-color: #505050;
            }
            QPushButton#speedButton {
                min-width: 80px;
                padding: 4px 12px;
                font-weight: bold;
                margin-left: 10px;
                background-color: #1E1E1E;
                border: 1px solid #404040;
            }
            QPushButton#speedButton:hover {
                background-color: #2D2D2D;
                border-color: #505050;
            }
        """
        
        self.rewind_btn = QPushButton("⏪")
        self.play_btn = QPushButton("⏵")
        self.stop_btn = QPushButton("⏹")
        self.forward_btn = QPushButton("⏩")
        self.speed_btn = QPushButton("1.0x")  # Botão de velocidade
        self.speed_btn.setObjectName("speedButton")

        # Menu de velocidade com ícones e itens mais intuitivos
        self.speed_menu = QMenu(self)
        self.speed_menu.setStyleSheet("""
            QMenu {
                background-color: #333333;
                color: white;
                border: 1px solid #404040;
                padding: 5px;
                min-width: 150px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #404040;
            }
            QMenu::item:checked {
                color: #0078D4;
                font-weight: bold;
            }
            QMenu::separator {
                height: 1px;
                background: #404040;
                margin: 5px 0px;
            }
        """)
        
        # Adicionar opções de velocidade com checkmarks e ícones
        speed_group = QActionGroup(self)
        speed_group.setExclusive(True)
        
        speeds = [
            ("Muito Lento (0.25x)", 0.25),
            ("Lento (0.5x)", 0.5),
            ("Devagar (0.75x)", 0.75),
            ("Normal (1.0x)", 1.0),
            ("Rápido (1.5x)", 1.5),
            ("Muito Rápido (2.0x)", 2.0)
        ]
        
        for speed_text, speed_value in speeds:
            action = QAction(speed_text, self)
            action.setCheckable(True)
            action.setData(speed_value)
            if speed_value == 1.0:
                action.setChecked(True)
            speed_group.addAction(action)
            self.speed_menu.addAction(action)
            action.triggered.connect(lambda checked, v=speed_value, t=speed_text: self.change_speed(v, t))
            
        # Personalizar botão de velocidade
        self.speed_btn.setStyleSheet(button_style + """
            QPushButton#speedButton {
                min-width: 80px;
                padding: 4px 12px;
                font-weight: bold;
                background-color: #333333;
                color: white;
            }
            QPushButton#speedButton:hover {
                background-color: #404040;
            }
        """)
        self.speed_btn.setFixedWidth(80)
        self.speed_btn.clicked.connect(self.show_speed_menu)
        
        for btn in [self.rewind_btn, self.play_btn, self.stop_btn, self.forward_btn, self.speed_btn]:
            btn.setFixedHeight(32)
            if btn != self.speed_btn:
                btn.setFixedSize(32, 32)
            btn.setStyleSheet(button_style)
            controls.addWidget(btn)
        
        # Configurar layout dos controles
        controls = QHBoxLayout()
        controls.setContentsMargins(10, 5, 10, 5)
        controls.setSpacing(8)  # Espaçamento entre botões
        
        # Adicionar botões na ordem correta
        controls.addStretch(1)  # Espaço flexível no início
        controls.addWidget(self.rewind_btn)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.stop_btn)
        controls.addWidget(self.forward_btn)
        controls.addWidget(self.speed_btn)
        controls.addStretch(1)  # Espaço flexível no final

        # Conectar sinais
        self.play_btn.clicked.connect(self.toggle_playback)
        self.stop_btn.clicked.connect(self.stop_playback)
        
        # Configurar press and hold para avanço/retrocesso
        self.rewind_btn.pressed.connect(self.start_rewind)
        self.rewind_btn.released.connect(self.stop_fast_playback)
        
        self.forward_btn.pressed.connect(self.start_fast_forward)
        self.forward_btn.released.connect(self.stop_fast_playback)
        
        # Centralizar os controles
        controls.addStretch(1)
        controls_widget = QWidget()
        controls_widget.setLayout(controls)
        controls.addStretch(1)
        
        preview_inner_layout.addWidget(controls_widget)
        preview_layout.addWidget(preview_inner)
        
        return preview_container

    # Adicionar métodos de controle
    def enable_playback_button(self):
        """Reabilita o botão de playback após o delay"""
        self.is_button_enabled = True
        self.button_timer.stop()

    def toggle_playback(self):
        if not self.is_button_enabled:
            return

        if hasattr(self, 'preview') and self.preview.player:
            try:
                print("Alternando reprodução...")
                self.is_button_enabled = False  # Desabilita temporariamente

                if not self.preview.is_playing:
                    self.preview.play()
                    if self.preview.is_playing:
                        self.play_btn.setText("⏸")
                else:
                    self.preview.pause()
                    if not self.preview.is_playing:
                        self.play_btn.setText("⏵")

                print(f"Estado atual: {'reproduzindo' if self.preview.is_playing else 'pausado'}")
                self.button_timer.start(300)  # Reabilita após 300ms

            except Exception as e:
                print(f"Erro ao alternar reprodução: {e}")
                self.play_btn.setText("⏵")
                self.is_button_enabled = True

    def stop_playback(self):
        if hasattr(self, 'preview') and self.preview.player:
            try:
                print("Parando reprodução...")
                self.preview.stop()
                self.play_btn.setText("⏵")
                print("Reprodução parada")
            except Exception as e:
                print(f"Erro ao parar reprodução: {e}")

    def start_rewind(self):
        """Inicia retrocesso rápido"""
        if hasattr(self, 'preview') and self.preview.player:
            self.preview.start_rewind()
            self.rewind_btn.setStyleSheet(self.rewind_btn.styleSheet() + "background-color: #505050;")

    def start_fast_forward(self):
        """Inicia avanço rápido"""
        if hasattr(self, 'preview') and self.preview.player:
            self.preview.start_fast_forward()
            self.forward_btn.setStyleSheet(self.forward_btn.styleSheet() + "background-color: #505050;")

    def stop_fast_playback(self):
        """Para avanço/retrocesso rápido"""
        if hasattr(self, 'preview') and self.preview.player:
            self.preview.stop_fast_playback()
            # Restaurar estilo original dos botões
            button_style = """
                background-color: #333333;
                color: white;
                border: none;
                border-radius: 16px;
                font-size: 14px;
                padding: 4px;
            """
            self.rewind_btn.setStyleSheet(button_style)
            self.forward_btn.setStyleSheet(button_style)

    def show_speed_menu(self):
        """Mostra o menu de velocidade abaixo do botão"""
        if self.speed_menu:
            pos = self.speed_btn.mapToGlobal(self.speed_btn.rect().bottomLeft())
            self.speed_menu.popup(pos)

    def change_speed(self, speed_value, speed_text):
        """Altera a velocidade de reprodução"""
        if hasattr(self, 'preview') and self.preview.player:
            try:
                self.preview.set_playback_speed(speed_value)
                # Extrair apenas o valor numérico para exibir no botão
                speed_display = f"{speed_value:.2f}x"
                self.speed_btn.setText(speed_display)

                # Atualizar o checkmark no menu
                for action in self.speed_menu.actions():
                    action.setChecked(action.data() == speed_value)

            except Exception as e:
                print(f"Erro ao alterar velocidade: {e}")

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
                
                # Garantir que os controles estejam no estado correto
                self.play_btn.setText("⏵")
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
