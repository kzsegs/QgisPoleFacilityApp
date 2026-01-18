"""
基本設定タブ - パス設定、定数設定、検査状態選択肢の編集

UI構成:
    ■ パス設定
      - 写真ルートディレクトリ
      - エクスポート先デフォルトパス
    ■ 定数設定
      - 最大写真サイズ、CSV最大レコード数等
    ■ 検査状態選択肢
      - 検査状態1, 2, 3の選択肢編集
"""

from typing import Dict, Any, List
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLineEdit, QPushButton, QSpinBox,
    QListWidget, QListWidgetItem, QFileDialog, QMessageBox
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
        
        # 検査状態選択肢セクション
        status_group = self._create_inspection_status_section()
        layout.addWidget(status_group)
        
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
    
    def _create_inspection_status_section(self) -> QGroupBox:
        """
        検査状態選択肢セクション作成
        
        Returns:
            QGroupBox
        """
        group = QGroupBox("検査状態選択肢")
        layout = QVBoxLayout(group)
        layout.setSpacing(15)
        
        # 検査状態1, 2, 3
        for i in [1, 2, 3]:
            status_layout = self._create_status_list_widget(i)
            layout.addLayout(status_layout)
        
        return group
    
    def _create_status_list_widget(self, status_index: int) -> QVBoxLayout:
        """
        検査状態リストウィジェット作成
        
        Args:
            status_index: 検査状態インデックス（1, 2, 3）
        
        Returns:
            QVBoxLayout
        """
        from PyQt5.QtWidgets import QLabel
        
        layout = QVBoxLayout()
        
        # ラベル
        label = QLabel(f"検査状態{status_index}:")
        layout.addWidget(label)
        
        # リストウィジェット
        list_widget = QListWidget()
        list_widget.setMaximumHeight(120)
        layout.addWidget(list_widget)
        
        # ボタン群
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("追加")
        add_btn.clicked.connect(
            lambda: self._add_status_item(status_index)
        )
        btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("削除")
        remove_btn.clicked.connect(
            lambda: self._remove_status_item(status_index)
        )
        btn_layout.addWidget(remove_btn)
        
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        # ウィジェット登録
        self.widgets[f'status_{status_index}'] = list_widget
        
        return layout
    
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
        
        # 検査状態選択肢
        inspection_status = self.config.get('inspection_status', {})
        
        for i in [1, 2, 3]:
            key = f'status_{i}'
            if key in self.widgets:
                list_widget = self.widgets[key]
                items = inspection_status.get(key, [])
                
                for item_text in items:
                    list_widget.addItem(item_text)
    
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
    
    def _add_status_item(self, status_index: int) -> None:
        """
        検査状態アイテムを追加
        
        Args:
            status_index: 検査状態インデックス
        """
        from PyQt5.QtWidgets import QInputDialog
        
        text, ok = QInputDialog.getText(
            self,
            "項目追加",
            f"検査状態{status_index}の新しい項目を入力:"
        )
        
        if ok and text:
            list_widget = self.widgets[f'status_{status_index}']
            list_widget.addItem(text)
    
    def _remove_status_item(self, status_index: int) -> None:
        """
        検査状態アイテムを削除
        
        Args:
            status_index: 検査状態インデックス
        """
        list_widget = self.widgets[f'status_{status_index}']
        current_item = list_widget.currentItem()
        
        if current_item:
            row = list_widget.row(current_item)
            list_widget.takeItem(row)
    
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
            "inspection_status": {}
        }
        
        # 検査状態選択肢
        for i in [1, 2, 3]:
            key = f'status_{i}'
            list_widget = self.widgets[key]
            
            items = []
            for row in range(list_widget.count()):
                items.append(list_widget.item(row).text())
            
            values["inspection_status"][key] = items
        
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
        
        # 検査状態選択肢チェック（最低1項目必要）
        for i in [1, 2, 3]:
            list_widget = self.widgets[f'status_{i}']
            if list_widget.count() == 0:
                QMessageBox.warning(
                    self,
                    "入力エラー",
                    f"検査状態{i}は最低1項目必要です。"
                )
                return False
        
        return True
