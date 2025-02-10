from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QLabel, QTreeWidget,
                           QTreeWidgetItem)
from PyQt5.QtCore import Qt

class EffectsPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setFrameStyle(QFrame.Panel | QFrame.Raised)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        title = QLabel("Efeitos")
        title.setStyleSheet("font-weight: bold;")
        
        self.effects_tree = QTreeWidget()
        self.effects_tree.setHeaderLabel("Efeitos Disponíveis")
        
        # Adicionar categorias de efeitos
        self.add_effect_category("Transições", [
            "Dissolve",
            "Fade",
            "Wipe",
            "Slide"
        ])
        
        self.add_effect_category("Filtros de Vídeo", [
            "Brilho/Contraste",
            "Saturação",
            "Temperatura",
            "Vinheta"
        ])
        
        self.add_effect_category("Efeitos de Áudio", [
            "Equalização",
            "Compressor",
            "Reverb",
            "Noise Reduction"
        ])
        
        layout.addWidget(title)
        layout.addWidget(self.effects_tree)
        
    def add_effect_category(self, category_name, effects):
        category = QTreeWidgetItem(self.effects_tree)
        category.setText(0, category_name)
        
        for effect in effects:
            effect_item = QTreeWidgetItem(category)
            effect_item.setText(0, effect)
            effect_item.setFlags(effect_item.flags() | Qt.ItemIsDragEnabled)
