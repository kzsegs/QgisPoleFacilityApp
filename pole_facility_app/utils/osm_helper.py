"""
OSM Helper - OpenStreetMap背景地図ユーティリティ（v1.9.1新規）

OpenStreetMapタイルレイヤーの追加・削除・存在確認を提供する。

使用例:
    # OSMレイヤー追加
    layer = OSMHelper.add_osm_layer()
    
    # 既存確認
    if OSMHelper.is_osm_layer_exists():
        print("OSMレイヤーは既に存在します")
    
    # OSMレイヤー削除
    OSMHelper.remove_osm_layer()
"""

from typing import Optional
from qgis.core import QgsProject, QgsRasterLayer, QgsMessageLog, Qgis


class OSMHelper:
    """
    OpenStreetMap背景地図を管理するヘルパークラス。
    
    クラスメソッドのみを提供する（インスタンス化不要）。
    
    Attributes:
        OSM_LAYER_NAME: OSMレイヤーの固定名
        OSM_URI: OSM XYZタイルのURI
    """
    
    OSM_LAYER_NAME = "OpenStreetMap"
    OSM_URI = "type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    
    @classmethod
    def add_osm_layer(cls) -> Optional[QgsRasterLayer]:
        """
        OSM背景地図レイヤーをプロジェクトに追加する。
        
        Returns:
            QgsRasterLayer: 追加したレイヤー（成功時）
            None: 既に存在する場合、または作成失敗時
        
        処理フロー:
            1. 既存チェック（既に存在する場合はNoneを返す）
            2. XYZタイルレイヤー作成
            3. バリデーション
            4. プロジェクトに追加（最背面配置）
        
        Note:
            - レイヤー名は "OpenStreetMap" 固定
            - 重複追加を防ぐため、既存チェックを行う
            - ネットワークエラーは即時検出できない（タイル読み込み時に発生）
        """
        # 既存チェック
        if cls.is_osm_layer_exists():
            QgsMessageLog.logMessage(
                "OSMレイヤーは既に存在します",
                "PoleFacility", Qgis.Info
            )
            return None
        
        # XYZタイルレイヤー作成
        layer = QgsRasterLayer(cls.OSM_URI, cls.OSM_LAYER_NAME, "wms")
        
        # バリデーション
        if not layer.isValid():
            QgsMessageLog.logMessage(
                "OSMレイヤーの作成に失敗しました",
                "PoleFacility", Qgis.Critical
            )
            return None
        
        # プロジェクトに追加
        QgsProject.instance().addMapLayer(layer, False)
        
        # 最背面に配置
        root = QgsProject.instance().layerTreeRoot()
        root.insertLayer(-1, layer)
        
        QgsMessageLog.logMessage(
            "OSMレイヤーを追加しました",
            "PoleFacility", Qgis.Info
        )
        
        return layer
    
    @classmethod
    def is_osm_layer_exists(cls) -> bool:
        """
        OSMレイヤーが既に存在するかチェックする。
        
        Returns:
            bool: 存在する場合True
        
        処理:
            プロジェクト内の全レイヤーから名前で検索
        """
        for layer in QgsProject.instance().mapLayers().values():
            if layer.name() == cls.OSM_LAYER_NAME:
                return True
        return False
    
    @classmethod
    def remove_osm_layer(cls) -> bool:
        """
        OSMレイヤーをプロジェクトから削除する。
        
        Returns:
            bool: 削除成功時True、レイヤーが存在しない場合False
        
        処理:
            プロジェクト内の全レイヤーから名前で検索して削除
        """
        for layer_id, layer in QgsProject.instance().mapLayers().items():
            if layer.name() == cls.OSM_LAYER_NAME:
                QgsProject.instance().removeMapLayer(layer_id)
                QgsMessageLog.logMessage(
                    "OSMレイヤーを削除しました",
                    "PoleFacility", Qgis.Info
                )
                return True
        
        QgsMessageLog.logMessage(
            "OSMレイヤーが見つかりません",
            "PoleFacility", Qgis.Warning
        )
        return False
