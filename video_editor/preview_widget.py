from typing import Optional, List, Dict

# Standard library imports
import time
import traceback
from pathlib import Path

# Third-party imports
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QSizePolicy, QHBoxLayout,
    QSlider, QWidget, QPushButton, QMenu, QActionGroup, 
    QStyle, QAction, QWidgetAction
)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QImage, QPixmap

# Local imports
from video_editor.vlc_player import VLCPlayer


class PreviewWidget(QFrame):
    """
    Widget para preview e controle de vídeo com interface gráfica.
    
    Este widget fornece controles completos de reprodução de vídeo incluindo:
    - Play/Pause/Stop
    - Controle de velocidade
    - Controle de volume
    - Barra de progresso
    - Preview do vídeo
    
    Attributes:
        UPDATE_INTERVAL: Intervalo de atualização do frame em ms
        LOAD_WAIT_TIME: Tempo de espera para carregamento do vídeo em segundos
        AVAILABLE_SPEEDS: Lista de velocidades de reprodução disponíveis
    """
    
    # Constantes da classe
    UPDATE_INTERVAL: int = 16
    LOAD_WAIT_TIME: float = 2.0
    AVAILABLE_SPEEDS: List[float] = [
        0.25,  # Muito lento
        0.5,   # Lento
        0.75,  # Devagar
        1.0,   # Normal
        1.25,  # Pouco rápido
        1.5,   # Rápido
        1.75,  # Muito rápido
        2.0    # Ultra rápido
    ]
    
    def __init__(self) -> None:
        """Inicializa o widget de preview de vídeo."""
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: #1A1A1A;
                border-radius: 10px;
            }
            QSlider::groove:horizontal {
                border: none;
                background: #333333;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #0078D4;
                border: 2px solid #0078D4;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 10px;
            }
            QSlider::handle:horizontal:hover {
                background: #2B88D9;
                border-color: #2B88D9;
            }
            QSlider::sub-page:horizontal {
                background: #0078D4;
                border-radius: 2px;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 20px;
                padding: 8px;
                margin: 2px;
                min-width: 40px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.08);
            }
            QLabel {
                color: #E0E0E0;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            #time_label {
                color: #0078D4;
                font-weight: bold;
                padding: 5px 10px;
                background-color: rgba(0, 120, 212, 0.1);
                border-radius: 4px;
            }
            #speed_button {
                color: #4CAF50;
                font-weight: bold;
                padding: 8px 16px;
                border: 1px solid #4CAF50;
                background-color: rgba(76, 175, 80, 0.1);
            }
            #speed_button:hover {
                background-color: rgba(76, 175, 80, 0.15);
            }
        """)
        
        # Estado do player
        self.player: Optional[VLCPlayer] = None
        self.is_playing: bool = False
        self.duration: int = 0
        self.slider_being_dragged: bool = False
        self.was_playing: bool = False
        self.current_speed_index: int = 3  # Índice da velocidade normal (1.0)
        self.playback_speed: float = self.AVAILABLE_SPEEDS[self.current_speed_index]
        self.last_volume: int = 100
        
        # Configuração da UI
        self.setup_ui()
        
        # Timer para atualização contínua da posição
        self.position_timer = QTimer()
        self.position_timer.setInterval(100)
        self.position_timer.timeout.connect(self.update_position)

    def setup_ui(self) -> None:
        self.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 4px;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QPushButton {
                background-color: #333333;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px;
                min-width: 35px;
                min-height: 35px;
                margin: 0px 5px;
            }
            QPushButton:hover {
                background-color: #404040;
            }
            QPushButton:pressed {
                background-color: #505050;
            }
            #speed_control QPushButton {
                font-weight: bold;
                min-width: 30px;
                max-width: 30px;
            }
            #speed_control QLabel {
                font-family: 'Consolas', monospace;
                font-weight: bold;
                color: #4CAF50;
                background-color: #2d2d2d;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Display de vídeo
        self.display = QLabel()
        self.display.setAlignment(Qt.AlignCenter)
        self.display.setStyleSheet("background-color: black;")
        self.display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.display.setMinimumSize(320, 240)
        layout.addWidget(self.display)
        
        # Container para controles de progresso
        progress_container = QWidget()
        progress_container.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-radius: 8px;
            }
            QLabel {
                color: #e0e0e0;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                padding: 0 5px;
            }
            QSlider::groove:horizontal {
                border: none;
                height: 6px;
                background: #333333;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #4CAF50;
                border: none;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #66BB6A;
            }
            QSlider::sub-page:horizontal {
                background: #4CAF50;
                border-radius: 3px;
            }
        """)
        
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(10, 5, 10, 5)
        
        # Barra de progresso e tempo com layout melhorado
        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("00:00")
        self.duration_label = QLabel("00:00")
        
        # Configuração do slider de progresso
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setTracking(True)
        self.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_slider_released)
        self.progress_slider.sliderMoved.connect(self.on_slider_moved)
        
        time_layout.addWidget(self.current_time_label)
        time_layout.addWidget(self.progress_slider)
        time_layout.addWidget(self.duration_label)
        
        progress_layout.addLayout(time_layout)

        # Botões de controle alinhados
        controls_container = QWidget()
        controls_layout = QHBoxLayout(controls_container)
        controls_layout.setContentsMargins(10, 5, 10, 5)
        controls_layout.setAlignment(Qt.AlignCenter)  # Centralizar todos os controles
        
        # Atualizar estilo dos botões com sombras e efeitos mais elegantes
        button_style = """
            QPushButton {
                background-color: #333333;
                color: white;
                border: none;
                border-radius: 17px;
                padding: 8px;
                min-width: 35px;
                min-height: 35px;
                margin: 0px 5px;
            }
            QPushButton:hover {
                background-color: #404040;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
            #speed_button {
                background-color: #2D2D2D;
                color: #4CAF50;
                border: 1px solid #404040;
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 80px;
                font-weight: bold;
                margin: 0 10px;
                font-family: 'Segoe UI', sans-serif;
            }
            #speed_button:hover {
                background-color: #353535;
                border-color: #4CAF50;
            }
            #speed_button:pressed {
                background-color: #252525;
            }
        """
        
        # Botões de controle com tamanho fixo e ícones proporcionais
        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.setFixedSize(40, 40)
        self.play_button.setIconSize(QSize(24, 24))
        self.play_button.clicked.connect(self.toggle_playback)
        
        self.stop_button = QPushButton()
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_button.setFixedSize(40, 40)
        self.stop_button.setIconSize(QSize(24, 24))
        self.stop_button.clicked.connect(self.stop)
        
        # Menu de velocidade com design aprimorado
        self.speed_menu = QMenu(self)
        self.speed_menu.setStyleSheet("""
            QMenu {
                background-color: #2D2D2D;
                color: white;
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
                color: #4CAF50;
            }
            QMenu::item:checked {
                color: #4CAF50;
                font-weight: bold;
            }
            QMenu::separator {
                height: 1px;
                background: #404040;
                margin: 6px 0px;
            }
            QMenu::indicator {
                width: 18px;
                height: 18px;
            }
        """)

        # Grupo para ações de velocidade com ícones
        speed_group = QActionGroup(self)
        speed_group.setExclusive(True)

        # Velocidades com ícones indicativos
        for i, speed in enumerate(self.AVAILABLE_SPEEDS):
            icon = "⏪" if speed < 1 else "⏩" if speed > 1 else "▶️"
            action = QAction(f"{icon} {speed:.2f}x", self)
            action.setCheckable(True)
            action.setChecked(speed == 1.0)  # Marcar 1.0x como padrão
            action.setData(i)  # Usando o índice como dado
            speed_group.addAction(action)
            self.speed_menu.addAction(action)
            # Conectar usando lambda com captura correta do índice
            action.triggered.connect(lambda checked, s=speed, i=i: self.set_playback_speed(i))

        # Botão de velocidade com estilo personalizado
        self.speed_button = QPushButton("▶️ 1.00x")
        self.speed_button.setObjectName("speed_button")
        self.speed_button.setFixedSize(80, 40)
        self.speed_button.clicked.connect(self.show_speed_menu)
        self.speed_button.setToolTip("Alterar velocidade de reprodução")

        # Aplicar estilos aos botões
        self.play_button.setStyleSheet(button_style)
        self.stop_button.setStyleSheet(button_style)
        self.speed_button.setStyleSheet(button_style)

        # Adicionar widgets ao layout com alinhamento central
        controls_layout.addStretch()
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.speed_button)
        controls_layout.addStretch()

        # Menu de áudio com controles de volume
        self.audio_menu = QMenu(self)
        self.audio_menu.setStyleSheet("""
            QMenu {
                background-color: #2D2D2D;
                color: white;
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
            QMenu::separator {
                height: 1px;
                background: #404040;
                margin: 6px 0px;
            }
        """)

        # Slider de volume no menu
        volume_widget = QWidget()
        volume_layout = QHBoxLayout(volume_widget)
        volume_layout.setContentsMargins(10, 5, 10, 5)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(150)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none;
                height: 6px;
                background: #333333;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #4CAF50;
                border: none;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #4CAF50;
                border-radius: 3px;
            }
        """)
        self.volume_slider.valueChanged.connect(self.set_volume)

        volume_layout.addWidget(QLabel("🔈"))  # Ícone de volume
        volume_layout.addWidget(self.volume_slider)
        volume_layout.addWidget(QLabel("🔊"))  # Ícone de volume alto

        volume_action = QWidgetAction(self)
        volume_action.setDefaultWidget(volume_widget)
        self.audio_menu.addAction(volume_action)
        
        # Ação de Mute
        self.mute_action = QAction("🔇 Mudo", self)
        self.mute_action.setCheckable(True)
        self.mute_action.triggered.connect(self.toggle_mute)
        self.audio_menu.addAction(self.mute_action)

        # Inicialização do volume
        self.last_volume = 100
        self.volume_slider.setValue(100)

        # Conectar eventos de volume
        self.volume_slider.valueChanged.connect(lambda v: self.set_volume(v))
        self.mute_action.triggered.connect(lambda checked: self.toggle_mute())

        # Botão de volume com estilo personalizado
        self.volume_button = QPushButton("🔊")
        self.volume_button.setObjectName("volume_button")
        self.volume_button.setFixedSize(40, 40)
        self.volume_button.clicked.connect(self.show_volume_menu)
        self.volume_button.setStyleSheet(button_style)
        self.volume_button.setToolTip("Controle de Volume")

        # Adicionar o botão de volume ao layout de controles
        controls_layout.addWidget(self.volume_button)
        controls_layout.addStretch()

        progress_layout.addWidget(controls_container)
        layout.addWidget(progress_container)

        # Configurar timer de atualização
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_frame)
        self.update_timer.setInterval(self.UPDATE_INTERVAL)

        # Aplicar efeito de sombra ao container de controles
        controls_container.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
        """)

        # Atualizar o texto do botão de velocidade ao inicializar
        self.speed_button.setText(f"▶️ {self.AVAILABLE_SPEEDS[self.current_speed_index]:.2f}x")
        self.speed_button.setStyleSheet(f"""
            #speed_button {{
                background-color: #2D2D2D;
                color: {self.get_speed_color(self.AVAILABLE_SPEEDS[self.current_speed_index])};
                border: 1px solid {self.get_speed_color(self.AVAILABLE_SPEEDS[self.current_speed_index])};
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            #speed_button:hover {{
                background-color: #353535;
            }}
        """)

    def show_speed_menu(self) -> None:
        """Mostra o menu de velocidade abaixo do botão"""
        pos = self.speed_button.mapToGlobal(self.speed_button.rect().bottomLeft())
        self.speed_menu.popup(pos)

    def show_volume_menu(self) -> None:
        pos = self.volume_button.mapToGlobal(self.volume_button.rect().bottomLeft())
        self.audio_menu.popup(pos)

    def load_video(self, file_path: str) -> bool:
        """
        Carrega um arquivo de vídeo no player.
        
        Args:
            file_path: Caminho do arquivo de vídeo a ser carregado
            
        Returns:
            bool: True se o vídeo foi carregado com sucesso, False caso contrário
        """
        try:
            print(f"Carregando vídeo: {file_path}")
            
            # Limpar player anterior se existir
            if self.player:
                self.player.stop()
                self.player = None
            
            # Criar novo player
            self.player = VLCPlayer(self.display)
            success = self.player.load(file_path)
            
            if not success:
                print("Falha ao carregar o vídeo")
                return False
                
            # Configurar player com timeout
            max_attempts = 10
            attempt = 0
            while attempt < max_attempts:
                try:
                    self._configure_player()
                    return True
                except Exception as e:
                    print(f"Tentativa {attempt + 1}/{max_attempts} falhou: {e}")
                    attempt += 1
                    import time
                    time.sleep(0.5)  # Esperar 500ms entre tentativas
                    
            print("Falha ao configurar player após múltiplas tentativas")
            return False
                
        except Exception as e:
            print(f"Erro ao carregar vídeo: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _configure_player(self) -> None:
        """Configura o estado inicial do player após carregar um vídeo."""
        # Obter duração do vídeo com timeout
        max_attempts = 5
        attempt = 0
        
        while attempt < max_attempts:
            self.duration = self.player.get_length()
            if self.duration > 0:
                break
            attempt += 1
            import time
            time.sleep(0.2)  # Esperar 200ms entre tentativas
        
        if self.duration <= 0:
            raise Exception("Não foi possível obter a duração do vídeo")
        
        # Configurar slider
        self.progress_slider.setRange(0, self.duration)
        self.progress_slider.setSingleStep(1000)
        self.progress_slider.setPageStep(5000)
        
        # Resetar estado
        self.progress_slider.setValue(0)
        self.update_time_label(0, self.duration)
        self.is_playing = False
        self.slider_being_dragged = False
        self.was_playing = False
        
        # Iniciar timer e habilitar controles
        self.position_timer.start()
        self._enable_controls()
        
        # Resetar velocidade com delay
        QTimer.singleShot(500, lambda: self.set_playback_speed(3))  # 1.0x

    def _enable_controls(self) -> None:
        """Habilita os controles do player após carregar um vídeo."""
        self.speed_button.setEnabled(True)
        self.play_button.setEnabled(True)
        self.stop_button.setEnabled(True)

    def play(self) -> None:
        if self.player and not self.is_playing:
            self.player.play()
            self.is_playing = True
            self.position_timer.start()
            print("Iniciando reprodução")

    def pause(self) -> None:
        if self.player and self.is_playing:
            self.player.pause()
            self.is_playing = False
            print("Pausando reprodução")

    def stop(self) -> None:
        if self.player:
            self.player.stop()
            self.is_playing = False
            self.position_timer.stop()
            self.progress_slider.setValue(0)
            self.update_time_label(0, self.duration)
            print("Parando reprodução")

    def on_slider_pressed(self) -> None:
        """Chamado quando o usuário começa a arrastar o slider"""
        self.slider_being_dragged = True
        if self.is_playing:
            self.was_playing = True
            self.player.pause()
            print("Slider pressionado - pausando vídeo")

    def on_slider_released(self) -> None:
        """Chamado quando o usuário solta o slider"""
        position = self.progress_slider.value()
        print(f"Mudando posição para: {position}ms")
        self.player.set_time(position)
        
        if self.was_playing:
            self.player.play()
            self.is_playing = True
            print("Retomando reprodução")
            
        self.was_playing = False
        self.slider_being_dragged = False

    def on_slider_moved(self, position: int) -> None:
        """Chamado quando o usuário move o slider"""
        self.update_time_label(position, self.duration)
        print(f"Slider movido para: {position}ms")

    def update_position(self) -> None:
        """Atualiza a posição do slider e o tempo mostrado"""
        if not self.player or self.slider_being_dragged:
            return
        
        try:
            position = self.player.get_time()
            if position is not None and position >= 0:
                # Atualizar slider somente se a mudança for significativa
                current_value = self.progress_slider.value()
                if abs(current_value - position) > 100:  # 100ms de diferença
                    self.progress_slider.setValue(position)
                    self.update_time_label(position, self.duration)
                    print(f"Posição atual: {position}ms / {self.duration}ms")
                    
                    # Adicionar efeito de brilho no slider
                    self.progress_slider.setStyleSheet("""
                        QSlider::handle:horizontal {
                            background: qradialgradient(
                                cx: 0.5, cy: 0.5, radius: 0.8,
                                fx: 0.5, fy: 0.5,
                                stop: 0 #0078D4,
                                stop: 1 #005A9E
                            );
                            border: 2px solid #0078D4;
                        }
                    """)
                    QTimer.singleShot(100, self.reset_slider_style)
                    
        except Exception as e:
            print(f"Erro ao atualizar posição: {e}")

    def reset_slider_style(self):
        """Reseta o estilo do slider após o efeito de brilho"""
        self.progress_slider.setStyleSheet("")

    def update_time_label(self, position: int, duration: int) -> None:
        """Atualiza os labels de tempo com validação de valores"""
        try:
            # Garantir que os valores são válidos
            position = max(0, position if position is not None else 0)
            duration = max(0, duration if duration is not None else 0)
            
            current = self.format_time(position)
            total = self.format_time(duration)
            
            self.current_time_label.setText(current)
            self.duration_label.setText(total)
            
        except Exception as e:
            print(f"Erro ao atualizar label de tempo: {e}")

    def format_time(self, ms: int) -> str:
        """Converte milissegundos em formato MM:SS"""
        try:
            s = int(ms // 1000)
            m = int(s // 60)
            s = int(s % 60)
            return f"{m:02d}:{s:02d}"
        except Exception as e:
            print(f"Erro ao formatar tempo: {e}")
            return "00:00"

    def check_sync(self) -> None:
        """Verifica sincronização A/V"""
        if self.player and self.is_playing:
            try:
                position = self.player.get_time()
                if position is not None:
                    if not self.progress_slider.isSliderDown():
                        self.progress_slider.setValue(position)
                        self.update_time_label(position, self.duration)
            except Exception as e:
                print(f"Erro ao verificar sincronização: {e}")

    def update_frame(self) -> None:
        """Atualiza o frame atual e o progresso"""
        if self.player and self.is_playing:
            try:
                position = self.player.get_time()
                if position is not None and not self.progress_slider.isSliderDown():
                    self.progress_slider.setValue(position)
                    self.update_time_label(position, self.duration)
            except Exception as e:
                print(f"Erro ao atualizar frame: {e}")

    def set_playback_speed(self, speed_index: int) -> bool:
        """
        Define a velocidade de reprodução do vídeo.
        
        Args:
            speed_index: Índice da velocidade na lista AVAILABLE_SPEEDS
            
        Returns:
            bool: True se a velocidade foi alterada com sucesso
        """
        try:
            if not self.player or not 0 <= speed_index < len(self.AVAILABLE_SPEEDS):
                return False
                
            speed = self.AVAILABLE_SPEEDS[speed_index]
            print(f"Alterando velocidade para: {speed}x")
            
            if not self.player.set_rate(float(speed)):
                print("Falha ao alterar velocidade")
                return False
                
            self.current_speed_index = speed_index
            self.playback_speed = speed
            
            self._update_speed_ui(speed_index)
            return True
            
        except Exception as e:
            print(f"Erro ao alterar velocidade: {e}")
            return False
            
    def _update_speed_ui(self, speed_index: int) -> None:
        """Atualiza a UI após mudança de velocidade."""
        speed = self.AVAILABLE_SPEEDS[speed_index]
        self.speed_button.setText(f"▶️ {speed:.2f}x")
        
        for action in self.speed_menu.actions():
            if isinstance(action, QAction) and action.data() == speed_index:
                action.setChecked(True)

    def increase_speed(self) -> None:
        """Aumenta a velocidade para o próximo nível"""
        if self.current_speed_index < len(self.AVAILABLE_SPEEDS) - 1:
            self.set_playback_speed(self.current_speed_index + 1)

    def decrease_speed(self) -> None:
        """Diminui a velocidade para o nível anterior"""
        if self.current_speed_index > 0:
            self.set_playback_speed(self.current_speed_index - 1)

    def get_current_speed_text(self) -> str:
        """Retorna o texto formatado da velocidade atual"""
        return f"{self.playback_speed:.2f}x"

    def start_fast_forward(self) -> None:
        """Inicia avanço rápido"""
        try:
            if self.player:
                # Salvar velocidade atual
                self.previous_speed = self.playback_speed
                # Definir velocidade rápida (2x mais rápido que a velocidade atual)
                self.set_playback_speed(self.playback_speed * 2.0)
                if not self.is_playing:
                    self.play()
        except Exception as e:
            print(f"Erro ao iniciar avanço rápido: {e}")

    def start_rewind(self) -> None:
        """Inicia retrocesso rápido"""
        try:
            if self.player:
                # Salvar velocidade atual
                self.previous_speed = self.playback_speed
                # Definir velocidade negativa para retroceder
                self.set_playback_speed(-2.0)
                if not self.is_playing:
                    self.play()
        except Exception as e:
            print(f"Erro ao iniciar retrocesso: {e}")

    def stop_fast_playback(self) -> None:
        """Para avanço/retrocesso rápido"""
        try:
            if self.player:
                # Restaurar velocidade anterior
                if hasattr(self, 'previous_speed'):
                    self.set_playback_speed(self.previous_speed)
                else:
                    self.set_playback_speed(1.0)
        except Exception as e:
            print(f"Erro ao parar reprodução rápida: {e}")

    def toggle_playback(self) -> None:
        """Alterna entre reproduzir e pausar"""
        if not self.player:
            return
            
        try:
            if self.is_playing:
                self.pause()
                self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
                # Manter a velocidade atual mesmo quando pausado
                self.speed_button.setEnabled(True)
                self.play_button.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 255, 255, 0.1);
                        border: 2px solid #0078D4;
                    }
                """)
            else:
                self.play()
                self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
                self.speed_button.setEnabled(True)
                self.play_button.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(0, 120, 212, 0.2);
                        border: 2px solid #0078D4;
                    }
                """)
        except Exception as e:
            print(f"Erro ao alternar reprodução: {e}")

    # Adicionar método para obter a cor da velocidade
    @staticmethod
    def get_speed_color(speed: float) -> str:
        if speed < 1:
            return '#FFA726'  # Laranja para velocidades lentas
        elif speed > 1:
            return '#4CAF50'  # Verde para velocidades rápidas
        else:
            return '#2196F3'  # Azul para velocidade normal

    def set_volume(self, value: int) -> bool:
        """Define o volume do player (0-100)"""
        try:
            if self.player:
                if self.player.set_volume(value):
                    self.update_volume_icon(value)
                    if value > 0 and self.mute_action.isChecked():
                        self.mute_action.setChecked(False)
                    print(f"Volume alterado para: {value}%")
                    return True
                else:
                    print(f"Falha ao alterar volume para: {value}%")
            return False
        except Exception as e:
            print(f"Erro ao alterar volume: {e}")
            return False

    def toggle_mute(self) -> None:
        """Ativa/desativa o mudo"""
        try:
            if self.player:
                is_muted = self.mute_action.isChecked()
                if is_muted:
                    # Salvar volume atual antes de mutar
                    self.last_volume = self.volume_slider.value()
                    self.player.set_mute(True)
                    self.volume_slider.setValue(0)
                    self.volume_button.setText("🔇")
                else:
                    # Restaurar último volume
                    last_vol = getattr(self, 'last_volume', 100)
                    self.player.set_mute(False)
                    self.player.set_volume(last_vol)
                    self.volume_slider.setValue(last_vol)
                    self.update_volume_icon(last_vol)
                
                print(f"Mudo: {'ativado' if is_muted else 'desativado'}")
        except Exception as e:
            print(f"Erro ao alternar mudo: {e}")
            self.mute_action.setChecked(False)

    def update_volume_icon(self, value: int) -> None:
        volume_styles = {
            0: ("🔇", "background-color: rgba(244, 67, 54, 0.1); color: #F44336;"),
            30: ("🔈", "background-color: rgba(255, 255, 255, 0.1); color: #E0E0E0;"),
            70: ("🔉", "background-color: rgba(0, 120, 212, 0.1); color: #0078D4;"),
            100: ("🔊", "background-color: rgba(76, 175, 80, 0.1); color: #4CAF50;")
        }
        
        icon, style = next(
            (icon, style) for threshold, (icon, style) in sorted(volume_styles.items())
            if value <= threshold
        )
        
        self.volume_button.setText(icon)
        self.volume_button.setStyleSheet(f"""
            QPushButton {{
                {style}
                border-radius: 20px;
                padding: 8px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.15);
            }}
        """)