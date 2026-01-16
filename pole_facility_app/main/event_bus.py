"""
イベントバス - プラグイン間のイベント通信を管理

Observerパターンによる疎結合な通信を実現する。
シングルトンパターンで実装され、アプリケーション全体で単一のインスタンスを共有する。

使用例:
    # イベント購読
    event_bus = EventBus.get_instance()
    event_bus.subscribe("data.imported", on_data_imported)
    
    # イベント発行
    event_bus.emit("data.imported", {"layer_id": "layer_001"})
    
    # 購読解除
    event_bus.unsubscribe("data.imported", on_data_imported)
"""

import threading
from typing import Callable, Dict, List, Any, Optional
from qgis.core import QgsMessageLog, Qgis


class EventBus:
    """
    プラグイン間のイベント通信を管理するシングルトンクラス。
    Observerパターンによる疎結合な通信を実現する。
    
    重要:
        - 直接インスタンス化は禁止（EventBus()は不可）
        - 必ずget_instance()を使用すること
        - 複数回get_instance()を呼んでもエラーにならない
        - スレッドセーフ（ダブルチェックロッキング使用）
    
    Attributes:
        _instance: シングルトンインスタンス
        _lock: スレッドセーフ用クラスレベルロック
        _subscribers: イベント名とコールバックのマッピング
        _instance_lock: インスタンスレベルのロック
    """
    
    _instance: Optional['EventBus'] = None
    _lock: threading.Lock = threading.Lock()
    
    def __new__(cls):
        """
        インスタンス生成を制御する。
        
        処理フロー:
            1. _instance が None なら新規生成
            2. ダブルチェックロッキングで排他制御
            3. 初期化は _initialize() で1度だけ実行
            4. 既存インスタンスがあればそれを返す
        
        Returns:
            EventBus: シングルトンインスタンス
        
        Note:
            直接呼び出さず、get_instance()を使用すること
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # ダブルチェック
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()  # 初期化（1度のみ）
        return cls._instance
    
    def __init__(self):
        """
        直接インスタンス化を防ぐため、何もしない。
        
        重要:
            - __new__ で初期化済みのため、ここでは何もしない
            - 初期化処理は _initialize() で実行
            - __init__ に初期化チェックを入れてはいけない
            
        誤った実装例（やってはいけない）:
            def __init__(self):
                if hasattr(self, '_initialized'):
                    raise RuntimeError("...")  # ← 毎回エラーになる
        
        正しい実装:
            def __init__(self):
                pass  # 何もしない
        """
        pass
    
    def _initialize(self):
        """
        内部初期化処理（__new__から1度だけ呼ばれる）
        
        処理内容:
            - _subscribers の初期化
            - _instance_lock の初期化
            - _initialized フラグの設定
        
        Note:
            - 外部から直接呼び出してはいけない
            - hasattr で _initialized チェックにより、重複実行を防ぐ
        """
        if not hasattr(self, '_initialized'):
            self._subscribers: Dict[str, List[Callable]] = {}
            self._instance_lock: threading.Lock = threading.Lock()
            self._initialized = True
            
            QgsMessageLog.logMessage(
                "EventBus初期化完了",
                "PoleFacility",
                Qgis.Info
            )
    
    @classmethod
    def get_instance(cls) -> 'EventBus':
        """
        EventBusのシングルトンインスタンスを取得する。
        
        Returns:
            EventBus: シングルトンインスタンス
        
        Thread Safety:
            スレッドセーフ（ダブルチェックロッキング使用）
        
        実装詳細:
            1. cls._instance が None の場合のみ cls() を呼ぶ
            2. cls() は __new__ を呼び出す
            3. __new__ 内で _initialize() が1度だけ実行される
            4. 2回目以降は既存の _instance を返すだけ
        
        Example:
            event_bus = EventBus.get_instance()
            # 何度呼んでも同じインスタンス、エラーなし
            event_bus2 = EventBus.get_instance()
            assert event_bus is event_bus2
        
        Note:
            スレッドセーフ（ダブルチェックロッキング使用）
        """
        if cls._instance is None:
            cls()  # __new__ が呼ばれる
        return cls._instance
    
    @classmethod
    def clear_instance(cls):
        """
        シングルトンインスタンスをクリアする。
        
        用途:
            - プラグインのunload時
            - テストの前後処理
            - アプリケーション終了時
        
        Thread Safety:
            スレッドセーフ（ロックを使用）
        
        Example:
            # プラグイン終了時
            def unload(self):
                EventBus.clear_instance()
                ConfigManager.clear_instance()
            
            # テスト用フィクスチャ
            @pytest.fixture(autouse=True)
            def reset_singletons():
                EventBus.clear_instance()
                yield
                EventBus.clear_instance()
        """
        with cls._lock:
            if cls._instance is not None:
                QgsMessageLog.logMessage(
                    "EventBusインスタンスをクリア",
                    "PoleFacility",
                    Qgis.Info
                )
            cls._instance = None
    
    def subscribe(self, event_name: str, callback: Callable[[Dict], None]) -> None:
        """
        イベントを購読する。
        
        Args:
            event_name: イベント名（例: "data.imported", "feature.selected"）
            callback: イベント発生時に呼び出されるコールバック関数
                     シグネチャ: callback(data: dict) -> None
        
        Raises:
            ValueError: event_nameが空または不正な形式の場合
            TypeError: callbackがCallableでない場合
        
        Example:
            def on_data_imported(data):
                layer_id = data.get("layer_id")
                print(f"Layer imported: {layer_id}")
            
            event_bus.subscribe("data.imported", on_data_imported)
        
        Note:
            同じcallbackを複数回登録した場合、重複して呼び出される
        """
        if not event_name or not isinstance(event_name, str):
            raise ValueError("event_nameは空でない文字列である必要があります")
        
        if not callable(callback):
            raise TypeError("callbackはCallableである必要があります")
        
        if not self._validate_event_name(event_name):
            raise ValueError(
                f"event_nameの形式が不正です: {event_name}\n"
                "形式: 'カテゴリ.アクション' (例: 'data.imported')"
            )
        
        with self._instance_lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            self._subscribers[event_name].append(callback)
        
        QgsMessageLog.logMessage(
            f"イベント購読: {event_name}",
            "PoleFacility",
            Qgis.Info
        )
    
    def unsubscribe(self, event_name: str, callback: Callable) -> bool:
        """
        イベント購読を解除する。
        
        Args:
            event_name: イベント名
            callback: 解除するコールバック関数
        
        Returns:
            bool: 解除成功時True、該当するsubscriptionがない場合False
        
        Example:
            success = event_bus.unsubscribe("data.imported", on_data_imported)
        """
        with self._instance_lock:
            if event_name in self._subscribers:
                try:
                    self._subscribers[event_name].remove(callback)
                    QgsMessageLog.logMessage(
                        f"イベント購読解除: {event_name}",
                        "PoleFacility",
                        Qgis.Info
                    )
                    
                    # リストが空になったら削除
                    if not self._subscribers[event_name]:
                        del self._subscribers[event_name]
                    
                    return True
                except ValueError:
                    return False
        return False
    
    def emit(self, event_name: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        イベントを発行する。
        
        Args:
            event_name: イベント名
            data: イベントデータ（オプション）
        
        Raises:
            ValueError: event_nameが空の場合
        
        Example:
            event_bus.emit("data.imported", {"layer_id": "layer_001"})
            event_bus.emit("app.initialized")  # データなし
        
        Note:
            - 登録されたcallbackは登録順に同期的に呼び出される
            - callback内で例外が発生しても、他のcallbackは実行される
            - callback内の例外はログに記録される
        """
        if not event_name:
            raise ValueError("event_nameは空にできません")
        
        if data is None:
            data = {}
        
        with self._instance_lock:
            subscribers = self._subscribers.get(event_name, []).copy()
        
        if subscribers:
            QgsMessageLog.logMessage(
                f"イベント発行: {event_name} (購読者数: {len(subscribers)})",
                "PoleFacility",
                Qgis.Info
            )
        
        for callback in subscribers:
            try:
                callback(data)
            except Exception as e:
                QgsMessageLog.logMessage(
                    f"イベントコールバックエラー: {event_name}\n"
                    f"コールバック: {callback.__name__}\n"
                    f"エラー: {str(e)}",
                    "PoleFacility",
                    Qgis.Critical
                )
    
    def clear_all(self) -> None:
        """
        全てのイベント購読を解除する。
        主にテスト時やアプリケーション終了時に使用。
        
        Example:
            event_bus.clear_all()
        """
        with self._instance_lock:
            count = sum(len(callbacks) for callbacks in self._subscribers.values())
            self._subscribers.clear()
        
        QgsMessageLog.logMessage(
            f"全イベント購読解除: {count}件",
            "PoleFacility",
            Qgis.Info
        )
    
    def _validate_event_name(self, event_name: str) -> bool:
        """
        イベント名の形式を検証する。
        
        Args:
            event_name: 検証するイベント名
        
        Returns:
            bool: 有効な形式の場合True
        
        Note:
            有効な形式: "カテゴリ.アクション" (例: "data.imported")
        """
        if not event_name or '.' not in event_name:
            return False
        
        parts = event_name.split('.')
        if len(parts) != 2:
            return False
        
        category, action = parts
        if not category or not action:
            return False
        
        return True
    
    def get_subscribers_count(self, event_name: str) -> int:
        """
        指定イベントの購読者数を取得する（デバッグ用）。
        
        Args:
            event_name: イベント名
        
        Returns:
            int: 購読者数
        """
        with self._instance_lock:
            return len(self._subscribers.get(event_name, []))
    
    def get_all_events(self) -> List[str]:
        """
        購読されている全イベント名を取得する（デバッグ用）。
        
        Returns:
            List[str]: イベント名のリスト
        """
        with self._instance_lock:
            return list(self._subscribers.keys())


class EventNames:
    """イベント名の定数定義"""
    
    # アプリケーションライフサイクル
    APP_INITIALIZED = "app.initialized"
    APP_SHUTDOWN = "app.shutdown"
    APP_EXIT_REQUESTED = "app.exit_requested"
    
    # データ管理
    DATA_IMPORTED = "data.imported"
    DATA_SAVED = "data.saved"
    DATA_EXPORTED = "data.exported"
    DATA_MODIFIED = "data.modified"
    
    # 地物操作
    FEATURE_SELECTED = "feature.selected"
    FEATURE_DESELECTED = "feature.deselected"
    FEATURE_UPDATED = "feature.updated"
    
    # 写真管理
    PHOTO_UPDATED = "photo.updated"
    PHOTO_DELETED = "photo.deleted"
    
    # 検索・フィルタ
    FILTER_APPLIED = "filter.applied"
    FILTER_CLEARED = "filter.cleared"
    
    # 設定
    CONFIG_CHANGED = "config.changed"
    
    # 選択ツール
    SELECT_TOOL_ACTIVATED = "select_tool.activated"
    SELECT_TOOL_DEACTIVATED = "select_tool.deactivated"
