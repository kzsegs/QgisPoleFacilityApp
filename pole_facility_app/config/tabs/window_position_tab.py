"""
ウィンドウ位置設定タブ - ウィンドウ位置のエクスポート/インポート/リセット

UI構成:
    ■ 現在のウィンドウ位置情報表示
      - 基本属性ダイアログ
      - 写真管理ダイアログ
      - 検査項目ダイアログ
    ■ 操作ボタン
      - エクスポート: config.jsonに書き出し
      - インポート: config.jsonから読み込み
      - リセット: デフォルト位置に戻す
"""

from typing import Dict, Any
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLabel, QPushButton, QMessageBox,
    QFileDialog
)
from PyQt5.QtCore import Qt
from qgis.core import QgsMessageLog, Qgis
import json


class WindowPositionTab(QWidget):
    """
    ウィンドウ位置設定タブ
    
    Attributes:
        config_manager: ConfigManagerインスタンス
        position_labels: 位置情報表示ラベル辞書
    """
    
    def __init__(self, config_manager, parent=None):
        """
        コンストラクタ
        
        Args:
            config_manager: ConfigManagerインスタンス
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.position_labels: Dict[str, QLabel] = {}
        
        self._create_ui()
        self._load_positions()
    
    def _create_ui(self) -> None:
        """UI構築"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # 説明ラベル
        description = QLabel(
            "各ウィンドウの位置・サイズ設定をconfig.jsonで管理します。\n"
            "マルチディスプレイ環境に対応（スクリーン番号を保存）。"
        )
        description.setStyleSheet("color: #666; font-size: 11px;")
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # 現在の位置情報グループ
        positions_group = self._create_positions_group()
        layout.addWidget(positions_group)
        
        # 操作ボタングループ
        actions_group = self._create_actions_group()
        layout.addWidget(actions_group)
        
        layout.addStretch()
    
    def _create_positions_group(self) -> QGroupBox:
        """現在の位置情報グループ作成"""
        group = QGroupBox("現在のウィンドウ位置")
        layout = QFormLayout(group)
        layout.setSpacing(10)
        
        # 各ダイアログの位置情報
        for dialog_type, label_text in [
            ('basic', '基本属性ダイアログ:'),
            ('photo', '写真管理ダイアログ:'),
            ('inspection', '検査項目ダイアログ:')
        ]:
            label = QLabel("未設定")
            label.setStyleSheet("color: #333; font-family: monospace;")
            layout.addRow(label_text, label)
            self.position_labels[dialog_type] = label
        
        return group
    
    def _create_actions_group(self) -> QGroupBox:
        """操作ボタングループ作成"""
        group = QGroupBox("操作")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        
        # エクスポートボタン
        export_btn = QPushButton("📤 現在の位置をエクスポート")
        export_btn.setToolTip("現在のウィンドウ位置設定をJSONファイルに保存")
        export_btn.clicked.connect(self._on_export_clicked)
        layout.addWidget(export_btn)
        
        # インポートボタン
        import_btn = QPushButton("📥 位置設定をインポート")
        import_btn.setToolTip("JSONファイルからウィンドウ位置設定を読み込み")
        import_btn.clicked.connect(self._on_import_clicked)
        layout.addWidget(import_btn)
        
        # リセットボタン
        reset_btn = QPushButton("🔄 デフォルト位置にリセット")
        reset_btn.setToolTip("全ウィンドウ位置をデフォルトに戻す")
        reset_btn.setStyleSheet("color: #d9534f;")
        reset_btn.clicked.connect(self._on_reset_clicked)
        layout.addWidget(reset_btn)
        
        # 更新ボタン
        refresh_btn = QPushButton("🔃 表示を更新")
        refresh_btn.setToolTip("config.jsonから最新の位置情報を読み込む")
        refresh_btn.clicked.connect(self._load_positions)
        layout.addWidget(refresh_btn)
        
        return group
    
    def _load_positions(self) -> None:
        """現在の位置情報を表示（v1.9.1改訂）"""
        # v1.9.1追加: 表示前に最新の設定を読み込む
        self.config_manager.reload()
        
        for dialog_type in ['basic', 'photo', 'inspection']:
            position = self.config_manager.get_window_position(dialog_type)
            
            if position:
                text = (
                    f"Screen: {position.get('screen', 0)}, "
                    f"X: {position.get('x', 0)}, "
                    f"Y: {position.get('y', 0)}, "
                    f"W: {position.get('width', 0)}, "
                    f"H: {position.get('height', 0)}"
                )
                self.position_labels[dialog_type].setText(text)
            else:
                self.position_labels[dialog_type].setText("未設定")
        
        QgsMessageLog.logMessage(
            "WindowPositionTab - 位置情報を更新しました",
            "PoleFacility", Qgis.Info
        )
    
    def _on_export_clicked(self) -> None:
        """エクスポートボタンクリック"""
        from datetime import datetime
        
        # デフォルトファイル名
        default_filename = f"window_positions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "ウィンドウ位置設定をエクスポート",
            default_filename,
            "JSON Files (*.json)"
        )
        
        if not filepath:
            return
        
        try:
            # window_positionsセクションのみを抽出
            window_positions = self.config_manager.config.get('window_positions', {})
            
            # JSONファイルに書き出し（UTF-8、整形あり）
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(
                    {'window_positions': window_positions},
                    f,
                    indent=2,
                    ensure_ascii=False
                )
            
            QMessageBox.information(
                self,
                "成功",
                f"ウィンドウ位置設定をエクスポートしました:\n{filepath}"
            )
            
            QgsMessageLog.logMessage(
                f"WindowPositionTab - エクスポート成功: {filepath}",
                "PoleFacility", Qgis.Info
            )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "エラー",
                f"エクスポートに失敗しました:\n{str(e)}"
            )
            
            QgsMessageLog.logMessage(
                f"WindowPositionTab - エクスポートエラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
    
    def _on_import_clicked(self) -> None:
        """インポートボタンクリック"""
        # 確認ダイアログ
        reply = QMessageBox.question(
            self,
            "確認",
            "現在のウィンドウ位置設定を上書きしますか？\n"
            "（事前にエクスポートでバックアップを推奨）",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "ウィンドウ位置設定ファイルを選択",
            "",
            "JSON Files (*.json)"
        )
        
        if not filepath:
            return
        
        try:
            # JSONファイル読み込み（UTF-8）
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # バリデーション
            if 'window_positions' not in data:
                raise ValueError("window_positionsセクションが見つかりません")
            
            window_positions = data['window_positions']
            
            # 各ダイアログの設定をチェック
            for dialog_type in ['basic', 'photo', 'inspection']:
                if dialog_type not in window_positions:
                    raise ValueError(f"{dialog_type}の設定が見つかりません")
                
                pos = window_positions[dialog_type]
                required_keys = ['screen', 'x', 'y', 'width', 'height']
                for key in required_keys:
                    if key not in pos:
                        raise ValueError(f"{dialog_type}.{key}が見つかりません")
            
            # config.jsonに反映
            self.config_manager.config['window_positions'] = window_positions
            self.config_manager.save_config()
            
            # 表示を更新
            self._load_positions()
            
            QMessageBox.information(
                self,
                "成功",
                "ウィンドウ位置設定をインポートしました。\n"
                "次回ウィンドウ表示時から反映されます。"
            )
            
            QgsMessageLog.logMessage(
                f"WindowPositionTab - インポート成功: {filepath}",
                "PoleFacility", Qgis.Info
            )
        
        except ValueError as e:
            QMessageBox.critical(
                self,
                "バリデーションエラー",
                f"設定ファイルの内容が不正です:\n{str(e)}"
            )
            
            QgsMessageLog.logMessage(
                f"WindowPositionTab - バリデーションエラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "エラー",
                f"インポートに失敗しました:\n{str(e)}"
            )
            
            QgsMessageLog.logMessage(
                f"WindowPositionTab - インポートエラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
    
    def _on_reset_clicked(self) -> None:
        """リセットボタンクリック"""
        reply = QMessageBox.question(
            self,
            "確認",
            "全ウィンドウ位置をデフォルトに戻しますか？\n"
            "（この操作は元に戻せません）",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            self.config_manager.reset_window_positions()
            self._load_positions()
            
            QMessageBox.information(
                self,
                "成功",
                "ウィンドウ位置をデフォルトにリセットしました。\n"
                "次回ウィンドウ表示時から反映されます。"
            )
            
            QgsMessageLog.logMessage(
                "WindowPositionTab - ウィンドウ位置リセット完了",
                "PoleFacility", Qgis.Info
            )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "エラー",
                f"リセットに失敗しました:\n{str(e)}"
            )
            
            QgsMessageLog.logMessage(
                f"WindowPositionTab - リセットエラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
    
    def get_values(self) -> dict:
        """
        入力値を取得（このタブでは不要）
        
        Returns:
            空辞書
        """
        return {}
    
    def validate(self) -> bool:
        """
        入力値をバリデーション（このタブでは常にTrue）
        
        Returns:
            True（常に成功）
        """
        return True
