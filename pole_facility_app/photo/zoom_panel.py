# -*- coding: utf-8 -*-
"""
Zoom Panel - 拡大表示パネル（Phase 3-A完成版）

機能:
    - hover中の画像/シーンを拡大表示
    - マウス座標中心に切り出し表示
    - 切り出し範囲: 元画像の100x100px（倍率で変化）
    - 表示サイズ: 400x300px固定
    - スライダーで倍率調整（100-500%、初期値200%）
    - EditorPanelのシーン全体（編集オブジェクト込み）をレンダリング
"""

from typing import Optional
from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider
from qgis.PyQt.QtCore import Qt, QSize, QPointF
from qgis.PyQt.QtGui import QPixmap, QPainter, QImage
from qgis.core import QgsMessageLog, Qgis


class ZoomPanel(QWidget):
    """
    拡大表示パネル（Phase 3-A完成版）
    """
    
    def __init__(self, parent=None):
        """初期化"""
        super().__init__(parent)
        
        self._current_source = None  # 画像パスまたはQGraphicsScene
        self._current_source_type = None  # "path" or "scene"
        self._current_mouse_pos = None  # QPointF（元画像座標系）
        self._zoom_factor = 2.0  # 初期倍率200%
        
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
        slider_label.setFixedWidth(50)
        slider_label.setStyleSheet("""
            QLabel {
                font-size: 10pt;
                color: #6c757d;
                background: none;
                border: 0px;
            }
        """)
        slider_layout.addWidget(slider_label)
        
        self._zoom_slider = QSlider(Qt.Horizontal, self)
        self._zoom_slider.setMinimum(100)
        self._zoom_slider.setMaximum(500)
        self._zoom_slider.setValue(200)  # 初期値200%
        self._zoom_slider.setTickPosition(QSlider.TicksBelow)
        self._zoom_slider.setTickInterval(50)
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
        
        self._zoom_value_label = QLabel("200%", self)
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
    
    def show_image(self, image_path: str = "", scene=None, mouse_pos=None):
        """
        画像またはシーンを拡大表示
        
        Args:
            image_path: 画像パス（空文字で非表示）
            scene: QGraphicsScene（Editorパネルのシーン全体）
            mouse_pos: QPointF（元画像座標系のマウス位置）
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
        
        self._current_mouse_pos = mouse_pos
        
        # デバッグ: マウス座標を出力
        if mouse_pos:
            QgsMessageLog.logMessage(
                f"ZoomPanel - マウス座標: ({mouse_pos.x():.1f}, {mouse_pos.y():.1f}), 倍率: {self._zoom_factor:.1f}x",
                "PoleFacility", Qgis.Info
            )
        
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
        """
        画像パスからレンダリング（マウス座標中心の切り出し）
        
        処理フロー:
            1. 元画像を読み込み
            2. マウス座標を中心に、倍率に応じた範囲を切り出し
               - 200%の場合: 100x100px（200/2）を切り出し
               - 100%の場合: 200x200pxを切り出し
            3. 切り出した領域を400x300pxに拡大表示
        """
        pixmap = QPixmap(image_path)
        
        if pixmap.isNull():
            self.clear()
            return
        
        original_width = pixmap.width()
        original_height = pixmap.height()
        
        # デバッグ: 元画像サイズ
        QgsMessageLog.logMessage(
            f"ZoomPanel - 元画像サイズ: {original_width}x{original_height}",
            "PoleFacility", Qgis.Info
        )
        
        # マウス座標がない場合は画像全体をフィット表示
        if not self._current_mouse_pos:
            scaled = pixmap.scaled(
                400, 300,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self._image_label.setPixmap(scaled)
            self._image_label.setText("")
            return
        
        # 切り出し範囲を計算（倍率で変化）
        # 基準サイズ: 200x200px
        # 200%の場合: 100x100px（より狭い範囲＝より拡大）
        crop_width = 200 / self._zoom_factor
        crop_height = 200 / self._zoom_factor
        
        # マウス座標を中心に切り出し範囲を計算
        center_x = self._current_mouse_pos.x()
        center_y = self._current_mouse_pos.y()
        
        left = max(0, center_x - crop_width / 2)
        top = max(0, center_y - crop_height / 2)
        
        # 画像範囲を超えないように調整
        if left + crop_width > original_width:
            left = max(0, original_width - crop_width)
        if top + crop_height > original_height:
            top = max(0, original_height - crop_height)
        
        # デバッグ: 切り出し範囲
        QgsMessageLog.logMessage(
            f"ZoomPanel - 切り出し: left={left:.1f}, top={top:.1f}, size={crop_width:.1f}x{crop_height:.1f}",
            "PoleFacility", Qgis.Info
        )
        
        # 切り出し
        cropped = pixmap.copy(
            int(left),
            int(top),
            int(crop_width),
            int(crop_height)
        )
        
        # 400x300にスケール
        scaled = cropped.scaled(
            400, 300,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        self._image_label.setPixmap(scaled)
        self._image_label.setText("")
    
    def _render_scene(self, scene):
        """
        QGraphicsSceneからレンダリング（マウス座標中心の切り出し）
        
        処理フロー:
            1. シーン全体を高解像度でレンダリング
            2. マウス座標を中心に切り出し
            3. 400x300pxに拡大表示
        """
        if not scene:
            self.clear()
            return
        
        scene_rect = scene.sceneRect()
        
        if scene_rect.isEmpty():
            self.clear()
            return
        
        scene_width = scene_rect.width()
        scene_height = scene_rect.height()
        
        # マウス座標がない場合は全体をフィット表示
        if not self._current_mouse_pos:
            image = QImage(int(scene_width), int(scene_height), QImage.Format_ARGB32)
            image.fill(Qt.white)
            
            painter = QPainter(image)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            scene.render(painter)
            painter.end()
            
            pixmap = QPixmap.fromImage(image)
            scaled = pixmap.scaled(400, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            self._image_label.setPixmap(scaled)
            self._image_label.setText("")
            return
        
        # シーン全体を高解像度でレンダリング（倍率適用）
        render_width = int(scene_width * self._zoom_factor)
        render_height = int(scene_height * self._zoom_factor)
        
        image = QImage(render_width, render_height, QImage.Format_ARGB32)
        image.fill(Qt.white)
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # スケール適用してシーンをレンダリング
        painter.scale(self._zoom_factor, self._zoom_factor)
        scene.render(painter)
        painter.end()
        
        # マウス座標を中心に切り出し（レンダリング後の座標系）
        center_x = self._current_mouse_pos.x() * self._zoom_factor
        center_y = self._current_mouse_pos.y() * self._zoom_factor
        
        crop_width = 400
        crop_height = 300
        
        left = max(0, center_x - crop_width / 2)
        top = max(0, center_y - crop_height / 2)
        
        # 範囲調整
        if left + crop_width > render_width:
            left = max(0, render_width - crop_width)
        if top + crop_height > render_height:
            top = max(0, render_height - crop_height)
        
        # 切り出し
        cropped = image.copy(
            int(left),
            int(top),
            int(crop_width),
            int(crop_height)
        )
        
        pixmap = QPixmap.fromImage(cropped)
        
        self._image_label.setPixmap(pixmap)
        self._image_label.setText("")
    
    def clear(self):
        """表示をクリア"""
        self._current_source = None
        self._current_source_type = None
        self._current_mouse_pos = None
        self._image_label.setPixmap(QPixmap())
        self._image_label.setText("hover時に画像を表示")
    
    def get_current_source(self):
        """現在表示中のソースを取得"""
        return self._current_source
    
    def get_zoom_factor(self) -> float:
        """現在の倍率を取得"""
        return self._zoom_factor
