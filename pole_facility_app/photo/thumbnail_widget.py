# -*- coding: utf-8 -*-
"""
Thumbnail Widget - サムネイル列ウィジェット

列名とサムネイル画像を縦に配置するウィジェット。
写真管理ダイアログの左端列に使用。
"""

import os
from typing import Optional
from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QLabel
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QPixmap
from qgis.core import QgsMessageLog, Qgis


class ThumbnailWidget(QWidget):
    """
    サムネイル列のウィジェット
    
    構成:
        - 列名ラベル（太字・10pt・中央揃え）
        - サムネイル画像（80x60px）
    
    使用例:
        widget = ThumbnailWidget("設備正面", "/path/to/image.jpg")
    """
    
    def __init__(self, display_name: str, config_manager=None, image_path: str = "", parent=None):
        """
        初期化
        
        Args:
            display_name: 列名（例: "設備正面"）
            config_manager: ConfigManager インスタンス（パス解決用）
            image_path: 画像パス（相対パスまたは絶対パス）
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self._display_name = display_name
        self._config_manager = config_manager
        self._image_path = image_path
        
        self._name_label = None
        self._thumbnail_label = None
        
        self._create_ui()
        
        # 画像を設定
        if image_path:
            self.set_image(image_path)
    
    def _create_ui(self):
        """UI作成"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # 列名ラベル（太字・10pt・中央揃え）
        self._name_label = QLabel(self._display_name, self)
        self._name_label.setAlignment(Qt.AlignCenter)
        self._name_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 10pt;
                color: #333;
                padding: 4px;
            }
        """)
        layout.addWidget(self._name_label)
        
        # サムネイル画像（80x60px）
        self._thumbnail_label = QLabel(self)
        self._thumbnail_label.setAlignment(Qt.AlignCenter)
        self._thumbnail_label.setFixedSize(80, 60)
        self._thumbnail_label.setStyleSheet("""
            QLabel {
                background: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 2px;
            }
        """)
        self._thumbnail_label.setText("画像なし")
        layout.addWidget(self._thumbnail_label)
        
        layout.addStretch()
    
    def set_image(self, image_path: str):
        """
        画像を更新
        
        Args:
            image_path: 画像パス（相対パスまたは絶対パス）
        """
        self._image_path = image_path
        
        if not image_path:
            self._thumbnail_label.setText("画像なし")
            self._thumbnail_label.setPixmap(QPixmap())
            return
        
        try:
            # パス解決
            actual_path = self._resolve_photo_path(image_path)
            
            pixmap = QPixmap(actual_path)
            
            if pixmap.isNull():
                self._thumbnail_label.setText("画像なし")
                self._thumbnail_label.setPixmap(QPixmap())
                return
            
            # 80x60にフィット
            scaled = self._calculate_thumbnail_size(pixmap)
            self._thumbnail_label.setPixmap(scaled)
            self._thumbnail_label.setText("")
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"ThumbnailWidget - 画像読み込みエラー: {str(e)}",
                "PoleFacility", Qgis.Warning
            )
            self._thumbnail_label.setText("画像なし")
            self._thumbnail_label.setPixmap(QPixmap())
    
    def _resolve_photo_path(self, relative_path: str) -> str:
        """
        相対パスから実際のファイルパスを解決
        
        Args:
            relative_path: 相対パスまたは絶対パス
        
        Returns:
            str: 実際のファイルパス
        """
        if not relative_path:
            return ""
        
        # 絶対パスの場合はそのまま
        if os.path.isabs(relative_path):
            return relative_path
        
        # ConfigManagerがない場合はそのまま
        if not self._config_manager:
            return relative_path
        
        # ルートパス取得
        photo_root = self._config_manager.get_photo_root_path()
        
        if not photo_root:
            return relative_path
        
        # パス結合
        normalized_relative = relative_path.replace('\\', '/')
        actual_path = os.path.join(photo_root, normalized_relative)
        actual_path = os.path.normpath(actual_path)
        
        return actual_path
    
    def _calculate_thumbnail_size(self, pixmap: QPixmap) -> QPixmap:
        """
        サムネイルサイズを計算（80x60にフィット）
        
        Args:
            pixmap: 元画像
        
        Returns:
            QPixmap: スケーリングされた画像
        """
        max_width = 80
        max_height = 60
        
        return pixmap.scaled(
            max_width, max_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
    
    def get_display_name(self) -> str:
        """列名を取得"""
        return self._display_name
    
    def get_image_path(self) -> str:
        """画像パスを取得"""
        return self._image_path
