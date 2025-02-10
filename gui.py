from PyQt5.QtWidgets import (QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout,
                           QWidget, QFileDialog, QLabel, QComboBox, QProgressBar,
                           QAction, QListWidget, QListWidgetItem, QTextEdit,
                           QGroupBox, QMessageBox, QMenu, QFrame, QSizePolicy, 
                           QStackedWidget, QSlider, QStyle, QApplication)  # Adicionar QApplication aqui
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtGui import QIcon, QFont
import json
from pathlib import Path
from worker import AudioProcessingWorker
import sys
import os
from video_player import VideoPlayer
from video_editor.clipchamp_editor import ClipchampEditor

def load_stylesheet(filename):
    """Carrega arquivo CSS"""
    css_file = Path(__file__).parent / 'assets' / 'css' / filename
    if css_file.exists():
        with open(css_file, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

class MainWindow(QMainWindow):
    VIDEO_FORMATS = "*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Extractor and Transcriber")
        self.setGeometry(100, 100, 1400, 800)
        self.current_project = None
        
        # Carregar stylesheet
        self.setStyleSheet(load_stylesheet('gui.css'))
        
        # Widget central com layout horizontal
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.horizontal_layout = QHBoxLayout(self.central_widget)
        self.horizontal_layout.setContentsMargins(0, 0, 0, 0)
        self.horizontal_layout.setSpacing(0)

        # Criar menu lateral e configurar interface
        self.create_sidebar()
        self.setup_ui()
        self.setup_menu()
        self.menu_buttons['editor'] = self.create_menu_button("Editor de Vídeo", "🎬", self.show_video_editor)

    def setup_ui(self):
        # Container principal
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(15)
        
        # Adicionar ao layout principal
        self.horizontal_layout.addWidget(self.sidebar_frame)
        self.horizontal_layout.addWidget(self.content_container)
        
        # Configurar áreas
        self.create_viewer_area()
        self.create_transcription_area()
        self.create_projects_area()
        self.create_new_project_area()

    def create_sidebar(self):
        # Frame para o sidebar
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setObjectName("sidebar")
        self.sidebar_frame.setFixedWidth(250)
        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Logo ou título
        logo_label = QLabel("Audio Extractor")
        logo_label.setObjectName("logo")
        logo_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(logo_label)

        # Simplificar menu de botões
        self.menu_buttons = {
            'new_project': self.create_menu_button("Novo Projeto", "➕", lambda: self.show_content(3)),
            'video': self.create_menu_button("Player de Vídeo", "🎬", lambda: self.show_content(0)),
            'transcripts': self.create_menu_button("Transcrição", "📝", lambda: self.show_content(1)),
            'projects': self.create_menu_button("Projetos", "📁", lambda: self.show_content(2))
        }
        
        # Adicionar botões ao layout
        for btn in self.menu_buttons.values():
            sidebar_layout.addWidget(btn)

        # Espaçadorv
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sidebar_layout.addWidget(spacer)

    def create_menu_button(self, text, icon, callback):
        btn = QPushButton(f" {icon} {text}")
        btn.setObjectName("menuButton")
        if callback:
            btn.clicked.connect(callback)
        self.sidebar_frame.layout().addWidget(btn)
        return btn  # Retornar o botão para permitir configurações adicionais

    def create_new_project_area(self):
        new_project_container = QWidget()
        new_project_layout = QVBoxLayout(new_project_container)
        new_project_layout.setContentsMargins(20, 20, 20, 20)
        new_project_layout.setSpacing(15)
        
        file_group = QGroupBox("Seleção de Arquivo")
        file_layout = QVBoxLayout(file_group)

        self.file_label = QLabel("Selecione um arquivo de vídeo")
        self.file_label.setFont(QFont("Roboto", 12))
        file_layout.addWidget(self.file_label)

        select_layout = QHBoxLayout()
        self.select_button = QPushButton("Selecionar Vídeo")
        self.select_button.setIcon(QIcon("icons/select.png"))
        self.select_button.clicked.connect(self.select_video)
        select_layout.addWidget(self.select_button)

        self.process_button = QPushButton("Processar")
        self.process_button.setIcon(QIcon("icons/process.png"))
        self.process_button.clicked.connect(self.process_video)
        self.process_button.setEnabled(False)
        select_layout.addWidget(self.process_button)

        file_layout.addLayout(select_layout)

        self.language_combo = QComboBox()
        self.language_combo.addItems(["pt", "en", "es", "fr", "de"])
        file_layout.addWidget(self.language_combo)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        file_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        file_layout.addWidget(self.status_label)

        new_project_layout.addWidget(file_group)
        self.content_stack.addWidget(new_project_container)  # index 3

    def create_viewer_area(self):
        # Container principal
        self.content_stack = QStackedWidget()
        
        # Área de vídeo com layout horizontal
        video_container = QWidget()
        video_layout = QHBoxLayout(video_container)
        
        # Lista de vídeos (lado esquerdo)
        videos_group = QGroupBox("Arquivos de Vídeo")
        videos_layout = QVBoxLayout(videos_group)
        
        self.videos_list = QListWidget()
        self.videos_list.itemClicked.connect(self.select_video_from_list)
        videos_layout.addWidget(self.videos_list)
        
        video_layout.addWidget(videos_group, stretch=1)
        
        # Player de vídeo (lado direito)
        player_container = QWidget()
        player_layout = QVBoxLayout(player_container)
        self.video_player = VideoPlayer()
        player_layout.addWidget(self.video_player)
        
        # Remover controles de volume duplicados aqui
        video_layout.addWidget(player_container, stretch=2)
        
        self.content_stack.addWidget(video_container)  # index 0
        self.content_layout.addWidget(self.content_stack)

    def create_transcription_area(self):
        # Área de transcrição
        transcript_container = QWidget()
        transcript_layout = QVBoxLayout(transcript_container)
        
        transcript_buttons = QHBoxLayout()
        self.clear_transcript_btn = QPushButton("Limpar Transcrição")
        self.clear_transcript_btn.clicked.connect(self.clear_transcript)
        self.save_transcript_btn = QPushButton("Salvar Transcrição")
        self.save_transcript_btn.clicked.connect(self.save_transcript)
        
        transcript_buttons.addWidget(self.clear_transcript_btn)
        transcript_buttons.addWidget(self.save_transcript_btn)
        
        self.transcript_area = QTextEdit()
        self.transcript_area.setReadOnly(False)  # Permitir edição
        
        transcript_layout.addLayout(transcript_buttons)
        transcript_layout.addWidget(self.transcript_area)
        
        self.content_stack.addWidget(transcript_container)  # index 1

    def create_projects_area(self):
        # Área de projetos
        projects_container = QWidget()
        projects_layout = QVBoxLayout(projects_container)
        self.previous_projects_list = QListWidget()
        self.previous_projects_list.itemClicked.connect(self.load_previous_project)
        projects_layout.addWidget(self.previous_projects_list)
        
        self.content_stack.addWidget(projects_container)  # index 2

    def select_video(self):
        options = QFileDialog.Options()
        video_filter = f"Arquivos de Vídeo ({self.VIDEO_FORMATS});;Todos os Arquivos (*)"
        file_name, _ = QFileDialog.getOpenFileName(self, "Selecione um arquivo de vídeo", "", video_filter, options=options)
        if file_name:
            self.selected_video = file_name
            self.file_label.setText(f"Arquivo selecionado: {Path(file_name).name}")
            self.process_button.setEnabled(True)  # Habilitar botão de processar

    def process_video(self):
        if hasattr(self, 'selected_video'):
            self.process_button.setEnabled(False)
            self.select_button.setEnabled(False)
            self.progress_bar.setVisible(True)

            self.worker = AudioProcessingWorker(self.selected_video, self.language_combo.currentText())
            self.worker.progress.connect(self.update_progress)
            self.worker.finished.connect(self.on_processing_finished)
            self.worker.error.connect(self.on_error)

            self.worker.start()

    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.status_label.setText(message)

    def on_processing_finished(self, results):
        try:
            self.current_project = results
            self.process_button.setEnabled(True)
            self.select_button.setEnabled(True)
            self.progress_bar.setVisible(False)
            self.status_label.setText("Processamento concluído!")
            
            # Carregar dados do projeto
            self.load_project_data()
            
            # Mostrar a aba de transcrição
            self.show_content(1)  # index 1 é a aba de transcrição
            
        except Exception as e:
            self.on_error(f"Erro ao finalizar processamento: {str(e)}")

    def on_error(self, error_message):
        self.process_button.setEnabled(True)
        self.select_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Erro: {error_message}")
        self.transcript_area.setText(f"Ocorreu um erro durante o processamento:\n\n{error_message}")
        self.show_content(2)

    def load_project_data(self):
        if self.current_project:
            # Carregar transcrição
            self.load_transcription()
            
            # Verificar se existe áudio completo
            audio_file = Path(self.current_project['audio_file'])
            if not audio_file.exists():
                self.status_label.setText("Aviso: Arquivo de áudio não encontrado")
                return
                
            self.status_label.setText("Projeto carregado com sucesso!")
            
            # Apenas atualizar a lista de vídeos sem carregar o vídeo
            self.update_videos_list()

    def load_transcription(self):
        """Carrega a transcrição do projeto atual"""
        if self.current_project:
            transcript_path = Path(self.current_project['transcripts_dir']) / 'full_audio.json'
            if transcript_path.exists():
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    transcript_data = json.load(f)
                    self.transcript_area.setText(transcript_data.get('transcription', ''))
            else:
                self.transcript_area.clear()

    def show_viewer(self):
        self.show_content(1)
        # Carregar vídeo no novo player
        if hasattr(self, 'selected_video'):
            self.video_player.load_video(self.selected_video)

    def play_segment(self, item):
        segment_path = Path(item.data(Qt.UserRole))
        if segment_path.exists():
            if not hasattr(self, 'segment_player'):
                self.segment_player = QMediaPlayer()
            self.segment_player.setMedia(QMediaContent(QUrl.fromLocalFile(str(segment_path))))
            self.segment_player.play()
        else:
            QMessageBox.warning(self, "Erro", "Arquivo de áudio não encontrado")

    def start_segment_playback(self, media):
        """Inicia a reprodução do segmento garantindo que esteja no início"""
        if self.media_player:
            self.media_player.set_time(0)  # Força posição inicial
            self.media_player.play()

    def show_transcripts(self):
        """Mostra a aba de transcrições"""
        self.show_content(2)

    def show_segments(self):
        """Mostra a aba de segmentos"""
        self.show_content(0)

    def show_segment_context_menu(self, position):
        menu = QMenu()
        delete_action = menu.addAction("Excluir Segmento")
        action = menu.exec_(self.segments_list.mapToGlobal(position))
        if action == delete_action:
            current_item = self.segments_list.currentItem()
            if current_item:
                self.delete_segment(current_item)

    def delete_segment(self, item):
        try:
            if self.current_project:
                segment_path = Path(self.current_project['segments_dir']) / item.text()
                if segment_path.exists():
                    segment_path.unlink()
                    self.segments_list.takeItem(self.segments_list.row(item))
                    QMessageBox.information(self, "Sucesso", "Segmento excluído com sucesso!")
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao excluir segmento: {str(e)}")

    def clear_transcript(self):
        reply = QMessageBox.question(self, "Confirmar", "Deseja limpar a transcrição atual?",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.transcript_area.clear()

    def save_transcript(self):
        try:
            if self.current_project:
                transcript_path = Path(self.current_project['transcripts_dir']) / 'full_audio.json'
                transcript_data = {
                    'transcription': self.transcript_area.toPlainText(),
                    'audio_file': 'full_audio.wav',
                    'language': self.language_combo.currentText()
                }
                with open(transcript_path, 'w', encoding='utf-8') as f:
                    json.dump(transcript_data, f, ensure_ascii=False, indent=2)
                
                QMessageBox.information(self, "Sucesso", "Transcrição salva com sucesso!")
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao salvar transcrição: {str(e)}")

    def refresh_projects_list(self):
        """Atualiza a lista de projetos de forma otimizada"""
        try:
            projects_dir = Path(__file__).parent / 'projects'
            if not projects_dir.exists():
                return

            # Desabilitar atualizações visuais durante o preenchimento
            self.previous_projects_list.setUpdatesEnabled(False)
            self.previous_projects_list.clear()

            # Usar listdir em vez de glob para melhor performance
            project_dirs = []
            for item in os.listdir(str(projects_dir)):
                item_path = projects_dir / item
                if item_path.is_dir():
                    project_dirs.append(item)

            # Ordenar por data de modificação (mais recente primeiro)
            project_dirs.sort(key=lambda x: os.path.getmtime(str(projects_dir / x)), reverse=True)

            # Adicionar itens em lote
            self.previous_projects_list.addItems(project_dirs)

            # Reabilitar atualizações visuais
            self.previous_projects_list.setUpdatesEnabled(True)

        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao atualizar lista de projetos: {str(e)}")

    def load_previous_project(self, project_item):
        try:
            if isinstance(project_item, Path):
                project_dir = project_item
            else:
                project_dir = Path(__file__).parent / 'projects' / project_item.text()

            if not project_dir.exists():
                raise Exception("Diretório do projeto não encontrado")

            # Procurar arquivos necessários
            original_dir = project_dir / 'original'
            segments_dir = project_dir / 'segments'
            
            # Procurar vídeo original e áudio
            video_files = list(original_dir.glob('*.*'))
            video_files = [f for f in video_files if f.suffix.lower() in 
                          ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv']]
            
            if not video_files:
                raise Exception("Vídeo original não encontrado")
                
            video_file = video_files[0]  # Usar o primeiro vídeo encontrado
            audio_file = segments_dir / 'full_audio.wav'

            if not video_file.exists() or not audio_file.exists():
                raise Exception("Arquivos de vídeo ou áudio não encontrados")

            self.current_project = {
                'original_video': str(video_file),
                'audio_file': str(audio_file),
                'segments_dir': str(segments_dir),
                'transcripts_dir': str(project_dir / 'transcripts'),
                'original_dir': str(original_dir),
                'project_id': project_dir.name
            }

            self.selected_video = str(video_file)
            self.file_label.setText(f"Projeto carregado: {project_dir.name}")
            self.load_project_data()
            self.show_viewer()
            QMessageBox.information(self, "Sucesso", "Projeto carregado com sucesso!")

        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao carregar projeto: {str(e)}")

    def show_editor(self):
        """Mostra a aba do editor de segmentos"""
        self.show_content(4)  # Índice do editor de segmentos

    def handle_media_error(self, error):
        """Trata erros do media player"""
        error_msg = "Erro desconhecido"
        if error == QMediaPlayer.FormatError:
            error_msg = "Formato de mídia não suportado"
        elif error == QMediaPlayer.NetworkError:
            error_msg = "Erro de rede"
        elif error == QMediaPlayer.ResourceError:
            error_msg = "Recurso não encontrado"
        QMessageBox.warning(self, "Erro de Reprodução", error_msg)

    def open_editor(self):
        """Abre o editor de vídeo com o projeto atual"""
        if self.current_project:
            video_file = Path(self.current_project['original_video'])
            audio_file = Path(self.current_project['audio_file'])
            
            if video_file.exists() and audio_file.exists():
                self.editor = ClipchampEditor(self.current_project)
                self.editor.show()
            else:
                QMessageBox.warning(self, "Aviso", "Arquivos de vídeo ou áudio não encontrados.")
        else:
            QMessageBox.warning(self, "Aviso", "Nenhum projeto carregado.")

    def segment_selected(self, item):
        """Callback quando um segmento é selecionado"""
        segment_path = Path(item.data(Qt.UserRole))
        if segment_path.exists():
            # Atualizar label com informações do segmento
            self.current_segment_label.setText(f"Segmento: {segment_path.name}")
            
            # Habilitar controles
            for btn in [self.segment_play_btn, self.segment_stop_btn, self.segment_delete_btn]:
                btn.setEnabled(True)

            if not hasattr(self, 'segment_player'):
                self.segment_player = QMediaPlayer()
            self.segment_player.setMedia(QMediaContent(QUrl.fromLocalFile(str(segment_path))))

    def toggle_segment_playback(self):
        """Alterna entre play/pause do segmento"""
        if hasattr(self, 'segment_player'):
            if self.segment_player.state() == QMediaPlayer.PlayingState:
                self.segment_player.pause()
                self.segment_play_btn.setText("⏵")
                self.segment_play_btn.setChecked(False)
            else:
                self.segment_player.play()
                self.segment_play_btn.setText("⏸")
                self.segment_play_btn.setChecked(True)

    def stop_segment(self):
        """Para a reprodução do segmento"""
        if hasattr(self, 'segment_player'):
            self.segment_player.stop()
            self.segment_play_btn.setText("⏵")
            self.segment_play_btn.setChecked(False)

    def update_segment_progress(self):
        """Atualiza a barra de progresso do segmento"""
        if not self.media_player:
            return

        length = self.media_player.get_length()
        if length > 0:
            self.segment_progress.setMaximum(length)
            self.segment_progress.setValue(self.media_player.get_time())

    def delete_current_segment(self):
        """Exclui o segmento selecionado"""
        current_item = self.segments_list.currentItem()
        if current_item:
            reply = QMessageBox.question(
                self,
                "Confirmar Exclusão",
                "Tem certeza que deseja excluir este segmento?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                try:
                    segment_path = Path(current_item.data(Qt.UserRole))
                    if segment_path.exists():
                        segment_path.unlink()
                        self.stop_segment()
                        self.segments_list.takeItem(self.segments_list.row(current_item))
                        self.current_segment_label.setText("Nenhum segmento selecionado")
                        for btn in [self.segment_play_btn, self.segment_stop_btn, self.segment_delete_btn]:
                            btn.setEnabled(False)
                        QMessageBox.information(self, "Sucesso", "Segmento excluído com sucesso!")
                except Exception as e:
                    QMessageBox.warning(self, "Erro", f"Erro ao excluir segmento: {str(e)}")

    def show_content(self, index):
        """Mostra o conteúdo correspondente ao botão clicado"""
        # Desmarcar todos os botões
        for btn in self.menu_buttons.values():
            if hasattr(btn, 'setChecked'):
                btn.setChecked(False)

        # Marcar o botão atual
        sender = self.sender()
        if sender and hasattr(sender, 'setChecked'):
            sender.setChecked(True)
        
        # Mostrar o widget correspondente
        self.content_stack.setCurrentIndex(index)
        
        # Atualizar dados se necessário
        if index == 2:  # Projects tab
            QApplication.setOverrideCursor(Qt.WaitCursor)  # Mostrar cursor de espera
            try:
                self.refresh_projects_list()
            finally:
                QApplication.restoreOverrideCursor()  # Restaurar cursor normal

    def change_video_source(self, index):
        if self.current_project:
            try:
                # Usar sempre o vídeo original
                video_file = Path(self.current_project['original_video'])
                
                if video_file.exists():
                    print(f"Carregando vídeo: {video_file}")  # Debug
                    self.video_player.load_video(str(video_file))
                else:
                    QMessageBox.warning(self, "Erro", f"Arquivo não encontrado: {video_file}")
                    self.video_options.setCurrentIndex(0)
            
            except Exception as e:
                print(f"Erro detalhado: {str(e)}")  # Debug
                QMessageBox.warning(self, "Erro", f"Erro ao trocar fonte do vídeo: {str(e)}")
                self.video_options.setCurrentIndex(0)

    def setup_menu(self):
        """Configura o menu da aplicação"""
        menubar = self.menuBar()
        self.projects_menu = menubar.addMenu('&Projetos')
        
        # Ação para atualizar lista de projetos
        self.refresh_projects_action = QAction('Atualizar Lista', self)
        self.refresh_projects_action.triggered.connect(self.refresh_projects_list)
        self.projects_menu.addAction(self.refresh_projects_action)

    def update_videos_list(self):
        """Atualiza a lista de vídeos disponíveis no projeto atual"""
        if not self.current_project:
            return
            
        self.videos_list.clear()
        
        try:
            # Adicionar vídeo original
            original_video = Path(self.current_project['original_video'])
            if (original_video.exists()):
                item = QListWidgetItem(f"📼 {original_video.name}")
                item.setData(Qt.UserRole, str(original_video))
                self.videos_list.addItem(item)
                
        except Exception as e:
            print(f"Erro ao atualizar lista de vídeos: {e}")

    def select_video_from_list(self, item):
        """Seleciona o vídeo da lista mas não carrega automaticamente"""
        video_path = item.data(Qt.UserRole)
        if video_path:
            self.video_player.selected_video = video_path  # Apenas armazena o caminho
            print(f"Vídeo selecionado: {video_path}")

    def play_selected_video(self):
        """Carrega e reproduz o vídeo selecionado"""
        if hasattr(self.video_player, 'selected_video'):
            self.video_player.load_video(self.video_player.selected_video)
            self.video_player.play()

    def show_video_editor(self):
        """Abre o editor de vídeo com o projeto atual"""
        if self.current_project:
            self.editor_window = ClipchampEditor(self.current_project)
            self.editor_window.show()
        else:
            QMessageBox.warning(self, "Aviso", "Por favor, carregue um projeto primeiro.")
