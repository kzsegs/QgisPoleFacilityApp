"""
Progress Manager Module

作業状況（進捗）の管理とスタイル制御を担当するマネージャ。

v1.9.1新規作成:
    - 作業状況カラムの管理
    - ステータス管理（未確認・確認中・完了）
    - カテゴリ分類スタイルの適用
    - QgsMarkerSymbol.createSimple() 使用（marker_shapeは将来フェーズ）
"""

from typing import Optional, List, Dict

from qgis.core import (
    QgsVectorLayer, QgsField,
    QgsCategorizedSymbolRenderer, QgsMarkerSymbol,
    QgsRendererCategory, QgsMessageLog, Qgis
)
from PyQt5.QtCore import QVariant


class ProgressManager:
    """
    進捗管理クラス（Singleton）
    
    作業状況カラムの管理、ステータスの設定・取得、
    レイヤースタイルの適用を行う。
    """
    
    _instance: Optional['ProgressManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """内部初期化"""
        self._config_manager = None
        self._column_name = "作業状況"
        self._statuses = []
        self._default_status = "未確認"
    
    @classmethod
    def get_instance(cls) -> 'ProgressManager':
        """
        ProgressManagerのインスタンスを取得する。
        
        Returns:
            ProgressManager: シングルトンインスタンス
        """
        if cls._instance is None:
            cls()
        return cls._instance
    
    @classmethod
    def clear_instance(cls):
        """インスタンスをクリア（テスト用）"""
        cls._instance = None
    
    def configure(self, config_manager) -> None:
        """
        設定を読み込んで初期化する。
        
        Args:
            config_manager: ConfigManagerインスタンス
        
        Note:
            Plugin.initGui()から呼び出される
        """
        self._config_manager = config_manager
        progress_config = config_manager.get("progress_status", {})
        
        self._column_name = progress_config.get("column_name", "作業状況")
        self._statuses = progress_config.get("statuses", self._get_default_statuses())
        self._default_status = progress_config.get("default_status", "未確認")
        
        QgsMessageLog.logMessage(
            f"ProgressManager configured: column={self._column_name}, "
            f"statuses={len(self._statuses)}",
            "PoleFacility", Qgis.Info
        )
    
    def _get_default_statuses(self) -> List[Dict]:
        """
        デフォルトステータス定義を取得する。
        
        Returns:
            List[Dict]: デフォルトステータスリスト
        
        Note:
            marker_shapeはPhase 3-Bスコープ外（将来フェーズで対応）
        """
        return [
            {"name": "未確認", "color": "#808080", "marker_size": 5},
            {"name": "確認中", "color": "#FFD700", "marker_size": 5},
            {"name": "完了", "color": "#32CD32", "marker_size": 5}
        ]
    
    def ensure_status_column(self, layer: QgsVectorLayer) -> bool:
        """
        作業状況カラムが存在することを確認し、なければ追加する。
        
        Args:
            layer: 対象レイヤー
        
        Returns:
            bool: カラム存在確認・追加が成功した場合True
        
        処理フロー:
            1. レイヤーの有効性チェック
            2. 既存フィールド名リスト取得
            3. 作業状況カラムの存在確認
            4. 存在しない場合は追加＋デフォルト値設定
        """
        if layer is None or not layer.isValid():
            return False
        
        # フィールド名リスト取得
        field_names = [f.name() for f in layer.fields()]
        
        if self._column_name in field_names:
            QgsMessageLog.logMessage(
                f"作業状況カラムは既に存在: {self._column_name}",
                "PoleFacility", Qgis.Info
            )
            return True
        
        # カラム追加
        layer.startEditing()
        layer.addAttribute(QgsField(self._column_name, QVariant.String))
        
        # 全地物にデフォルト値を設定
        field_index = layer.fields().indexFromName(self._column_name)
        for feature in layer.getFeatures():
            layer.changeAttributeValue(
                feature.id(), field_index, self._default_status
            )
        
        layer.commitChanges()
        
        QgsMessageLog.logMessage(
            f"作業状況カラムを追加: {self._column_name}",
            "PoleFacility", Qgis.Info
        )
        
        return True
    
    def get_status(self, layer: QgsVectorLayer, feature_id: int) -> Optional[str]:
        """
        地物のステータスを取得する。
        
        Args:
            layer: 対象レイヤー
            feature_id: 地物ID
        
        Returns:
            Optional[str]: ステータス名、取得できない場合None
        """
        if layer is None or not layer.isValid():
            return None
        
        feature = layer.getFeature(feature_id)
        if not feature.isValid():
            return None
        
        field_index = layer.fields().indexFromName(self._column_name)
        if field_index < 0:
            return None
        
        return feature[field_index]
    
    def set_status(self, layer: QgsVectorLayer, feature_id: int, status: str) -> bool:
        """
        地物のステータスを更新する。
        
        Args:
            layer: 対象レイヤー
            feature_id: 地物ID
            status: 設定するステータス名
        
        Returns:
            bool: 更新が成功した場合True
        
        処理フロー:
            1. レイヤー有効性チェック
            2. フィールドインデックス取得
            3. 属性値を更新
            4. レイヤースタイルを再適用
        """
        if layer is None or not layer.isValid():
            return False
        
        field_index = layer.fields().indexFromName(self._column_name)
        if field_index < 0:
            QgsMessageLog.logMessage(
                f"作業状況カラムが見つかりません: {self._column_name}",
                "PoleFacility", Qgis.Warning
            )
            return False
        
        # 属性値を更新
        layer.startEditing()
        layer.changeAttributeValue(feature_id, field_index, status)
        layer.commitChanges()
        
        # スタイルを再適用
        self.apply_style(layer)
        
        QgsMessageLog.logMessage(
            f"ステータス更新: feature_id={feature_id}, status={status}",
            "PoleFacility", Qgis.Info
        )
        
        return True
    
    def set_status_in_progress(self, layer: QgsVectorLayer, feature_id: int) -> bool:
        """
        地物を「確認中」に設定する。
        
        Args:
            layer: 対象レイヤー
            feature_id: 地物ID
        
        Returns:
            bool: 更新が成功した場合True
        """
        return self.set_status(layer, feature_id, "確認中")
    
    def set_status_completed(self, layer: QgsVectorLayer, feature_id: int) -> bool:
        """
        地物を「完了」に設定する。
        
        Args:
            layer: 対象レイヤー
            feature_id: 地物ID
        
        Returns:
            bool: 更新が成功した場合True
        """
        return self.set_status(layer, feature_id, "完了")
    
    def apply_style(self, layer: QgsVectorLayer) -> None:
        """
        レイヤーにカテゴリ分類スタイルを適用する。
        
        Args:
            layer: 対象レイヤー
        
        Note:
            QgsMarkerSymbol.createSimple()を使用
            marker_shapeはPhase 3-Bスコープ外（形状は丸固定）
        """
        if layer is None or not layer.isValid():
            return
        
        categories = []
        
        for status in self._statuses:
            color = status.get("color", "#808080")
            size = status.get("marker_size", 8)
            
            # QgsMarkerSymbol.createSimple()でシンボル作成
            # 形状は丸（circle）固定
            symbol = QgsMarkerSymbol.createSimple({
                'name': 'circle',
                'color': color,
                'size': str(size)
            })
            
            category = QgsRendererCategory(
                status["name"], symbol, status["name"]
            )
            categories.append(category)
        
        # カテゴリ分類レンダラーを設定
        renderer = QgsCategorizedSymbolRenderer(self._column_name, categories)
        layer.setRenderer(renderer)
        layer.triggerRepaint()
        
        QgsMessageLog.logMessage(
            f"スタイル適用完了: {len(categories)}カテゴリ",
            "PoleFacility", Qgis.Info
        )
    
    def get_statuses(self) -> List[Dict]:
        """
        ステータスリストを取得する。
        
        Returns:
            List[Dict]: ステータスリストのコピー
        """
        return self._statuses.copy()
    
    def get_column_name(self) -> str:
        """
        作業状況カラム名を取得する。
        
        Returns:
            str: カラム名
        """
        return self._column_name
