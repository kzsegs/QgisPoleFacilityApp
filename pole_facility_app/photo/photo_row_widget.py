# -*- coding: utf-8 -*-
"""
Photo Row Widget - 修正前/修正後列ウィジェット

画像表示とアイコンツールバーを持つウィジェット。
マウスオーバーで拡大パネルに画像を送信。
"""

from typing import Optional
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QToolBar, QAction
)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QSize
from qgis.PyQt.QtGui import QPixmap
from qgis.core import QgsApplication, QgsMessageLog, Qgis


class PhotoRowWidget(QWidget):
    """
    修正前/修正後列のウィジェット
    
    構成:
        - 画像表示エリア（200x150px）
        - アイコンツールバー（編集・保存・削除・差し替え）
    
    シグナル:
        - hovered: マウスオーバー時に画像パスを送信
        - edit_clicked: 編集ボタンクリック
        - save_clicked: 保存ボタンクリック
        - delete_clicked: 削除ボタンクリック
        - replace_clicked: 差し替えボタンクリック
    
    使用例:
        widget = PhotoRowWidget("/path/to/image.jpg", "before")
        widget.hovered.connect(zoom_panel.show_image)
    """
    
    hovered = pyqtSignal(str)  # image_path
    edit_clicked = pyqtSignal()
    save_clicked = pyqtSignal()
    delete_clicked = pyqtSignal()
    replace_clicked = pyqtSignal()
    
    def __init__(self, image_path: str = "", photo_type: str = "before", parent=None):
        """
        初期化
        
        Args:
            image_path: 画像パス
            photo_type: "before" or "after"
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self._image_path = image_path
        self._photo_type = photo_type
        
        self._image_label = None
        self._toolbar = None
        
        self._create_ui()
        
        # 画像を設定
        if image_path:
            self.set_image(image_path)
    
    def _create_ui(self):
        """UI作成"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # 画像表示エリア（200x150px）
        self._image_label = QLabel(self)
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setFixedSize(200, 150)
        self._image_label.setStyleSheet("""
            QLabel {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
        """)
        self._image_label.setText("画像なし")
        layout.addWidget(self._image_label)
        
        # アイコンツールバー
        self._toolbar = self._create_toolbar()
        layout.addWidget(self._toolbar)
        
        # マウストラッキング有効化
        self.setMouseTracking(True)
        self._image_label.setMouseTracking(True)
    
    def _create_toolbar(self) -> QToolBar:
        """
        アイコンツールバー作成
        
        Returns:
            QToolBar: ツールバー
        """
        toolbar = QToolBar(self)
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setStyleSheet("""
            QToolBar {
                background: white;
                border: none;
                spacing: 4px;
            }
            QToolButton {
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QToolButton:hover {
                background: #e9ecef;
            }
        """)
        
        # 編集ボタン
        edit_action = QAction(
            QgsApplication.getThemeIcon("mActionToggleEditing.svg"),
            "編集",
            self
        )
        edit_action.setToolTip("写真を編集（描画ツール）")
        edit_action.triggered.connect(self.edit_clicked.emit)
        toolbar.addAction(edit_action)
        
        # 保存ボタン
        save_action = QAction(
            QgsApplication.getThemeIcon("mActionFileSave.svg"),
            "保存",
            self
        )
        save_action.setToolTip("編集内容を保存")
        save_action.triggered.connect(self.save_clicked.emit)
        toolbar.addAction(save_action)
        
        # 削除ボタン
        delete_action = QAction(
            QgsApplication.getThemeIcon("mActionDeleteSelected.svg"),
            "削除",
            self
        )
        delete_action.setToolTip("編集内容を削除")
        delete_action.triggered.connect(self.delete_clicked.emit)
        toolbar.addAction(delete_action)
        
        # 差し替えボタン
        replace_action = QAction(
            QgsApplication.getThemeIcon("mActionAddImage.svg"),
            "元画像差し替え",
            self
        )
        replace_action.setToolTip("元画像を別の画像に差し替え")
        replace_action.triggered.connect(self.replace_clicked.emit)
        toolbar.addAction(replace_action)
        
        return toolbar
    
    def set_image(self, image_path: str):
        """
        画像を更新
        
        Args:
            image_path: 画像パス
        """
        self._image_path = image_path
        
        if not image_path:
            self._image_label.setText("画像なし")
            self._image_label.setPixmap(QPixmap())
            return
        
        try:
            pixmap = QPixmap(image_path)
            
            if pixmap.isNull():
                self._image_label.setText("画像なし")
                self._image_label.setPixmap(QPixmap())
                return
            
            # 200x150にフィット
            scaled = self._calculate_normal_size(pixmap)
            self._image_label.setPixmap(scaled)
            self._image_label.setText("")
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"PhotoRowWidget - 画像読み込みエラー: {str(e)}",
                "PoleFacility", Qgis.Warning
            )
            self._image_label.setText("画像なし")
            self._image_label.setPixmap(QPixmap())
    
    def _calculate_normal_size(self, pixmap: QPixmap) -> QPixmap:
        """
        通常表示サイズを計算（200x150にフィット）
        
        Args:
            pixmap: 元画像
        
        Returns:
            QPixmap: スケーリングされた画像
        """
        max_width = 200
        max_height = 150
        
        return pixmap.scaled(
            max_width, max_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
    
    def enterEvent(self, event):
        """マウスオーバー時"""
        super().enterEvent(event)
        if self._image_path:
            self.hovered.emit(self._image_path)
    
    def leaveEvent(self, event):
        """マウスアウト時"""
        super().leaveEvent(event)
        self.hovered.emit("")  # 空文字で非表示
    
    def get_image_path(self) -> str:
        """画像パスを取得"""
        return self._image_path
    
    def get_photo_type(self) -> str:
        """写真タイプを取得"""
        return self._photo_type
