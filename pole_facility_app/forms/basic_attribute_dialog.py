# -*- coding: utf-8 -*-
"""
Basic Attribute Dialog - 基本属性ダイアログ

設備の基本属性（識別情報・位置情報）を表示するダイアログ。
複数ウィンドウUIの1つ目のダイアログ。

機能:
    - 収容区域コード、収容区域名、設備名、設備番号の表示
    - 緯度座標、経度座標の表示
    - 読み取り専用または編集可能（設定による）
    - セクション単位でグループ化表示
"""

from typing import Optional
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QWidget
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.core import QgsFeature, QgsVectorLayer, QgsMessageLog, Qgis

from ..forms.dynamic_form_builder import DynamicFormBuilder


class BasicAttributeDialog(QDialog):
    """
    基本属性ダイアログ
    
    使用例:
        dialog = BasicAttributeDialog(config_manager, data_manager, parent)
        dialog.set_feature(feature)
        dialog.show()
    
    表示フィールド（デフォルト）:
        識別情報:
            - 収容区域コード
            - 収容区域名
            - 設備名
            - 設備番号
        位置情報:
            - 緯度座標
            - 経度座標
    """
    
    closed = pyqtSignal()  # ダイアログクローズ時のシグナル
    
    def __init__(self, config_manager, data_manager, parent=None):
        """
        初期化
        
        Args:
            config_manager: ConfigManager インスタンス
            data_manager: DataManager インスタンス
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self._config_manager = config_manager
        self._data_manager = data_manager
        self._feature = None
        self._layer = None
        
        # フォームビルダー
        self._form_builder = None
        
        # フィールド設定
        self._fields_config = []
        
        self._setup_window()
        self._load_field_config()
        self._create_ui()
    
    def _setup_window(self):
        """ウィンドウ設定"""
        self.setWindowTitle("基本属性")
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowCloseButtonHint |
            Qt.WindowMinimizeButtonHint
        )
        self.resize(400, 300)
    
    def _load_field_config(self):
        """
        フィールド設定を読み込み
        
        default_config.json の field_categories.basic から取得
        
        デフォルト設定:
            [
                {
                    "name": "収容区域コード",
                    "label": "収容区域コード",
                    "type": "text",
                    "editable": false,
                    "section": "識別情報"
                },
                ...
            ]
        """
        try:
            # field_categories.basic 取得
            field_categories = self._config_manager.get("field_categories", {})
            basic_config = field_categories.get("basic", {})
            
            if not basic_config:
                QgsMessageLog.logMessage(
                    "BasicAttributeDialog - field_categories.basic が設定されていません",
                    "PoleFacility", Qgis.Warning
                )
                self._fields_config = self._get_default_config()
                return
            
            self._fields_config = basic_config.get("fields", [])
            
            if not self._fields_config:
                QgsMessageLog.logMessage(
                    "BasicAttributeDialog - フィールド設定が空です",
                    "PoleFacility", Qgis.Warning
                )
                self._fields_config = self._get_default_config()
            
            QgsMessageLog.logMessage(
                f"BasicAttributeDialog - フィールド設定読み込み完了: {len(self._fields_config)}件",
                "PoleFacility", Qgis.Info
            )
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"BasicAttributeDialog - 設定読み込みエラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
            self._fields_config = self._get_default_config()
    
    def _get_default_config(self) -> list:
        """
        デフォルトのフィールド設定を返す
        
        Returns:
            list: フィールド設定のリスト
        """
        return [
            {
                "name": "収容区域コード",
                "label": "収容区域コード",
                "type": "text",
                "editable": False,
                "section": "識別情報"
            },
            {
                "name": "収容区域名",
                "label": "収容区域名",
                "type": "text",
                "editable": False,
                "section": "識別情報"
            },
            {
                "name": "設備名",
                "label": "設備名",
                "type": "text",
                "editable": False,
                "section": "識別情報"
            },
            {
                "name": "設備番号",
                "label": "設備番号",
                "type": "text",
                "editable": False,
                "section": "識別情報"
            },
            {
                "name": "緯度座標",
                "label": "緯度",
                "type": "number",
                "editable": False,
                "section": "位置情報"
            },
            {
                "name": "経度座標",
                "label": "経度",
                "type": "number",
                "editable": False,
                "section": "位置情報"
            }
        ]
    
    def _create_ui(self):
        """
        UI作成
        
        レイアウト:
            [タイトルラベル]
            [フォーム（DynamicFormBuilder）]
            [閉じるボタン]
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # タイトル
        title_label = QLabel("基本属性情報", self)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #333;
                padding-bottom: 8px;
                border-bottom: 2px solid #007AFF;
            }
        """)
        layout.addWidget(title_label)
        
        # フォームビルダー初期化
        self._form_builder = DynamicFormBuilder(self._config_manager)
        
        # フォームは set_feature() で構築
        # ここではプレースホルダーのみ配置
        self._form_placeholder = QWidget(self)
        self._form_placeholder.setStyleSheet("background-color: #f8f9fa;")
        layout.addWidget(self._form_placeholder)
        
        layout.addStretch()
        
        # ボタンエリア
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_button = QPushButton("閉じる", self)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 24px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """)
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
    
    def set_feature(self, feature: QgsFeature):
        """
        地物をセット
        
        Args:
            feature: 地物オブジェクト
        
        処理フロー:
            1. 地物を保存
            2. フォームを構築（DynamicFormBuilder.build()）
            3. ウィンドウタイトルを更新
        """
        try:
            self._feature = feature
            
            if not feature or not feature.isValid():
                QgsMessageLog.logMessage(
                    "BasicAttributeDialog - 無効な地物が指定されました",
                    "PoleFacility", Qgis.Warning
                )
                return
            
            # フォーム構築
            form_widget = self._form_builder.build(self._fields_config, feature)
            
            # 既存のフォームを置き換え
            if self._form_placeholder:
                # プレースホルダーを削除
                layout = self.layout()
                layout.replaceWidget(self._form_placeholder, form_widget)
                self._form_placeholder.deleteLater()
                self._form_placeholder = form_widget
            
            # タイトル更新
            self._update_title()
            
            QgsMessageLog.logMessage(
                f"BasicAttributeDialog - 地物設定完了: feature_id={feature.id()}",
                "PoleFacility", Qgis.Info
            )
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"BasicAttributeDialog - set_feature エラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
    
    def refresh(self):
        """
        表示を更新
        
        現在の地物で再構築
        """
        if self._feature:
            self.set_feature(self._feature)
    
    def _update_title(self):
        """
        ウィンドウタイトルを更新
        
        タイトル形式: "基本属性 - 設備番号: X"
        """
        if not self._feature:
            return
        
        try:
            # 設備番号を取得
            equipment_number = self._feature.get("設備番号", "")
            
            if equipment_number:
                self.setWindowTitle(f"基本属性 - 設備番号: {equipment_number}")
            else:
                self.setWindowTitle("基本属性")
        
        except Exception as e:
            QgsMessageLog.logMessage(
                f"BasicAttributeDialog - タイトル更新エラー: {str(e)}",
                "PoleFacility", Qgis.Warning
            )
            self.setWindowTitle("基本属性")
    
    def closeEvent(self, event):
        """
        クローズイベント
        
        Args:
            event: QCloseEvent
        
        処理:
            closed シグナルを発行してから閉じる
        """
        QgsMessageLog.logMessage(
            "BasicAttributeDialog - ダイアログを閉じます",
            "PoleFacility", Qgis.Info
        )
        
        self.closed.emit()
        super().closeEvent(event)
    
    def get_values(self) -> dict:
        """
        フォームの値を取得
        
        Returns:
            dict: {field_name: value, ...}
        
        Note:
            読み取り専用フィールドも含む全ての値を返す
        """
        if self._form_builder:
            return self._form_builder.get_values()
        return {}
    
    def get_editable_values(self) -> dict:
        """
        編集可能なフィールドの値を取得
        
        Returns:
            dict: {field_name: value, ...}
        
        Note:
            editable=True のフィールドのみ返す
        """
        if self._form_builder:
            return self._form_builder.get_editable_values()
        return {}
    
    def get_widget(self, field_name: str):
        """
        特定フィールドのウィジェットを取得
        
        Args:
            field_name: フィールド名
        
        Returns:
            QWidget: ウィジェット、存在しない場合は None
        """
        if self._form_builder:
            return self._form_builder.get_widget(field_name)
        return None
