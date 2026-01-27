"""
デバッグ設定タブ - ログ設定とデバッグオプション

UI構成:
    ■ ログ設定
      - ログ出力有効化
      - ログレベル選択
      - ファイル出力設定
    ■ その他のデバッグオプション（Phase 2用プレースホルダー）
"""

from typing import Dict, Any
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QCheckBox, QRadioButton,
    QButtonGroup, QLineEdit, QPushButton,
    QLabel, QFileDialog
)
from PyQt5.QtCore import Qt


class DebugSettingsTab(QWidget):
    """
    デバッグ設定タブ
    
    Attributes:
        schema: スキーマ定義辞書
        config: 設定辞書への参照
        enable_logging_checkbox: ログ出力有効化チェックボックス
        log_level_radio_group: ログレベルラジオボタングループ
        log_to_file_checkbox: ファイル出力チェックボックス
        log_file_path_edit: ログディレクトリパス入力
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
        
        self._create_ui()
        self._load_values()
    
    def _create_ui(self) -> None:
        """UI構築"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # ログ設定グループ
        log_group = QGroupBox("ログ設定")
        log_layout = QVBoxLayout(log_group)
        log_layout.setSpacing(10)
        
        # ログ出力有効化
        self.enable_logging_checkbox = QCheckBox("ログ出力を有効化")
        log_layout.addWidget(self.enable_logging_checkbox)
        
        log_layout.addSpacing(10)
        
        # ログレベル
        log_level_label = QLabel("ログレベル:")
        log_layout.addWidget(log_level_label)
        
        self.log_level_radio_group = QButtonGroup(self)
        self.log_level_radios: Dict[str, QRadioButton] = {}
        
        for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            radio = QRadioButton(level)
            self.log_level_radio_group.addButton(radio)
            self.log_level_radios[level] = radio
            log_layout.addWidget(radio)
        
        log_layout.addSpacing(10)
        
        # ファイル出力
        self.log_to_file_checkbox = QCheckBox("ファイルに出力")
        log_layout.addWidget(self.log_to_file_checkbox)
        
        # ログ保存先ディレクトリ
        log_dir_label = QLabel("ログ保存先ディレクトリ:")
        log_layout.addWidget(log_dir_label)
        
        log_dir_layout = QHBoxLayout()
        
        self.log_file_path_edit = QLineEdit()
        self.log_file_path_edit.setPlaceholderText("(空の場合は標準出力のみ。ファイル名は自動生成されます)")
        log_dir_layout.addWidget(self.log_file_path_edit)
        
        log_dir_browse_btn = QPushButton("参照...")
        log_dir_browse_btn.setMaximumWidth(80)
        log_dir_browse_btn.clicked.connect(self._on_browse_log_dir_clicked)
        log_dir_layout.addWidget(log_dir_browse_btn)
        
        log_layout.addLayout(log_dir_layout)
        
        # 補足説明
        log_file_note = QLabel("※ ログファイル名: pole_facility_YYYYMMDD_HHMMSS.log（日時自動付与）")
        log_file_note.setStyleSheet("color: #666; font-size: 10px;")
        log_layout.addWidget(log_file_note)
        
        layout.addWidget(log_group)
        
        # 将来の拡張用プレースホルダー
        future_group = QGroupBox("その他のデバッグオプション")
        future_layout = QVBoxLayout(future_group)
        
        future_label = QLabel(
            "※ Phase 2で追加予定:\n"
            "- パフォーマンス計測\n"
            "- メモリ使用量モニタリング\n"
            "- SQLクエリログ"
        )
        future_label.setStyleSheet("color: #666; font-size: 11px;")
        future_label.setWordWrap(True)
        future_layout.addWidget(future_label)
        
        layout.addWidget(future_group)
        
        layout.addStretch()
    
    def _load_values(self) -> None:
        """現在の設定値をUIに反映"""
        debug = self.config.get('debug', {})
        
        # ログ出力有効化
        self.enable_logging_checkbox.setChecked(
            debug.get('enable_logging', True)
        )
        
        # ログレベル
        current_level = debug.get('log_level', 'INFO')
        if current_level in self.log_level_radios:
            self.log_level_radios[current_level].setChecked(True)
        
        # ファイル出力
        self.log_to_file_checkbox.setChecked(
            debug.get('log_to_file', False)
        )
        
        # ログディレクトリパス（v1.9.1修正：log_file_path → log_directory）
        self.log_file_path_edit.setText(
            debug.get('log_directory', '')
        )
    
    def _on_browse_log_dir_clicked(self) -> None:
        """ログ保存先ディレクトリ参照ボタンクリック時"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "ログ保存先ディレクトリを選択",
            "",
            QFileDialog.ShowDirsOnly
        )
        
        if directory:
            self.log_file_path_edit.setText(directory)
    
    def get_values(self) -> dict:
        """
        入力値を取得
        
        Returns:
            設定辞書
        """
        # 選択されているログレベルを取得
        log_level = 'INFO'  # デフォルト
        for level, radio in self.log_level_radios.items():
            if radio.isChecked():
                log_level = level
                break
        
        # v1.9.1修正：log_file_path → log_directory
        return {
            "debug": {
                "enable_logging": self.enable_logging_checkbox.isChecked(),
                "log_level": log_level,
                "log_to_file": self.log_to_file_checkbox.isChecked(),
                "log_directory": self.log_file_path_edit.text()
            }
        }
    
    def validate(self) -> bool:
        """
        入力値をバリデーション
        
        Returns:
            True（常に成功）
        
        Note:
            ログディレクトリパスが空でも問題ないため、常にTrueを返す
        """
        return True
