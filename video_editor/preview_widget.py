from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy, QHBoxLayout, QSlider, QWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from pathlib import Path
import time

try:
    from ffpyplayer.player import MediaPlayer
    HAS_FFPLAYER = True
except ImportError:
    HAS_FFPLAYER = False
    print("ERRO: ffpyplayer não encontrado. Por favor, instale com: pip install ffpyplayer")

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    print("OpenCV não encontrado. Algumas funcionalidades podem estar limitadas.")

class PreviewWidget(QFrame):
    def __init__(self):
        super().__init__()
        # Inicializar variáveis antes de setup_ui
        self.player = None
        self.current_file = None
        self.is_playing = False
        self.frame_duration = 1/30
        self.playback_state_changed = False
        self.duration = 0
        self.update_interval = 16  # Aproximadamente 60fps
        self.last_update_time = 0
        self.playback_speed = 1.0  # Velocidade normal
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
        
        # Novo: acumulador para controle de frames
        self.frame_accumulator = 0.0
        # Novo: controle de tempo entre frames
        self.last_frame_time = 0.0
        self.frame_interval = 1/30  # Intervalo base entre frames (30 FPS)
        self.accumulated_time = 0
        
        # Configurar timer de seek
        self.seek_timer = QTimer()
        self.seek_timer.setSingleShot(True)
        self.seek_timer.timeout.connect(self._perform_seek)
        self.pending_seek_position = None
        
        self.fast_forward_timer = QTimer()
        self.fast_forward_timer.timeout.connect(self.update_fast_playback)
        self.fast_forward_timer.setInterval(50)  # 50ms para atualização suave
        
        self.sync_timer = QTimer()  # Timer para sincronização
        self.sync_timer.timeout.connect(self.check_sync)
        self.sync_timer.setInterval(1000)  # Verificar sincronização a cada segundo
        
        # Configurar UI
        self.setup_ui()
        
        if not HAS_FFPLAYER:
            self.show_error_message("ffpyplayer não encontrado")
            
        self.current_filters = []  # Lista para rastrear filtros ativos
        self.current_pts = 0.0  # Adicionar controle de pts atual
        
        self.frame_skip = 0  # Contador para pular frames
        self.frame_repeat = 1  # Contador para repetir frames
        
        self.target_frame_time = 1/30  # Tempo alvo entre frames (30 FPS)
        self.last_frame_time = 0

        self.clock_start = 0
        self.video_time = 0
        self.frame_count = 0

        self.last_pts = 0  # Adicionar controle do último PTS
        self.frame_timer = QTimer()  # Timer específico para controle de frames
        self.frame_timer.timeout.connect(self.get_next_frame)
        self.frame_timer.setInterval(16)  # ~60fps inicial
            
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
        
    def format_time(self, seconds):
        """Formata o tempo em MM:SS"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
        
    def seek_to_position(self):
        """Agenda um seek com debounce"""
        if self.player and self.duration > 0:
            try:
                position = self.progress_slider.value() / 1000.0
                self.video_time = position
                if self.is_playing:
                    self.clock_start = time.time()
                self.player.seek(position)
            except Exception as e:
                print(f"Erro durante seek: {e}")
    
    def _perform_seek(self):
        """Executa o seek efetivamente após o debounce"""
        if self.pending_seek_position is not None and self.player:
            try:
                position = max(0, min(self.pending_seek_position, self.duration))
                was_playing = self.is_playing
                
                if was_playing:
                    self.player.set_pause(True)
                
                print(f"Seeking to: {position:.2f}s")
                self.player.seek(position, relative=False)
                
                # Pequena pausa para o seek completar
                import time
                time.sleep(0.1)
                
                # Atualizar frame e interface
                self._update_after_seek(position)
                
                if was_playing:
                    self.player.set_pause(False)
                    
            except Exception as e:
                print(f"Erro durante seek: {e}")
            finally:
                self.pending_seek_position = None
                
    def _update_after_seek(self, position):
        """Atualiza a interface após um seek"""
        try:
            frame, _ = self.player.get_frame()
            if frame:
                image, _ = frame
                if image:
                    w, h = image.get_size()
                    frame_data = image.to_memoryview()[0]
                    q_img = QImage(frame_data, w, h, w * 3, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(q_img)
                    scaled_pixmap = pixmap.scaled(
                        self.display.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.display.setPixmap(scaled_pixmap)
            
            # Atualizar controles de tempo
            self.current_time_label.setText(self.format_time(position))
            if not self.progress_slider.isSliderDown():
                self.progress_slider.setValue(int(position * 1000))
                
        except Exception as e:
            print(f"Erro ao atualizar frame após seek: {e}")
                
    def on_slider_pressed(self):
        """Chamado quando o usuário começa a arrastar o slider"""
        if self.player:
            self.was_playing = self.is_playing
            if self.is_playing:
                self.player.set_pause(True)
                self.update_timer.stop()
            # Cancelar qualquer seek pendente
            if self.seek_timer.isActive():
                self.seek_timer.stop()
                self.pending_seek_position = None
            
    def on_slider_released(self):
        """Chamado quando o usuário solta o slider"""
        if self.player:
            # Executar o seek imediatamente
            self._perform_seek()
            if self.was_playing:
                QTimer.singleShot(100, self.resume_playback)
                
    def resume_playback(self):
        """Retoma a reprodução após um seek"""
        if self.player and self.was_playing:
            self.player.set_pause(False)
            self.update_timer.start()
            self.is_playing = True
                
    def update_progress(self, override_time=None):
        """Atualiza a barra de progresso e os labels de tempo"""
        if self.player:
            try:
                current_time = override_time if override_time is not None else self.player.get_pts()
                if current_time is not None and self.duration > 0:
                    current_ms = int(time.time() * 1000)
                    # Atualizar apenas se passou tempo suficiente desde a última atualização
                    if (current_ms - self.last_update_time) >= self.update_interval:
                        if not self.progress_slider.isSliderDown():
                            position_ms = int(current_time * 1000)
                            self.progress_slider.setValue(position_ms)
                            self.current_time_label.setText(self.format_time(current_time))
                        self.last_update_time = current_ms
            except Exception as e:
                print(f"Erro ao atualizar progresso: {e}")
                
    def update_frame(self):
        """Atualiza o frame atual do vídeo"""
        if not self.player:
            return
            
        try:
            frame, val = self.player.get_frame()
            
            if val == 'eof':
                print("Fim do vídeo alcançado")
                self.stop()
                return
                
            if frame is not None:
                image, pts = frame
                if image:
                    w, h = image.get_size()
                    frame_data = image.to_memoryview()[0]
                    q_img = QImage(frame_data, w, h, w * 3, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(q_img)
                    scaled_pixmap = pixmap.scaled(
                        self.display.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.display.setPixmap(scaled_pixmap)
                    self.update_progress()
                    
        except Exception as e:
            print(f"Erro ao atualizar frame: {e}")

    def get_next_frame(self):
        """Obtém o próximo frame baseado na velocidade"""
        if not self.player or not self.is_playing:
            return
            
        try:
            # Calcular quanto tempo passou desde o último frame
            current_pts = self.player.get_pts() or 0
            pts_diff = current_pts - self.last_pts
            
            # Ajustar o PTS baseado na velocidade
            if self.playback_speed != 1.0:
                target_pts = current_pts + (pts_diff * self.playback_speed)
                if target_pts < self.duration:
                    self.player.seek(target_pts)
                else:
                    self.stop()
                    return
            
            frame, val = self.player.get_frame()
            
            if val == 'eof':
                self.stop()
                return
                
            if frame is not None:
                image, pts = frame
                if image:
                    w, h = image.get_size()
                    frame_data = image.to_memoryview()[0]
                    q_img = QImage(frame_data, w, h, w * 3, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(q_img)
                    scaled_pixmap = pixmap.scaled(
                        self.display.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.display.setPixmap(scaled_pixmap)
                    
                    # Atualizar último PTS conhecido
                    self.last_pts = pts if pts is not None else current_pts
                    
                    # Atualizar progresso
                    self.update_progress(self.last_pts)
                    
        except Exception as e:
            print(f"Erro ao obter próximo frame: {e}")

    def load_video(self, file_path):
        """Carrega um novo vídeo"""
        if not HAS_FFPLAYER:
            self.show_error_message("ffpyplayer não encontrado")
            return
            
        if self.player:
            try:
                self.player.close_player()
                self.player = None
            except Exception as e:
                print(f"Erro ao fechar player existente: {e}")
            
        if Path(file_path).exists():
            try:
                print(f"Carregando vídeo: {file_path}")
                
                # Configurar opções do FFmpeg para melhor performance
                ff_opts = {
                    'autoexit': False,
                    'sync': 'audio',
                    'framedrop': True,
                    'seek_threshold': 0.1,
                    'probesize': 32,  # Reduzir tempo de probe
                    'analyzeduration': 0,  # Reduzir tempo de análise
                    'fflags': 'nobuffer',  # Reduzir latência
                    'flags': 'low_delay',  # Reduzir latência
                    'thread_queue_size': 512,  # Aumentar buffer de threads
                    'max_delay': 500000,  # 500ms de delay máximo
                }
                
                self.player = MediaPlayer(str(file_path), ff_opts=ff_opts)
                self.current_file = file_path
                
                # Resetar variáveis de controle
                self.clock_start = time.time()
                self.video_time = 0
                self.frame_count = 0
                
                # Aguardar inicialização
                time.sleep(0.5)
                
                # Obter duração do vídeo
                metadata = self.player.get_metadata()
                self.duration = metadata.get('duration', 0)
                
                # Configurar slider
                self.progress_slider.setRange(0, int(self.duration * 1000))
                self.progress_slider.setSingleStep(33)  # ~1 frame em 30fps
                self.progress_slider.setPageStep(1000)  # 1 segundo por page step
                self.duration_label.setText(self.format_time(self.duration))
                
                # Forçar pausa inicial
                self.player.set_pause(True)
                self.is_playing = False
                
                # Forçar atualização do primeiro frame
                self.update_frame()
                print("Vídeo carregado com sucesso")
                
                # Limpar mensagem de erro se existir
                self.display.setStyleSheet("background-color: black;")
                
            except Exception as e:
                print(f"Erro ao carregar vídeo: {e}")
                import traceback
                traceback.print_exc()
                self.show_error_message(str(e))
                
    def play(self):
        """Inicia a reprodução"""
        if self.player and not self.playback_state_changed:
            try:
                if not self.is_playing:
                    print("Iniciando reprodução...")
                    self.playback_state_changed = True
                    self.player.set_pause(False)
                    self.is_playing = True
                    self.last_pts = self.player.get_pts() or 0
                    self.frame_timer.start()
                    print(f"Estado do player: reproduzindo, timer ativo: {self.frame_timer.isActive()}")
                    QTimer.singleShot(100, self.reset_state_changed)
            except Exception as e:
                print(f"Erro ao iniciar reprodução: {e}")
                self.playback_state_changed = False

    def pause(self):
        """Pausa a reprodução"""
        if self.player and not self.playback_state_changed:
            try:
                if self.is_playing:
                    print("Pausando reprodução...")
                    self.playback_state_changed = True
                    self.player.set_pause(True)
                    self.is_playing = False
                    self.frame_timer.stop()
                    print(f"Estado do player: pausado, timer ativo: {self.frame_timer.isActive()}")
                    QTimer.singleShot(100, self.reset_state_changed)
            except Exception as e:
                print(f"Erro ao pausar reprodução: {e}")
                self.playback_state_changed = False

    def stop(self):
        """Para a reprodução e volta ao início"""
        if self.player:
            try:
                print("Parando reprodução...")
                self.player.set_pause(True)
                self.is_playing = False
                self.frame_timer.stop()
                self.last_pts = 0
                
                # Voltar ao início
                self.player.seek(0, relative=False)
                time.sleep(0.1)
                
                # Forçar atualização do frame inicial e progresso
                self.progress_slider.setValue(0)
                self.current_time_label.setText("00:00")
                self.update_frame()
                print("Reprodução parada e resetada")
            except Exception as e:
                print(f"Erro ao parar reprodução: {e}")

    def seek(self, position):
        """Busca uma posição específica no vídeo"""
        if self.player:
            try:
                self.player.seek(position, relative=False)
                # Atualizar a interface após o seek
                self.progress_slider.setValue(int(position * 1000))
                self.current_time_label.setText(self.format_time(position))
            except Exception as e:
                print(f"Erro durante seek: {e}")
                
    def closeEvent(self, event):
        """Evento chamado quando o widget é fechado"""
        if self.player:
            self.player.close_player()
            self.player = None
        super().closeEvent(event)

    def update_fast_playback(self):
        """Atualiza a posição durante avanço/retrocesso rápido"""
        if self.player:
            try:
                current_time = self.player.get_pts()
                new_time = current_time + (0.2 * self.playback_speed)  # Avança/retrocede 0.2s por tick
                self.seek(max(0, min(new_time, self.duration)))
            except Exception as e:
                print(f"Erro durante avanço/retrocesso rápido: {e}")

    def start_fast_forward(self):
        """Inicia o avanço rápido"""
        self.playback_speed = 3.0  # 3x mais rápido
        if not self.fast_forward_timer.isActive():
            self.fast_forward_timer.start()
            if hasattr(self.player, 'set_rate'):
                self.player.set_rate(3.0)

    def start_rewind(self):
        """Inicia o retrocesso rápido"""
        self.playback_speed = -3.0  # 3x mais rápido para trás
        if not self.fast_forward_timer.isActive():
            self.fast_forward_timer.start()
            if hasattr(self.player, 'set_rate'):
                self.player.set_rate(-3.0)

    def stop_fast_playback(self):
        """Para o avanço/retrocesso rápido"""
        self.fast_forward_timer.stop()
        if hasattr(self.player, 'set_rate'):
            self.set_playback_speed(1.0)  # Volta para velocidade normal

    def change_playback_speed(self):
        """Altera a velocidade de reprodução"""
        if self.player:
            try:
                # Converter valor do slider para velocidade (25-200 para 0.25-2.0)
                speed = self.speed_slider.value() / 100.0
                self.playback_speed = speed
                
                # Atualizar label
                self.speed_value_label.setText(f"{speed:.1f}x")
                
                # Aplicar velocidade ao player
                if hasattr(self.player, 'set_rate'):
                    self.player.set_rate(speed)
                print(f"Velocidade alterada para {speed:.1f}x")
            except Exception as e:
                print(f"Erro ao alterar velocidade: {e}")

    def jump_to_next_keyframe(self):
        """Pula para o próximo keyframe"""
        if self.player:
            try:
                current_time = self.player.get_pts()
                # Avança aprox. 2 segundos ou até o próximo keyframe
                self.seek(min(current_time + 2.0, self.duration))
            except Exception as e:
                print(f"Erro ao pular para próximo keyframe: {e}")

    def jump_to_previous_keyframe(self):
        """Pula para o keyframe anterior"""
        if self.player:
            try:
                current_time = self.player.get_pts()
                # Retrocede aprox. 2 segundos ou até o keyframe anterior
                self.seek(max(0, current_time - 2.0))
            except Exception as e:
                print(f"Erro ao pular para keyframe anterior: {e}")

    def set_playback_speed(self, speed_value):
        """Define a velocidade de reprodução"""
        if self.player:
            try:
                print(f"Alterando velocidade para {speed_value}x")
                self.playback_speed = speed_value
                
                # Ajustar intervalo do timer baseado na velocidade
                target_fps = 60  # FPS base
                if speed_value < 1.0:
                    # Para velocidades lentas, manter FPS alto para suavidade
                    interval = int(1000 / target_fps)
                else:
                    # Para velocidades rápidas, ajustar o intervalo
                    interval = max(1, int((1000 / target_fps) / speed_value))
                
                self.frame_timer.setInterval(interval)
                print(f"Velocidade alterada para {speed_value:.2f}x (intervalo: {interval}ms)")
                
            except Exception as e:
                print(f"Erro ao alterar velocidade: {e}")

    def check_sync(self):
        """Verifica e corrige a sincronização de áudio/vídeo"""
        if self.player and self.is_playing:
            try:
                video_pts = self.player.get_pts()
                audio_pts = self.player.get_audio_pts()
                
                if audio_pts is not None and video_pts is not None:
                    diff = abs(audio_pts - video_pts)
                    if diff > 0.1:  # Se diferença maior que 100ms
                        print(f"Corrigindo dessincronização: {diff:.3f}s")
                        self.player.seek(video_pts)
            except Exception as e:
                print(f"Erro ao verificar sincronização: {e}")
