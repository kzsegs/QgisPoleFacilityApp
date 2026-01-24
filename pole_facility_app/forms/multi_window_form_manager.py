# -*- coding: utf-8 -*-
"""
Multi Window Form Manager - 複数ウィンドウフォームマネージャ

3つのダイアログ（基本属性・写真管理・検査項目）を統合管理するマネージャ。
Singletonパターンで実装され、アプリケーション全体で単一のインスタンスを共有。

機能:
    - 3つのダイアログの生成・管理
    - 地物選択時の一括表示・更新
    - ダイアログ間のイベント連携
    - ウィンドウ位置・サイズの記憶（将来拡張）

使用例:
    # 初期化
    manager = MultiWindowFormManager.get_instance()
    manager.initialize(event_bus, config_manager, data_manager)
    
    # 表示
    manager.show_forms(layer, feature, parent)
    
    # 更新
    manager.update_forms(feature)
    
    # 閉じる
    manager.close_all_forms()
"""

import threading
from typing import Optional, Dict, List
from qgis.PyQt.QtWidgets import QWidget
from qgis.core import QgsFeature, QgsVectorLayer, QgsMessageLog, Qgis

from .basic_attribute_dialog import BasicAttributeDialog
from .photo_management_dialog import PhotoManagementDialog
from .inspection_form_dialog import InspectionFormDialog


