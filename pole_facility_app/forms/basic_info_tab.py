"""
Basic Info Tab Module

基本情報タブ。
収容区域コード、設備名、設備番号、座標等の読み取り専用フィールドを表示する。
"""

import logging
from typing import Dict, Any

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QGroupBox
)
from PyQt5.QtCore import Qt
from qgis.core import QgsFeature

# ロガー設定
logger = logging.getLogger(__name__)


class BasicInfoTab(QWidget):
    """
    基本情報タブ。
    
    収容区域コード、収容区域名、設備名、設備番号、緯度座標、経度座標を
    読み取り専用で表示する。
    """
    
    # フィールド定義
    FIELDS = [
        {"name": "収容区域コード", "key": "収容区域コード", "readonly": True},
        {"name": "収容区域名", "key": "収容区域名", "readonly": True},
        {"name": "設備名", "key": "設備名", "readonly": True},
        {"name": "設備番号", "key": "設備番号", "readonly": True},
        {"name": "緯度座標", "key": "緯度座標", "readonly": True},
        {"name": "経度座標", "key": "経度座標", "readonly": True},
    ]
    
    def __init__(self, parent=None):
        """
        BasicInfoTabを初期化する。
        
        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        # ウィジェット辞書
        self.field_widgets: Dict[str, QLineEdit] = {}
        
        self._setup_ui()
        
        logger.debug("BasicInfoTab initialized")
    
    def _setup_ui(self) -> None:
        """
        UIを構築する。
        
        レイアウト:
            フォームレイアウトで各フィールドを縦に配置
        """
        layout = QVBoxLayout()
        
        # グループボックス
        group = QGroupBox("基本情報")
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # 各フィールドを作成
        for field_def in self.FIELDS:
            field_name = field_def["name"]
            field_key = field_def["key"]
            is_readonly = field_def["readonly"]
            
            # テキスト入力フィールド
            line_edit = QLineEdit()
            line_edit.setReadOnly(is_readonly)
            line_edit.setProperty("data-testid", f"basic-{field_key}")
            
            # 読み取り専用の場合はスタイル変更
            if is_readonly:
                line_edit.setStyleSheet("""
                    QLineEdit:read-only {
                        background-color: #f0f0f0;
                        color: #333;
                    }
                """)
            
            # ウィジェット辞書に保存
            self.field_widgets[field_key] = line_edit
            
            # フォームレイアウトに追加
            form_layout.addRow(f"{field_name}:", line_edit)
        
        group.setLayout(form_layout)
        layout.addWidget(group)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def set_data(self, feature: QgsFeature) -> None:
        """
        地物データを設定する。
        
        Args:
            feature: 表示する地物
        """
        for field_key, widget in self.field_widgets.items():
            value = feature.attribute(field_key)
            
            # 値をテキストに変換
            if value is None:
                text = ""
            else:
                text = str(value)
            
            widget.setText(text)
        
        logger.debug(f"Basic info data set for feature ID={feature.id()}")
    
    def get_data(self) -> Dict[str, Any]:
        """
        タブ内のデータを取得する。
        
        Returns:
            Dict[str, Any]: フィールド名と値の辞書
        
        Note:
            基本情報タブは全て読み取り専用のため、このメソッドは使用されない
        """
        data = {}
        
        for field_key, widget in self.field_widgets.items():
            data[field_key] = widget.text()
        
        return data
    
    def is_modified(self) -> bool:
        """
        タブ内のデータが変更されたかどうかを返す。
        
        Returns:
            bool: 常にFalse（読み取り専用のため変更不可）
        """
        return False
    
    def clear(self) -> None:
        """
        全てのフィールドをクリアする。
        """
        for widget in self.field_widgets.values():
            widget.clear()
        
        logger.debug("Basic info tab cleared")
