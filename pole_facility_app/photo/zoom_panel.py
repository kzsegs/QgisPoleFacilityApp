# -*- coding: utf-8 -*-
"""
Zoom Panel - 拡大表示パネル（改善版）

機能:
    - hover中の画像/シーンを拡大表示
    - スライダーで倍率調整（100-800%）
    - 初期倍率400%
    - EditorPanelのシーン全体（編集オブジェクト込み）をレンダリング
"""

from typing import Optional
from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider
from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QPixmap, QPainter, QImage
from qgis.core import QgsMessageLog, Qgis


class ZoomPanel(QWidget):
    """
    拡大表示パネル（改善版）
    """
    
    def __init__(self, parent=None):
        """初期化"""
        super().__init__(parent)
        
        self._current_source = None  # 画像パスまたはQGraphicsScene
        self._current_source_type = None  # "path" or "scene"
        self._zoom_factor = 4.0  # 初期倍率400%
        
        self._title_label = None
        self._image_label = None
        self._zoom_slider = None
        self._zoom_value_label = None
        
        self._create_ui()
    
    def _create_ui(self):
        """UI作成"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # パネルスタイル
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 4px;
            }
        """)
        
        # タイトル
        self._title_label = QLabel("拡大表示", self)
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 11pt;
                color: #495057;
                background: transparent;
                border: none;
                padding: 4px;
            }
        """)
        layout.addWidget(self._title_label)
        
        # スライダーエリア
        slider_layout = QHBoxLayout()
        slider_layout.setSpacing(8)
        
        slider_label = QLabel("倍率:", self)
        slider_label.setFixedWidth(40)
        slider_label.setStyleSheet("""
            QLabel {
                font-size: 10pt;
                color: #6c757d;
                background: transparent;
                border: none;
            }
        """)
        slider_layout.addWidget(slider_label)
        
        self._zoom_slider = QSlider(Qt.Horizontal, self)
        self._zoom_slider.setMinimum(100)
        self._zoom_slider.setMaximum(800)
        self._zoom_slider.setValue(400)  # 初期値400%
        self._zoom_slider.setTickPosition(QSlider.TicksBelow)
        self._zoom_slider.setTickInterval(100)
        self._zoom_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: white;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #3498db;
                border: 1px solid #2980b9;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
        """)
        self._zoom_slider.valueChanged.connect(self._on_slider_changed)
        slider_layout.addWidget(self._zoom_slider, 1)
        
        self._zoom_value_label = QLabel("400%", self)
        self._zoom_value_label.setFixedWidth(55)
        self._zoom_value_label.setAlignment(Qt.AlignCenter)
        self._zoom_value_label.setStyleSheet("""
            QLabel {
                font-size: 10pt;
                font-weight: bold;
                color: #2c3e50;
                background: transparent;
                border: none;
                padding: 2px;
            }
        """)
        slider_layout.addWidget(self._zoom_value_label)
        
        layout.addLayout(slider_layout)
        
        # 画像表示エリア（400x300px）
        self._image_label = QLabel(self)
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setFixedSize(400, 300)
        self._image_label.setStyleSheet("""
            QLabel {
                background: white;
                border: 1px solid #ced4da;
                border-radius: 2px;
            }
        """)
        self._image_label.setText("hover時に画像を表示")
        layout.addWidget(self._image_label, alignment=Qt.AlignCenter)
        
        layout.addStretch()
    
    def _on_slider_changed(self, value: int):
        """スライダー変更時"""
        self._zoom_factor = value / 100.0
        self._zoom_value_label.setText(f"{value}%")
        
        # 再描画
        if self._current_source:
            self._render_current_source()
    
    def show_image(self, image_path: str = "", scene=None):
        """
        画像またはシーンを拡大表示
        
        Args:
            image_path: 画像パス（空文字で非表示）
            scene: QGraphicsScene（Editorパネルのシーン全体）
        """
        if not image_path and not scene:
            self.clear()
            return
        
        if scene:
            self._current_source = scene
            self._current_source_type = "scene"
        else:
            self._current_source = image_path
            self._current_source_type = "path"
        
        self._render_current_source()
    
    def _render_current_source(self):
        """現在のソースをレンダリング"""
        try:
            if self._current_source_type == "path":
                self._render_image_path(self._current_source)
            elif self._current_source_type == "scene":
                self._render_scene(self._current_source)
        except Exception as e:
            QgsMessageLog.logMessage(
                f"ZoomPanel - レンダリングエラー: {str(e)}",
                "PoleFacility", Qgis.Warning
            )
            self.clear()
    
    def _render_image_path(self, image_path: str):
        """画像パスからレンダリング"""
        pixmap = QPixmap(image_path)
        
        if pixmap.isNull():
            self.clear()
            return
        
        # 倍率適用
        original_width = pixmap.width()
        original_height = pixmap.height()
        
        scaled_width = int(original_width * self._zoom_factor)
        scaled_height = int(original_height * self._zoom_factor)
        
        # 表示エリアにフィット
        max_width = 400
        max_height = 300
        
        if scaled_width > max_width or scaled_height > max_height:
            scale = min(max_width / scaled_width, max_height / scaled_height)
            scaled_width = int(scaled_width * scale)
            scaled_height = int(scaled_height * scale)
        
        scaled = pixmap.scaled(
            scaled_width, scaled_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        self._image_label.setPixmap(scaled)
        self._image_label.setText("")
    
    def _render_scene(self, scene):
        """QGraphicsSceneからレンダリング（編集オブジェクト込み）"""
        if not scene:
            self.clear()
            return
        
        # シーン全体の範囲を取得
        scene_rect = scene.sceneRect()
        
        if scene_rect.isEmpty():
            self.clear()
            return
        
        # 倍率適用
        scaled_width = int(scene_rect.width() * self._zoom_factor)
        scaled_height = int(scene_rect.height() * self._zoom_factor)
        
        # 表示エリアにフィット
        max_width = 400
        max_height = 300
        
        if scaled_width > max_width or scaled_height > max_height:
            scale = min(max_width / scaled_width, max_height / scaled_height)
            scaled_width = int(scaled_width * scale)
            scaled_height = int(scaled_height * scale)
        
        # QImageを作成してシーンをレンダリング
        image = QImage(scaled_width, scaled_height, QImage.Format_ARGB32)
        image.fill(Qt.white)
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # シーン全体を描画
        scene.render(painter)
        painter.end()
        
        pixmap = QPixmap.fromImage(image)
        
        self._image_label.setPixmap(pixmap)
        self._image_label.setText("")
    
    def clear(self):
        """表示をクリア"""
        self._current_source = None
        self._current_source_type = None
        self._image_label.setPixmap(QPixmap())
        self._image_label.setText("hover時に画像を表示")
    
    def get_current_source(self):
        """現在表示中のソースを取得"""
        return self._current_source
    
    def get_zoom_factor(self) -> float:
        """現在の倍率を取得"""
        return self._zoom_factor

