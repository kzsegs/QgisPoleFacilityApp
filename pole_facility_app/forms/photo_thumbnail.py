"""
Photo Thumbnail Widget Module

修正前・修正後の写真サムネイルを表示するウィジェット。
各3枚ずつ、計6枚の写真を管理する。
"""

import os
import logging
from typing import List, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QGroupBox, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QCursor

# ロガー設定
logger = logging.getLogger(__name__)


class ClickableLabel(QLabel):
    """
    クリック可能なQLabel。
    
    写真サムネイル用のラベルで、クリック・ダブルクリックイベントを発行する。
    
    Signals:
        clicked: クリック時
        double_clicked: ダブルクリック時
    """
    
    clicked = pyqtSignal()
    double_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        """ClickableLabelを初期化する。"""
        super().__init__(parent)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setAlignment(Qt.AlignCenter)
        self.setScaledContents(False)
        
        # 枠線を追加
        self.setStyleSheet("""
            ClickableLabel {
                border: 1px solid #ccc;
                background-color: #f5f5f5;
                padding: 2px;
            }
            ClickableLabel:hover {
                border: 2px solid #4a90e2;
                background-color: #e8f4fd;
            }
        """)
    
    def mousePressEvent(self, event):
        """マウスプレスイベント処理。"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """マウスダブルクリックイベント処理。"""
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)


class PhotoThumbnailWidget(QWidget):
    """
    写真サムネイル表示ウィジェット。
    
    修正前3枚、修正後3枚の計6枚の写真をサムネイル表示する。
    
    Signals:
        thumbnail_clicked: サムネイルクリック時 (photo_type: str, index: int)
        thumbnail_double_clicked: サムネイルダブルクリック時 (path: str)
    """
    
    # シグナル定義
    thumbnail_clicked = pyqtSignal(str, int)  # photo_type, index
    thumbnail_double_clicked = pyqtSignal(str)  # path
    
    def __init__(self, parent=None, config_manager=None):
        """
        PhotoThumbnailWidgetを初期化する。
        
        Args:
            parent: 親ウィジェット
            config_manager: 設定マネージャ
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        
        # サムネイルサイズ
        self.thumbnail_size = 100
        if config_manager:
            self.thumbnail_size = config_manager.get("constants.thumbnail_size", 100)
        
        # 写真パスリスト
        self.before_paths: List[str] = ["", "", ""]
        self.after_paths: List[str] = ["", "", ""]
        
        # 選択インデックス
        self.selected_index: int = -1
        self.selected_type: str = ""
        
        # ラベルリスト
        self.before_labels: List[ClickableLabel] = []
        self.after_labels: List[ClickableLabel] = []
        
        self._setup_ui()
        
        logger.debug("PhotoThumbnailWidget initialized")
    
    def _setup_ui(self) -> None:
        """
        UIを構築する。
        
        レイアウト:
            修正前写真(3枚) | 修正後写真(3枚)
        """
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        # 修正前写真グループ
        before_group = self._create_photo_group("修正前写真", "before")
        layout.addWidget(before_group)
        
        # 修正後写真グループ
        after_group = self._create_photo_group("修正後写真", "after")
        layout.addWidget(after_group)
        
        self.setLayout(layout)
    
    def _create_photo_group(self, title: str, photo_type: str) -> QGroupBox:
        """
        写真グループを作成する。
        
        Args:
            title: グループタイトル
            photo_type: 写真タイプ ("before" or "after")
        
        Returns:
            QGroupBox: 作成したグループボックス
        """
        group = QGroupBox(title)
        grid_layout = QGridLayout()
        grid_layout.setSpacing(5)
        
        # 3枚の写真ラベルを作成
        labels = []
        for i in range(3):
            label = ClickableLabel()
            label.setFixedSize(self.thumbnail_size, self.thumbnail_size)
            label.setProperty("data-testid", f"{photo_type}-photo-{i+1}")
            
            # シグナル接続
            label.clicked.connect(
                lambda idx=i, pt=photo_type: self._on_label_clicked(pt, idx)
            )
            label.double_clicked.connect(
                lambda idx=i, pt=photo_type: self._on_label_double_clicked(pt, idx)
            )
            
            # プレースホルダー表示
            self._show_placeholder(label, i + 1)
            
            labels.append(label)
            
            # グリッドに配置（横3列）
            grid_layout.addWidget(label, 0, i)
        
        # ラベルリストに保存
        if photo_type == "before":
            self.before_labels = labels
        else:
            self.after_labels = labels
        
        group.setLayout(grid_layout)
        return group
    
    def _show_placeholder(self, label: QLabel, number: int) -> None:
        """
        プレースホルダーを表示する。
        
        Args:
            label: 対象ラベル
            number: 写真番号
        """
        label.setText(f"写真{number}\n(なし)")
        label.setStyleSheet("""
            ClickableLabel {
                border: 1px dashed #ccc;
                background-color: #f9f9f9;
                color: #999;
                font-size: 10px;
            }
        """)
    
    def set_photos(self, before_paths: List[str], after_paths: List[str]) -> None:
        """
        写真を設定する。
        
        Args:
            before_paths: 修正前写真のパスリスト（最大3件）
            after_paths: 修正後写真のパスリスト（最大3件）
        
        Note:
            - パスが空の場合はプレースホルダーを表示
            - ConfigManagerのルートパスと結合してフルパスを生成
        """
        # パスリストを保存（最大3件）
        self.before_paths = (before_paths + ["", "", ""])[:3]
        self.after_paths = (after_paths + ["", "", ""])[:3]
        
        # 修正前写真を設定
        for i, path in enumerate(self.before_paths):
            self._set_photo_to_label(self.before_labels[i], path, i + 1)
        
        # 修正後写真を設定
        for i, path in enumerate(self.after_paths):
            self._set_photo_to_label(self.after_labels[i], path, i + 1)
        
        logger.debug(f"Photos set: {len([p for p in before_paths if p])} before, "
                    f"{len([p for p in after_paths if p])} after")
    
    def _set_photo_to_label(self, label: QLabel, relative_path: str, number: int) -> None:
        """
        ラベルに写真を設定する。
        
        Args:
            label: 対象ラベル
            relative_path: 相対パス
            number: 写真番号
        """
        if not relative_path:
            # パスが空の場合はプレースホルダー
            self._show_placeholder(label, number)
            return
        
        # フルパスを解決
        full_path = self._resolve_path(relative_path)
        
        if not os.path.exists(full_path):
            # ファイルが存在しない場合はエラー表示
            label.setText(f"写真{number}\n(ファイルなし)")
            label.setStyleSheet("""
                ClickableLabel {
                    border: 1px dashed #f00;
                    background-color: #ffe0e0;
                    color: #c00;
                    font-size: 10px;
                }
            """)
            logger.warning(f"Photo file not found: {full_path}")
            return
        
        # サムネイル画像を作成
        pixmap = self._create_thumbnail(full_path)
        
        if pixmap and not pixmap.isNull():
            label.setPixmap(pixmap)
            label.setStyleSheet("""
                ClickableLabel {
                    border: 1px solid #ccc;
                    background-color: white;
                    padding: 2px;
                }
                ClickableLabel:hover {
                    border: 2px solid #4a90e2;
                    background-color: #e8f4fd;
                }
            """)
        else:
            # 読み込み失敗
            label.setText(f"写真{number}\n(読込失敗)")
            label.setStyleSheet("""
                ClickableLabel {
                    border: 1px dashed #f90;
                    background-color: #fff8e0;
                    color: #f60;
                    font-size: 10px;
                }
            """)
            logger.warning(f"Failed to load thumbnail: {full_path}")
    
    def _resolve_path(self, relative_path: str) -> str:
        """
        相対パスをフルパスに解決する。
        
        Args:
            relative_path: ルートパスからの相対パス
        
        Returns:
            str: フルパス
        """
        if not relative_path:
            return ""
        
        # 絶対パスの場合はそのまま返す
        if os.path.isabs(relative_path):
            return relative_path
        
        # ConfigManagerからルートパスを取得
        if self.config_manager:
            root_path = self.config_manager.get_photo_root_path()
            if root_path:
                return os.path.join(root_path, relative_path)
        
        # ルートパスがない場合は相対パスのまま
        return relative_path
    
    def _create_thumbnail(self, path: str) -> Optional[QPixmap]:
        """
        サムネイル画像を作成する。
        
        Args:
            path: 画像ファイルのフルパス
        
        Returns:
            Optional[QPixmap]: サムネイル画像、失敗時はNone
        """
        try:
            pixmap = QPixmap(path)
            
            if pixmap.isNull():
                return None
            
            # アスペクト比を維持してサムネイルサイズに縮小
            thumbnail = pixmap.scaled(
                self.thumbnail_size,
                self.thumbnail_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            return thumbnail
            
        except Exception as e:
            logger.exception(f"Failed to create thumbnail: {e}")
            return None
    
    def _on_label_clicked(self, photo_type: str, index: int) -> None:
        """
        ラベルクリック時の処理。
        
        Args:
            photo_type: 写真タイプ ("before" or "after")
            index: 写真インデックス (0-2)
        """
        self.selected_type = photo_type
        self.selected_index = index
        
        # シグナル発行
        self.thumbnail_clicked.emit(photo_type, index)
        
        logger.debug(f"Thumbnail clicked: {photo_type}[{index}]")
    
    def _on_label_double_clicked(self, photo_type: str, index: int) -> None:
        """
        ラベルダブルクリック時の処理。
        
        Args:
            photo_type: 写真タイプ ("before" or "after")
            index: 写真インデックス (0-2)
        
        Note:
            写真エディタを開くためのシグナルを発行
        """
        # 対応するパスを取得
        if photo_type == "before":
            path = self.before_paths[index]
        else:
            path = self.after_paths[index]
        
        if not path:
            logger.debug("No photo to open")
            return
        
        # フルパスを解決
        full_path = self._resolve_path(path)
        
        # シグナル発行
        self.thumbnail_double_clicked.emit(full_path)
        
        logger.debug(f"Thumbnail double-clicked: {full_path}")
    
    def get_selected_path(self) -> str:
        """
        選択中の写真パスを取得する。
        
        Returns:
            str: 選択中の写真のフルパス、未選択の場合は空文字列
        """
        if self.selected_index < 0:
            return ""
        
        # 対応するパスを取得
        if self.selected_type == "before":
            path = self.before_paths[self.selected_index]
        elif self.selected_type == "after":
            path = self.after_paths[self.selected_index]
        else:
            return ""
        
        return self._resolve_path(path)
    
    def clear(self) -> None:
        """
        全ての写真をクリアする。
        """
        self.before_paths = ["", "", ""]
        self.after_paths = ["", "", ""]
        self.selected_index = -1
        self.selected_type = ""
        
        # プレースホルダーを表示
        for i, label in enumerate(self.before_labels):
            self._show_placeholder(label, i + 1)
        
        for i, label in enumerate(self.after_labels):
            self._show_placeholder(label, i + 1)
        
        logger.debug("Photos cleared")
    
    def refresh(self) -> None:
        """
        現在の写真パスで再読み込みする。
        """
        self.set_photos(self.before_paths, self.after_paths)
