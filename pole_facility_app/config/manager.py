"""
設定管理モジュール

ConfigManagerはアプリケーション設定をSingletonパターンで管理する。
JSONファイルによる永続化をサポート。
"""

import os
import json
import threading
from typing import Any, Optional
from pathlib import Path

try:
    from qgis.core import Qgis, QgsMessageLog
    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False
    # フォールバック用の簡易ロガー
    class Qgis:
        Info = 0
        Warning = 1
        Critical = 2
    
    class QgsMessageLog:
        @staticmethod
        def logMessage(message, tag, level):
            print(f"[{tag}] {message}")


class ConfigError(Exception):
    """設定エラー"""
    pass


class ConfigManager:
    """
    アプリケーション設定を管理するシングルトンクラス。
    JSONファイルによる永続化をサポート。
    
    重要:
        - 直接インスタンス化は禁止（ConfigManager()は不可）
        - 必ずget_instance()を使用すること
        - 複数回get_instance()を呼んでもエラーにならない
        - スレッドセーフ（ダブルチェックロッキング使用）
    
    Attributes:
        _instance: シングルトンインスタンス
        _lock: スレッドセーフ用クラスレベルロック
        _config_path: 設定ファイルのパス
        _settings: 設定値を格納する辞書
        _default_settings: デフォルト設定値
        _event_bus: イベントバス（オプション）
    
    Example:
        config = ConfigManager.get_instance()
        config.initialize("C:/Users/user/.pole_facility/config.json")
        photo_root = config.get_photo_root_path()
        config.set_photo_root_path("C:/Data/Photos")
        config.save_config()
    """
    
    _instance: Optional['ConfigManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """
        インスタンス生成を制御する。
        
        処理フロー:
            1. _instance が None なら新規生成
            2. ダブルチェックロッキングで排他制御
            3. 初期化は _initialize() で1度だけ実行
            4. 既存インスタンスがあればそれを返す
        
        Returns:
            ConfigManager: シングルトンインスタンス
        
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
            - _config_path の初期化
            - _settings の初期化
            - _default_settings の初期化
            - _event_bus の初期化
            - _user_initialized フラグの初期化
            - _initialized フラグの設定
        
        Note:
            - 外部から直接呼び出してはいけない
            - hasattr で _initialized チェックにより、重複実行を防ぐ
            - _user_initialized は initialize() が呼ばれたかを示す別のフラグ
        """
        if not hasattr(self, '_initialized'):
            self._config_path: Optional[str] = None
            self._settings: dict = {}
            self._default_settings: dict = {}
            self._event_bus = None
            self._user_initialized = False  # initialize()が呼ばれたか
            self._initialized = True  # _initialize()が呼ばれたか
            
            if QGIS_AVAILABLE:
                QgsMessageLog.logMessage(
                    "ConfigManager初期化完了",
                    "PoleFacility",
                    Qgis.Info
                )
    
    @classmethod
    def get_instance(cls) -> 'ConfigManager':
        """
        ConfigManagerのシングルトンインスタンスを取得する。
        
        Returns:
            ConfigManager: シングルトンインスタンス
        
        Thread Safety:
            スレッドセーフ（ダブルチェックロッキング使用）
        
        実装詳細:
            1. cls._instance が None の場合のみ cls() を呼ぶ
            2. cls() は __new__ を呼び出す
            3. __new__ 内で _initialize() が1度だけ実行される
            4. 2回目以降は既存の _instance を返すだけ
        
        Example:
            config = ConfigManager.get_instance()
            # 何度呼んでも同じインスタンス、エラーなし
            config2 = ConfigManager.get_instance()
            assert config is config2
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
                ConfigManager.clear_instance()
                yield
                ConfigManager.clear_instance()
        """
        with cls._lock:
            if cls._instance is not None:
                if QGIS_AVAILABLE:
                    QgsMessageLog.logMessage(
                        "ConfigManagerインスタンスをクリア",
                        "PoleFacility",
                        Qgis.Info
                    )
            cls._instance = None
    
    def initialize(self, config_path: Optional[str] = None, event_bus=None) -> None:
        """
        ConfigManagerを初期化する（設定ファイルの読み込み）。
        
        Args:
            config_path: 設定ファイルのパス（省略時はデフォルトパス使用）
            event_bus: EventBusインスタンス（オプション）
        
        Raises:
            ConfigError: 設定ファイルの読み込みに失敗した場合
        
        Example:
            config = ConfigManager.get_instance()
            config.initialize("C:/Users/user/.pole_facility/config.json")
        
        Note:
            - これは _initialize() とは別物
            - _initialize() はインスタンス生成時の内部初期化
            - initialize() は設定ファイルの読み込み
            - 設定ファイルが存在しない場合、デフォルト設定で新規作成
            - 既存ファイルのバージョンが古い場合、自動マイグレーション実行
        """
        if self._user_initialized:
            return
        
        self._event_bus = event_bus
        
        # デフォルト設定を読み込み
        self._default_settings = self._create_default_config()
        
        # 設定ファイルパスを決定
        if config_path is None:
            config_path = self._get_default_config_path()
        
        self._config_path = config_path
        
        # 設定ファイルの読み込み
        if not self.load_config():
            # 読み込み失敗時はデフォルト設定を使用
            self._settings = self._default_settings.copy()
            # デフォルト設定で保存
            self.save_config()
        
        self._user_initialized = True
        
        if QGIS_AVAILABLE:
            QgsMessageLog.logMessage(
                f"ConfigManager設定読み込み完了: {self._config_path}",
                "PoleFacility",
                Qgis.Info
            )
    
    def load_config(self) -> bool:
        """
        設定ファイルを読み込む。
        
        Returns:
            bool: 読み込み成功時True
        
        Note:
            - ファイルが存在しない場合はFalseを返す（エラーではない）
            - JSON形式が不正な場合はエラーログを出力してFalseを返す
        """
        if not self._config_path or not os.path.exists(self._config_path):
            return False
        
        try:
            with open(self._config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
            
            # バリデーション
            if not self._validate_config(loaded_config):
                if QGIS_AVAILABLE:
                    QgsMessageLog.logMessage(
                        "Invalid config file, using defaults",
                        "PoleFacility",
                        Qgis.Warning
                    )
                return False
            
            # マイグレーション
            self._settings = self._migrate_config(loaded_config)
            
            return True
            
        except json.JSONDecodeError as e:
            if QGIS_AVAILABLE:
                QgsMessageLog.logMessage(
                    f"JSON decode error: {str(e)}",
                    "PoleFacility",
                    Qgis.Critical
                )
            return False
        except Exception as e:
            if QGIS_AVAILABLE:
                QgsMessageLog.logMessage(
                    f"Config load error: {str(e)}",
                    "PoleFacility",
                    Qgis.Critical
                )
            return False
    
    def save_config(self) -> bool:
        """
        設定をファイルに保存する。
        
        Returns:
            bool: 保存成功時True
        
        Raises:
            ConfigError: 保存に失敗した場合
        """
        if not self._config_path:
            raise ConfigError("Config path not set")
        
        try:
            # ディレクトリが存在しない場合は作成
            config_dir = os.path.dirname(self._config_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            
            # JSON形式で保存
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            error_msg = f"Config save error: {str(e)}"
            if QGIS_AVAILABLE:
                QgsMessageLog.logMessage(error_msg, "PoleFacility", Qgis.Critical)
            raise ConfigError(error_msg)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        設定値を取得する。ドット記法でネストしたキーにアクセス可能。
        
        Args:
            key: 設定キー（例: "paths.photo_root", "constants.max_photo_size_mb"）
            default: キーが存在しない場合のデフォルト値
        
        Returns:
            Any: 設定値、またはデフォルト値
        
        Example:
            photo_root = config.get("paths.photo_root", "")
            max_size = config.get("constants.max_photo_size_mb", 10)
        """
        keys = key.split('.')
        value = self._settings
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        設定値を更新する。
        
        Args:
            key: 設定キー
            value: 設定値
        
        Raises:
            ValueError: キーが空の場合
        
        Example:
            config.set("paths.photo_root", "C:/Data/Photos")
        
        Note:
            - 設定変更時、config.changedイベントが発行される
            - 変更は即座に反映されるが、save_config()を呼ぶまで永続化されない
        """
        if not key:
            raise ValueError("Key cannot be empty")
        
        keys = key.split('.')
        settings = self._settings
        
        # ネストした辞書を作成
        for k in keys[:-1]:
            if k not in settings:
                settings[k] = {}
            settings = settings[k]
        
        # 値を設定
        old_value = settings.get(keys[-1])
        settings[keys[-1]] = value
        
        # イベント発行
        if self._event_bus and old_value != value:
            try:
                self._event_bus.emit("config.changed", {
                    "key": key,
                    "old_value": old_value,
                    "new_value": value
                })
            except:
                pass  # EventBusがない場合は無視
    
    def get_photo_root_path(self) -> str:
        """
        写真ルートパスを取得する。
        
        Returns:
            str: 写真ルートパス（未設定の場合は空文字列）
        
        Example:
            root = config.get_photo_root_path()
            full_path = os.path.join(root, relative_path)
        """
        return self.get("paths.photo_root", "")
    
    def set_photo_root_path(self, path: str) -> None:
        """
        写真ルートパスを設定する。
        
        Args:
            path: 写真ルートパス
        
        Raises:
            ValueError: パスが存在しないディレクトリの場合
        
        Example:
            config.set_photo_root_path("C:/Data/Photos")
        """
        if path and not os.path.isdir(path):
            raise ValueError(f"Directory does not exist: {path}")
        
        self.set("paths.photo_root", path)
    
    def get_export_path(self) -> str:
        """
        エクスポート先パスを取得する。
        
        Returns:
            str: エクスポート先パス（未設定の場合は空文字列）
        """
        return self.get("paths.export_path", "")
    
    def set_export_path(self, path: str) -> None:
        """
        エクスポート先パスを設定する。
        
        Args:
            path: エクスポート先パス
        
        Raises:
            ValueError: パスが存在しないディレクトリの場合
        """
        if path and not os.path.isdir(path):
            raise ValueError(f"Directory does not exist: {path}")
        
        self.set("paths.export_path", path)
    
    def get_inspection_status_list(self, status_num: int) -> list[str]:
        """
        検査状態の選択肢リストを取得する。
        
        Args:
            status_num: 検査状態番号（1, 2, or 3）
        
        Returns:
            list[str]: 選択肢リスト
        
        Raises:
            ValueError: status_numが1-3以外の場合
        
        Example:
            status_list = config.get_inspection_status_list(1)
            # ["状態1A", "状態1B", "状態1C", "状態1D", "その他1"]
        """
        if status_num not in [1, 2, 3]:
            raise ValueError(f"status_num must be 1, 2, or 3, got: {status_num}")
        
        key = f"inspection_status.status_{status_num}"
        return self.get(key, [])
    
    def reset_to_defaults(self) -> None:
        """
        全設定をデフォルト値にリセットする。
        
        Example:
            config.reset_to_defaults()
            config.save_config()
        """
        self._settings = self._default_settings.copy()
        
        if self._event_bus:
            try:
                self._event_bus.emit("config.reset", {})
            except:
                pass
    
    def _get_default_config_path(self) -> str:
        """
        デフォルト設定ファイルパスを取得する。
        
        Returns:
            str: デフォルトパス
        
        Note:
            ユーザーホームディレクトリ/.pole_facility/config.json
        """
        home_dir = str(Path.home())
        config_dir = os.path.join(home_dir, '.pole_facility')
        return os.path.join(config_dir, 'config.json')
    
    def _create_default_config(self) -> dict:
        """
        デフォルト設定を作成する。
        
        Returns:
            dict: デフォルト設定辞書
        """
        # default_config.jsonを読み込む
        default_config_file = os.path.join(
            os.path.dirname(__file__),
            'default_config.json'
        )
        
        if os.path.exists(default_config_file):
            try:
                with open(default_config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                if QGIS_AVAILABLE:
                    QgsMessageLog.logMessage(
                        f"Failed to load default_config.json: {str(e)}",
                        "PoleFacility",
                        Qgis.Warning
                    )
        
        # フォールバック: ハードコードされたデフォルト設定
        return {
            "version": "1.0",
            "paths": {
                "photo_root": "",
                "export_path": ""
            },
            "ui": {
                "window_geometry": {
                    "x": 100,
                    "y": 100,
                    "width": 1200,
                    "height": 800
                },
                "last_import_directory": "",
                "last_export_directory": ""
            },
            "constants": {
                "max_photo_size_mb": 10,
                "max_records_per_csv": 1000,
                "thumbnail_size": 100,
                "auto_save_interval_minutes": 0
            },
            "inspection_status": {
                "status_1": ["状態1A", "状態1B", "状態1C", "状態1D", "その他1"],
                "status_2": ["状態2A", "状態2B", "状態2C", "状態2D", "その他2"],
                "status_3": ["状態3A", "状態3B", "状態3C", "状態3D", "その他3"]
            },
            "field_mapping": {
                "latitude": "緯度座標",
                "longitude": "経度座標",
                "facility_number": "設備番号",
                "inspection_date": "検査日"
            }
        }
    
    def _validate_config(self, config: dict) -> bool:
        """
        設定ファイルの内容を検証する。
        
        Args:
            config: 検証する設定辞書
        
        Returns:
            bool: 有効な場合True
        """
        # 必須キーのチェック
        required_keys = ["version", "paths", "inspection_status"]
        for key in required_keys:
            if key not in config:
                return False
        
        # バージョンチェック
        if not isinstance(config.get("version"), str):
            return False
        
        return True
    
    def _migrate_config(self, config: dict) -> dict:
        """
        古いバージョンの設定を最新版にマイグレーションする。
        
        Args:
            config: マイグレーション対象の設定
        
        Returns:
            dict: マイグレーション後の設定
        """
        version = config.get("version", "1.0")
        
        # 現在はバージョン1.0のみなのでマイグレーション不要
        # 将来のバージョンアップ時にここに追加
        
        # デフォルト設定と統合（新しいキーを追加）
        migrated = self._default_settings.copy()
        self._deep_update(migrated, config)
        
        return migrated
    
    def _deep_update(self, target: dict, source: dict) -> None:
        """
        辞書を再帰的にマージする。
        
        Args:
            target: マージ先の辞書（更新される）
            source: マージ元の辞書
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
