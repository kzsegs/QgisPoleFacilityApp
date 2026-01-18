"""
カラム設定タブ - Phase 2用の枠組み

Phase 2で実装予定の機能:
    - CSVカラムの読み込み専用/書き込み可能設定
    - 必須項目/任意項目の設定
    - データ型の設定
    - バリデーションルールの設定
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt


class ColumnSettingsTab(QWidget):
    """
    カラム設定タブ（Phase 2用のプレースホルダー）
    
    Note:
        現在は枠組みのみ実装。
        get_values()は空辞書、validate()は常にTrueを返す。
    """
    
    def __init__(self, parent=None):
        """
        コンストラクタ
        
        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self._create_ui()
    
    def _create_ui(self) -> None:
        """プレースホルダーUI作成"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # プレースホルダーメッセージ
        placeholder_label = QLabel(
            "■ CSVカラム設定\n\n"
            "※ この機能はPhase 2で実装予定です\n\n"
            "[将来、以下の設定が可能になります]\n"
            "- カラムの読み込み専用/書き込み可能設定\n"
            "- 必須項目/任意項目の設定\n"
            "- データ型の設定 (テキスト/数値/リスト/日付)\n"
            "- バリデーションルールの設定"
        )
        placeholder_label.setStyleSheet("color: #666; font-size: 12px;")
        placeholder_label.setWordWrap(True)
        
        layout.addWidget(placeholder_label)
        layout.addStretch()
    
    def get_values(self) -> dict:
        """
        入力値を取得（Phase 2実装時まで空辞書を返す）
        
        Returns:
            空辞書
        """
        return {}
    
    def validate(self) -> bool:
        """
        入力値をバリデーション（Phase 2実装時まで常にTrueを返す）
        
        Returns:
            True（常に成功）
        """
        return True
