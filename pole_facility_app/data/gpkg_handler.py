"""
GeoPackageハンドラー - GeoPackageファイルの読み書き

QGISレイヤをGeoPackage形式で保存・読み込みする機能を提供。
メタデータの管理も行う。

使用例:
    handler = GeoPackageHandler()
    
    # 保存
    metadata = {
        "last_editor": "山田太郎",
        "last_modified": "2024-12-01 10:00:00",
        "source_csv": "facilities.csv"
    }
    handler.save(layer, "work.gpkg", metadata)
    
    # 読み込み
    layer = handler.load("work.gpkg")
"""

import os
from typing import Optional, Dict, Any
from datetime import datetime
from qgis.core import (
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsCoordinateReferenceSystem,
    QgsMessageLog,
    Qgis
)


class GeoPackageHandler:
    """
    GeoPackageファイルの読み書きを行う。
    
    メタデータとして以下の情報を管理:
        - last_editor: 最終編集者
        - last_modified: 最終更新日時
        - source_csv: 元CSVファイルパス
    """
    
    # レイヤ名（GeoPackage内）
    LAYER_NAME = "pole_facilities"
    
    def __init__(self):
        """GeoPackageHandlerを初期化する。"""
        QgsMessageLog.logMessage(
            "GeoPackageHandler初期化完了",
            "PoleFacility",
            Qgis.Info
        )
    
    def save(
        self,
        layer: QgsVectorLayer,
        path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        レイヤをGeoPackageに保存する。
        
        Args:
            layer: 保存するレイヤ
            path: 保存先パス
            metadata: メタデータ（オプション）
                - last_editor: 最終編集者
                - last_modified: 最終更新日時
                - source_csv: 元CSVパス
        
        Returns:
            bool: 保存成功時True
        
        Raises:
            ValueError: レイヤが無効な場合
            IOError: 保存に失敗した場合
        
        処理フロー:
            1. 既存ファイルがある場合はバックアップ作成
            2. QgsVectorFileWriter.writeAsVectorFormat()で保存
            3. メタデータをテーブルに書き込み
        """
        if not layer or not layer.isValid():
            raise ValueError("レイヤが無効です")
        
        try:
            QgsMessageLog.logMessage(
                f"GeoPackage保存開始: {path}",
                "PoleFacility",
                Qgis.Info
            )
            
            # バックアップ作成（既存ファイルがある場合）
            if os.path.exists(path):
                self._create_backup(path)
            
            # 保存オプション設定
            save_options = QgsVectorFileWriter.SaveVectorOptions()
            save_options.driverName = "GPKG"
            save_options.layerName = self.LAYER_NAME
            
            # 既存ファイルの場合は上書き
            if os.path.exists(path):
                save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
            else:
                save_options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
            
            # 座標参照系（WGS84固定）
            crs = QgsCoordinateReferenceSystem("EPSG:4326")
            
            # 保存実行
            error = QgsVectorFileWriter.writeAsVectorFormatV2(
                layer,
                path,
                layer.transformContext(),
                save_options
            )
            
            if error[0] != QgsVectorFileWriter.NoError:
                raise IOError(f"GeoPackage保存エラー: {error[1]}")
            
            # メタデータ保存
            if metadata:
                self._save_metadata(path, metadata)
            
            QgsMessageLog.logMessage(
                f"GeoPackage保存完了: {path}",
                "PoleFacility",
                Qgis.Info
            )
            
            return True
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"GeoPackage保存エラー: {str(e)}",
                "PoleFacility",
                Qgis.Critical
            )
            raise
    
    def load(self, path: str) -> QgsVectorLayer:
        """
        GeoPackageからレイヤを読み込む。
        
        Args:
            path: GeoPackageファイルのパス
        
        Returns:
            QgsVectorLayer: 読み込んだレイヤ
        
        Raises:
            FileNotFoundError: ファイルが存在しない場合
            ValueError: レイヤ読み込みに失敗した場合
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"ファイルが見つかりません: {path}")
        
        try:
            QgsMessageLog.logMessage(
                f"GeoPackage読み込み開始: {path}",
                "PoleFacility",
                Qgis.Info
            )
            
            # レイヤURI構築
            uri = f"{path}|layername={self.LAYER_NAME}"
            
            # レイヤ読み込み
            layer = QgsVectorLayer(uri, self.LAYER_NAME, "ogr")
            
            if not layer.isValid():
                raise ValueError(f"レイヤ読み込みに失敗しました: {path}")
            
            QgsMessageLog.logMessage(
                f"GeoPackage読み込み完了: {layer.featureCount()}件",
                "PoleFacility",
                Qgis.Info
            )
            
            return layer
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"GeoPackage読み込みエラー: {str(e)}",
                "PoleFacility",
                Qgis.Critical
            )
            raise
    
    def get_metadata(self, path: str) -> Optional[Dict[str, Any]]:
        """
        GeoPackageからメタデータを取得する。
        
        Args:
            path: GeoPackageファイルのパス
        
        Returns:
            Optional[Dict[str, Any]]: メタデータ、取得失敗時はNone
        """
        try:
            # SQLiteデータベースとして直接アクセス
            import sqlite3
            
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            
            # メタデータテーブルが存在するかチェック
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='pole_facility_metadata'"
            )
            
            if not cursor.fetchone():
                conn.close()
                return None
            
            # メタデータ取得
            cursor.execute("SELECT key, value FROM pole_facility_metadata")
            rows = cursor.fetchall()
            
            conn.close()
            
            if rows:
                return {row[0]: row[1] for row in rows}
            
            return None
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"メタデータ取得エラー: {str(e)}",
                "PoleFacility",
                Qgis.Warning
            )
            return None
    
    def _create_backup(self, path: str) -> None:
        """
        既存ファイルのバックアップを作成する。
        
        Args:
            path: バックアップ対象ファイル
        """
        try:
            import shutil
            
            # バックアップファイル名（タイムスタンプ付き）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{path}.backup_{timestamp}"
            
            shutil.copy2(path, backup_path)
            
            QgsMessageLog.logMessage(
                f"バックアップ作成: {backup_path}",
                "PoleFacility",
                Qgis.Info
            )
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"バックアップ作成エラー: {str(e)}",
                "PoleFacility",
                Qgis.Warning
            )
    
    def _save_metadata(self, path: str, metadata: Dict[str, Any]) -> None:
        """
        メタデータをGeoPackageに保存する。
        
        Args:
            path: GeoPackageファイルのパス
            metadata: メタデータ
        """
        try:
            import sqlite3
            
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            
            # メタデータテーブル作成（存在しない場合）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pole_facility_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # メタデータ挿入/更新
            for key, value in metadata.items():
                cursor.execute(
                    "INSERT OR REPLACE INTO pole_facility_metadata (key, value) VALUES (?, ?)",
                    (key, str(value))
                )
            
            # 最終更新日時を自動追加
            cursor.execute(
                "INSERT OR REPLACE INTO pole_facility_metadata (key, value) VALUES (?, ?)",
                ("last_saved", datetime.now().isoformat())
            )
            
            conn.commit()
            conn.close()
            
            QgsMessageLog.logMessage(
                f"メタデータ保存完了: {len(metadata)}件",
                "PoleFacility",
                Qgis.Info
            )
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"メタデータ保存エラー: {str(e)}",
                "PoleFacility",
                Qgis.Warning
            )


class DataSaveError(Exception):
    """GeoPackage保存エラー"""
    pass
