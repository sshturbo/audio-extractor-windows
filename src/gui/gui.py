from PyQt5.QtWidgets import (QMainWindow, QPushButton, QVBoxLayout, QHBoxLayout,
                           QWidget, QFileDialog, QLabel, QComboBox, QProgressBar,
                           QAction, QListWidget, QListWidgetItem, QTextEdit,
                           QGroupBox, QMessageBox, QMenu, QFrame, QSizePolicy, 
                           QStackedWidget, QSlider, QStyle, QApplication, QProgressDialog, QDialog)  # Adicionado QDialog
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtGui import QIcon, QFont
import json
import time
from pathlib import Path
from src.worker.worker import AudioProcessingWorker
from src.worker.subtitle_worker import SubtitleExtractionWorker  # Fixed import
import sys
import os
from .video_player import VideoPlayer  # Fixed relative import
from .editor_window import VideoEditor  # Also fixed this import
from ..video_editor.clipchamp_editor import ClipchampEditor  # Corrigindo importação para usar caminho relativo
from ..translation.translator import GoogleTranslator  # Adicionando importação do GoogleTranslator

def load_stylesheet(filename):
    """Carrega arquivo CSS"""
    # Corrigindo o caminho para procurar na pasta assets na raiz do projeto
    css_file = Path(__file__).parent.parent.parent / 'assets' / 'css' / filename
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
        
        # Configurar ícone da aplicação
        icon_path = Path(__file__).parent.parent.parent / 'assets' / 'icons' / 'app_icon.png'
        if (icon_path.exists()):
            self.setWindowIcon(QIcon(str(icon_path)))
        
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
        
        # Carregar stylesheet por último, após todos os widgets serem criados
        self.setStyleSheet(load_stylesheet('gui.css'))

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
        
        # Grupo de seleção de arquivo
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

        # Grupo de configuração de idioma
        language_group = QGroupBox("Idioma Alvo")
        language_layout = QVBoxLayout(language_group)
        
        self.language_combo = QComboBox()
        languages = [
            ("Português", "pt"),
            ("English", "en"),
            ("日本語", "ja"),
            ("中文", "zh"),
            ("한국어", "ko"),
            ("Español", "es"),
            ("Français", "fr"),
            ("Deutsch", "de"),
            ("Italiano", "it"),
            ("Русский", "ru")
        ]
        
        for display_name, code in languages:
            self.language_combo.addItem(display_name, code)
        
        self.language_combo.setCurrentText("Português")
        language_layout.addWidget(self.language_combo)
        
        language_hint = QLabel("Selecione o idioma para a tradução final")
        language_hint.setStyleSheet("color: #666; font-style: italic;")
        language_layout.addWidget(language_hint)

        file_layout.addWidget(language_group)

        # Grupo de status e progresso
        status_group = QGroupBox("Status do Processamento")
        status_layout = QVBoxLayout(status_group)

        # Área de log com estilo
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(150)
        self.log_area.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }
        """)
        status_layout.addWidget(self.log_area)

        # Barra de progresso com detalhes
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        
        self.progress_label = QLabel("Aguardando...")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bbb;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        status_layout.addWidget(progress_container)
        
        # Adicionar grupos ao layout principal
        new_project_layout.addWidget(file_group)
        new_project_layout.addWidget(status_group)
        
        self.content_stack.addWidget(new_project_container)

    def log_message(self, message, level="info"):
        """Adiciona mensagem ao log com formatação por nível"""
        color_map = {
            "info": "black",
            "success": "green",
            "warning": "orange",
            "error": "red",
            "progress": "blue"
        }
        color = color_map.get(level, "black")
        
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"<span style='color: gray'>[{timestamp}]</span> <span style='color: {color}'>{message}</span>"
        
        self.log_area.append(formatted_message)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def update_progress(self, value, message=""):
        """Atualiza a barra de progresso e o log"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
        
        # Adicionar ao log se for uma nova mensagem
        if message and message != self.progress_label.text():
            self.log_message(message, "progress")

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

        # Botão de reprodução
        play_button = QPushButton("Reproduzir Selecionado")
        play_button.clicked.connect(self.play_selected_video)
        videos_layout.addWidget(play_button)
        
        # Botões de controle de vídeo
        buttons_layout = QHBoxLayout()
        
        # Adicionar botão de extração de legendas
        extract_subtitles_btn = QPushButton("Extrair Legendas")
        extract_subtitles_btn.clicked.connect(self.extract_video_subtitles)
        buttons_layout.addWidget(extract_subtitles_btn)
        
        videos_layout.addLayout(buttons_layout)
        
        video_layout.addWidget(videos_group, stretch=1)
        
        # Player de vídeo (lado direito)
        player_container = QWidget()
        player_layout = QVBoxLayout(player_container)
        self.video_player = VideoPlayer()
        player_layout.addWidget(self.video_player)
        
        video_layout.addWidget(player_container, stretch=2)
        
        self.content_stack.addWidget(video_container)
        self.content_layout.addWidget(self.content_stack)

    def extract_video_subtitles(self):
        """Extrai legendas do vídeo selecionado"""
        if not self.current_project:
            QMessageBox.warning(self, "Aviso", "Por favor, carregue um projeto primeiro.")
            return
            
        try:
            # Mostrar diálogo de seleção de idioma
            lang_dialog = LanguageSelectionDialog(self)
            if lang_dialog.exec_() != QDialog.Accepted:
                return  # Usuário cancelou
                
            target_language = lang_dialog.get_selected_language()
            
            video_file = Path(self.current_project['original_video'])
            if not video_file.exists():
                raise FileNotFoundError("Arquivo de vídeo não encontrado")
            
            # Criar diretório para legendas
            subtitles_dir = Path(self.current_project['transcripts_dir']) / "subtitles"
            subtitles_dir.mkdir(parents=True, exist_ok=True)
            
            # Mostrar diálogo de progresso
            progress = QProgressDialog("Extraindo legendas do vídeo...", "Cancelar", 0, 100, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setAutoClose(False)  # Não fechar automaticamente
            progress.show()
            
            # Iniciar extração em thread separada
            self.subtitle_worker = SubtitleExtractionWorker(
                str(video_file), 
                subtitles_dir,
                target_language  # Passar o idioma selecionado
            )
            
            # Conectar sinais
            self.subtitle_worker.progressChanged.connect(progress.setValue)
            self.subtitle_worker.statusChanged.connect(progress.setLabelText)
            self.subtitle_worker.logMessage.connect(lambda msg: self.log_message(msg, "info"))
            self.subtitle_worker.finished.connect(progress.close)
            self.subtitle_worker.finished.connect(self.on_subtitle_extraction_finished)
            self.subtitle_worker.error.connect(self.on_subtitle_extraction_error)
            
            self.subtitle_worker.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao iniciar extração de legendas: {str(e)}")

    def on_subtitle_extraction_finished(self, subtitles_file):
        """Chamado quando a extração de legendas é concluída"""
        try:
            # Carregar legendas extraídas
            with open(subtitles_file, 'r', encoding='utf-8') as f:
                subtitles_data = json.load(f)
            
            # Atualizar área de texto
            if subtitles_data and 'subtitles' in subtitles_data:
                extracted_text = "\n".join(sub['text'] for sub in subtitles_data['subtitles'] if sub['text'])
                self.original_text_area.setText(extracted_text)
                
                # Tentar traduzir automaticamente
                if self.language_combo.currentData() != "en":  # Se não for inglês
                    self.retranslate_text()
            
            QMessageBox.information(self, "Sucesso", 
                "Legendas extraídas com sucesso!\nAs legendas foram carregadas na área de texto.")
            
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao carregar legendas extraídas: {str(e)}")

    def on_subtitle_extraction_error(self, error_msg):
        """Chamado quando ocorre um erro na extração de legendas"""
        QMessageBox.critical(self, "Erro", f"Erro na extração de legendas: {error_msg}")

    def create_transcription_area(self):
        """Cria a área de transcrição com suporte a múltiplos idiomas"""
        transcript_container = QWidget()
        transcript_layout = QVBoxLayout(transcript_container)
        
        # Área de informações de idioma
        lang_info = QHBoxLayout()
        self.detected_lang_label = QLabel("Idioma detectado: -")
        self.target_lang_label = QLabel("Idioma alvo: -")
        lang_info.addWidget(self.detected_lang_label)
        lang_info.addWidget(self.target_lang_label)
        transcript_layout.addLayout(lang_info)
        
        # Botões de controle
        transcript_buttons = QHBoxLayout()
        self.clear_transcript_btn = QPushButton("Limpar")
        self.save_transcript_btn = QPushButton("Salvar")
        self.retranslate_btn = QPushButton("Traduzir Novamente")
        
        self.clear_transcript_btn.clicked.connect(self.clear_transcript)
        self.save_transcript_btn.clicked.connect(self.save_transcript)
        self.retranslate_btn.clicked.connect(self.retranslate_text)
        
        transcript_buttons.addWidget(self.clear_transcript_btn)
        transcript_buttons.addWidget(self.save_transcript_btn)
        transcript_buttons.addWidget(self.retranslate_btn)
        
        # Criar áreas de texto para original e tradução
        texts_layout = QHBoxLayout()
        
        # Área de texto original
        original_group = QGroupBox("Texto Original")
        original_layout = QVBoxLayout(original_group)
        self.original_text_area = QTextEdit()
        self.original_text_area.setReadOnly(True)
        original_layout.addWidget(self.original_text_area)
        
        # Área de texto traduzido
        translated_group = QGroupBox("Texto Traduzido")
        translated_layout = QVBoxLayout(translated_group)
        self.transcript_area = QTextEdit()
        self.transcript_area.setReadOnly(False)  # Permitir edição da tradução
        translated_layout.addWidget(self.transcript_area)
        
        # Adicionar as duas áreas lado a lado
        texts_layout.addWidget(original_group)
        texts_layout.addWidget(translated_group)
        
        # Montar layout final
        transcript_layout.addLayout(transcript_buttons)
        transcript_layout.addLayout(texts_layout)
        
        self.content_stack.addWidget(transcript_container)

    def retranslate_text(self):
        """Traduz o texto novamente usando o Google Translate"""
        if not self.current_project:
            return
        
        try:
            # Obter texto original e idioma alvo
            original_text = self.original_text_area.toPlainText()
            target_lang = self.language_combo.currentData()
            
            if not original_text:
                QMessageBox.warning(self, "Aviso", "Não há texto original para traduzir.")
                return
            
            # Criar tradutor e traduzir
            translator = GoogleTranslator()
            translated_text = translator.translate(original_text, target_lang)
            
            # Atualizar área de texto traduzido
            self.transcript_area.setText(translated_text)
            
            QMessageBox.information(self, "Sucesso", "Texto traduzido com sucesso!")
            
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao traduzir texto: {str(e)}")

    def update_language_labels(self, detected_lang, target_lang):
        """Atualiza os labels de idioma"""
        self.detected_lang_label.setText(f"Idioma detectado: {detected_lang}")
        self.target_lang_label.setText(f"Idioma alvo: {target_lang}")

    def load_transcription(self):
        """Carrega a transcrição do projeto atual"""
        if self.current_project:
            transcript_path = Path(self.current_project['transcripts_dir']) / 'full_audio.json'
            if transcript_path.exists():
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    transcript_data = json.load(f)
                    self.original_text_area.setText(transcript_data.get('original_text', ''))
                    self.transcript_area.setText(transcript_data.get('translated_text', ''))
                    
                    # Atualizar labels de idioma
                    source_lang = transcript_data.get('source_language', '-')
                    target_lang = transcript_data.get('target_language', '-')
                    self.update_language_labels(source_lang, target_lang)
            else:
                self.original_text_area.clear()
                self.transcript_area.clear()
                self.update_language_labels('-', '-')

    def clear_transcript(self):
        reply = QMessageBox.question(self, "Confirmar", "Deseja limpar a transcrição atual?",
                                   QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.original_text_area.clear()
            self.transcript_area.clear()

    def save_transcript(self):
        try:
            if self.current_project:
                transcript_path = Path(self.current_project['transcripts_dir']) / 'full_audio.json'
                transcript_data = {
                    'audio_file': 'full_audio.wav',
                    'language': self.language_combo.currentText(),
                    'original_text': self.original_text_area.toPlainText(),
                    'translated_text': self.transcript_area.toPlainText()
                }
                with open(transcript_path, 'w', encoding='utf-8') as f:
                    json.dump(transcript_data, f, ensure_ascii=False, indent=2)
                
                QMessageBox.information(self, "Sucesso", "Transcrição salva com sucesso!")
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao salvar transcrição: {str(e)}")

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
            try:
                self.log_area.clear()  # Limpar logs anteriores
                self.log_message("=== Iniciando Novo Processamento ===", "info")
                self.log_message(f"Vídeo selecionado: {self.selected_video}", "info")
                
                self.process_button.setEnabled(False)
                self.select_button.setEnabled(False)
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
                
                # Pegar o código do idioma
                selected_language = self.language_combo.currentData()
                if not selected_language:
                    selected_language = "pt"
                    
                self.log_message(f"Idioma selecionado: {self.language_combo.currentText()} ({selected_language})", "info")

                # Configurar e iniciar o worker
                self.worker = AudioProcessingWorker(self.selected_video, selected_language)
                self.worker.progress.connect(self.update_progress)
                self.worker.status.connect(lambda msg: self.log_message(msg, "progress"))
                self.worker.finished.connect(self.on_processing_finished)
                self.worker.error.connect(self.on_error)

                self.log_message("Iniciando processamento...", "success")
                self.worker.start()

            except Exception as e:
                self.on_error(str(e))

    def update_progress(self, value, message=""):
        """Atualiza a barra de progresso e o log"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
        
        # Adicionar ao log se for uma nova mensagem
        if message != self.progress_label.text():
            self.log_message(message, "progress")

    def on_processing_finished(self, results):
        try:
            self.current_project = results
            self.process_button.setEnabled(True)
            self.select_button.setEnabled(True)
            
            self.log_message("✓ Processamento concluído com sucesso!", "success")
            self.progress_bar.setValue(100)
            self.progress_label.setText("Processamento concluído!")
            
            # Carregar dados do projeto
            self.load_project_data()
            
            # Mostrar a aba de transcrição
            self.show_content(1)
            
        except Exception as e:
            self.on_error(f"Erro ao finalizar processamento: {str(e)}")  # Fixed missing parenthesis and quote

    def on_error(self, error_message):
        self.log_message(f"❌ ERRO: {error_message}", "error")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Erro no processamento")
        self.process_button.setEnabled(True)
        self.select_button.setEnabled(True)
        QMessageBox.critical(self, "Erro", error_message)

    def load_project_data(self):
        if self.current_project:
            # Carregar transcrição
            self.load_transcription()
            
            # Verificar se existe áudio completo
            audio_file = Path(self.current_project['audio_file'])
            if not audio_file.exists():
                self.log_message("Aviso: Arquivo de áudio não encontrado", "warning")
                return
                
            self.log_message("Projeto carregado com sucesso!", "success")
            
            # Apenas atualizar a lista de vídeos sem carregar o vídeo
            self.update_videos_list()

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
            self.original_text_area.clear()
            self.transcript_area.clear()

    def save_transcript(self):
        try:
            if self.current_project:
                transcript_path = Path(self.current_project['transcripts_dir']) / 'full_audio.json'
                transcript_data = {
                    'audio_file': 'full_audio.wav',
                    'language': self.language_combo.currentText(),
                    'original_text': self.original_text_area.toPlainText(),
                    'translated_text': self.transcript_area.toPlainText()
                }
                with open(transcript_path, 'w', encoding='utf-8') as f:
                    json.dump(transcript_data, f, ensure_ascii=False, indent=2)
                
                QMessageBox.information(self, "Sucesso", "Transcrição salva com sucesso!")
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao salvar transcrição: {str(e)}")

    def refresh_projects_list(self):
        """Atualiza a lista de projetos"""
        try:
            self.previous_projects_list.clear()
            # Garantir que usamos o caminho absoluto para a pasta projects
            projects_dir = Path("projects").absolute()
            print(f"Procurando projetos em: {projects_dir}")
            
            if projects_dir.exists():
                for project_dir in sorted(projects_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                    if project_dir.is_dir():
                        item = QListWidgetItem(project_dir.name)
                        # Armazenar o caminho completo nos dados do item
                        item.setData(Qt.UserRole, str(project_dir))
                        self.previous_projects_list.addItem(item)
                print(f"Encontrados {self.previous_projects_list.count()} projetos")
            else:
                print("Diretório de projetos não encontrado")
                
        except Exception as e:
            print(f"Erro ao atualizar lista de projetos: {e}")

    def load_previous_project(self, project_item):
        try:
            # Usar o caminho armazenado nos dados do item
            project_dir = Path(project_item.data(Qt.UserRole) if hasattr(project_item, 'data') else str(project_item))

            if not project_dir.exists():
                raise Exception(f"Diretório do projeto não encontrado: {project_dir}")

            print(f"Carregando projeto de: {project_dir}")  # Debug log

            # Garantir caminhos absolutos para todas as subpastas
            original_dir = project_dir / 'original'
            segments_dir = project_dir / 'segments'
            transcripts_dir = project_dir / 'transcripts'

            # Verificar existência das pastas
            for dir_path in [original_dir, segments_dir, transcripts_dir]:
                if not dir_path.exists():
                    raise Exception(f"Pasta necessária não encontrada: {dir_path}")

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
                'transcripts_dir': str(transcripts_dir),
                'original_dir': str(original_dir),
                'project_id': project_dir.name
            }

            self.selected_video = str(video_file)
            self.file_label.setText(f"Projeto carregado: {project_dir.name}")
            self.load_project_data()
            self.show_viewer()
            QMessageBox.information(self, "Sucesso", "Projeto carregado com sucesso!")
            print(f"Projeto carregado: {project_dir}")

        except Exception as e:
            print(f"Erro ao carregar projeto: {e}")  # Debug
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
        # Iniciar editor sem passar arquivos automaticamente
        self.editor = VideoEditor()
        self.editor.show()
        
        # Se existir um projeto, apenas preparar o áudio
        if self.current_project:
            audio_file = Path(self.current_project['audio_file'])
            if audio_file.exists():
                self.editor.audio_file = str(audio_file)
                self.editor.setup_audio_player()

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
            self.video_player.selected_video = video_path
            # Atualizar UI para mostrar o vídeo selecionado
            print(f"Vídeo selecionado: {video_path}")
            
            # Resetar player anterior se existir
            if self.video_player.player:
                self.video_player.stop()
                self.video_player.player = None

    def play_selected_video(self):
        """Carrega e reproduz o vídeo selecionado"""
        if hasattr(self.video_player, 'selected_video') and self.video_player.selected_video:
            if not self.video_player.player:
                if self.video_player.load_video(self.video_player.selected_video):
                    self.video_player.toggle_play()
            else:
                self.video_player.toggle_play()

    def show_video_editor(self):
        """Abre o editor de vídeo com o projeto atual"""
        if self.current_project:
            self.editor_window = ClipchampEditor(self.current_project)
            self.editor_window.show()
        else:
            QMessageBox.warning(self, "Aviso", "Por favor, carregue um projeto primeiro.")

    def create_status_area(self):
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Aguardando processamento...")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        
        return status_group

    def update_status(self, message):
        self.status_label.setText(message)

class LanguageSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Selecionar Idioma")
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Adicionar explicação
        explanation = QLabel("Selecione o idioma para a geração das legendas:")
        layout.addWidget(explanation)
        
        # Criar combo box de idiomas
        self.language_combo = QComboBox()
        languages = [
            ("Português (Brasil)", "pt-BR"),
            ("English", "en-US"),
            ("日本語", "ja-JP"),
            ("中文", "zh-CN"),
            ("한국어", "ko-KR"),
            ("Español", "es-ES"),
            ("Français", "fr-FR"),
            ("Deutsch", "de-DE"),
            ("Italiano", "it-IT"),
            ("Русский", "ru-RU")
        ]
        
        for display_name, code in languages:
            self.language_combo.addItem(display_name, code)
            
        layout.addWidget(self.language_combo)
        
        # Botões
        button_box = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancelar")
        
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        
        button_box.addWidget(ok_button)
        button_box.addWidget(cancel_button)
        layout.addLayout(button_box)

    def get_selected_language(self):
        return self.language_combo.currentData()
