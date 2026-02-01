"""
基本設定タブ - パス設定、定数設定

UI構成:
    ■ パス設定
      - 写真ルートディレクトリ
      - エクスポート先デフォルトパス
    ■ 定数設定
      - 最大写真サイズ、CSV最大レコード数等

Note:
    検査状態選択肢はカラム設定タブで管理
"""

from typing import Dict, Any, List
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLineEdit, QPushButton, QSpinBox,
    QFileDialog, QMessageBox, QLabel
)
from PyQt5.QtCore import Qt
from qgis.core import QgsMessageLog, Qgis


class BasicSettingsTab(QWidget):
    """
    基本設定タブ
    
    Attributes:
        schema: スキーマ定義辞書
        config: 設定辞書への参照
        widgets: フィールド名→ウィジェットのマッピング
    """
    
    def __init__(self, schema: dict, config: dict, parent=None):
        """
        コンストラクタ
        
        Args:
            schema: config_schema.json のデータ
            config: 現在の設定辞書
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self.schema = schema
        self.config = config
        self.widgets: Dict[str, Any] = {}
        
        self._create_ui()
        self._load_values()
    
    def _create_ui(self) -> None:
        """UI構築"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # パス設定セクション
        paths_group = self._create_paths_section()
        layout.addWidget(paths_group)
        
        # 定数設定セクション
        constants_group = self._create_constants_section()
        layout.addWidget(constants_group)
        
        layout.addStretch()
    
    def _create_paths_section(self) -> QGroupBox:
        """
        パス設定セクション作成
        
        Returns:
            QGroupBox
        """
        group = QGroupBox("パス設定")
        layout = QFormLayout(group)
        layout.setSpacing(10)
        
        # 写真ルートディレクトリ
        photo_root_layout = QHBoxLayout()
        self.photo_root_edit = QLineEdit()
        self.photo_root_edit.setMinimumWidth(300)
        photo_root_layout.addWidget(self.photo_root_edit)
        
        photo_root_browse_btn = QPushButton("参照...")
        photo_root_browse_btn.setMaximumWidth(80)
        photo_root_browse_btn.clicked.connect(
            lambda: self._on_browse_clicked('photo_root')
        )
        photo_root_layout.addWidget(photo_root_browse_btn)
        
        layout.addRow("写真ルートディレクトリ:", photo_root_layout)
        
        # エクスポート先デフォルトパス
        export_path_layout = QHBoxLayout()
        self.export_path_edit = QLineEdit()
        self.export_path_edit.setMinimumWidth(300)
        export_path_layout.addWidget(self.export_path_edit)
        
        export_path_browse_btn = QPushButton("参照...")
        export_path_browse_btn.setMaximumWidth(80)
        export_path_browse_btn.clicked.connect(
            lambda: self._on_browse_clicked('export_path')
        )
        export_path_layout.addWidget(export_path_browse_btn)
        
        layout.addRow("エクスポート先デフォルトパス:", export_path_layout)
        
        # ウィジェット登録
        self.widgets['photo_root'] = self.photo_root_edit
        self.widgets['export_path'] = self.export_path_edit
        
        return group
    
    def _create_constants_section(self) -> QGroupBox:
        """
        定数設定セクション作成
        
        Returns:
            QGroupBox
        """
        group = QGroupBox("定数設定")
        layout = QFormLayout(group)
        layout.setSpacing(10)
        
        # スキーマから定数フィールドを取得
        constants_fields = self.schema.get('sections', {}).get('constants', {}).get('fields', {})
        
        # 最大写真サイズ
        if 'max_photo_size_mb' in constants_fields:
            field_def = constants_fields['max_photo_size_mb']
            self.max_photo_size_spin = QSpinBox()
            self.max_photo_size_spin.setRange(
                field_def.get('min', 1),
                field_def.get('max', 100)
            )
            self.max_photo_size_spin.setSuffix(" MB")
            layout.addRow(field_def['label'] + ":", self.max_photo_size_spin)
            self.widgets['max_photo_size_mb'] = self.max_photo_size_spin
        
        # CSV最大レコード数
        if 'max_records_per_csv' in constants_fields:
            field_def = constants_fields['max_records_per_csv']
            self.max_records_spin = QSpinBox()
            self.max_records_spin.setRange(
                field_def.get('min', 1),
                field_def.get('max', 10000)
            )
            layout.addRow(field_def['label'] + ":", self.max_records_spin)
            self.widgets['max_records_per_csv'] = self.max_records_spin
        
        # サムネイルサイズ
        if 'thumbnail_size' in constants_fields:
            field_def = constants_fields['thumbnail_size']
            self.thumbnail_size_spin = QSpinBox()
            self.thumbnail_size_spin.setRange(
                field_def.get('min', 50),
                field_def.get('max', 500)
            )
            self.thumbnail_size_spin.setSuffix(" px")
            layout.addRow(field_def['label'] + ":", self.thumbnail_size_spin)
            self.widgets['thumbnail_size'] = self.thumbnail_size_spin
        
        # 自動保存間隔
        if 'auto_save_interval_minutes' in constants_fields:
            field_def = constants_fields['auto_save_interval_minutes']
            self.auto_save_interval_spin = QSpinBox()
            self.auto_save_interval_spin.setRange(
                field_def.get('min', 0),
                field_def.get('max', 60)
            )
            self.auto_save_interval_spin.setSuffix(" 分 (0=無効)")
            layout.addRow(field_def['label'] + ":", self.auto_save_interval_spin)
            self.widgets['auto_save_interval_minutes'] = self.auto_save_interval_spin
        
        return group
    
    def _load_values(self) -> None:
        """現在の設定値をUIに反映"""
        # パス設定
        self.photo_root_edit.setText(
            self.config.get('paths', {}).get('photo_root', '')
        )
        self.export_path_edit.setText(
            self.config.get('paths', {}).get('export_path', '')
        )
        
        # 定数設定
        constants = self.config.get('constants', {})
        
        if 'max_photo_size_mb' in self.widgets:
            self.widgets['max_photo_size_mb'].setValue(
                constants.get('max_photo_size_mb', 10)
            )
        
        if 'max_records_per_csv' in self.widgets:
            self.widgets['max_records_per_csv'].setValue(
                constants.get('max_records_per_csv', 1000)
            )
        
        if 'thumbnail_size' in self.widgets:
            self.widgets['thumbnail_size'].setValue(
                constants.get('thumbnail_size', 100)
            )
        
        if 'auto_save_interval_minutes' in self.widgets:
            self.widgets['auto_save_interval_minutes'].setValue(
                constants.get('auto_save_interval_minutes', 0)
            )
    
    def _on_browse_clicked(self, field_name: str) -> None:
        """
        参照ボタンクリック時
        
        Args:
            field_name: フィールド名（'photo_root' または 'export_path'）
        """
        directory = QFileDialog.getExistingDirectory(
            self,
            "ディレクトリを選択",
            "",
            QFileDialog.ShowDirsOnly
        )
        
        if directory:
            if field_name == 'photo_root':
                self.photo_root_edit.setText(directory)
            elif field_name == 'export_path':
                self.export_path_edit.setText(directory)
    
    def get_values(self) -> dict:
        """
        入力値を取得
        
        Returns:
            設定辞書
        """
        values = {
            "paths": {
                "photo_root": self.photo_root_edit.text(),
                "export_path": self.export_path_edit.text()
            },
            "constants": {
                "max_photo_size_mb": self.widgets['max_photo_size_mb'].value(),
                "max_records_per_csv": self.widgets['max_records_per_csv'].value(),
                "thumbnail_size": self.widgets['thumbnail_size'].value(),
                "auto_save_interval_minutes": self.widgets['auto_save_interval_minutes'].value()
            },
            "inspection_status": self.config.get('inspection_status', {})  # 既存値を保持
        }
        
        return values
    
    def validate(self) -> bool:
        """
        入力値をバリデーション
        
        Returns:
            True: バリデーション成功
            False: バリデーション失敗
        """
        # パス必須チェック
        if not self.photo_root_edit.text():
            QMessageBox.warning(
                self,
                "入力エラー",
                "写真ルートディレクトリを指定してください。"
            )
            return False
        
        if not self.export_path_edit.text():
            QMessageBox.warning(
                self,
                "入力エラー",
                "エクスポート先デフォルトパスを指定してください。"
            )
            return False
        
        return True
