from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy, QHBoxLayout, QSlider, QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from pathlib import Path
import time
from video_editor.vlc_player import VLCPlayer

class PreviewWidget(QFrame):
    def __init__(self):
        super().__init__()
        # Inicializar variáveis
        self.player = None
        self.is_playing = False
        self.duration = 0
        self.playback_speed = 1.0
        self.available_speeds = {
            "0.25x": 0.25,
            "0.5x": 0.5,
            "0.75x": 0.75,
            "Normal": 1.0,
            "1.25x": 1.25,
            "1.5x": 1.5,
            "1.75x": 1.75,
            "2x": 2.0
        }
        
        # Timers
        self.seek_timer = QTimer()
        self.seek_timer.setSingleShot(True)
        self.seek_timer.timeout.connect(self._perform_seek)
        
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.check_sync)
        self.sync_timer.setInterval(1000)
        
        # Novo: adicionar variável para controle de seek
        self.pending_seek_position = None
        self.was_playing = False
        self.update_interval = 16  # ~60fps
        
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
        progress_container.setStyleSheet("background-color: #1e1e1e;")
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(10, 5, 10, 5)
        
        # Barra de progresso e tempo
        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("00:00")
        self.duration_label = QLabel("00:00")
        
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setTracking(True)
        self.progress_slider.sliderMoved.connect(self.seek_to_position)
        self.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_slider_released)
        
        time_layout.addWidget(self.current_time_label)
        time_layout.addWidget(self.progress_slider)
        time_layout.addWidget(self.duration_label)
        
        progress_layout.addLayout(time_layout)
        layout.addWidget(progress_container)
        
        # Timer para atualização do frame e progresso
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_frame)
        self.update_timer.setInterval(self.update_interval)

    def load_video(self, file_path):
        """Carrega um novo vídeo usando VLC"""
        if self.player:
            try:
                self.player.stop()
                self.player.release()
            except Exception as e:
                print(f"Erro ao fechar player existente: {e}")
            
        if Path(file_path).exists():
            try:
                print(f"Carregando vídeo: {file_path}")
                
                self.player = VLCPlayer(self.display)
                success = self.player.load(file_path)
                
                if success:
                    # Configurar duração e estado inicial
                    self.duration = self.player.get_length() / 1000.0
                    self.progress_slider.setRange(0, int(self.duration * 1000))
                    self.progress_slider.setValue(0)
                    self.update_time_label(0)
                    
                    # Forçar pausa inicial
                    self.player.pause()
                    self.is_playing = False
                    
                    # Iniciar timer de sincronização
                    self.sync_timer.start()
                    
                    print("Vídeo carregado com sucesso")
                    return True
                    
                print("Erro ao carregar vídeo")
                return False
                    
            except Exception as e:
                print(f"Erro ao carregar vídeo: {e}")
                import traceback
                traceback.print_exc()
                return False

    def play(self):
        """Inicia a reprodução"""
        if self.player and not self.is_playing:
            self.player.play()
            self.is_playing = True

    def pause(self):
        """Pausa a reprodução"""
        if self.player and self.is_playing:
            self.player.pause()
            self.is_playing = False

    def stop(self):
        """Para a reprodução"""
        if self.player:
            self.player.stop()
            self.is_playing = False
            self.player.set_time(0)
            self.progress_slider.setValue(0)
            self.update_time_label(0)

    def _perform_seek(self):
        """Executa o seek efetivamente após o debounce"""
        if self.pending_seek_position is not None and self.player:
            try:
                position = max(0, min(self.pending_seek_position, self.duration))
                self.was_playing = self.is_playing
                
                if self.was_playing:
                    self.player.pause()
                
                print(f"Seeking to: {position:.2f}s")
                self.player.set_time(int(position * 1000))  # Converter para ms
                
                # Pequena pausa para o seek completar
                self.update_time_label(position * 1000)
                
                if self.was_playing:
                    self.player.play()
                    
            except Exception as e:
                print(f"Erro durante seek: {e}")
            finally:
                self.pending_seek_position = None

    def seek_to_position(self):
        """Agenda um seek com debounce"""
        if self.player and self.duration > 0:
            try:
                position = self.progress_slider.value() / 1000.0  # ms para segundos
                self.pending_seek_position = position
                if not self.seek_timer.isActive():
                    self.seek_timer.start(50)  # 50ms debounce
            except Exception as e:
                print(f"Erro ao agendar seek: {e}")

    def update_time_label(self, position_ms):
        """Atualiza o label de tempo"""
        try:
            current = self.format_time(position_ms)
            total = self.format_time(self.duration * 1000)
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
                        self.update_time_label(position)
            except Exception as e:
                print(f"Erro ao verificar sincronização: {e}")

    def on_slider_pressed(self):
        """Chamado quando o usuário começa a arrastar o slider"""
        if self.player:
            self.was_playing = self.is_playing
            if self.is_playing:
                self.player.pause()
                self.update_timer.stop()

    def on_slider_released(self):
        """Chamado quando o usuário solta o slider"""
        if self.player:
            # Executar o seek imediatamente
            position = self.progress_slider.value() / 1000.0  # ms para segundos
            self.player.set_time(int(position * 1000))
            
            # Retomar reprodução se estava tocando antes
            if self.was_playing:
                self.player.play()
                self.is_playing = True
                self.update_timer.start()

    def update_frame(self):
        """Atualiza o frame atual e o progresso"""
        if self.player and self.is_playing:
            try:
                position = self.player.get_time()
                if position is not None and not self.progress_slider.isSliderDown():
                    self.progress_slider.setValue(position)
                    self.update_time_label(position)
            except Exception as e:
                print(f"Erro ao atualizar frame: {e}")

    def closeEvent(self, event):
        """Evento de fechamento"""
        if self.player:
            self.player.stop()
            self.player.release()
        super().closeEvent(event)
