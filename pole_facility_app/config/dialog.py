"""
設定ダイアログ - 設定画面のメインダイアログ

3タブ構成で設定を管理:
    - 基本設定タブ
    - カラム設定タブ（Phase 2用）
    - デバッグ設定タブ

使用例:
    dialog = SettingsDialogWidget(parent)
    dialog.exec_()
"""

from typing import Optional
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QMessageBox,
    QFileDialog
)
from PyQt5.QtCore import Qt
from qgis.core import QgsMessageLog, Qgis

from .tabs import BasicSettingsTab, ColumnSettingsTab, DebugSettingsTab
from ..config.manager import ConfigManager
from ..main.event_bus import EventBus, EventNames


class SettingsDialogWidget(QDialog):
    """
    設定ダイアログ
    
    Attributes:
        config_manager: ConfigManagerインスタンス
        schema: スキーマ定義辞書
        current_config: 現在の設定辞書（作業用）
        tab_widget: タブウィジェット
        basic_settings_tab: 基本設定タブ
        column_settings_tab: カラム設定タブ
        debug_settings_tab: デバッグ設定タブ
    """
    
    def __init__(self, parent=None):
        """
        コンストラクタ
        
        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self.config_manager = ConfigManager.get_instance()
        self.schema = self.config_manager._load_schema()
        self.current_config = {}
        
        self.setWindowTitle("設定")
        self.setModal(True)
        self.resize(700, 600)
        
        # 先に設定を読み込んでからUIを作成
        self._load_current_config()
        self._create_ui()
        
        QgsMessageLog.logMessage(
            "SettingsDialogWidget初期化完了",
            "PoleFacility",
            Qgis.Info
        )
    
    def _create_ui(self) -> None:
        """UI構築"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # タブウィジェット
        self.tab_widget = QTabWidget(self)
        self._create_tabs()
        layout.addWidget(self.tab_widget)
        
        # ボタン
        button_layout = self._create_buttons()
        layout.addLayout(button_layout)
    
    def _create_tabs(self) -> None:
        """タブ作成"""
        # 基本設定タブ
        self.basic_settings_tab = BasicSettingsTab(
            self.schema,
            self.current_config,
            self
        )
        self.tab_widget.addTab(self.basic_settings_tab, "基本設定")
        
        # カラム設定タブ（枠のみ）
        self.column_settings_tab = ColumnSettingsTab(self)
        self.tab_widget.addTab(self.column_settings_tab, "カラム設定")
        
        # デバッグ設定タブ
        self.debug_settings_tab = DebugSettingsTab(
            self.schema,
            self.current_config,
            self
        )
        self.tab_widget.addTab(self.debug_settings_tab, "デバッグ設定")
    
    def _create_buttons(self) -> QHBoxLayout:
        """ボタン作成"""
        layout = QHBoxLayout()
        
        # インポートボタン
        import_btn = QPushButton("インポート")
        import_btn.clicked.connect(self._on_import_clicked)
        layout.addWidget(import_btn)
        
        # エクスポートボタン
        export_btn = QPushButton("エクスポート")
        export_btn.clicked.connect(self._on_export_clicked)
        layout.addWidget(export_btn)
        
        layout.addStretch()
        
        # OKボタン
        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_ok_clicked)
        layout.addWidget(ok_btn)
        
        # キャンセルボタン
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.clicked.connect(self._on_cancel_clicked)
        layout.addWidget(cancel_btn)
        
        return layout
    
    def _load_current_config(self) -> None:
        """現在の設定をUIに反映"""
        import copy
        self.current_config = copy.deepcopy(self.config_manager.config)
        
        QgsMessageLog.logMessage(
            f"設定を読み込みました: inspection_status={self.current_config.get('inspection_status', {})}",
            "PoleFacility",
            Qgis.Info
        )
    
    def _validate_all_tabs(self) -> bool:
        """
        全タブのバリデーション
        
        Returns:
            True: 全タブ成功
            False: いずれかのタブで失敗
        """
        # 基本設定タブ
        if not self.basic_settings_tab.validate():
            self.tab_widget.setCurrentIndex(0)
            return False
        
        # カラム設定タブ（Phase 2実装時まで常にTrue）
        if not self.column_settings_tab.validate():
            self.tab_widget.setCurrentIndex(1)
            return False
        
        # デバッグ設定タブ
        if not self.debug_settings_tab.validate():
            self.tab_widget.setCurrentIndex(2)
            return False
        
        return True
    
    def _save_current_values(self) -> bool:
        """
        現在のUI値を保存する
        
        Returns:
            True: 保存成功
            False: バリデーション失敗
        """
        # バリデーション
        if not self._validate_all_tabs():
            return False
        
        # 値取得
        basic_values = self.basic_settings_tab.get_values()
        column_values = self.column_settings_tab.get_values()
        debug_values = self.debug_settings_tab.get_values()
        
        # マージ
        merged_config = self.current_config.copy()
        
        # 基本設定
        merged_config['paths'] = basic_values['paths']
        merged_config['constants'] = basic_values['constants']
        merged_config['inspection_status'] = basic_values['inspection_status']
        
        # デバッグ設定
        merged_config['debug'] = debug_values['debug']
        
        # 保存
        try:
            self.config_manager.config = merged_config
            self.config_manager.save_config()
            
            # current_configも更新
            self.current_config = merged_config
            
            # イベント発行
            EventBus.get_instance().emit(EventNames.CONFIG_CHANGED, {})
            
            return True
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "エラー",
                f"設定の保存に失敗しました:\n{str(e)}"
            )
            
            QgsMessageLog.logMessage(
                f"設定保存エラー: {str(e)}",
                "PoleFacility",
                Qgis.Critical
            )
            return False
    
    def _on_ok_clicked(self) -> None:
        """
        OKボタンクリック時
        
        処理フロー:
            1. 全タブのバリデーション
            2. 各タブから値取得
            3. マージして設定保存
            4. EventBus でイベント発行
            5. ダイアログを閉じる
        """
        if self._save_current_values():
            QMessageBox.information(
                self,
                "成功",
                "設定を保存しました。"
            )
            self.accept()
    
    def _on_cancel_clicked(self) -> None:
        """キャンセルボタンクリック時"""
        self.reject()
    
    def _on_import_clicked(self) -> None:
        """
        インポートボタンクリック時
        
        処理フロー:
            1. 現在の設定をエクスポートするか確認
            2. ファイル選択ダイアログ
            3. Shift-JIS でJSON読み込み
            4. バリデーション
            5. UIに反映
        """
        # 現在の設定をエクスポートするか確認
        reply = QMessageBox.question(
            self,
            "確認",
            "インポートする前に、現在の設定をエクスポートしますか？",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Cancel:
            return
        
        if reply == QMessageBox.Yes:
            # 現在の設定をエクスポート
            default_filename = f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "現在の設定をエクスポート",
                default_filename,
                "JSON Files (*.json)"
            )
            
            if filepath:
                try:
                    self.config_manager.export_config(filepath)
                    QMessageBox.information(
                        self,
                        "成功",
                        f"現在の設定をエクスポートしました:\n{filepath}"
                    )
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "エラー",
                        f"エクスポートに失敗しました:\n{str(e)}"
                    )
                    return
        
        # インポート処理
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "設定ファイルを選択",
            "",
            "JSON Files (*.json)"
        )
        
        if not filepath:
            return
        
        try:
            self.config_manager.import_config(filepath)
            self._load_current_config()
            
            # 各タブをリロード
            self.basic_settings_tab._load_values()
            self.debug_settings_tab._load_values()
            
            QMessageBox.information(
                self,
                "成功",
                "設定をインポートしました。"
            )
        
        except ValueError as e:
            QMessageBox.critical(
                self,
                "バリデーションエラー",
                f"設定ファイルの内容が不正です:\n{str(e)}"
            )
            
            QgsMessageLog.logMessage(
                f"設定インポートバリデーションエラー: {str(e)}",
                "PoleFacility",
                Qgis.Critical
            )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "エラー",
                f"設定のインポートに失敗しました:\n{str(e)}"
            )
            
            QgsMessageLog.logMessage(
                f"設定インポートエラー: {str(e)}",
                "PoleFacility",
                Qgis.Critical
            )
    
    def _on_export_clicked(self) -> None:
        """
        エクスポートボタンクリック時
        
        処理フロー:
            1. 現在の値を保存するか確認
            2. ファイル保存ダイアログ
            3. 現在の設定を Shift-JIS でJSON保存
        """
        # 現在の値を保存するか確認
        reply = QMessageBox.question(
            self,
            "確認",
            "エクスポートする前に、現在の設定を保存しますか？",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Cancel:
            return
        
        if reply == QMessageBox.Yes:
            # 現在の値を保存
            if not self._save_current_values():
                # バリデーションエラー時は処理を中断
                return
        
        # デフォルトファイル名
        default_filename = f"config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "設定ファイルを保存",
            default_filename,
            "JSON Files (*.json)"
        )
        
        if not filepath:
            return
        
        try:
            self.config_manager.export_config(filepath)
            
            QMessageBox.information(
                self,
                "成功",
                f"設定をエクスポートしました:\n{filepath}"
            )
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "エラー",
                f"設定のエクスポートに失敗しました:\n{str(e)}"
            )
            
            QgsMessageLog.logMessage(
                f"設定エクスポートエラー: {str(e)}",
                "PoleFacility",
                Qgis.Critical
            )