class MultiWindowFormManager:
    """
    複数ウィンドウフォームマネージャ（Singleton）
    
    責務:
        - 3つのダイアログのライフサイクル管理
        - 地物データの一括セット
        - ダイアログ間のイベント連携
        - 表示状態の管理
    
    ダイアログ構成:
        - basic: BasicAttributeDialog（基本属性）
        - photo: PhotoManagementDialog（写真管理）
        - inspection: InspectionFormDialog（検査項目）
    
    Singleton実装:
        - get_instance() で取得
        - clear_instance() でクリア（テスト用）
    """
    
    _instance: Optional['MultiWindowFormManager'] = None
    _lock: threading.Lock = threading.Lock()
    
    def __new__(cls):
        """
        インスタンス生成を制御（Singletonパターン）
        
        Returns:
            MultiWindowFormManager: シングルトンインスタンス
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # ダブルチェック
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def __init__(self):
        """
        直接インスタンス化を防ぐため、何もしない
        
        Note:
            初期化処理は _initialize() で実行
        """
        pass
    
    def _initialize(self):
        """
        内部初期化処理（__new__から1度だけ呼ばれる）
        
        Note:
            hasattr チェックにより重複実行を防ぐ
        """
        if not hasattr(self, '_initialized'):
            # 依存オブジェクト
            self.event_bus = None
            self.config_manager = None
            self.data_manager = None
            
            # 現在の地物・レイヤ
            self.current_feature: Optional[QgsFeature] = None
            self.current_layer: Optional[QgsVectorLayer] = None
            
            # ダイアログインスタンス
            self.dialogs: Dict[str, Optional[QWidget]] = {
                'basic': None,
                'photo': None,
                'inspection': None
            }
            
            # 親ウィジェット
            self._parent: Optional[QWidget] = None
            
            self._initialized = True
            
            QgsMessageLog.logMessage(
                "MultiWindowFormManager初期化完了",
                "PoleFacility",
                Qgis.Info
            )
    
    @classmethod
    def get_instance(cls) -> 'MultiWindowFormManager':
        """
        MultiWindowFormManagerのシングルトンインスタンスを取得
        
        Returns:
            MultiWindowFormManager: シングルトンインスタンス
        
        Thread Safety:
            スレッドセーフ（ダブルチェックロッキング使用）
        
        Example:
            manager = MultiWindowFormManager.get_instance()
            manager.initialize(event_bus, config_manager, data_manager)
        """
        if cls._instance is None:
            cls()  # __new__ が呼ばれる
        return cls._instance
    
    @classmethod
    def clear_instance(cls):
        """
        シングルトンインスタンスをクリア
        
        用途:
            - プラグインのunload時
            - テストの前後処理
        
        Thread Safety:
            スレッドセーフ（ロックを使用）
        
        Example:
            def unload(self):
                MultiWindowFormManager.clear_instance()
        """
        with cls._lock:
            if cls._instance is not None:
                # ダイアログを閉じる
                if hasattr(cls._instance, 'dialogs'):
                    cls._instance.close_all_forms()
                
                QgsMessageLog.logMessage(
                    "MultiWindowFormManagerインスタンスをクリア",
                    "PoleFacility",
                    Qgis.Info
                )
            cls._instance = None
    
    def initialize(self, event_bus, config_manager, data_manager):
        """
        マネージャの初期化
        
        Args:
            event_bus: EventBus インスタンス
            config_manager: ConfigManager インスタンス
            data_manager: DataManager インスタンス
        
        Note:
            show_forms() の前に必ず呼び出す
        """
        self.event_bus = event_bus
        self.config_manager = config_manager
        self.data_manager = data_manager
        
        QgsMessageLog.logMessage(
            "MultiWindowFormManager - 依存オブジェクト設定完了",
            "PoleFacility",
            Qgis.Info
        )
    
    def show_forms(
        self, 
        layer: QgsVectorLayer, 
        feature: QgsFeature, 
        parent: Optional[QWidget] = None
    ):
        """
        3つのダイアログを表示
        
        Args:
            layer: 対象レイヤ
            feature: 表示する地物
            parent: 親ウィジェット
        
        処理フロー:
            1. 現在の地物・レイヤを保存
            2. ダイアログが未作成なら作成
            3. 各ダイアログにレイヤをセット（v1.6.1仕様）
            4. 各ダイアログに地物をセット
            5. 全ダイアログを表示
            6. イベント発行（forms.shown）
        
        Example:
            manager.show_forms(layer, feature, iface.mainWindow())
        """
        try:
            # 1. 現在の地物・レイヤを保存
            self.current_layer = layer
            self.current_feature = feature
            self._parent = parent
            
            # 2. ダイアログが未作成なら作成
            self._create_dialogs_if_needed(parent)
            
            # 3. 各ダイアログにレイヤをセット（v1.6.1仕様）
            self._set_layer_to_dialogs(layer)
            
            # 4. 各ダイアログに地物をセット
            self._set_feature_to_dialogs(feature)
            
            # 5. 全ダイアログを表示
            for dialog_type, dialog in self.dialogs.items():
                if dialog and not dialog.isVisible():
                    dialog.show()
                    QgsMessageLog.logMessage(
                        f"MultiWindowFormManager - {dialog_type}ダイアログを表示",
                        "PoleFacility", Qgis.Info
                    )
            
            # 6. イベント発行
            if self.event_bus:
                self.event_bus.emit("forms.shown", {
                    "dialog_types": list(self.dialogs.keys()),
                    "feature_id": feature.id() if feature else None
                })
            
            QgsMessageLog.logMessage(
                f"MultiWindowFormManager - 全ダイアログ表示完了: feature_id={feature.id() if feature else None}",
                "PoleFacility", Qgis.Info
            )
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"MultiWindowFormManager - show_forms エラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
    
    def update_forms(self, feature: QgsFeature):
        """
        既に表示されているダイアログの内容を更新
        
        Args:
            feature: 新しい地物
        
        処理:
            各ダイアログの set_feature() を呼び出す
        
        Note:
            ダイアログを閉じずに別の地物に切り替える場合に使用
        
        Example:
            # 別の地物を選択した時
            manager.update_forms(new_feature)
        """
        try:
            self.current_feature = feature
            
            # 各ダイアログに地物をセット
            self._set_feature_to_dialogs(feature)
            
            # イベント発行
            if self.event_bus:
                self.event_bus.emit("feature.changed", {
                    "feature_id": feature.id() if feature else None
                })
            
            QgsMessageLog.logMessage(
                f"MultiWindowFormManager - ダイアログ更新完了: feature_id={feature.id() if feature else None}",
                "PoleFacility", Qgis.Info
            )
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"MultiWindowFormManager - update_forms エラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
    
    def close_all_forms(self):
        """
        全てのダイアログを閉じる
        
        処理:
            各ダイアログの close() を呼び出す
        
        Example:
            # 選択解除時
            manager.close_all_forms()
        """
        try:
            for dialog_type, dialog in self.dialogs.items():
                if dialog and dialog.isVisible():
                    dialog.close()
                    QgsMessageLog.logMessage(
                        f"MultiWindowFormManager - {dialog_type}ダイアログを閉じました",
                        "PoleFacility", Qgis.Info
                    )
            
            # イベント発行
            if self.event_bus:
                self.event_bus.emit("forms.closed", {})
            
            QgsMessageLog.logMessage(
                "MultiWindowFormManager - 全ダイアログを閉じました",
                "PoleFacility", Qgis.Info
            )
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"MultiWindowFormManager - close_all_forms エラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
    
    def close_form(self, dialog_type: str):
        """
        特定のダイアログを閉じる
        
        Args:
            dialog_type: ダイアログタイプ（"basic", "photo", "inspection"）
        
        Example:
            manager.close_form("basic")
        """
        try:
            dialog = self.dialogs.get(dialog_type)
            if dialog and dialog.isVisible():
                dialog.close()
                QgsMessageLog.logMessage(
                    f"MultiWindowFormManager - {dialog_type}ダイアログを閉じました",
                    "PoleFacility", Qgis.Info
                )
        except Exception as e:
            QgsMessageLog.logMessage(
                f"MultiWindowFormManager - close_form エラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
    
    def is_any_form_visible(self) -> bool:
        """
        いずれかのダイアログが表示されているか確認
        
        Returns:
            bool: いずれか1つでも表示されていればTrue
        
        Example:
            if not manager.is_any_form_visible():
                manager.show_forms(layer, feature)
        """
        for dialog in self.dialogs.values():
            if dialog and dialog.isVisible():
                return True
        return False
    
    def get_visible_forms(self) -> List[str]:
        """
        表示中のダイアログタイプのリストを取得
        
        Returns:
            List[str]: 表示中のダイアログタイプ
        
        Example:
            visible = manager.get_visible_forms()
            # → ["basic", "photo"]
        """
        visible = []
        for dialog_type, dialog in self.dialogs.items():
            if dialog and dialog.isVisible():
                visible.append(dialog_type)
        return visible
    
    def _create_dialogs_if_needed(self, parent: Optional[QWidget] = None):
        """
        ダイアログが未作成なら作成
        
        Args:
            parent: 親ウィジェット
        
        処理:
            1. 各ダイアログを生成
            2. シグナルを接続
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
                QgsMessageLog.logMessage(
                    "MultiWindowFormManager - BasicAttributeDialog作成完了",
                    "PoleFacility", Qgis.Info
                )
            
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
                QgsMessageLog.logMessage(
                    "MultiWindowFormManager - PhotoManagementDialog作成完了",
                    "PoleFacility", Qgis.Info
                )
            
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
                QgsMessageLog.logMessage(
                    "MultiWindowFormManager - InspectionFormDialog作成完了",
                    "PoleFacility", Qgis.Info
                )
        
        except Exception as e:
            QgsMessageLog.logMessage(
                f"MultiWindowFormManager - ダイアログ作成エラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
    
    def _set_layer_to_dialogs(self, layer: QgsVectorLayer):
        """
        各ダイアログにレイヤをセット（v1.6.1仕様）
        
        Args:
            layer: 対象レイヤ
        
        Note:
            PhotoManagementDialog と InspectionFormDialog は
            保存処理にレイヤが必要なため、set_feature() の前に呼び出す
        """
        try:
            # 写真管理ダイアログ
            if self.dialogs['photo']:
                self.dialogs['photo'].set_layer(layer)
                QgsMessageLog.logMessage(
                    "MultiWindowFormManager - PhotoManagementDialogにレイヤをセット",
                    "PoleFacility", Qgis.Info
                )
            
            # 検査項目ダイアログ
            if self.dialogs['inspection']:
                self.dialogs['inspection'].set_layer(layer)
                QgsMessageLog.logMessage(
                    "MultiWindowFormManager - InspectionFormDialogにレイヤをセット",
                    "PoleFacility", Qgis.Info
                )
        
        except Exception as e:
            QgsMessageLog.logMessage(
                f"MultiWindowFormManager - レイヤ設定エラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
    
    def _set_feature_to_dialogs(self, feature: QgsFeature):
        """
        各ダイアログに地物をセット
        
        Args:
            feature: 地物
        
        Note:
            _set_layer_to_dialogs() の後に呼び出す
        """
        try:
            # 基本属性ダイアログ
            if self.dialogs['basic']:
                self.dialogs['basic'].set_feature(feature)
                QgsMessageLog.logMessage(
                    "MultiWindowFormManager - BasicAttributeDialogに地物をセット",
                    "PoleFacility", Qgis.Info
                )
            
            # 写真管理ダイアログ
            if self.dialogs['photo']:
                self.dialogs['photo'].set_feature(feature)
                QgsMessageLog.logMessage(
                    "MultiWindowFormManager - PhotoManagementDialogに地物をセット",
                    "PoleFacility", Qgis.Info
                )
            
            # 検査項目ダイアログ
            if self.dialogs['inspection']:
                self.dialogs['inspection'].set_feature(feature)
                QgsMessageLog.logMessage(
                    "MultiWindowFormManager - InspectionFormDialogに地物をセット",
                    "PoleFacility", Qgis.Info
                )
        
        except Exception as e:
            QgsMessageLog.logMessage(
                f"MultiWindowFormManager - 地物設定エラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
    
    def _on_dialog_closed(self, dialog_type: str):
        """
        ダイアログクローズ時のハンドラ
        
        Args:
            dialog_type: クローズされたダイアログタイプ
        
        処理:
            イベントを発行
        """
        QgsMessageLog.logMessage(
            f"MultiWindowFormManager - {dialog_type}ダイアログがクローズされました",
            "PoleFacility", Qgis.Info
        )
        
        # イベント発行
        if self.event_bus:
            self.event_bus.emit("dialog.closed", {
                "dialog_type": dialog_type
            })
    
    def _on_photo_saved(self, field_name: str, relative_path: str):
        """
        写真保存完了時のハンドラ
        
        Args:
            field_name: フィールド名
            relative_path: 保存された相対パス
        
        処理:
            イベントを発行
        """
        QgsMessageLog.logMessage(
            f"MultiWindowFormManager - 写真保存完了: {field_name} → {relative_path}",
            "PoleFacility", Qgis.Info
        )
        
        # イベント発行
        if self.event_bus:
            self.event_bus.emit("photo.saved", {
                "feature_id": self.current_feature.id() if self.current_feature else None,
                "field_name": field_name,
                "path": relative_path
            })
    
    def _on_data_saved(self):
        """
        検査項目保存完了時のハンドラ
        
        処理:
            イベントを発行
        """
        QgsMessageLog.logMessage(
            "MultiWindowFormManager - 検査項目保存完了",
            "PoleFacility", Qgis.Info
        )
        
        # イベント発行
        if self.event_bus:
            self.event_bus.emit("data.modified", {
                "feature_id": self.current_feature.id() if self.current_feature else None,
                "source": "inspection_form"
            })
    
    def save_window_positions(self):
        """
        ウィンドウ位置・サイズを保存（将来拡張）
        
        Note:
            QSettings を使用してウィンドウ位置を永続化
        """
        # Phase 2-2 で実装
        pass
    
    def restore_window_positions(self):
        """
        ウィンドウ位置・サイズを復元（将来拡張）
        
        Note:
            QSettings から読み込んでウィンドウ位置を復元
        """
        # Phase 2-2 で実装
        pass
    
    def cleanup(self):
        """
        リソースのクリーンアップ
        
        処理:
            - 全ダイアログを閉じる
            - ダイアログインスタンスを削除
        
        Note:
            プラグインのunload時に呼び出す
        """
        try:
            # 全ダイアログを閉じる
            self.close_all_forms()
            
            # ダイアログインスタンスを削除
            for dialog_type in list(self.dialogs.keys()):
                if self.dialogs[dialog_type]:
                    self.dialogs[dialog_type].deleteLater()
                    self.dialogs[dialog_type] = None
            
            # 参照をクリア
            self.current_feature = None
            self.current_layer = None
            self._parent = None
            
            QgsMessageLog.logMessage(
                "MultiWindowFormManager - クリーンアップ完了",
                "PoleFacility", Qgis.Info
            )
        
        except Exception as e:
            QgsMessageLog.logMessage(
                f"MultiWindowFormManager - クリーンアップエラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
