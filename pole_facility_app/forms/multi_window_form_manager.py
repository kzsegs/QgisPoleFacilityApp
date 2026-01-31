"""
Multi-Window Form Manager Module

複数ウィンドウで属性フォームを表示・管理するマネージャ。

機能:
    - 基本属性ダイアログ、写真管理ダイアログ、検査項目ダイアログの統合管理
    - 地物選択時の3ウィンドウ同時表示
    - ウィンドウ間のデータ同期
    - イベント連携

v1.6.1改訂:
    - 閉じたウィンドウの再表示バグ修正
    - show_forms()で表示状態チェック追加
    - update_forms()で非表示ダイアログも再表示
"""

import logging
import threading
from typing import Optional, Dict, List

from qgis.core import QgsVectorLayer, QgsFeature, QgsMessageLog, Qgis
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget, QDialog

from .basic_attribute_dialog import BasicAttributeDialog
from .photo_management_dialog import PhotoManagementDialog
from .inspection_form_dialog import InspectionFormDialog


# ロガー設定
logger = logging.getLogger(__name__)


class MultiWindowFormManager(QObject):
    """
    複数ウィンドウフォームマネージャ（Singleton）。
    
    3つのダイアログ（基本属性、写真管理、検査項目）を統合管理する。
    地物選択時に3つのウィンドウを同時表示し、データ同期を行う。
    
    Signals:
        forms_shown: 全フォームが表示された時
        forms_closed: 全フォームが閉じられた時
    """
    
    # シグナル定義
    forms_shown = pyqtSignal(list, int)  # (dialog_types, feature_id)
    forms_closed = pyqtSignal()
    
    # Singletonインスタンス
    _instance: Optional['MultiWindowFormManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """
        Singletonパターン実装（スレッドセーフ）。
        
        Returns:
            MultiWindowFormManager: シングルトンインスタンス
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        MultiWindowFormManagerを初期化する。
        
        Note:
            Singletonパターンのため、初期化は1回のみ実行される。
            実際の初期化はinitialize()メソッドで行う。
        """
        # QObjectの初期化は必ず実行
        super().__init__()
        
        # 既に初期化済みの場合は属性設定をスキップ
        if hasattr(self, '_initialized'):
            return
        
        # 初期化フラグ
        self._initialized = False
        
        # 依存オブジェクト
        self.event_bus = None
        self.config_manager = None
        self.data_manager = None
        
        # 現在のレイヤと地物
        self.current_layer: Optional[QgsVectorLayer] = None
        self.current_feature: Optional[QgsFeature] = None
        
        # ダイアログインスタンス
        self.dialogs: Dict[str, Optional[QDialog]] = {
            'basic': None,
            'photo': None,
            'inspection': None
        }
        
        logger.info("MultiWindowFormManager instance created")
    
    @classmethod
    def get_instance(cls) -> 'MultiWindowFormManager':
        """
        シングルトンインスタンスを取得する。
        
        Returns:
            MultiWindowFormManager: シングルトンインスタンス
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def clear_instance(cls):
        """
        シングルトンインスタンスをクリアする（テスト用）。
        
        Note:
            本番環境では使用しない。テスト時のみ使用。
        """
        if cls._instance is not None:
            cls._instance.cleanup()
            cls._instance = None
            logger.info("MultiWindowFormManager instance cleared")
    
    def initialize(self, event_bus, config_manager, data_manager):
        """
        依存オブジェクトをセットして初期化する。
        
        Args:
            event_bus: イベントバス
            config_manager: 設定マネージャ
            data_manager: データマネージャ
        
        Note:
            NavigationControllerから呼び出される。
            複数回呼び出されても問題ないように設計。
        """
        if self._initialized:
            logger.debug("MultiWindowFormManager already initialized")
            return
        
        self.event_bus = event_bus
        self.config_manager = config_manager
        self.data_manager = data_manager
        
        # イベント購読
        self._subscribe_events()
        
        self._initialized = True
        logger.info("MultiWindowFormManager initialized")
        QgsMessageLog.logMessage(
            "MultiWindowFormManager - 初期化完了",
            "PoleFacility", Qgis.Info
        )
    
    def _subscribe_events(self):
        """
        イベントバスのイベントを購読する。
        
        購読イベント:
            - feature.selected: 地物選択時（show_formsトリガー）
            - feature.deselected: 地物選択解除時（close_all_formsトリガー）
        """
        if self.event_bus is None:
            return
        
        # 地物選択解除時に全ダイアログを閉じる
        self.event_bus.subscribe("feature.deselected", 
                                 lambda data: self.close_all_forms())
        
        logger.debug("Event subscriptions completed")
    
    def show_forms(self, layer: QgsVectorLayer, feature: QgsFeature,
                   parent: Optional[QWidget] = None):
        """
        3つのダイアログを表示する。
        
        Args:
            layer: 対象レイヤ
            feature: 表示する地物
            parent: 親ウィジェット（通常はQGISメインウィンドウ）
        
        処理フロー:
            1. レイヤと地物を保存
            2. ダイアログが未作成なら作成
            3. 各ダイアログにレイヤをセット
            4. 各ダイアログに地物をセット
            5. 全ダイアログを表示
            6. forms.shownイベント発行
        
        v1.6.1改訂:
            - 既存ダイアログが閉じている場合も再表示するように修正
            - 表示状態チェックを is_any_form_visible() で行う
        """
        # レイヤと地物を保存
        self.current_layer = layer
        self.current_feature = feature
        
        # ダイアログが未作成なら作成
        self._create_dialogs_if_needed(parent)
        
        # 各ダイアログにレイヤをセット
        self._set_layer_to_dialogs(layer)
        
        # 各ダイアログに地物をセット
        self._set_feature_to_dialogs(feature)
        
        # 全ダイアログを表示（閉じているダイアログも再表示）
        for dialog_type, dialog in self.dialogs.items():
            if dialog is not None and not dialog.isVisible():
                dialog.show()
                logger.debug(f"{dialog_type} dialog shown")
        
        # ウィンドウ位置・サイズを復元（初回表示時のみ）
        self.restore_window_positions()
        
        # イベント発行
        dialog_types = list(self.dialogs.keys())
        self.forms_shown.emit(dialog_types, feature.id())
        self.event_bus.emit("forms.shown", {
            "dialog_types": dialog_types,
            "feature_id": feature.id()
        })
        
        logger.info(f"All forms shown for feature ID={feature.id()}")
        QgsMessageLog.logMessage(
            f"MultiWindowFormManager - 全ダイアログ表示: feature_id={feature.id()}",
            "PoleFacility", Qgis.Info
        )
    
    def update_forms(self, feature: QgsFeature):
        """
        既存のダイアログを別の地物データで更新する。
        
        Args:
            feature: 新しい地物
        
        処理フロー:
            1. 地物を保存
            2. 各ダイアログに新しい地物をセット
            3. 閉じているダイアログは再表示
            4. feature.changedイベント発行
        
        v1.6.1改訂:
            - 閉じているダイアログも再表示するように修正
        """
        self.current_feature = feature
        
        # 各ダイアログを更新
        self._set_feature_to_dialogs(feature)
        
        # 閉じているダイアログは再表示
        for dialog_type, dialog in self.dialogs.items():
            if dialog is not None and not dialog.isVisible():
                dialog.show()
                logger.debug(f"{dialog_type} dialog re-shown")
        
        # イベント発行
        self.event_bus.emit("feature.changed", {"feature_id": feature.id()})
        
        logger.info(f"All forms updated for feature ID={feature.id()}")
        QgsMessageLog.logMessage(
            f"MultiWindowFormManager - 全ダイアログ更新: feature_id={feature.id()}",
            "PoleFacility", Qgis.Info
        )
    
    def close_all_forms(self):
        """
        全てのダイアログを閉じる。
        
        Note:
            ダイアログオブジェクト自体は破棄せず、非表示にするのみ。
            次回の show_forms() で再利用される。
        """
        closed_count = 0
        
        for dialog_type, dialog in self.dialogs.items():
            if dialog is not None and dialog.isVisible():
                dialog.close()
                closed_count += 1
                logger.debug(f"{dialog_type} dialog closed")
        
        if closed_count > 0:
            # イベント発行
            self.forms_closed.emit()
            self.event_bus.emit("forms.closed")
            
            logger.info(f"{closed_count} forms closed")
            QgsMessageLog.logMessage(
                f"MultiWindowFormManager - {closed_count}個のダイアログを閉じました",
                "PoleFacility", Qgis.Info
            )
    
    def close_form(self, form_type: str):
        """
        特定のダイアログを閉じる。
        
        Args:
            form_type: ダイアログタイプ ('basic', 'photo', 'inspection')
        """
        if form_type not in self.dialogs:
            logger.warning(f"Unknown form type: {form_type}")
            return
        
        dialog = self.dialogs[form_type]
        if dialog is not None and dialog.isVisible():
            dialog.close()
            logger.debug(f"{form_type} dialog closed")
    
    def is_any_form_visible(self) -> bool:
        """
        いずれかのダイアログが表示中かどうかを返す。
        
        Returns:
            bool: いずれかのダイアログが表示中の場合True
        """
        return any(
            dialog is not None and dialog.isVisible()
            for dialog in self.dialogs.values()
        )
    
    def get_visible_forms(self) -> List[str]:
        """
        現在表示中のダイアログのタイプリストを返す。
        
        Returns:
            List[str]: 表示中のダイアログタイプのリスト
        """
        return [
            dialog_type
            for dialog_type, dialog in self.dialogs.items()
            if dialog is not None and dialog.isVisible()
        ]
    
    def _create_dialogs_if_needed(self, parent: Optional[QWidget] = None):
        """
        ダイアログが未作成の場合に作成する。
        
        Args:
            parent: 親ウィジェット
        
        Note:
            既に作成済みのダイアログは再利用される。
        """
        try:
            # 基本属性ダイアログ
            if self.dialogs['basic'] is None:
                self.dialogs['basic'] = BasicAttributeDialog(
                    self.config_manager,
                    self.data_manager,
                    parent
                )
                self.dialogs['basic'].closed.connect(
                    lambda: self._on_dialog_closed('basic')
                )
                logger.debug("BasicAttributeDialog created")
            
            # 写真管理ダイアログ
            if self.dialogs['photo'] is None:
                self.dialogs['photo'] = PhotoManagementDialog(
                    self.config_manager,
                    self.data_manager,
                    parent
                )
                self.dialogs['photo'].closed.connect(
                    lambda: self._on_dialog_closed('photo')
                )
                self.dialogs['photo'].photo_saved.connect(
                    self._on_photo_saved
                )
                logger.debug("PhotoManagementDialog created")
            
            # 検査項目ダイアログ
            if self.dialogs['inspection'] is None:
                self.dialogs['inspection'] = InspectionFormDialog(
                    self.config_manager,
                    self.data_manager,
                    parent
                )
                self.dialogs['inspection'].closed.connect(
                    lambda: self._on_dialog_closed('inspection')
                )
                self.dialogs['inspection'].data_saved.connect(
                    self._on_data_saved
                )
                logger.debug("InspectionFormDialog created")
        
        except Exception as e:
            logger.exception(f"Failed to create dialogs: {e}")
            QgsMessageLog.logMessage(
                f"MultiWindowFormManager - ダイアログ作成エラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
    
    def _set_layer_to_dialogs(self, layer: QgsVectorLayer):
        """
        各ダイアログにレイヤをセットする。
        
        Args:
            layer: 対象レイヤ
        
        Note:
            写真管理と検査項目ダイアログは保存処理でレイヤが必要。
        """
        if self.dialogs['photo'] is not None:
            self.dialogs['photo'].set_layer(layer)
        
        if self.dialogs['inspection'] is not None:
            self.dialogs['inspection'].set_layer(layer)
        
        logger.debug("Layer set to dialogs")
    
    def _set_feature_to_dialogs(self, feature: QgsFeature):
        """
        各ダイアログに地物をセットする。
        
        Args:
            feature: 対象地物
        """
        if self.dialogs['basic'] is not None:
            self.dialogs['basic'].set_feature(feature)
        
        if self.dialogs['photo'] is not None:
            self.dialogs['photo'].set_feature(feature)
        
        if self.dialogs['inspection'] is not None:
            self.dialogs['inspection'].set_feature(feature)
        
        logger.debug(f"Feature set to dialogs: ID={feature.id()}")
    
    def _on_dialog_closed(self, dialog_type: str):
        """
        ダイアログが閉じられた時の処理。
        
        Args:
            dialog_type: 閉じられたダイアログのタイプ
        
        Note:
            v1.6.1: ダイアログオブジェクトは破棄せず再利用するため、
            self.dialogs[dialog_type] = None は行わない。
        """
        # イベント発行
        self.event_bus.emit("dialog.closed", {"dialog_type": dialog_type})
        
        logger.debug(f"{dialog_type} dialog closed event handled")
        
        # 全てのダイアログが閉じたかチェック
        if not self.is_any_form_visible():
            self.forms_closed.emit()
            self.event_bus.emit("forms.closed")
            logger.info("All forms closed")
    
    def _on_photo_saved(self, field_name: str, relative_path: str):
        """
        写真が保存された時の処理。
        
        Args:
            field_name: 保存されたフィールド名
            relative_path: 保存された写真の相対パス
        """
        if self.current_feature is None:
            return
        
        # イベント発行
        self.event_bus.emit("photo.saved", {
            "feature_id": self.current_feature.id(),
            "field_name": field_name,
            "path": relative_path
        })
        
        logger.info(f"Photo saved: field={field_name}, path={relative_path}")
    
    def _on_data_saved(self):
        """
        検査項目データが保存された時の処理。
        """
        if self.current_feature is None:
            return
        
        # イベント発行
        self.event_bus.emit("data.modified", {
            "feature_id": self.current_feature.id(),
            "source": "inspection_form"
        })
        
        logger.info("Inspection data saved")
    
    def cleanup(self):
        """
        リソースをクリーンアップする。
        
        Note:
            - ウィンドウ位置・サイズを保存
            - 全ダイアログを閉じる
            - ダイアログオブジェクトを破棄
            - 参照をクリア
        """
        # ウィンドウ位置・サイズを保存
        self.save_window_positions()
        
        # 全ダイアログを閉じる
        self.close_all_forms()
        
        # ダイアログを破棄
        for dialog_type, dialog in self.dialogs.items():
            if dialog is not None:
                dialog.deleteLater()
                logger.debug(f"{dialog_type} dialog deleted")
        
        # 参照をクリア
        self.dialogs = {
            'basic': None,
            'photo': None,
            'inspection': None
        }
        
        self.current_layer = None
        self.current_feature = None
        
        logger.info("MultiWindowFormManager cleaned up")
        QgsMessageLog.logMessage(
            "MultiWindowFormManager - クリーンアップ完了",
            "PoleFacility", Qgis.Info
        )
    
    def save_window_positions(self):
        """
        全ダイアログのウィンドウ位置・サイズを保存する（v1.9.1改訂）。
        
        保存内容:
            - スクリーン番号（マルチディスプレイ対応）
            - X,Y座標（グローバル座標）
            - 幅、高さ
        
        保存先:
            config.json の window_positions セクション
            - basic: 基本属性ダイアログ
            - photo: 写真管理ダイアログ
            - inspection: 検査項目ダイアログ
        
        Note:
            - cleanup() から自動的に呼び出される
            - ダイアログが存在しない場合はスキップ
            - マルチディスプレイ環境に対応
        
        v1.9.1改訂:
            - geometry()ではなくpos()+size()で座標取得（グローバル座標保証）
        """
        if self.config_manager is None:
            logger.warning("ConfigManager is not initialized")
            return
        
        from PyQt5.QtWidgets import QApplication
        
        for dialog_type, dialog in self.dialogs.items():
            if dialog is not None:
                # 現在のスクリーンを取得
                screen = QApplication.desktop().screenNumber(dialog)
                
                # v1.9.1修正: pos() + size() でグローバル座標取得
                pos = dialog.pos()
                size = dialog.size()
                x = pos.x()
                y = pos.y()
                width = size.width()
                height = size.height()
                
                # config.jsonに保存
                self.config_manager.save_window_position(
                    dialog_type, screen, x, y, width, height
                )
                
                logger.debug(f"{dialog_type} dialog position saved: screen={screen} x={x} y={y} w={width} h={height}")
                QgsMessageLog.logMessage(
                    f"MultiWindowFormManager - {dialog_type}ダイアログの位置を保存: screen={screen}",
                    "PoleFacility", Qgis.Info
                )
        
        logger.info("Window positions saved to config.json")
    
    def restore_window_positions(self):
        """
        全ダイアログのウィンドウ位置・サイズを復元する（v1.9.1改訂）。
        
        復元内容:
            - スクリーン番号（マルチディスプレイ対応）
            - X,Y座標（グローバル座標）
            - 幅、高さ
        
        復元元:
            config.json の window_positions セクション
        
        Note:
            - show_forms() から自動的に呼び出される
            - 保存データがない場合はデフォルト位置を使用
            - ダイアログが存在しない場合はスキップ
            - 画面外チェック機能付き（マルチディスプレイ対応）
        
        v1.9.1改訂:
            - setGeometry()ではなくmove()+resize()で位置設定
            - 全ディスプレイ範囲での画面内チェック強化
        """
        if self.config_manager is None:
            logger.warning("ConfigManager is not initialized")
            return
        
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QRect
        
        desktop = QApplication.desktop()
        
        for dialog_type, dialog in self.dialogs.items():
            if dialog is not None:
                # config.jsonから位置情報を取得
                position = self.config_manager.get_window_position(dialog_type)
                
                if position:
                    screen = position.get('screen', 0)
                    x = position.get('x', 100)
                    y = position.get('y', 100)
                    width = position.get('width', 400)
                    height = position.get('height', 300)
                    
                    # スクリーン数チェック
                    if screen >= desktop.screenCount():
                        logger.warning(f"{dialog_type}: screen {screen} not found, using screen 0")
                        screen = 0
                    
                    # v1.9.1追加: 画面内チェック強化
                    if not self._is_position_visible(x, y, width, height, desktop):
                        # 画面外の場合はプライマリディスプレイ中央に配置
                        logger.warning(f"{dialog_type}: window outside screen, centering")
                        primary = desktop.screenGeometry(0)
                        x = primary.x() + (primary.width() - width) // 2
                        y = primary.y() + (primary.height() - height) // 2
                    
                    # v1.9.1修正: move() + resize() で位置設定
                    dialog.move(x, y)
                    dialog.resize(width, height)
                    
                    # コンフィグインポート時に位置を反映させるため表示
                    dialog.show()
                    
                    logger.debug(f"{dialog_type} dialog position restored: screen={screen} x={x} y={y} w={width} h={height}")
                    QgsMessageLog.logMessage(
                        f"MultiWindowFormManager - {dialog_type}ダイアログの位置を復元: screen={screen}",
                        "PoleFacility", Qgis.Info
                    )
                else:
                    logger.debug(f"{dialog_type} dialog has no saved position")
        
        logger.info("Window positions restored from config.json")
    
    def _is_position_visible(self, x: int, y: int, width: int, height: int, 
                            desktop) -> bool:
        """
        ウィンドウ位置が画面内に表示可能かチェック（v1.9.1追加）。
        
        Args:
            x: ウィンドウのX座標
            y: ウィンドウのY座標
            width: ウィンドウの幅
            height: ウィンドウの高さ
            desktop: QDesktopWidget
        
        Returns:
            bool: いずれかの画面と交差していればTrue
        
        Note:
            全ディスプレイの範囲をチェックし、いずれかと交差していれば表示可能と判定
        """
        from PyQt5.QtCore import QRect
        
        window_rect = QRect(x, y, width, height)
        
        # 全ディスプレイをチェック
        for i in range(desktop.screenCount()):
            if desktop.screenGeometry(i).intersects(window_rect):
                return True
        
        return False
    
    def close_all_dialogs(self):
        """
        全ダイアログを閉じる（v1.9.1追加）。
        
        Note:
            - UIController._do_exit()から呼び出される
            - プラグイン終了時に使用
            - エラーが発生してもスキップして続行
        """
        for dialog_type, dialog in self.dialogs.items():
            if dialog is not None:
                try:
                    dialog.close()
                    logger.debug(f"{dialog_type} dialog closed")
                except Exception as e:
                    logger.warning(f"Failed to close {dialog_type} dialog: {e}")
        
        self.dialogs.clear()
        logger.info("All dialogs closed")
