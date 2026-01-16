"""
Field Status Tab Module

現場状況タブ。
写真サムネイル表示と検査箇所・検査状態の編集を提供する。
"""

import logging
from typing import Dict, Any, List

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QGroupBox, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
from qgis.core import QgsFeature

from .photo_thumbnail import PhotoThumbnailWidget

# ロガー設定
logger = logging.getLogger(__name__)


class InspectionItemWidget(QWidget):
    """
    検査項目ウィジェット。
    
    検査箇所、検査状態、備考の3つのフィールドを持つ。
    
    Signals:
        field_changed: フィールド変更時
    """
    
    field_changed = pyqtSignal(str, object)  # field_name, value
    
    def __init__(self, item_number: int, status_options: List[str], parent=None):
        """
        InspectionItemWidgetを初期化する。
        
        Args:
            item_number: 検査項目番号 (1-3)
            status_options: 検査状態の選択肢リスト
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self.item_number = item_number
        self.status_options = status_options
        
        # フィールド名
        self.location_field = f"検査箇所{item_number}"
        self.status_field = f"検査状態{item_number}"
        self.remark_field = f"検査状態{item_number}備考"
        
        # ウィジェット
        self.location_edit: QLineEdit = None
        self.status_combo: QComboBox = None
        self.remark_edit: QLineEdit = None
        
        # 初期値（変更検知用）
        self.initial_values: Dict[str, Any] = {}
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """UIを構築する。"""
        layout = QFormLayout()
        layout.setSpacing(5)
        
        # 検査箇所
        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("検査箇所を入力")
        self.location_edit.setProperty("data-testid", f"location-{self.item_number}")
        layout.addRow(f"検査箇所{self.item_number}:", self.location_edit)
        
        # 検査状態（ドロップダウン）
        self.status_combo = QComboBox()
        self.status_combo.addItem("")  # 空の選択肢
        self.status_combo.addItems(self.status_options)
        self.status_combo.setProperty("data-testid", f"status-{self.item_number}")
        layout.addRow(f"検査状態{self.item_number}:", self.status_combo)
        
        # 備考
        self.remark_edit = QLineEdit()
        self.remark_edit.setPlaceholderText("備考を入力")
        self.remark_edit.setProperty("data-testid", f"remark-{self.item_number}")
        layout.addRow(f"備考{self.item_number}:", self.remark_edit)
        
        self.setLayout(layout)
    
    def _connect_signals(self) -> None:
        """シグナルを接続する。"""
        self.location_edit.textChanged.connect(
            lambda text: self.field_changed.emit(self.location_field, text)
        )
        self.status_combo.currentTextChanged.connect(
            lambda text: self.field_changed.emit(self.status_field, text)
        )
        self.remark_edit.textChanged.connect(
            lambda text: self.field_changed.emit(self.remark_field, text)
        )
    
    def set_data(self, location: str, status: str, remark: str) -> None:
        """
        データを設定する。
        
        Args:
            location: 検査箇所
            status: 検査状態
            remark: 備考
        """
        self.location_edit.setText(location or "")
        
        # 検査状態を選択
        index = self.status_combo.findText(status or "")
        if index >= 0:
            self.status_combo.setCurrentIndex(index)
        else:
            self.status_combo.setCurrentIndex(0)  # 空を選択
        
        self.remark_edit.setText(remark or "")
        
        # 初期値を保存
        self.initial_values = {
            self.location_field: location or "",
            self.status_field: status or "",
            self.remark_field: remark or "",
        }
    
    def get_data(self) -> Dict[str, str]:
        """
        データを取得する。
        
        Returns:
            Dict[str, str]: フィールド名と値の辞書
        """
        return {
            self.location_field: self.location_edit.text(),
            self.status_field: self.status_combo.currentText(),
            self.remark_field: self.remark_edit.text(),
        }
    
    def is_modified(self) -> bool:
        """
        データが変更されたかどうかを返す。
        
        Returns:
            bool: 変更されている場合True
        """
        current_data = self.get_data()
        return current_data != self.initial_values


class FieldStatusTab(QWidget):
    """
    現場状況タブ。
    
    写真サムネイル（修正前3枚、修正後3枚）と
    検査項目（検査箇所・状態・備考）を表示・編集する。
    
    Signals:
        field_changed: フィールド変更時
        photo_clicked: 写真クリック時
    """
    
    # シグナル定義
    field_changed = pyqtSignal(str, object)  # field_name, value
    photo_clicked = pyqtSignal(str)  # photo_path
    
    def __init__(self, parent=None, config_manager=None):
        """
        FieldStatusTabを初期化する。
        
        Args:
            parent: 親ウィジェット
            config_manager: 設定マネージャ
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        
        # ウィジェット
        self.photo_thumbnail: PhotoThumbnailWidget = None
        self.inspection_widgets: List[InspectionItemWidget] = []
        
        self._setup_ui()
        
        logger.debug("FieldStatusTab initialized")
    
    def _setup_ui(self) -> None:
        """
        UIを構築する。
        
        レイアウト:
            - 写真セクション（上部）
            - 検査項目セクション（下部、スクロール可能）
        """
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # 写真セクション
        photo_section = self._setup_photo_section()
        layout.addWidget(photo_section)
        
        # 検査項目セクション
        inspection_section = self._setup_inspection_section()
        layout.addWidget(inspection_section, 1)  # ストレッチ優先度1
        
        self.setLayout(layout)
    
    def _setup_photo_section(self) -> QWidget:
        """
        写真セクションを構築する。
        
        Returns:
            QWidget: 写真セクション
        """
        group = QGroupBox("設備写真")
        layout = QVBoxLayout()
        
        # 写真サムネイルウィジェット
        self.photo_thumbnail = PhotoThumbnailWidget(
            parent=self,
            config_manager=self.config_manager
        )
        
        # シグナル接続
        self.photo_thumbnail.thumbnail_double_clicked.connect(
            self._on_photo_double_clicked
        )
        
        layout.addWidget(self.photo_thumbnail)
        group.setLayout(layout)
        
        return group
    
    def _setup_inspection_section(self) -> QWidget:
        """
        検査項目セクションを構築する。
        
        Returns:
            QWidget: 検査項目セクション（スクロール可能）
        """
        # スクロールエリア
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        
        # コンテンツウィジェット
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(15)
        
        # 検査状態の選択肢を取得
        status_options_1 = self._get_status_options(1)
        status_options_2 = self._get_status_options(2)
        status_options_3 = self._get_status_options(3)
        
        # 検査項目1
        inspection_1 = InspectionItemWidget(1, status_options_1, self)
        inspection_1.field_changed.connect(self.field_changed.emit)
        self.inspection_widgets.append(inspection_1)
        content_layout.addWidget(inspection_1)
        
        # 検査項目2
        inspection_2 = InspectionItemWidget(2, status_options_2, self)
        inspection_2.field_changed.connect(self.field_changed.emit)
        self.inspection_widgets.append(inspection_2)
        content_layout.addWidget(inspection_2)
        
        # 検査項目3
        inspection_3 = InspectionItemWidget(3, status_options_3, self)
        inspection_3.field_changed.connect(self.field_changed.emit)
        self.inspection_widgets.append(inspection_3)
        content_layout.addWidget(inspection_3)
        
        content_layout.addStretch()
        content_widget.setLayout(content_layout)
        
        scroll_area.setWidget(content_widget)
        
        return scroll_area
    
    def _get_status_options(self, status_num: int) -> List[str]:
        """
        検査状態の選択肢を取得する。
        
        Args:
            status_num: 検査状態番号 (1-3)
        
        Returns:
            List[str]: 選択肢リスト
        """
        if self.config_manager:
            try:
                return self.config_manager.get_inspection_status_list(status_num)
            except Exception as e:
                logger.warning(f"Failed to get status options: {e}")
        
        # デフォルトの選択肢
        return [
            f"状態{status_num}A",
            f"状態{status_num}B",
            f"状態{status_num}C",
            f"状態{status_num}D",
            f"その他{status_num}"
        ]
    
    def set_data(self, feature: QgsFeature) -> None:
        """
        地物データを設定する。
        
        Args:
            feature: 表示する地物
        """
        # 写真パスを取得して設定
        before_paths = [
            feature.attribute("設備写真1URI_修正前") or "",
            feature.attribute("設備写真2URI_修正前") or "",
            feature.attribute("設備写真3URI_修正前") or "",
        ]
        
        after_paths = [
            feature.attribute("設備写真1URI_修正後") or "",
            feature.attribute("設備写真2URI_修正後") or "",
            feature.attribute("設備写真3URI_修正後") or "",
        ]
        
        self.photo_thumbnail.set_photos(before_paths, after_paths)
        
        # 検査項目を設定
        for i, widget in enumerate(self.inspection_widgets, start=1):
            location = feature.attribute(f"検査箇所{i}") or ""
            status = feature.attribute(f"検査状態{i}") or ""
            remark = feature.attribute(f"検査状態{i}備考") or ""
            
            widget.set_data(location, status, remark)
        
        logger.debug(f"Field status data set for feature ID={feature.id()}")
    
    def get_data(self) -> Dict[str, Any]:
        """
        タブ内のデータを取得する。
        
        Returns:
            Dict[str, Any]: フィールド名と値の辞書
        """
        data = {}
        
        # 検査項目データを取得
        for widget in self.inspection_widgets:
            data.update(widget.get_data())
        
        # 写真パスは読み取り専用のため取得しない
        
        return data
    
    def is_modified(self) -> bool:
        """
        タブ内のデータが変更されたかどうかを返す。
        
        Returns:
            bool: 変更されている場合True
        """
        return any(widget.is_modified() for widget in self.inspection_widgets)
    
    def clear(self) -> None:
        """
        全てのフィールドをクリアする。
        """
        self.photo_thumbnail.clear()
        
        for widget in self.inspection_widgets:
            widget.set_data("", "", "")
        
        logger.debug("Field status tab cleared")
    
    def _on_photo_double_clicked(self, path: str) -> None:
        """
        写真ダブルクリック時の処理。
        
        Args:
            path: 写真のフルパス
        
        Note:
            写真エディタを開くためのシグナルを発行
        """
        self.photo_clicked.emit(path)
        logger.debug(f"Photo double-clicked: {path}")
