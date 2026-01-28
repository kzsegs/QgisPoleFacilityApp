"""
データマネージャー - CSV読み込み、GeoPackage保存、CSVエクスポートの統合管理

データ層の中核コンポーネント。
CSVParser、GeoPackageHandlerを統合し、レイヤ管理を行う。

使用例:
    data_manager = DataManager(iface, event_bus, config_manager)
    
    # CSVインポート（ダイアログ）
    data_manager.import_csv_dialog()
    
    # GeoPackage保存
    data_manager.set_last_editor("山田太郎")
    data_manager.save_to_gpkg()
    
    # CSVエクスポート（ダイアログ）
    data_manager.export_csv_dialog()
"""

import os
import csv
from typing import Optional, List, Dict, Any
from datetime import datetime
from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from qgis.core import (
    QgsVectorLayer,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem
)
from qgis.gui import QgisInterface
from PyQt5.QtCore import QVariant

from ..main.event_bus import EventBus, EventNames
from .csv_parser import CSVParser, ValidationResult, DataImportError
from .gpkg_handler import GeoPackageHandler, DataSaveError
from ..utils.logger import Logger


class DataManager:
    """
    CSV読み込み、GeoPackage読み書き、レイヤ管理を行う。
    
    Attributes:
        iface: QGISインターフェース
        event_bus: イベントバス
        config_manager: 設定マネージャー
        csv_parser: CSVパーサー
        gpkg_handler: GeoPackageハンドラー
        current_layer: 現在のレイヤ
        gpkg_path: GeoPackageファイルパス
        source_csv_path: 元CSVファイルパス
        is_modified: 変更フラグ
        last_editor: 最終編集者
        modification_history: 変更履歴（セッション内のみ）
    """
    
    def __init__(
        self,
        iface: QgisInterface,
        event_bus: EventBus,
        config_manager=None
    ):
        """
        DataManagerを初期化する。
        
        Args:
            iface: QGISインターフェース
            event_bus: イベントバス
            config_manager: 設定マネージャー（オプション）
        """
        self.iface = iface
        self.event_bus = event_bus
        self.config_manager = config_manager
        
        # コンポーネント
        self.csv_parser = CSVParser(config_manager)
        self.gpkg_handler = GeoPackageHandler()
        
        # 状態管理
        self.current_layer: Optional[QgsVectorLayer] = None
        self.gpkg_path: Optional[str] = None
        self.source_csv_path: Optional[str] = None
        self.is_modified: bool = False
        self.last_editor: str = ""
        self.modification_history: List[Dict[str, Any]] = []
        
        Logger.info("DataManager初期化完了")
    
    # ========== ダイアログメソッド（新規追加） ==========
    
    def import_csv_dialog(self) -> bool:
        """
        CSVファイル選択ダイアログを表示してインポートする。
        
        Returns:
            bool: インポート成功時True、キャンセル時False
        """
        # ファイル選択ダイアログ
        file_path, _ = QFileDialog.getOpenFileName(
            self.iface.mainWindow(),
            "CSVファイルを選択",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            Logger.info("CSVインポートがキャンセルされました")
            return False
        
        try:
            # インポート実行
            success = self.import_csv(file_path)
            
            if success:
                QMessageBox.information(
                    self.iface.mainWindow(),
                    "インポート完了",
                    f"CSVファイルをインポートしました。\n\n"
                    f"ファイル: {os.path.basename(file_path)}\n"
                    f"件数: {self.current_layer.featureCount()}件"
                )
            
            return success
            
        except DataImportError as e:
            QMessageBox.critical(
                self.iface.mainWindow(),
                "インポートエラー",
                f"CSVファイルのインポートに失敗しました。\n\n{str(e)}"
            )
            return False
        except Exception as e:
            QMessageBox.critical(
                self.iface.mainWindow(),
                "予期しないエラー",
                f"予期しないエラーが発生しました。\n\n{str(e)}"
            )
            return False
    
    def export_csv_dialog(self) -> bool:
        """
        CSV保存先選択ダイアログを表示してエクスポートする。
        
        Returns:
            bool: エクスポート成功時True、キャンセル時False
        """
        if not self.current_layer:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "エクスポートエラー",
                "エクスポートするデータがありません。\n\n"
                "先にCSVファイルをインポートしてください。"
            )
            return False
        
        # デフォルトのファイル名
        default_name = "export_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"
        
        # ファイル保存ダイアログ
        file_path, _ = QFileDialog.getSaveFileName(
            self.iface.mainWindow(),
            "CSVファイルを保存",
            default_name,
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            Logger.info("CSVエクスポートがキャンセルされました")
            return False
        
        try:
            # エクスポート実行
            success = self.export_to_csv(file_path)
            
            if success:
                QMessageBox.information(
                    self.iface.mainWindow(),
                    "エクスポート完了",
                    f"CSVファイルをエクスポートしました。\n\n"
                    f"ファイル: {os.path.basename(file_path)}\n"
                    f"件数: {self.current_layer.featureCount()}件"
                )
            
            return success
            
        except Exception as e:
            QMessageBox.critical(
                self.iface.mainWindow(),
                "エクスポートエラー",
                f"CSVファイルのエクスポートに失敗しました。\n\n{str(e)}"
            )
            return False
    
    # ========== 既存メソッド ==========
    
    def import_csv(self, csv_path: str) -> bool:
        """
        CSVファイルをインポートしてレイヤとして表示する（v1.9.1改訂）。
        
        Args:
            csv_path: CSVファイルのパス
        
        Returns:
            bool: インポート成功時True
        
        Raises:
            DataImportError: インポートに失敗した場合
        
        処理フロー:
            1. ファイル存在確認
            2. CSVParser.parse()でデータ読み込み
            3. CSVParser.validate()でバリデーション
            4. _create_layer_from_data()でレイヤ作成
            5. _setup_layer_style()でスタイル設定
            6. _add_layer_to_project()でプロジェクトに追加
            7. data.importedイベント発行
            8. ConfigManager.reload()で設定再読み込み（v1.9.1追加）
        """
        try:
            Logger.info(f"CSVインポート開始: {csv_path}")
            
            # 1. ファイル存在確認
            if not os.path.exists(csv_path):
                raise DataImportError(f"ファイルが見つかりません: {csv_path}")
            
            # 2. データ読み込み
            data = self.csv_parser.parse(csv_path)
            
            if not data:
                raise DataImportError("CSVファイルにデータがありません")
            
            # 3. バリデーション
            validation_result = self.csv_parser.validate(data)
            
            if not validation_result.is_valid:
                error_messages = [
                    f"行{error.row}: {error.field} - {error.message}"
                    for error in validation_result.errors[:5]  # 最初の5件のみ
                ]
                raise DataImportError(
                    f"データバリデーションエラー:\n" + "\n".join(error_messages)
                )
            
            # 4. レイヤ作成
            layer = self._create_layer_from_data(data)
            
            if not layer or not layer.isValid():
                raise DataImportError("レイヤの作成に失敗しました")
            
            # 4.5. 写真ウィジェット設定（★追加）
            self._setup_photo_widgets(layer)
            Logger.info("写真ウィジェット設定を適用しました")
            
            # 5. スタイル設定
            self._setup_layer_style(layer)
            
            # 6. プロジェクトに追加
            self._add_layer_to_project(layer)
            
            # 7. 地図の表示範囲を調整
            self._zoom_to_layer(layer)
            
            # 状態更新
            self.current_layer = layer
            self.source_csv_path = csv_path
            self.is_modified = False
            self.modification_history.clear()
            
            # 8. イベント発行
            self.event_bus.emit(EventNames.DATA_IMPORTED, {
                "layer_id": layer.id(),
                "feature_count": layer.featureCount(),
                "source_path": csv_path
            })
            
            Logger.info(f"CSVインポート完了: {layer.featureCount()}件")
            
            # 9. ConfigManager.reload()で設定再読み込み（v1.9.1追加）
            if self.config_manager:
                self.config_manager.reload()
                Logger.info("ConfigManager - 設定を再読み込みしました（CSVインポート後）")
            
            return True
            
        except DataImportError:
            raise
        except Exception as e:
            Logger.error(f"CSVインポートエラー: {str(e)}")
            raise DataImportError(f"予期しないエラー: {str(e)}")
    
    def save_to_gpkg(self, gpkg_path: Optional[str] = None) -> bool:
        """
        現在のレイヤをGeoPackageに保存する。
        
        Args:
            gpkg_path: 保存先パス（省略時は前回のパスまたはデフォルトパス）
        
        Returns:
            bool: 保存成功時True
        
        Raises:
            DataSaveError: 保存に失敗した場合
        """
        if not self.current_layer:
            raise DataSaveError("保存するレイヤがありません")
        
        try:
            # 保存先パス決定
            if gpkg_path:
                self.gpkg_path = gpkg_path
            elif not self.gpkg_path:
                # デフォルトパス
                self.gpkg_path = os.path.join(
                    os.path.dirname(self.source_csv_path) if self.source_csv_path else "",
                    "pole_facility_work.gpkg"
                )
            
            Logger.info(f"GeoPackage保存開始: {self.gpkg_path}")
            
            # メタデータ作成
            metadata = {
                "last_editor": self.last_editor,
                "last_modified": datetime.now().isoformat(),
                "source_csv": self.source_csv_path or "",
            }
            
            # 保存実行
            success = self.gpkg_handler.save(
                self.current_layer,
                self.gpkg_path,
                metadata
            )
            
            if success:
                self.is_modified = False
                
                # イベント発行
                self.event_bus.emit(EventNames.DATA_SAVED, {
                    "gpkg_path": self.gpkg_path,
                    "last_editor": self.last_editor,
                })
                
                Logger.info(f"GeoPackage保存完了: {self.gpkg_path}")
                
                # 成功メッセージ
                QMessageBox.information(
                    self.iface.mainWindow(),
                    "保存完了",
                    f"データを保存しました。\n\n"
                    f"ファイル: {os.path.basename(self.gpkg_path)}"
                )
            
            return success
            
        except Exception as e:
            Logger.error(f"GeoPackage保存エラー: {str(e)}")
            QMessageBox.critical(
                self.iface.mainWindow(),
                "保存エラー",
                f"データの保存に失敗しました。\n\n{str(e)}"
            )
            raise DataSaveError(f"保存に失敗しました: {str(e)}")
    
    def export_to_csv(self, output_path: str) -> bool:
        """
        現在のレイヤをCSVファイルにエクスポートする。
        
        Args:
            output_path: 出力先CSVファイルのパス
        
        Returns:
            bool: エクスポート成功時True
        
        Raises:
            ValueError: レイヤがない場合
        """
        if not self.current_layer:
            raise ValueError("エクスポートするレイヤがありません")
        
        try:
            Logger.info(f"CSVエクスポート開始: {output_path}")
            
            # フィールド名取得
            field_names = [field.name() for field in self.current_layer.fields()]
            
            # CSVファイル書き込み
            with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=field_names)
                writer.writeheader()
                
                # 全地物をエクスポート
                for feature in self.current_layer.getFeatures():
                    row = {}
                    for field_name in field_names:
                        value = feature[field_name]
                        
                        # QDate → 文字列変換
                        if isinstance(value, QDate):
                            if value.isValid():
                                row[field_name] = value.toString("yyyy/MM/dd")
                            else:
                                row[field_name] = ""
                        # None → 空文字列
                        elif value is None:
                            row[field_name] = ""
                        else:
                            row[field_name] = str(value)
                    
                    writer.writerow(row)
            
            # イベント発行
            self.event_bus.emit(EventNames.DATA_EXPORTED, {
                "csv_path": output_path,
                "feature_count": self.current_layer.featureCount(),
            })
            
            Logger.info(f"CSVエクスポート完了: {self.current_layer.featureCount()}件")
            
            return True
            
        except Exception as e:
            Logger.error(f"CSVエクスポートエラー: {str(e)}")
            raise
    
    def get_current_layer(self) -> Optional[QgsVectorLayer]:
        """現在のレイヤを取得する。"""
        return self.current_layer
    
    def get_feature_by_id(self, feature_id: int) -> Optional[QgsFeature]:
        """
        IDで地物を取得する。
        
        Args:
            feature_id: 地物ID
        
        Returns:
            Optional[QgsFeature]: 地物、見つからない場合はNone
        """
        if not self.current_layer:
            return None
        
        return self.current_layer.getFeature(feature_id)
    
    def update_feature(self, feature: QgsFeature) -> bool:
        """
        地物の属性を更新する。
        
        Args:
            feature: 更新する地物（変更済みの属性を含む）
        
        Returns:
            bool: 更新成功時True
        
        Note:
            座標（緯度座標、経度座標）の変更は許可されない
        """
        if not self.current_layer:
            return False
        
        try:
            # レイヤを編集モードに設定
            self.current_layer.startEditing()
            
            # 属性を更新
            success = self.current_layer.updateFeature(feature)
            
            if success:
                # 編集をコミット
                self.current_layer.commitChanges()
                
                # 変更フラグ設定
                self.is_modified = True
                
                # イベント発行
                self.event_bus.emit(EventNames.FEATURE_UPDATED, {
                    "feature_id": feature.id(),
                })
                
                Logger.info(f"地物更新完了: ID={feature.id()}")
            else:
                self.current_layer.rollBack()
            
            return success
            
        except Exception as e:
            self.current_layer.rollBack()
            Logger.error(f"地物更新エラー: {str(e)}")
            return False
    
    def is_data_modified(self) -> bool:
        """データが変更されているかチェックする。"""
        return self.is_modified
    
    def get_last_editor(self) -> str:
        """最終編集者を取得する。"""
        return self.last_editor
    
    def set_last_editor(self, name: str) -> None:
        """
        最終編集者を設定する。
        
        Args:
            name: 編集者名
        """
        self.last_editor = name
        Logger.info(f"最終編集者設定: {name}")
    
    def has_unsaved_changes(self) -> bool:
        """未保存の変更があるかチェックする。"""
        return self.is_modified
    
    def cleanup(self) -> None:
        """DataManagerのクリーンアップを行う。"""
        self.current_layer = None
        self.gpkg_path = None
        self.source_csv_path = None
        self.is_modified = False
        self.modification_history.clear()
        
        Logger.info("DataManagerクリーンアップ完了")
    
    def _create_layer_from_data(self, data: List[Dict[str, Any]]) -> QgsVectorLayer:
        """
        データからQGISレイヤを作成する。
        
        Args:
            data: CSVパース済みデータ
        
        Returns:
            QgsVectorLayer: 作成したレイヤ
        """
        # フィールド定義
        fields = self._setup_layer_fields()
        
        # メモリレイヤ作成（WGS84、ポイント）
        layer = QgsVectorLayer(
            "Point?crs=EPSG:4326",
            "電柱設備",
            "memory"
        )
        
        provider = layer.dataProvider()
        provider.addAttributes(fields)
        layer.updateFields()
        
        # 地物追加
        features = []
        for row in data:
            feature = QgsFeature(fields)
            
            # 座標設定
            lat = row.get("緯度座標")
            lon = row.get("経度座標")
            
            # デバッグ: 座標値を確認
            if lat is None or lon is None:
                Logger.warning(f"警告: 座標が空です - 設備番号: {row.get('設備番号')}, lat={lat}, lon={lon}")
            
            if lat is not None and lon is not None:
                try:
                    lat_float = float(lat)
                    lon_float = float(lon)
                    point = QgsPointXY(lon_float, lat_float)  # 経度, 緯度の順
                    geometry = QgsGeometry.fromPointXY(point)
                    feature.setGeometry(geometry)
                    
                    # デバッグ: ジオメトリ設定を確認
                    if feature.hasGeometry():
                        Logger.info(f"ジオメトリ設定成功: 設備番号={row.get('設備番号')}, 座標=({lon_float}, {lat_float})")
                    else:
                        Logger.error(f"エラー: ジオメトリが設定されませんでした - 設備番号={row.get('設備番号')}")
                except (ValueError, TypeError) as e:
                    Logger.error(f"座標変換エラー: 設備番号={row.get('設備番号')}, lat={lat}, lon={lon}, error={str(e)}")
            
            # 属性設定
            for field in fields:
                field_name = field.name()
                value = row.get(field_name)
                feature.setAttribute(field_name, value)
            
            features.append(feature)
        
        provider.addFeatures(features)
        layer.updateExtents()
        
        # デバッグ: レイヤ情報を出力
        extent = layer.extent()
        Logger.info(f"レイヤ作成完了: {len(features)}件")
        Logger.info(
            f"レイヤ範囲: xMin={extent.xMinimum():.6f}, yMin={extent.yMinimum():.6f}, "
            f"xMax={extent.xMaximum():.6f}, yMax={extent.yMaximum():.6f}"
        )
        Logger.info(f"レイヤCRS: {layer.crs().authid()}")
        Logger.info(f"ジオメトリタイプ: {QgsWkbTypes.displayString(layer.wkbType())}")
        
        # 写真ウィジェットを設定
        self._setup_photo_widgets(layer)
        
        return layer
    
    def _setup_layer_fields(self) -> QgsFields:
        """
        レイヤのフィールドを定義する。
        
        Returns:
            QgsFields: フィールド定義
        """
        fields = QgsFields()
        
        # 基本情報（文字列）
        fields.append(QgsField("収容区域コード", QVariant.String))
        fields.append(QgsField("収容区域名", QVariant.String))
        fields.append(QgsField("設備名", QVariant.String))
        fields.append(QgsField("設備番号", QVariant.String))
        fields.append(QgsField("緯度座標", QVariant.Double))
        fields.append(QgsField("経度座標", QVariant.Double))
        
        # 写真パス（文字列）
        for i in range(1, 4):
            fields.append(QgsField(f"設備写真{i}URI_修正前", QVariant.String))
        for i in range(1, 4):
            fields.append(QgsField(f"設備写真{i}URI_修正後", QVariant.String))
        
        # 検査項目（文字列）
        for i in range(1, 4):
            fields.append(QgsField(f"検査箇所{i}", QVariant.String))
            fields.append(QgsField(f"検査状態{i}", QVariant.String))
            fields.append(QgsField(f"検査状態{i}備考", QVariant.String))
        
        # 判定結果（文字列）
        fields.append(QgsField("総合判定結果1", QVariant.String))
        fields.append(QgsField("総合判定結果1備考", QVariant.String))
        fields.append(QgsField("備考", QVariant.String))
        
        # 日付
        fields.append(QgsField("検査日", QVariant.Date))
        
        # 検査者情報（文字列）
        fields.append(QgsField("検査者氏名", QVariant.String))
        fields.append(QgsField("確認者氏名", QVariant.String))
        
        return fields
    
    def _setup_layer_style(self, layer: QgsVectorLayer) -> None:
        """
        レイヤのスタイルを設定する。
        
        Args:
            layer: スタイル設定対象のレイヤ
        """
        # シンプルなマーカー表示
        # 詳細なスタイル設定は将来実装
        pass
    
    def _setup_photo_widgets(self, layer: QgsVectorLayer) -> None:
        """
        写真フィールドにエディタウィジェットを設定
        
        Args:
            layer: 設定対象レイヤ
        """
        try:
            from qgis.core import QgsEditorWidgetSetup
            
            # 修正前写真フィールド（表示専用）
            for i in [1, 2, 3]:
                field_name = f"設備写真{i}URI_修正前"
                field_idx = layer.fields().indexOf(field_name)
                
                if field_idx >= 0:
                    setup = QgsEditorWidgetSetup(
                        "Photo Viewer",  # ウィジェットタイプ
                        {}  # 設定（必要に応じて）
                    )
                    layer.setEditorWidgetSetup(field_idx, setup)
                    
                    Logger.info(f"Photo Viewer設定: {field_name}")
            
            # 修正後写真フィールド（編集可能）
            for i in [1, 2, 3]:
                field_name = f"設備写真{i}URI_修正後"
                field_idx = layer.fields().indexOf(field_name)
                
                if field_idx >= 0:
                    setup = QgsEditorWidgetSetup(
                        "Photo Editor",  # ウィジェットタイプ
                        {
                            "source_field": f"設備写真{i}URI_修正前"
                        }
                    )
                    layer.setEditorWidgetSetup(field_idx, setup)
                    
                    Logger.info(f"Photo Editor設定: {field_name}")
            
            Logger.info("写真ウィジェットを設定しました")
            
        except Exception as e:
            Logger.warning(f"写真ウィジェット設定エラー: {str(e)}")
    
    def fix_photo_widget_settings(self, layer: Optional[QgsVectorLayer] = None) -> bool:
        """
        既存レイヤの写真ウィジェット設定を修正
        
        古いプラグイン設定や不正な設定を検出し、
        正しい Photo Viewer / Photo Editor 設定に修正する。
        
        Args:
            layer: 修正対象レイヤ（省略時は current_layer）
        
        Returns:
            bool: 修正が必要だった場合True、問題なかった場合False
        
        Note:
            - GeoPackageに古い設定が残っている場合に使用
            - import_csv() では自動的に正しい設定が適用される
        """
        try:
            target_layer = layer if layer else self.current_layer
            
            if not target_layer or not target_layer.isValid():
                Logger.warning("修正対象のレイヤが見つかりません")
                return False
            
            from qgis.core import QgsEditorWidgetSetup
            
            Logger.info(f"写真ウィジェット設定を修正中: {target_layer.name()}")
            
            fixed_count = 0
            
            # 修正前写真フィールドをチェック・修正
            for i in [1, 2, 3]:
                field_name = f"設備写真{i}URI_修正前"
                field_idx = target_layer.fields().indexOf(field_name)
                
                if field_idx >= 0:
                    current_setup = target_layer.editorWidgetSetup(field_idx)
                    current_type = current_setup.type()
                    
                    # 期待されるタイプと異なる、または古いプラグイン設定の場合
                    if current_type != "Photo Viewer":
                        Logger.info(f"修正: {field_name} ({current_type} → Photo Viewer)")
                        
                        setup = QgsEditorWidgetSetup("Photo Viewer", {})
                        target_layer.setEditorWidgetSetup(field_idx, setup)
                        fixed_count += 1
            
            # 修正後写真フィールドをチェック・修正
            for i in [1, 2, 3]:
                field_name = f"設備写真{i}URI_修正後"
                field_idx = target_layer.fields().indexOf(field_name)
                
                if field_idx >= 0:
                    current_setup = target_layer.editorWidgetSetup(field_idx)
                    current_type = current_setup.type()
                    
                    # 期待されるタイプと異なる、または古いプラグイン設定の場合
                    if current_type != "Photo Editor":
                        Logger.info(f"修正: {field_name} ({current_type} → Photo Editor)")
                        
                        setup = QgsEditorWidgetSetup(
                            "Photo Editor",
                            {"source_field": f"設備写真{i}URI_修正前"}
                        )
                        target_layer.setEditorWidgetSetup(field_idx, setup)
                        fixed_count += 1
            
            if fixed_count > 0:
                Logger.info(f"✓ 写真ウィジェット設定を修正しました ({fixed_count}件)")
                return True
            else:
                Logger.info("✓ 写真ウィジェット設定は正常です")
                return False
        
        except Exception as e:
            Logger.error(f"❌ 写真ウィジェット設定の修正エラー: {str(e)}")
            return False
    
    def _add_layer_to_project(self, layer: QgsVectorLayer) -> None:
        """
        レイヤをQGISプロジェクトに追加する。
        
        Args:
            layer: 追加するレイヤ
        """
        QgsProject.instance().addMapLayer(layer)
        
        Logger.info(f"レイヤ追加完了: {layer.name()}")
    
    def _zoom_to_layer(self, layer: QgsVectorLayer) -> None:
        """
        レイヤの範囲に地図表示をズームする。
        
        Args:
            layer: 対象レイヤ
        
        Note:
            レイヤの範囲に10%の余白を追加して表示する。
        """
        if not layer or not layer.isValid():
            return
        
        extent = layer.extent()
        
        # 10%の余白を追加
        width = extent.width()
        height = extent.height()
        margin_x = width * 0.1
        margin_y = height * 0.1
        
        extent.setXMinimum(extent.xMinimum() - margin_x)
        extent.setXMaximum(extent.xMaximum() + margin_x)
        extent.setYMinimum(extent.yMinimum() - margin_y)
        extent.setYMaximum(extent.yMaximum() + margin_y)
        
        # 地図キャンバスに適用
        self.iface.mapCanvas().setExtent(extent)
        self.iface.mapCanvas().refresh()
        
        Logger.info(
            f"地図表示をレイヤ範囲に調整: "
            f"範囲=({extent.xMinimum():.6f}, {extent.yMinimum():.6f}) - "
            f"({extent.xMaximum():.6f}, {extent.yMaximum():.6f})"
        )
