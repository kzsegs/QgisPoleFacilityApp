"""
Attribute Form Widget Module

地物属性を表示・編集するメインフォームウィジェット。
3タブ構成（基本情報、現場状況、判定結果）で属性を管理する。
"""

import logging
from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from qgis.core import QgsVectorLayer, QgsFeature

from .basic_info_tab import BasicInfoTab
from .field_status_tab import FieldStatusTab
from .result_tab import ResultTab

# ロガー設定
logger = logging.getLogger(__name__)


class AttributeFormWidget(QDockWidget):
    """
    属性フォームウィジェット。
    
    地物の属性を3タブ構成で表示・編集する。
    - 基本情報タブ: 読み取り専用フィールド
    - 現場状況タブ: 写真と検査項目
    - 判定結果タブ: 判定結果と検査情報
    
    Signals:
        saved: 保存完了時 (QgsFeature)
        cancelled: キャンセル時
        modified: 変更検知時
    """
    
    # シグナル定義
    saved = pyqtSignal(QgsFeature)
    cancelled = pyqtSignal()
    modified = pyqtSignal()
    
    def __init__(self, parent=None, event_bus=None, config_manager=None,
                 data_manager=None):
        """
        AttributeFormWidgetを初期化する。
        
        Args:
            parent: 親ウィジェット
            event_bus: イベントバス
            config_manager: 設定マネージャ
            data_manager: データマネージャ
        """
        super().__init__("設備情報", parent)
        
        self.event_bus = event_bus
        self.config_manager = config_manager
        self.data_manager = data_manager
        
        # 現在の地物
        self.feature: Optional[QgsFeature] = None
        self.layer: Optional[QgsVectorLayer] = None
        
        # 変更フラグ
        self.is_modified_flag: bool = False
        
        # タブウィジェット
        self.tab_widget: QTabWidget = None
        self.basic_info_tab: BasicInfoTab = None
        self.field_status_tab: FieldStatusTab = None
        self.result_tab: ResultTab = None
        
        # ボタン
        self.save_btn: QPushButton = None
        self.cancel_btn: QPushButton = None
        
        self._setup_ui()
        self._connect_signals()
        
        # ドックウィジェット設定
        self.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        
        logger.debug("AttributeFormWidget initialized")
    
    def _setup_ui(self) -> None:
        """
        UIを構築する。
        
        レイアウト:
            - タブウィジェット（上部）
            - ボタン行（下部）
        """
        # メインウィジェット
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        
        # 基本情報タブ
        self.basic_info_tab = BasicInfoTab(self)
        self.tab_widget.addTab(self.basic_info_tab, "基本情報")
        
        # 現場状況タブ
        self.field_status_tab = FieldStatusTab(self, self.config_manager)
        self.tab_widget.addTab(self.field_status_tab, "現場状況")
        
        # 判定結果タブ
        self.result_tab = ResultTab(self)
        self.tab_widget.addTab(self.result_tab, "判定結果")
        
        main_layout.addWidget(self.tab_widget)
        
        # ボタン行
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_btn = QPushButton("保存")
        self.save_btn.setProperty("data-testid", "save-form-btn")
        self.save_btn.setDefault(True)
        
        self.cancel_btn = QPushButton("キャンセル")
        self.cancel_btn.setProperty("data-testid", "cancel-form-btn")
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(button_layout)
        
        main_widget.setLayout(main_layout)
        self.setWidget(main_widget)
    
    def _connect_signals(self) -> None:
        """
        シグナルを接続する。
        """
        # ボタンシグナル
        self.save_btn.clicked.connect(self._on_save_clicked)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        
        # フィールド変更シグナル
        self.field_status_tab.field_changed.connect(self._on_field_changed)
        self.result_tab.field_changed.connect(self._on_field_changed)
        
        # 写真クリックシグナル
        self.field_status_tab.photo_clicked.connect(self._on_photo_clicked)
    
    def set_feature(self, feature: QgsFeature) -> None:
        """
        表示する地物を設定する。
        
        Args:
            feature: 表示する地物
        
        Note:
            - 未保存の変更がある場合は確認ダイアログを表示
            - 各タブにデータを設定
            - 変更フラグをリセット
        """
        # 未保存の変更がある場合は確認
        if self.is_modified_flag:
            reply = self._confirm_discard_changes()
            if not reply:
                return
        
        # 地物とレイヤを保存
        self.feature = QgsFeature(feature)
        self.layer = self.data_manager.get_current_layer()
        
        # 各タブにデータを設定
        self.basic_info_tab.set_data(feature)
        self.field_status_tab.set_data(feature)
        self.result_tab.set_data(feature)
        
        # ウィンドウタイトルを更新
        facility_number = feature.attribute("設備番号") or "不明"
        self.setWindowTitle(f"設備情報 - {facility_number}")
        
        # 変更フラグをリセット
        self.is_modified_flag = False
        self.save_btn.setEnabled(False)
        
        logger.info(f"Feature set: ID={feature.id()}, 設備番号={facility_number}")
    
    def get_feature(self) -> Optional[QgsFeature]:
        """
        現在の地物を取得する。
        
        Returns:
            Optional[QgsFeature]: 現在の地物、未設定の場合None
        """
        return self.feature
    
    def save_changes(self) -> bool:
        """
        変更を保存する。
        
        Returns:
            bool: 保存成功時True
        
        Note:
            1. バリデーション実行
            2. データ収集
            3. 地物属性更新
            4. DataManager経由で保存
            5. 成功時にsavedシグナル発行
        """
        if not self.feature or not self.layer:
            logger.error("No feature or layer to save")
            return False
        
        # バリデーション
        is_valid, error_message = self.validate()
        if not is_valid:
            QMessageBox.warning(
                self,
                "入力エラー",
                f"入力内容にエラーがあります:\n{error_message}"
            )
            return False
        
        # データを収集
        field_values = self._collect_field_values()
        
        # 地物属性を更新
        for field_name, value in field_values.items():
            self.feature.setAttribute(field_name, value)
        
        try:
            # DataManager経由で保存
            success = self.data_manager.update_feature(self.feature)
            
            if success:
                # 成功メッセージ
                QMessageBox.information(
                    self,
                    "保存完了",
                    "変更を保存しました。"
                )
                
                # シグナル発行
                self.saved.emit(self.feature)
                
                # イベント発行
                if self.event_bus:
                    self.event_bus.emit("feature.updated", {
                        "feature_id": self.feature.id()
                    })
                
                # 変更フラグをリセット
                self.is_modified_flag = False
                self.save_btn.setEnabled(False)
                
                # 各タブの初期値を更新
                self.field_status_tab.set_data(self.feature)
                self.result_tab.set_data(self.feature)
                
                logger.info(f"Feature saved: ID={self.feature.id()}")
                return True
            else:
                QMessageBox.warning(
                    self,
                    "保存失敗",
                    "変更の保存に失敗しました。"
                )
                return False
        
        except Exception as e:
            logger.exception(f"Exception during save: {e}")
            QMessageBox.critical(
                self,
                "エラー",
                f"保存中にエラーが発生しました:\n{str(e)}"
            )
            return False
    
    def _collect_field_values(self) -> Dict[str, Any]:
        """
        各タブからフィールド値を収集する。
        
        Returns:
            Dict[str, Any]: フィールド名と値の辞書
        """
        field_values = {}
        
        # 現場状況タブ（検査項目のみ、写真パスは含まない）
        field_values.update(self.field_status_tab.get_data())
        
        # 判定結果タブ
        field_values.update(self.result_tab.get_data())
        
        return field_values
    
    def discard_changes(self) -> None:
        """
        変更を破棄する。
        
        Note:
            元のデータで各タブを再設定
        """
        if self.feature:
            self.basic_info_tab.set_data(self.feature)
            self.field_status_tab.set_data(self.feature)
            self.result_tab.set_data(self.feature)
            
            self.is_modified_flag = False
            self.save_btn.setEnabled(False)
            
            logger.debug("Changes discarded")
    
    def is_form_modified(self) -> bool:
        """
        フォームが変更されたかどうかを返す。
        
        Returns:
            bool: 変更されている場合True
        """
        return self.is_modified_flag
    
    def validate(self) -> tuple[bool, str]:
        """
        フォーム全体をバリデーションする。
        
        Returns:
            tuple[bool, str]: (有効かどうか, エラーメッセージ)
        """
        # 判定結果タブのバリデーション
        is_valid, error_message = self.result_tab.validate()
        if not is_valid:
            return False, error_message
        
        # その他のバリデーションは必要に応じて追加
        
        return True, ""
    
    def _on_field_changed(self, field_name: str, value: Any) -> None:
        """
        フィールド変更時の処理。
        
        Args:
            field_name: 変更されたフィールド名
            value: 新しい値
        """
        self.is_modified_flag = True
        self.save_btn.setEnabled(True)
        self.modified.emit()
        
        logger.debug(f"Field changed: {field_name}")
    
    def _on_save_clicked(self) -> None:
        """
        保存ボタンクリック時の処理。
        """
        self.save_changes()
    
    def _on_cancel_clicked(self) -> None:
        """
        キャンセルボタンクリック時の処理。
        """
        # 未保存の変更がある場合は確認
        if self.is_modified_flag:
            reply = self._confirm_discard_changes()
            if not reply:
                return
            
            # 変更を破棄
            self.discard_changes()
        
        # シグナル発行
        self.cancelled.emit()
        
        # フォームを閉じる
        self.close()
    
    def _confirm_discard_changes(self) -> bool:
        """
        変更破棄の確認ダイアログを表示する。
        
        Returns:
            bool: 破棄する場合True、キャンセルの場合False
        """
        reply = QMessageBox.question(
            self,
            "確認",
            "保存されていない変更があります。破棄しますか?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        return reply == QMessageBox.Yes
    
    def _on_photo_clicked(self, path: str) -> None:
        """
        写真クリック時の処理。
        
        Args:
            path: 写真のフルパス
        
        Note:
            Phase 1では写真エディタ連携は未実装
            Phase 2でPhotoViewerIntegrationと連携予定
        """
        # TODO: Phase 2で写真エディタ連携を実装
        logger.info(f"Photo clicked: {path} (editor integration pending)")
        
        # イベントバスでイベント発行（将来の拡張用）
        if self.event_bus:
            self.event_bus.emit("photo.clicked", {"path": path})
    
    def closeEvent(self, event):
        """
        クローズイベント処理。
        
        Args:
            event: クローズイベント
        """
        # 未保存の変更がある場合は確認
        if self.is_modified_flag:
            reply = self._confirm_discard_changes()
            if not reply:
                event.ignore()
                return
        
        # イベントを受け入れる
        event.accept()
        
        # シグナル発行
        self.cancelled.emit()
        
        logger.debug("Attribute form closed")
