"""
Search Manager Module

検索・フィルタ機能を管理するマネージャ。
検索条件の適用、フィルタ解除、結果ハイライトを制御する。
"""

import logging
from typing import Optional, List

from qgis.core import QgsVectorLayer, QgsExpression, QgsFeature
from qgis.gui import QgisInterface
from PyQt5.QtCore import QObject, Qt

from .filter import SearchFilter
from .panel import SearchPanelWidget

# ロガー設定
logger = logging.getLogger(__name__)


class SearchManager(QObject):
    """
    検索マネージャ。
    
    検索パネルの表示管理、フィルタの適用・解除、
    検索結果のハイライト表示を行う。
    """
    
    def __init__(self, iface: QgisInterface, event_bus, config_manager,
                 data_manager):
        """
        SearchManagerを初期化する。
        
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
        
        # 検索パネル
        self.search_panel: Optional[SearchPanelWidget] = None
        
        # 現在のフィルタ
        self.current_filter: Optional[SearchFilter] = None
        
        # ハイライトされた地物ID
        self.highlighted_features: List[int] = []
        
        logger.info("SearchManager initialized")
    
    def initialize(self) -> None:
        """
        SearchManagerを初期化する。
        
        Note:
            検索パネルを作成し、シグナルを接続
            ※パネルは作成するが表示はしない
        """
        # 検索パネルを作成
        self.search_panel = SearchPanelWidget(
            parent=self.iface.mainWindow(),
            config_manager=self.config_manager
        )
        
        # シグナル接続
        self.search_panel.search_requested.connect(self._on_search_requested)
        self.search_panel.clear_requested.connect(self._on_clear_requested)
        
        logger.info("SearchManager initialized successfully")
    
    def show_search_panel(self) -> None:
        """
        検索パネルを表示する。
        
        Note:
            ドックウィジェットとして右側に表示
        """
        if self.search_panel is None:
            self.initialize()
        
        # ドックウィジェットとして追加（右側に配置）
        self.iface.addDockWidget(
            Qt.RightDockWidgetArea,  # 単一のエリアを指定
            self.search_panel
        )
        
        # 表示
        self.search_panel.show()
        
        logger.info("Search panel shown")
    
    def hide_search_panel(self) -> None:
        """
        検索パネルを非表示にする。
        """
        if self.search_panel is not None:
            self.search_panel.hide()
            logger.info("Search panel hidden")
    
    def apply_filter(self, filter_obj: SearchFilter) -> int:
        """
        フィルタを適用する。
        
        Args:
            filter_obj: 適用するフィルタ
        
        Returns:
            int: フィルタに一致した地物の数
        
        Note:
            - QGISレイヤにフィルタ式を適用
            - 一致した地物をハイライト表示
            - filter.appliedイベントを発行
        """
        if filter_obj.is_empty():
            logger.warning("Cannot apply empty filter")
            return 0
        
        # 現在のレイヤを取得
        layer = self.data_manager.get_current_layer()
        if layer is None:
            logger.error("No active layer to apply filter")
            return 0
        
        # フィルタ式を生成
        expression_str = filter_obj.to_expression()
        
        if not expression_str:
            logger.warning("Empty filter expression")
            return 0
        
        # 式の妥当性を検証
        expression = QgsExpression(expression_str)
        if expression.hasParserError():
            logger.error(f"Invalid filter expression: {expression.parserErrorString()}")
            return 0
        
        # レイヤにフィルタを適用
        self._apply_layer_filter(layer, expression_str)
        
        # 一致した地物を取得
        matching_features = list(layer.getFeatures())
        feature_count = len(matching_features)
        
        # ハイライト表示
        feature_ids = [f.id() for f in matching_features]
        self._highlight_results(layer, feature_ids)
        
        # 現在のフィルタを保存
        self.current_filter = filter_obj
        
        # イベント発行
        self.event_bus.emit("filter.applied", {
            "filter": filter_obj.to_dict(),
            "count": feature_count
        })
        
        logger.info(f"Filter applied: {feature_count} features matched")
        
        return feature_count
    
    def clear_filter(self) -> None:
        """
        フィルタを解除する（v1.9.1改訂 - レイヤー削除済みチェック追加）
        
        Note:
            - レイヤのフィルタ式をクリア
            - ハイライトを解除
            - filter.clearedイベントを発行
        """
        # 現在のレイヤを取得
        layer = self.data_manager.get_current_layer()
        if layer is None:
            logger.warning("No active layer to clear filter")
            return
        
        # レイヤーが削除済みかチェック（v1.9.1追加）
        try:
            if not layer.isValid():
                logger.warning("Layer is no longer valid, skipping filter clear")
                self.current_filter = None
                self.highlighted_features.clear()
                return
        except RuntimeError:
            # C++オブジェクトが削除済み
            logger.warning("Layer has been deleted, skipping filter clear")
            self.current_filter = None
            self.highlighted_features.clear()
            return
        
        # フィルタをクリア
        layer.setSubsetString("")
        
        # ハイライトを解除
        self._clear_highlight()
        
        # 現在のフィルタをクリア
        self.current_filter = None
        
        # キャンバスを更新
        self.iface.mapCanvas().refresh()
        
        # イベント発行
        self.event_bus.emit("filter.cleared")
        
        logger.info("Filter cleared")
    
    def get_current_filter(self) -> Optional[SearchFilter]:
        """
        現在のフィルタを取得する。
        
        Returns:
            Optional[SearchFilter]: 現在のフィルタ、未設定の場合None
        """
        return self.current_filter
    
    def get_filtered_count(self) -> int:
        """
        フィルタされた地物の数を取得する。
        
        Returns:
            int: フィルタされた地物の数
        """
        layer = self.data_manager.get_current_layer()
        if layer is None:
            return 0
        
        return layer.featureCount()
    
    def zoom_to_filtered(self) -> None:
        """
        フィルタされた地物にズームする。
        
        Note:
            全ての表示中地物を含む範囲にズーム
        """
        layer = self.data_manager.get_current_layer()
        if layer is None or layer.featureCount() == 0:
            logger.warning("No features to zoom to")
            return
        
        # レイヤの範囲にズーム
        extent = layer.extent()
        if extent.isEmpty():
            logger.warning("Empty extent")
            return
        
        # キャンバスの範囲を設定
        canvas = self.iface.mapCanvas()
        canvas.setExtent(extent)
        canvas.refresh()
        
        logger.info("Zoomed to filtered features")
    
    def _apply_layer_filter(self, layer: QgsVectorLayer, expression_str: str) -> None:
        """
        レイヤにフィルタ式を適用する。
        
        Args:
            layer: 対象レイヤ
            expression_str: フィルタ式
        """
        # サブセット文字列を設定（QGIS式でフィルタ）
        layer.setSubsetString(expression_str)
        
        # キャンバスを更新
        self.iface.mapCanvas().refresh()
        
        logger.debug(f"Layer filter applied: {expression_str}")
    
    def _highlight_results(self, layer: QgsVectorLayer, feature_ids: List[int]) -> None:
        """
        検索結果をハイライト表示する。
        
        Args:
            layer: 対象レイヤ
            feature_ids: ハイライトする地物のIDリスト
        
        Note:
            Phase 1では地物選択でハイライト実現
        """
        # 既存のハイライトをクリア
        self._clear_highlight()
        
        # 地物を選択状態にする（ハイライト効果）
        layer.selectByIds(feature_ids)
        
        # ハイライトされた地物IDを保存
        self.highlighted_features = feature_ids
        
        logger.debug(f"Highlighted {len(feature_ids)} features")
    
    def _clear_highlight(self) -> None:
        """
        ハイライトを解除する。
        """
        layer = self.data_manager.get_current_layer()
        if layer is None:
            return
        
        # 選択を解除
        layer.removeSelection()
        
        # ハイライトリストをクリア
        self.highlighted_features.clear()
        
        logger.debug("Highlight cleared")
    
    def _on_search_requested(self, filter_obj: SearchFilter) -> None:
        """
        検索要求時の処理。
        
        Args:
            filter_obj: 検索フィルタ
        """
        # フィルタを適用
        count = self.apply_filter(filter_obj)
        
        # 結果件数を検索パネルに表示
        if self.search_panel:
            self.search_panel.set_result_count(count)
        
        # 結果にズーム
        if count > 0:
            self.zoom_to_filtered()
    
    def _on_clear_requested(self) -> None:
        """
        クリア要求時の処理。
        """
        # フィルタを解除
        self.clear_filter()
    
    def cleanup(self) -> None:
        """
        SearchManagerをクリーンアップする。
        
        Note:
            - フィルタを解除
            - 検索パネルを破棄
        """
        # フィルタを解除
        self.clear_filter()
        
        # 検索パネルを破棄
        if self.search_panel is not None:
            self.search_panel.deleteLater()
            self.search_panel = None
        
        logger.info("SearchManager cleaned up")
