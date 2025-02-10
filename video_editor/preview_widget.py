from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QLabel, QSizePolicy, QHBoxLayout, 
                           QSlider, QWidget, QPushButton, QMenu, QActionGroup, QStyle, QAction)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QImage, QPixmap
import traceback
from pathlib import Path
import time
from video_editor.vlc_player import VLCPlayer

class PreviewWidget(QFrame):
    def __init__(self):
        super().__init__()
        # Inicializar variáveis básicas
        self.player = None
        self.is_playing = False
        self.duration = 0
        self.slider_being_dragged = False
        self.was_playing = False
        self.update_interval = 16
        self.load_wait_time = 2.0  # Aumentando o tempo de espera para 2 segundos
        
        # Velocidades disponíveis
        self.available_speeds = [
            0.25,  # Muito lento
            0.5,   # Lento
            0.75,  # Devagar
            1.0,   # Normal
            1.25,  # Pouco rápido
            1.5,   # Rápido
            1.75,  # Muito rápido
            2.0    # Ultra rápido
        ]
        self.current_speed_index = 3  # Índice da velocidade normal (1.0)
        self.playback_speed = self.available_speeds[self.current_speed_index]
        
        # Timer para atualização contínua da posição
        self.position_timer = QTimer()
        self.position_timer.setInterval(100)
        self.position_timer.timeout.connect(self.update_position)
        
        self.setup_ui()

    def setup_ui(self):
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
        for speed in self.available_speeds[:3]:
            action = QAction(f"⏪ {speed:.2f}x", self) if speed < 1 else QAction(f"{speed:.2f}x", self)
            action.setCheckable(True)
            action.setData(self.available_speeds.index(speed))
            speed_group.addAction(action)
            self.speed_menu.addAction(action)
            action.triggered.connect(lambda checked, s=speed: self.set_playback_speed(self.available_speeds.index(s)))

        self.speed_menu.addSeparator()

        # Velocidade normal (1.0x)
        normal_action = QAction("▶️ 1.00x", self)
        normal_action.setCheckable(True)
        normal_action.setChecked(True)
        normal_action.setData(3)
        speed_group.addAction(normal_action)
        self.speed_menu.addAction(normal_action)
        normal_action.triggered.connect(lambda checked: self.set_playback_speed(3))

        self.speed_menu.addSeparator()

        # Velocidades rápidas com ícones
        for speed in self.available_speeds[4:]:
            action = QAction(f"⏩ {speed:.2f}x", self)
            action.setCheckable(True)
            action.setData(self.available_speeds.index(speed))
            speed_group.addAction(action)
            self.speed_menu.addAction(action)
            action.triggered.connect(lambda checked, s=speed: self.set_playback_speed(self.available_speeds.index(s)))

        # Botão de velocidade com estilo personalizado
        self.speed_button = QPushButton("1.00x")
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

        progress_layout.addWidget(controls_container)
        layout.addWidget(progress_container)

        # Configurar timer de atualização
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_frame)
        self.update_timer.setInterval(self.update_interval)

        # Aplicar efeito de sombra ao container de controles
        controls_container.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
        """)

        # Atualizar o texto do botão de velocidade ao inicializar
        self.speed_button.setText(f"▶️ {self.available_speeds[self.current_speed_index]:.2f}x")
        self.speed_button.setStyleSheet(f"""
            #speed_button {{
                background-color: #2D2D2D;
                color: {self.get_speed_color(self.available_speeds[self.current_speed_index])};
                border: 1px solid {self.get_speed_color(self.available_speeds[self.current_speed_index])};
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            #speed_button:hover {{
                background-color: #353535;
            }}
        """)

    def show_speed_menu(self):
        """Mostra o menu de velocidade abaixo do botão"""
        pos = self.speed_button.mapToGlobal(self.speed_button.rect().bottomLeft())
        self.speed_menu.popup(pos)

    def load_video(self, file_path):
        try:
            print(f"Carregando vídeo: {file_path}")
            
            if self.player:
                self.player.stop()
                self.player.release()
                self.position_timer.stop()
            
            self.player = VLCPlayer(self.display)
            success = self.player.load(file_path)
            
            if success:
                # Aumentar tempo de espera para carregar a duração
                time.sleep(self.load_wait_time)
                
                # Obter duração do vídeo
                self.duration = self.player.get_length()
                print(f"Duração do vídeo: {self.duration}ms")
                
                if self.duration <= 0:
                    print("Erro: Duração inválida do vídeo")
                    return False
                
                # Configurar slider
                self.progress_slider.setRange(0, self.duration)
                self.progress_slider.setSingleStep(1000)
                self.progress_slider.setPageStep(5000)
                
                # Atualizar label de duração e zerar posição
                self.progress_slider.setValue(0)
                self.update_time_label(0, self.duration)
                
                # Forçar estado inicial
                self.is_playing = False
                self.slider_being_dragged = False
                self.was_playing = False
                
                # Iniciar timer de atualização
                self.position_timer.start()

                # Resetar velocidade para normal (1.0x) com delay
                self.current_speed_index = 3  # Índice da velocidade normal (1.0x)
                QTimer.singleShot(500, lambda: self.set_playback_speed(self.current_speed_index))
                
                # Habilitar botões de controle
                self.speed_button.setEnabled(True)
                self.play_button.setEnabled(True)
                self.stop_button.setEnabled(True)
                
                return True
            
            print("Erro ao carregar vídeo")
            return False
                
        except Exception as e:
            print(f"Erro ao carregar vídeo: {e}")
            traceback.print_exc()
            return False

    def play(self):
        if self.player and not self.is_playing:
            self.player.play()
            self.is_playing = True
            self.position_timer.start()
            print("Iniciando reprodução")

    def pause(self):
        if self.player and self.is_playing:
            self.player.pause()
            self.is_playing = False
            print("Pausando reprodução")

    def stop(self):
        if self.player:
            self.player.stop()
            self.is_playing = False
            self.position_timer.stop()
            self.progress_slider.setValue(0)
            self.update_time_label(0, self.duration)
            print("Parando reprodução")

    def on_slider_pressed(self):
        """Chamado quando o usuário começa a arrastar o slider"""
        self.slider_being_dragged = True
        if self.is_playing:
            self.was_playing = True
            self.player.pause()
            print("Slider pressionado - pausando vídeo")

    def on_slider_released(self):
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

    def on_slider_moved(self, position):
        """Chamado quando o usuário move o slider"""
        self.update_time_label(position, self.duration)
        print(f"Slider movido para: {position}ms")

    def update_position(self):
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
        except Exception as e:
            print(f"Erro ao atualizar posição: {e}")

    def update_time_label(self, position, duration):
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

    def format_time(self, ms):
        """Converte milissegundos em formato MM:SS"""
        try:
            s = int(ms // 1000)
            m = int(s // 60)
            s = int(s % 60)
            return f"{m:02d}:{s:02d}"
        except Exception as e:
            print(f"Erro ao formatar tempo: {e}")
            return "00:00"

    def check_sync(self):
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

    def update_frame(self):
        """Atualiza o frame atual e o progresso"""
        if self.player and self.is_playing:
            try:
                position = self.player.get_time()
                if position is not None and not self.progress_slider.isSliderDown():
                    self.progress_slider.setValue(position)
                    self.update_time_label(position, self.duration)
            except Exception as e:
                print(f"Erro ao atualizar frame: {e}")

    def set_playback_speed(self, speed_index):
        """Define a velocidade de reprodução usando o índice da lista de velocidades"""
        try:
            if not self.player or speed_index < 0 or speed_index >= len(self.available_speeds):
                return False
                
            speed = self.available_speeds[speed_index]
            print(f"Alterando velocidade para: {speed}x")
            
            # Adicionar pequeno delay antes de alterar a velocidade
            time.sleep(0.1)
            
            if self.player.set_rate(float(speed)):
                self.current_speed_index = speed_index
                self.playback_speed = speed
                
                # Atualizar texto do botão com indicador visual baseado na velocidade
                if speed < 1:
                    speed_text = f"⏪ {speed:.2f}x"
                elif speed > 1:
                    speed_text = f"⏩ {speed:.2f}x"
                else:
                    speed_text = f"▶️ {speed:.2f}x"
                
                self.speed_button.setText(speed_text)
                self.speed_button.setStyleSheet(f"""
                    #speed_button {{
                        background-color: #2D2D2D;
                        color: {self.get_speed_color(speed)};
                        border: 1px solid {self.get_speed_color(speed)};
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-weight: bold;
                    }}
                    #speed_button:hover {{
                        background-color: #353535;
                    }}
                """)
                
                # Atualizar o estado checked no menu
                for action in self.speed_menu.actions():
                    if isinstance(action, QAction) and action.data() == speed_index:
                        action.setChecked(True)
                
                return True
                
            print("Falha ao alterar velocidade")
            return False
            
        except Exception as e:
            print(f"Erro ao alterar velocidade: {e}")
            return False

    def increase_speed(self):
        """Aumenta a velocidade para o próximo nível"""
        if self.current_speed_index < len(self.available_speeds) - 1:
            self.set_playback_speed(self.current_speed_index + 1)

    def decrease_speed(self):
        """Diminui a velocidade para o nível anterior"""
        if self.current_speed_index > 0:
            self.set_playback_speed(self.current_speed_index - 1)

    def get_current_speed_text(self):
        """Retorna o texto formatado da velocidade atual"""
        return f"{self.playback_speed:.2f}x"

    def start_fast_forward(self):
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

    def start_rewind(self):
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

    def stop_fast_playback(self):
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

    def toggle_playback(self):
        """Alterna entre reproduzir e pausar"""
        if not self.player:
            return
            
        try:
            if self.is_playing:
                self.pause()
                self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
                # Manter a velocidade atual mesmo quando pausado
                self.speed_button.setEnabled(True)
            else:
                self.play()
                self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
                self.speed_button.setEnabled(True)
        except Exception as e:
            print(f"Erro ao alternar reprodução: {e}")

    # Adicionar método para obter a cor da velocidade
    @staticmethod
    def get_speed_color(speed):
        if speed < 1:
            return '#FFA726'  # Laranja para velocidades lentas
        elif speed > 1:
            return '#4CAF50'  # Verde para velocidades rápidas
        else:
            return '#2196F3'  # Azul para velocidade normal