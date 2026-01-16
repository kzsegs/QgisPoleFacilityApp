"""
Result Tab Module

判定結果タブ。
総合判定結果、備考、検査日、検査者氏名、確認者氏名を編集する。
"""

import logging
from typing import Dict, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QDateEdit, QGroupBox, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QDate
from qgis.core import QgsFeature

# ロガー設定
logger = logging.getLogger(__name__)


class ResultTab(QWidget):
    """
    判定結果タブ。
    
    総合判定結果、備考、検査日、検査者氏名、確認者氏名を表示・編集する。
    
    Signals:
        field_changed: フィールド変更時
    """
    
    # シグナル定義
    field_changed = pyqtSignal(str, object)  # field_name, value
    
    # フィールド定義
    FIELDS = [
        {
            "name": "総合判定結果1",
            "key": "総合判定結果1",
            "widget_type": "line_edit",
            "placeholder": "総合判定結果を入力"
        },
        {
            "name": "総合判定結果1備考",
            "key": "総合判定結果1備考",
            "widget_type": "text_edit",
            "placeholder": "総合判定結果の詳細を入力"
        },
        {
            "name": "備考",
            "key": "備考",
            "widget_type": "text_edit",
            "placeholder": "その他の備考を入力"
        },
        {
            "name": "検査日",
            "key": "検査日",
            "widget_type": "date_edit",
            "placeholder": ""
        },
        {
            "name": "検査者氏名",
            "key": "検査者氏名",
            "widget_type": "line_edit",
            "placeholder": "検査者氏名を入力"
        },
        {
            "name": "確認者氏名",
            "key": "確認者氏名",
            "widget_type": "line_edit",
            "placeholder": "確認者氏名を入力"
        },
    ]
    
    def __init__(self, parent=None):
        """
        ResultTabを初期化する。
        
        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        # ウィジェット辞書
        self.field_widgets: Dict[str, QWidget] = {}
        
        # 初期値（変更検知用）
        self.initial_values: Dict[str, Any] = {}
        
        self._setup_ui()
        self._connect_signals()
        
        logger.debug("ResultTab initialized")
    
    def _setup_ui(self) -> None:
        """
        UIを構築する。
        
        レイアウト:
            フォームレイアウトで各フィールドを縦に配置
        """
        layout = QVBoxLayout()
        
        # スクロールエリア
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        
        # コンテンツウィジェット
        content_widget = QWidget()
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # 各フィールドを作成
        for field_def in self.FIELDS:
            field_name = field_def["name"]
            field_key = field_def["key"]
            widget_type = field_def["widget_type"]
            placeholder = field_def["placeholder"]
            
            # ウィジェットを作成
            if widget_type == "line_edit":
                widget = QLineEdit()
                widget.setPlaceholderText(placeholder)
                widget.setProperty("data-testid", f"result-{field_key}")
                
            elif widget_type == "text_edit":
                widget = QTextEdit()
                widget.setPlaceholderText(placeholder)
                widget.setMaximumHeight(100)
                widget.setProperty("data-testid", f"result-{field_key}")
                
            elif widget_type == "date_edit":
                widget = QDateEdit()
                widget.setCalendarPopup(True)
                widget.setDisplayFormat("yyyy/MM/dd")
                widget.setDate(QDate.currentDate())
                widget.setProperty("data-testid", f"result-{field_key}")
            
            else:
                logger.warning(f"Unknown widget type: {widget_type}")
                continue
            
            # ウィジェット辞書に保存
            self.field_widgets[field_key] = widget
            
            # フォームレイアウトに追加
            form_layout.addRow(f"{field_name}:", widget)
        
        content_widget.setLayout(form_layout)
        scroll_area.setWidget(content_widget)
        
        layout.addWidget(scroll_area)
        self.setLayout(layout)
    
    def _connect_signals(self) -> None:
        """
        シグナルを接続する。
        """
        for field_key, widget in self.field_widgets.items():
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(
                    lambda text, key=field_key: self.field_changed.emit(key, text)
                )
            elif isinstance(widget, QTextEdit):
                widget.textChanged.connect(
                    lambda key=field_key: self.field_changed.emit(
                        key, self.field_widgets[key].toPlainText()
                    )
                )
            elif isinstance(widget, QDateEdit):
                widget.dateChanged.connect(
                    lambda date, key=field_key: self.field_changed.emit(
                        key, date.toString("yyyy/MM/dd")
                    )
                )
    
    def set_data(self, feature: QgsFeature) -> None:
        """
        地物データを設定する。
        
        Args:
            feature: 表示する地物
        """
        for field_key, widget in self.field_widgets.items():
            value = feature.attribute(field_key)
            
            if isinstance(widget, QLineEdit):
                widget.setText(value or "")
                self.initial_values[field_key] = value or ""
                
            elif isinstance(widget, QTextEdit):
                widget.setPlainText(value or "")
                self.initial_values[field_key] = value or ""
                
            elif isinstance(widget, QDateEdit):
                # 日付フィールドの処理
                if value:
                    # 文字列からQDateに変換
                    if isinstance(value, str):
                        # "yyyy/MM/dd"形式を想定
                        parts = value.split('/')
                        if len(parts) == 3:
                            try:
                                year, month, day = map(int, parts)
                                date = QDate(year, month, day)
                                if date.isValid():
                                    widget.setDate(date)
                                else:
                                    widget.setDate(QDate.currentDate())
                            except ValueError:
                                widget.setDate(QDate.currentDate())
                        else:
                            widget.setDate(QDate.currentDate())
                    else:
                        # QDateオブジェクトの場合
                        widget.setDate(value)
                else:
                    widget.setDate(QDate.currentDate())
                
                self.initial_values[field_key] = widget.date().toString("yyyy/MM/dd")
        
        logger.debug(f"Result data set for feature ID={feature.id()}")
    
    def get_data(self) -> Dict[str, Any]:
        """
        タブ内のデータを取得する。
        
        Returns:
            Dict[str, Any]: フィールド名と値の辞書
        """
        data = {}
        
        for field_key, widget in self.field_widgets.items():
            if isinstance(widget, QLineEdit):
                data[field_key] = widget.text()
                
            elif isinstance(widget, QTextEdit):
                data[field_key] = widget.toPlainText()
                
            elif isinstance(widget, QDateEdit):
                data[field_key] = widget.date().toString("yyyy/MM/dd")
        
        return data
    
    def is_modified(self) -> bool:
        """
        タブ内のデータが変更されたかどうかを返す。
        
        Returns:
            bool: 変更されている場合True
        """
        current_data = self.get_data()
        
        for field_key, current_value in current_data.items():
            initial_value = self.initial_values.get(field_key, "")
            if current_value != initial_value:
                return True
        
        return False
    
    def clear(self) -> None:
        """
        全てのフィールドをクリアする。
        """
        for widget in self.field_widgets.values():
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QTextEdit):
                widget.clear()
            elif isinstance(widget, QDateEdit):
                widget.setDate(QDate.currentDate())
        
        self.initial_values.clear()
        
        logger.debug("Result tab cleared")
    
    def validate(self) -> tuple[bool, str]:
        """
        タブ内のデータをバリデーションする。
        
        Returns:
            tuple[bool, str]: (有効かどうか, エラーメッセージ)
        """
        # 必須フィールドチェック（検査日）
        date_widget = self.field_widgets.get("検査日")
        if date_widget and isinstance(date_widget, QDateEdit):
            if not date_widget.date().isValid():
                return False, "検査日が無効です"
        
        # その他のバリデーションは必要に応じて追加
        
        return True, ""
