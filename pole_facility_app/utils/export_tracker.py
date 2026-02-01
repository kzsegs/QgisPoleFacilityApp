"""
Export Tracker - エクスポート状態追跡（v1.9.1）

CSVエクスポート後の編集状態を追跡するSingletonクラス。
メモリ管理のみで、設定ファイルへの永続化は行わない。

Classes:
    ExportTracker: エクスポート状態管理
"""

from typing import Optional
from datetime import datetime
from qgis.core import QgsMessageLog, Qgis


class ExportTracker:
    """
    CSVエクスポート後の編集状態を追跡（Singleton）
    
    メモリ管理のみ:
        - QGISを閉じると編集フラグはリセットされる
        - 設定ファイル（config.json）への永続化は行わない
    
    Attributes:
        _has_unsaved_changes (bool): 未エクスポートの編集があるか
        _last_export_time (Optional[datetime]): 最後のエクスポート時刻
    """
    
    _instance: Optional['ExportTracker'] = None
    
    def __new__(cls):
        """Singletonパターンの実装"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """インスタンス初期化"""
        self._has_unsaved_changes = False
        self._last_export_time: Optional[datetime] = None
    
    @classmethod
    def get_instance(cls) -> 'ExportTracker':
        """
        Singletonインスタンスを取得
        
        Returns:
            ExportTracker: Singletonインスタンス
        """
        if cls._instance is None:
            cls()
        return cls._instance
    
    @classmethod
    def clear_instance(cls):
        """
        インスタンスをクリア（テスト用）
        
        Note:
            プロダクションコードでは使用しない
        """
        cls._instance = None
    
    def mark_exported(self) -> None:
        """
        エクスポート完了をマーク
        
        Called by:
            DataManager.export_csv()
        """
        self._has_unsaved_changes = False
        self._last_export_time = datetime.now()
        QgsMessageLog.logMessage(
            "ExportTracker - エクスポート完了をマーク",
            "PoleFacility", Qgis.Info
        )
    
    def mark_modified(self) -> None:
        """
        データ編集をマーク
        
        Called by:
            - InspectionFormDialog._on_confirm_clicked()
            - PhotoEditorPanel._on_save_clicked()
        """
        self._has_unsaved_changes = True
        QgsMessageLog.logMessage(
            "ExportTracker - データ編集をマーク",
            "PoleFacility", Qgis.Info
        )
    
    def has_unsaved_changes(self) -> bool:
        """
        未エクスポートの編集があるか
        
        Returns:
            bool: 未エクスポートの編集がある場合True
        """
        return self._has_unsaved_changes
    
    def get_last_export_time(self) -> Optional[datetime]:
        """
        最後のエクスポート時刻を取得
        
        Returns:
            Optional[datetime]: 最後のエクスポート時刻、未エクスポートの場合None
        """
        return self._last_export_time
    
    def reset(self) -> None:
        """
        状態をリセット
        
        Note:
            通常は使用しない（テスト用）
        """
        self._has_unsaved_changes = False
        self._last_export_time = None
        QgsMessageLog.logMessage(
            "ExportTracker - 状態をリセット",
            "PoleFacility", Qgis.Info
        )
