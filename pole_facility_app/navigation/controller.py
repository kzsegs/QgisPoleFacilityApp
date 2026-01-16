"""
Navigation Controller Module

画面遷移とダイアログ管理を担当するコントローラ。
地物選択、属性フォーム表示、各種ダイアログの管理を行う。
"""

import logging
from typing import Optional

from qgis.core import QgsVectorLayer, QgsFeature, QgsProject
from qgis.gui import QgisInterface, QgsMapToolIdentifyFeature
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QDialog

from .form_strategy import IFormStrategy, QgsFormStrategy


# ロガー設定
logger = logging.getLogger(__name__)


class NavigationController(QObject):
    """
    画面遷移制御コントローラ。
    
    地物選択時の属性フォーム表示制御、ダイアログの表示管理、
    画面遷移状態の管理を行う。
    
    Signals:
        feature_selected: 地物が選択された時
        feature_deselected: 地物の選択が解除された時
    """
    
    # シグナル定義
    feature_selected = pyqtSignal(QgsFeature)  # 地物選択時
    feature_deselected = pyqtSignal()  # 地物選択解除時
    
    def __init__(self, iface: QgisInterface, event_bus, config_manager,
                 data_manager):
        """
        NavigationControllerを初期化する。
        
        Args:
            iface: QGISインターフェース
            event_bus: イベントバス
            config_manager: 設定マネージャ
            data_manager: データマネージャ
        """
        super().__init__()
        
        self.iface = iface
        self.event_bus = event_bus
        self.config_manager = config_manager
        self.data_manager = data_manager
        
        # 現在表示中のダイアログ
        self._current_dialog: Optional[QDialog] = None
        
        # 地物選択ツール
        self._map_tool: Optional[QgsMapToolIdentifyFeature] = None
        self._previous_map_tool = None  # 前回のマップツールを保存
        
        # 選択中の地物
        self._selected_feature: Optional[QgsFeature] = None
        
        # フォーム表示戦略（Phase 1ではQGIS標準フォーム）
        self._form_strategy: IFormStrategy = QgsFormStrategy()
        
        logger.info("NavigationController initialized")
    
    def initialize(self) -> None:
        """
        NavigationControllerを初期化する。
        
        地図ツールのセットアップ、シグナル接続を行う。
        """
        # マップツールは後でセットアップ（データがインポートされた後）
        logger.info("NavigationController initialized successfully")
    
    def _setup_map_tool(self) -> None:
        """
        地物選択用のマップツールをセットアップする。
        
        QgsMapToolIdentifyFeatureを作成し、シグナルを接続する。
        """
        canvas = self.iface.mapCanvas()
        
        # 現在アクティブなレイヤを取得
        layer = self.data_manager.get_current_layer()
        
        if layer is None:
            logger.warning("No active layer for map tool setup")
            return
        
        # 地物選択ツールを作成
        self._map_tool = QgsMapToolIdentifyFeature(canvas, layer)
        self._map_tool.setButton(None)  # ツールバーボタンと関連付けない
        
        # 地物選択時のシグナル接続
        self._map_tool.featureIdentified.connect(self._on_feature_identified)
        
        logger.debug("Map tool setup completed")
    
    def activate_select_tool(self) -> None:
        """
        地物選択ツールを有効化する。
        
        現在のマップツールを保存し、選択ツールに切り替える。
        select_tool.activatedイベントを発行する。
        """
        if self._map_tool is None:
            self._setup_map_tool()
        
        if self._map_tool is None:
            logger.error("Failed to setup map tool")
            return
        
        canvas = self.iface.mapCanvas()
        
        # 現在のマップツールを保存
        self._previous_map_tool = canvas.mapTool()
        
        # 選択ツールに切り替え
        canvas.setMapTool(self._map_tool)
        
        # イベント発行
        self.event_bus.emit("select_tool.activated")
        
        logger.info("Select tool activated")
    
    def deactivate_select_tool(self) -> None:
        """
        地物選択ツールを無効化する。
        
        前回のマップツールに戻す。
        select_tool.deactivatedイベントを発行する。
        """
        if self._previous_map_tool is not None:
            canvas = self.iface.mapCanvas()
            canvas.setMapTool(self._previous_map_tool)
            self._previous_map_tool = None
        
        # イベント発行
        self.event_bus.emit("select_tool.deactivated")
        
        logger.info("Select tool deactivated")
    
    def is_select_tool_active(self) -> bool:
        """
        選択ツールがアクティブかどうかを返す。
        
        Returns:
            bool: 選択ツールがアクティブな場合True
        """
        if self._map_tool is None:
            return False
        
        canvas = self.iface.mapCanvas()
        return canvas.mapTool() == self._map_tool
    
    def _on_feature_identified(self, feature: QgsFeature) -> None:
        """
        地物が選択された時の処理。
        
        Args:
            feature: 選択された地物
        
        Note:
            - 選択された地物を保存
            - 属性フォームを表示
            - feature.selectedイベントを発行
        """
        self._selected_feature = feature
        
        # シグナル発行
        self.feature_selected.emit(feature)
        
        # イベント発行
        self.event_bus.emit("feature.selected", {"feature_id": feature.id()})
        
        # 属性フォームを表示
        self.show_attribute_form(feature)
        
        logger.info(f"Feature selected: ID={feature.id()}")
    
    def show_attribute_form(self, feature: QgsFeature) -> None:
        """
        属性フォームを表示する。
        
        Args:
            feature: 表示する地物
        
        Note:
            現在のフォーム表示戦略（Phase 1ではQGIS標準フォーム）を使用
        """
        layer = self.data_manager.get_current_layer()
        
        if layer is None:
            logger.error("No active layer for attribute form")
            return
        
        try:
            # フォーム表示戦略を使用してフォームを表示
            self._form_strategy.show_form(layer, feature, self.iface.mainWindow())
            
            logger.debug(f"Attribute form shown for feature ID={feature.id()}")
            
        except Exception as e:
            logger.exception(f"Failed to show attribute form: {e}")
    
    def close_attribute_form(self) -> None:
        """
        現在表示中の属性フォームを閉じる。
        """
        self._form_strategy.close_form()
        self._selected_feature = None
        self.feature_deselected.emit()
        self.event_bus.emit("feature.deselected")
        
        logger.debug("Attribute form closed")
    
    def close_current_dialog(self) -> None:
        """
        現在表示中のダイアログを閉じる。
        """
        if self._current_dialog is not None:
            self._current_dialog.close()
            self._current_dialog = None
            
            logger.debug("Current dialog closed")
    
    def get_selected_feature(self) -> Optional[QgsFeature]:
        """
        現在選択中の地物を取得する。
        
        Returns:
            Optional[QgsFeature]: 選択中の地物、なければNone
        """
        return self._selected_feature
    
    def cleanup(self) -> None:
        """
        NavigationControllerをクリーンアップする。
        
        Note:
            - マップツールの無効化
            - ダイアログの破棄
            - リソース解放
        """
        # 選択ツールを無効化
        if self.is_select_tool_active():
            self.deactivate_select_tool()
        
        # フォームを閉じる
        self.close_attribute_form()
        
        # ダイアログを閉じる
        self.close_current_dialog()
        
        # マップツールを破棄
        if self._map_tool is not None:
            self._map_tool.deleteLater()
            self._map_tool = None
        
        logger.info("NavigationController cleaned up")
