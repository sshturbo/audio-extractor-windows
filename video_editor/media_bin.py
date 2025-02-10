from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QLabel, QListWidget,
                           QListWidgetItem)
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDrag
from pathlib import Path

class MediaBin(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        title = QLabel("Media Bin")
        title.setStyleSheet("font-weight: bold;")
        
        self.list_widget = QListWidget()
        self.list_widget.setDragEnabled(True)
        
        layout.addWidget(title)
        layout.addWidget(self.list_widget)
        
    def add_media(self, filepath):
        item = QListWidgetItem(Path(filepath).name)
        item.setData(Qt.UserRole, filepath)
        self.list_widget.addItem(item)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            item = self.list_widget.currentItem()
            if item:
                drag = QDrag(self)
                mime_data = QMimeData()
                mime_data.setData("application/x-clip", 
                                item.data(Qt.UserRole).encode())
                drag.setMimeData(mime_data)
                drag.exec_(Qt.CopyAction)
