"""
Navigation Controller Module

画面遷移とダイアログ管理を担当するコントローラ。
地物選択、属性フォーム表示、各種ダイアログの管理を行う。

v1.6改訂:
    - MultiWindowFormManager統合（複数ウィンドウUI対応）
    - show_multi_window_form()メソッド追加
    - Phase 1互換性維持（設定で切り替え可能）
"""

from typing import Optional

from qgis.core import QgsVectorLayer, QgsFeature, QgsProject
from qgis.gui import QgisInterface, QgsMapToolIdentifyFeature
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QDialog

from .form_strategy import IFormStrategy, QgsFormStrategy
from ..forms.multi_window_form_manager import MultiWindowFormManager
from ..utils.logger import Logger


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
        
        # v1.9.1追加: 前回選択した地物（未編集チェック用）
        self._previous_feature_id: Optional[int] = None
        self._previous_was_in_progress: bool = False
        
        # フォーム表示戦略（Phase 1ではQGIS標準フォーム）
        self._form_strategy: IFormStrategy = QgsFormStrategy()
        
        # v1.6: 複数ウィンドウマネージャ
        self._multi_window_manager = MultiWindowFormManager.get_instance()
        self._multi_window_manager.initialize(
            event_bus, config_manager, data_manager
        )
        
        Logger.info("NavigationController initialized")
        Logger.info("NavigationController - MultiWindowFormManager統合完了")
    
    def initialize(self) -> None:
        """
        NavigationControllerを初期化する。
        
        地図ツールのセットアップ、シグナル接続を行う。
        
        v1.9.1追加:
            feature.confirmedイベントを購読（前回地物フラグクリア用）
        """
        # マップツールは後でセットアップ（データがインポートされた後）
        
        # v1.9.1追加: イベント購読
        self.event_bus.subscribe("feature.confirmed", self._on_feature_confirmed)
        
        Logger.info("NavigationController initialized successfully")
    
    def _on_feature_confirmed(self, event_data: dict) -> None:
        """
        地物確定イベントハンドラ（v1.9.1追加）
        
        Args:
            event_data: {"feature_id": int}
        
        処理:
            前回地物フラグをクリアして、次の選択時に未確認に戻さないようにする
        """
        feature_id = event_data.get("feature_id")
        
        if feature_id == self._previous_feature_id:
            # 確定された地物は未確認に戻さない
            self._previous_feature_id = None
            self._previous_was_in_progress = False
            
            Logger.info(
                f"NavigationController - 前回地物フラグクリア: feature_id={feature_id}"
            )
    
    def _setup_map_tool(self) -> None:
        """
        地物選択用のマップツールをセットアップする。
        
        QgsMapToolIdentifyFeatureを作成し、シグナルを接続する。
        """
        canvas = self.iface.mapCanvas()
        
        # 現在アクティブなレイヤを取得
        layer = self.data_manager.get_current_layer()
        
        if layer is None:
            Logger.warning("No active layer for map tool setup")
            return
        
        # 地物選択ツールを作成
        self._map_tool = QgsMapToolIdentifyFeature(canvas, layer)
        self._map_tool.setButton(None)  # ツールバーボタンと関連付けない
        
        # 地物選択時のシグナル接続
        self._map_tool.featureIdentified.connect(self._on_feature_identified)
        
        Logger.debug("Map tool setup completed")
    
    def activate_select_tool(self) -> None:
        """
        地物選択ツールを有効化する。
        
        現在のマップツールを保存し、選択ツールに切り替える。
        select_tool.activatedイベントを発行する。
        """
        if self._map_tool is None:
            self._setup_map_tool()
        
        if self._map_tool is None:
            Logger.error("Failed to setup map tool")
            return
        
        canvas = self.iface.mapCanvas()
        
        # 現在のマップツールを保存
        self._previous_map_tool = canvas.mapTool()
        
        # 選択ツールに切り替え
        canvas.setMapTool(self._map_tool)
        
        # イベント発行
        self.event_bus.emit("select_tool.activated")
        
        Logger.info("Select tool activated")
    
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
        
        Logger.info("Select tool deactivated")
    
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
            - 複数ウィンドウで属性フォームを表示（v1.6）
            - feature.selectedイベントを発行
            - v1.9.1: 未確認の場合は「確認中」に自動更新
            - v1.9.1修正: 前回の確認中地物が未編集なら未確認に戻す
        
        v1.6改訂:
            show_attribute_form() → show_multi_window_form() に変更
        
        v1.9.1改訂:
            ステータス自動更新処理を追加
        """
        layer = self.data_manager.get_current_layer()
        if not layer:
            return
        
        # v1.9.1修正: 前回の「確認中」地物を「未確認」に戻す（未編集の場合）
        if self._previous_feature_id is not None and self._previous_was_in_progress:
            try:
                from ..progress.progress_manager import ProgressManager
                
                progress_mgr = ProgressManager.get_instance()
                
                # 前回地物が「確認中」のままかチェック
                previous_status = progress_mgr.get_status(layer, self._previous_feature_id)
                
                if previous_status == "確認中":
                    # 「未確認」に戻す
                    progress_mgr.set_status(layer, self._previous_feature_id, "未確認")
                    Logger.info(
                        f"NavigationController - 前回地物を未確認に戻す: "
                        f"feature_id={self._previous_feature_id}"
                    )
            
            except Exception as e:
                Logger.error(f"NavigationController - 前回地物状態復元エラー: {str(e)}")
        
        # 現在の選択地物を保存
        self._selected_feature = feature
        
        # シグナル発行
        self.feature_selected.emit(feature)
        
        # イベント発行
        self.event_bus.emit("feature.selected", {"feature_id": feature.id()})
        
        # v1.9.1: ステータスを「確認中」に自動更新
        if layer and feature:
            try:
                from ..progress.progress_manager import ProgressManager
                
                progress_mgr = ProgressManager.get_instance()
                column_name = progress_mgr.get_column_name()
                
                # フィールド存在確認
                field_names = [f.name() for f in layer.fields()]
                
                if column_name in field_names:
                    current_status = feature[column_name]
                    
                    # 未確認の場合のみ「確認中」に更新
                    if current_status == "未確認":
                        progress_mgr.set_status_in_progress(layer, feature.id())
                        
                        # 前回地物として記録
                        self._previous_feature_id = feature.id()
                        self._previous_was_in_progress = True
                        
                        Logger.info(
                            f"NavigationController - ステータス自動更新: "
                            f"feature_id={feature.id()}, 未確認→確認中"
                        )
                    else:
                        # 既に「確認中」または「完了」の場合は記録しない
                        self._previous_feature_id = None
                        self._previous_was_in_progress = False
            
            except Exception as e:
                Logger.error(f"NavigationController - ステータス更新エラー: {str(e)}")
        
        # v1.6: 複数ウィンドウで属性フォームを表示
        self.show_multi_window_form(feature)
        
        Logger.info(f"Feature selected: ID={feature.id()}")
        Logger.info(f"NavigationController - 地物選択: ID={feature.id()}")
    
    def show_attribute_form(self, feature: QgsFeature) -> None:
        """
        属性フォームを表示する（Phase 1互換用）。
        
        Args:
            feature: 表示する地物
        
        Note:
            現在のフォーム表示戦略（Phase 1ではQGIS標準フォーム）を使用
            Phase 2ではshow_multi_window_form()を使用
        """
        layer = self.data_manager.get_current_layer()
        
        if layer is None:
            Logger.error("No active layer for attribute form")
            return
        
        try:
            # フォーム表示戦略を使用してフォームを表示
            self._form_strategy.show_form(layer, feature, self.iface.mainWindow())
            
            Logger.debug(f"Attribute form shown for feature ID={feature.id()}")
            
        except Exception as e:
            Logger.exception(f"Failed to show attribute form: {e}")
    
    def show_multi_window_form(self, feature: QgsFeature) -> None:
        """
        複数ウィンドウで属性フォームを表示する（v1.6新規）。
        
        Args:
            feature: 表示する地物
        
        処理フロー:
            1. レイヤを取得
            2. MultiWindowFormManagerにレイヤと地物をセット
            3. 既に表示中の場合は update_forms()
            4. 未表示の場合は show_forms()
        
        Note:
            Phase 2の複数ウィンドウUI用メソッド
        """
        layer = self.data_manager.get_current_layer()
        
        if layer is None:
            Logger.error("No active layer for multi-window form")
            Logger.warning("NavigationController - レイヤが見つかりません")
            return
        
        try:
            # 既に表示中の場合は更新、未表示の場合は新規表示
            if self._multi_window_manager.is_any_form_visible():
                self._multi_window_manager.update_forms(feature)
                Logger.info(f"NavigationController - 複数ウィンドウ更新: feature_id={feature.id()}")
            else:
                self._multi_window_manager.show_forms(
                    layer, feature, self.iface.mainWindow()
                )
                Logger.info(f"NavigationController - 複数ウィンドウ表示: feature_id={feature.id()}")
            
            Logger.debug(f"Multi-window form shown for feature ID={feature.id()}")
            
        except Exception as e:
            Logger.exception(f"Failed to show multi-window form: {e}")
            Logger.error(f"NavigationController - 複数ウィンドウ表示エラー: {str(e)}")
    
    def close_attribute_form(self) -> None:
        """
        現在表示中の属性フォームを閉じる。
        
        v1.6改訂:
            Phase 1の単一フォームと Phase 2の複数ウィンドウ両方に対応
        """
        # Phase 1: 単一フォーム
        self._form_strategy.close_form()
        
        # Phase 2: 複数ウィンドウ
        if self._multi_window_manager.is_any_form_visible():
            self._multi_window_manager.close_all_forms()
        
        self._selected_feature = None
        self.feature_deselected.emit()
        self.event_bus.emit("feature.deselected")
        
        Logger.debug("Attribute form closed")
        Logger.info("NavigationController - 属性フォームを閉じました")
    
    def close_current_dialog(self) -> None:
        """
        現在表示中のダイアログを閉じる。
        """
        if self._current_dialog is not None:
            self._current_dialog.close()
            self._current_dialog = None
            
            Logger.debug("Current dialog closed")
    
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
            - MultiWindowFormManagerのクリーンアップ（v1.6）
            - リソース解放
        """
        # 選択ツールを無効化
        if self.is_select_tool_active():
            self.deactivate_select_tool()
        
        # フォームを閉じる
        self.close_attribute_form()
        
        # ダイアログを閉じる
        self.close_current_dialog()
        
        # v1.6: 複数ウィンドウマネージャのクリーンアップ
        if self._multi_window_manager:
            self._multi_window_manager.cleanup()
        
        # マップツールを破棄
        if self._map_tool is not None:
            self._map_tool.deleteLater()
            self._map_tool = None
        
        Logger.info("NavigationController cleaned up")
        Logger.info("NavigationController - クリーンアップ完了")
