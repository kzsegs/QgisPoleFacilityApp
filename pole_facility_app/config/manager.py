"""
設定管理 - アプリケーション設定の読み書きと管理

シングルトンパターンで実装され、設定ファイル（default_config.json）の
読み書き、バリデーション、インポート/エクスポート機能を提供する。

使用例:
    config = ConfigManager.get_instance()
    photo_root = config.get_photo_root_path()
    config.set("paths.photo_root", "/new/path")
    config.save_config()
"""

import json
import os
import threading
from typing import Any, Dict, Optional
from qgis.core import QgsMessageLog, Qgis


class ConfigManager:
    """
    アプリケーション設定を管理するシングルトンクラス。
    設定ファイルの読み書き、バリデーション、インポート/エクスポート機能を提供する。
    
    重要:
        - 直接インスタンス化は禁止（ConfigManager()は不可）
        - 必ずget_instance()を使用すること
        - スレッドセーフ（ダブルチェックロッキング使用）
    
    Attributes:
        _instance: シングルトンインスタンス
        _lock: スレッドセーフ用クラスレベルロック
        config: 設定データ（辞書）
        schema: スキーマ定義（辞書）
        CONFIG_FILE: 設定ファイル名
        SCHEMA_FILE: スキーマファイル名
        ENCODING: ファイルエンコーディング（Shift-JIS）
    """
    
    _instance: Optional['ConfigManager'] = None
    _lock: threading.Lock = threading.Lock()
    
    CONFIG_FILE = "default_config.json"
    SCHEMA_FILE = "config_schema.json"
    ENCODING = "shift-jis"
    
    def __new__(cls):
        """
        インスタンス生成を制御する。
        
        Returns:
            ConfigManager: シングルトンインスタンス
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # ダブルチェック
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def __init__(self):
        """直接インスタンス化を防ぐため、何もしない"""
        pass
    
    def _initialize(self):
        """内部初期化処理（__new__から1度だけ呼ばれる）"""
        if not hasattr(self, '_initialized'):
            self.config: Dict[str, Any] = {}
            self.schema: Dict[str, Any] = {}
            self._instance_lock: threading.Lock = threading.Lock()
            self._initialized = True
            
            # 設定ファイル読み込み
            self.load_config()
            
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
        """
        if cls._instance is None:
            cls()
        return cls._instance
    
    @classmethod
    def clear_instance(cls):
        """シングルトンインスタンスをクリアする"""
        with cls._lock:
            if cls._instance is not None:
                QgsMessageLog.logMessage(
                    "ConfigManagerインスタンスをクリア",
                    "PoleFacility",
                    Qgis.Info
                )
            cls._instance = None
    
    def load_config(self) -> None:
        """
        設定ファイルを読み込む（Shift-JIS対応）
        
        処理:
            1. default_config.json を Shift-JIS で読み込み
            2. JSONパース
            3. self.config に格納
        
        エラーハンドリング:
            - UnicodeDecodeError → UTF-8でリトライ
            - JSONDecodeError → デフォルト値で起動
            - FileNotFoundError → デフォルト値で起動
        """
        config_path = self._get_config_path()
        
        try:
            with open(config_path, 'r', encoding=self.ENCODING) as f:
                self.config = json.load(f)
            
            QgsMessageLog.logMessage(
                f"設定ファイルを読み込みました（Shift-JIS）: {config_path}",
                "PoleFacility",
                Qgis.Info
            )
        
        except UnicodeDecodeError:
            # フォールバック: UTF-8でリトライ
            QgsMessageLog.logMessage(
                "Shift-JIS読み込み失敗、UTF-8でリトライします",
                "PoleFacility",
                Qgis.Warning
            )
            
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                
                QgsMessageLog.logMessage(
                    f"設定ファイルを読み込みました（UTF-8）: {config_path}",
                    "PoleFacility",
                    Qgis.Info
                )
            except Exception as e:
                QgsMessageLog.logMessage(
                    f"UTF-8読み込みも失敗: {str(e)}、デフォルト値を使用します",
                    "PoleFacility",
                    Qgis.Warning
                )
                self.config = self._get_default_config()
        
        except (FileNotFoundError, json.JSONDecodeError) as e:
            QgsMessageLog.logMessage(
                f"設定ファイル読み込みエラー: {str(e)}、デフォルト値を使用します",
                "PoleFacility",
                Qgis.Warning
            )
            self.config = self._get_default_config()
    
    def save_config(self) -> None:
        """
        設定ファイルを保存（Shift-JIS）
        
        処理:
            1. self.config を JSON文字列に変換
            2. default_config.json に Shift-JIS で保存
        
        Raises:
            IOError: ファイル書き込み失敗
        """
        config_path = self._get_config_path()
        
        try:
            with open(config_path, 'w', encoding=self.ENCODING) as f:
                json.dump(
                    self.config,
                    f,
                    ensure_ascii=False,
                    indent=2
                )
            
            QgsMessageLog.logMessage(
                f"設定ファイルを保存しました（Shift-JIS）: {config_path}",
                "PoleFacility",
                Qgis.Info
            )
        
        except Exception as e:
            QgsMessageLog.logMessage(
                f"設定ファイル保存エラー: {str(e)}",
                "PoleFacility",
                Qgis.Critical
            )
            raise
    
    def reload(self) -> None:
        """設定ファイルを再読み込みする"""
        self.load_config()
        QgsMessageLog.logMessage(
            "設定を再読み込みしました",
            "PoleFacility",
            Qgis.Info
        )
    
    def import_config(self, filepath: str) -> None:
        """
        設定ファイルをインポート（Shift-JIS）
        
        Args:
            filepath: インポート元ファイルパス
        
        処理:
            1. Shift-JIS でJSON読み込み
            2. スキーマバリデーション
            3. self.config に反映
            4. default_config.json に保存
        
        Raises:
            ValueError: バリデーション失敗
            IOError: ファイル読み込み失敗
        """
        try:
            # Shift-JIS でJSON読み込み
            with open(filepath, 'r', encoding=self.ENCODING) as f:
                imported_config = json.load(f)
            
            # スキーマバリデーション
            self._validate_config(imported_config)
            
            # 適用
            self.config = imported_config
            self.save_config()
            
            QgsMessageLog.logMessage(
                f"設定をインポートしました: {filepath}",
                "PoleFacility",
                Qgis.Info
            )
        
        except UnicodeDecodeError:
            # UTF-8でリトライ
            QgsMessageLog.logMessage(
                "Shift-JIS読み込み失敗、UTF-8でリトライします",
                "PoleFacility",
                Qgis.Warning
            )
            
            with open(filepath, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            self._validate_config(imported_config)
            self.config = imported_config
            self.save_config()
        
        except ValueError as e:
            QgsMessageLog.logMessage(
                f"設定のバリデーションエラー: {str(e)}",
                "PoleFacility",
                Qgis.Critical
            )
            raise
        
        except Exception as e:
            QgsMessageLog.logMessage(
                f"設定インポートエラー: {str(e)}",
                "PoleFacility",
                Qgis.Critical
            )
            raise
    
    def export_config(self, filepath: str) -> None:
        """
        設定ファイルをエクスポート（Shift-JIS）
        
        Args:
            filepath: エクスポート先ファイルパス
        
        Raises:
            IOError: ファイル書き込み失敗
        """
        try:
            with open(filepath, 'w', encoding=self.ENCODING) as f:
                json.dump(
                    self.config,
                    f,
                    ensure_ascii=False,
                    indent=2
                )
            
            QgsMessageLog.logMessage(
                f"設定をエクスポートしました: {filepath}",
                "PoleFacility",
                Qgis.Info
            )
        
        except Exception as e:
            QgsMessageLog.logMessage(
                f"設定エクスポートエラー: {str(e)}",
                "PoleFacility",
                Qgis.Critical
            )
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        設定値を取得する。
        
        Args:
            key: 設定キー（ドット記法サポート、例: "paths.photo_root"）
            default: デフォルト値
        
        Returns:
            設定値、存在しない場合はdefault
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        設定値を設定する。
        
        Args:
            key: 設定キー（ドット記法サポート）
            value: 設定値
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def get_photo_root_path(self) -> str:
        """写真ルートパスを取得する"""
        return self.get("paths.photo_root", "")
    
    def get_export_path(self) -> str:
        """エクスポート先デフォルトパスを取得する"""
        return self.get("paths.export_path", "")
    
    def get_inspection_status_choices(self, index: int) -> list:
        """
        検査状態の選択肢を取得する。
        
        Args:
            index: 検査状態のインデックス（1, 2, 3）
        
        Returns:
            選択肢のリスト
        """
        return self.get(f"inspection_status.status_{index}", [])
    
    def _get_config_path(self) -> str:
        """設定ファイルのパスを取得する"""
        return os.path.join(
            os.path.dirname(__file__),
            self.CONFIG_FILE
        )
    
    def _get_schema_path(self) -> str:
        """スキーマファイルのパスを取得する"""
        return os.path.join(
            os.path.dirname(__file__),
            self.SCHEMA_FILE
        )
    
    def _load_schema(self) -> Dict[str, Any]:
        """
        スキーマファイルを読み込む（UTF-8）
        
        Returns:
            スキーマ辞書
        """
        schema_path = self._get_schema_path()
        
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            QgsMessageLog.logMessage(
                f"スキーマファイル読み込みエラー: {str(e)}",
                "PoleFacility",
                Qgis.Warning
            )
            return {}
    
    def _validate_config(self, config: dict) -> bool:
        """
        config_schema.json に基づいてバリデーション
        
        Args:
            config: バリデーション対象の設定辞書
        
        Returns:
            True: バリデーション成功
        
        Raises:
            ValueError: バリデーション失敗（詳細メッセージ付き）
        """
        schema = self._load_schema()
        
        if not schema or 'sections' not in schema:
            # スキーマがない場合は検証をスキップ
            QgsMessageLog.logMessage(
                "スキーマファイルが見つかりません。バリデーションをスキップします",
                "PoleFacility",
                Qgis.Warning
            )
            return True
        
        # セクションごとにバリデーション
        for section_name, section_def in schema['sections'].items():
            if section_name not in config:
                raise ValueError(
                    f"必須セクションが見つかりません: {section_name}"
                )
            
            # フィールドごとにバリデーション
            for field_name, field_def in section_def.get('fields', {}).items():
                # 必須チェック
                if field_def.get('required', False):
                    if field_name not in config[section_name]:
                        raise ValueError(
                            f"必須フィールドが見つかりません: "
                            f"{section_name}.{field_name}"
                        )
                
                # 型・範囲チェック
                if field_name in config[section_name]:
                    value = config[section_name][field_name]
                    self._validate_field_type(
                        f"{section_name}.{field_name}",
                        value,
                        field_def
                    )
                    self._validate_field_range(
                        f"{section_name}.{field_name}",
                        value,
                        field_def
                    )
        
        return True
    
    def _validate_field_type(self, name: str, value: Any, field_def: dict) -> None:
        """
        フィールドの型をバリデーション
        
        Args:
            name: フィールド名（表示用）
            value: 検証する値
            field_def: フィールド定義
        
        Raises:
            ValueError: 型エラー
        """
        expected_type = field_def.get('type')
        
        if not expected_type:
            return
        
        type_map = {
            'string': str,
            'integer': int,
            'boolean': bool,
            'list': list,
            'directory': str,
            'file': str,
            'choice': str
        }
        
        expected_python_type = type_map.get(expected_type)
        
        if expected_python_type and not isinstance(value, expected_python_type):
            raise ValueError(
                f"フィールド {name} の型が不正です。"
                f"期待: {expected_type}, 実際: {type(value).__name__}"
            )
    
    def _validate_field_range(self, name: str, value: Any, field_def: dict) -> None:
        """
        フィールドの範囲をバリデーション
        
        Args:
            name: フィールド名（表示用）
            value: 検証する値
            field_def: フィールド定義
        
        Raises:
            ValueError: 範囲エラー
        """
        # 数値範囲チェック
        if 'min' in field_def and isinstance(value, (int, float)):
            if value < field_def['min']:
                raise ValueError(
                    f"フィールド {name} の値が小さすぎます。"
                    f"最小値: {field_def['min']}"
                )
        
        if 'max' in field_def and isinstance(value, (int, float)):
            if value > field_def['max']:
                raise ValueError(
                    f"フィールド {name} の値が大きすぎます。"
                    f"最大値: {field_def['max']}"
                )
        
        # 選択肢チェック
        if 'choices' in field_def and isinstance(value, str):
            if value not in field_def['choices']:
                raise ValueError(
                    f"フィールド {name} の値が選択肢にありません。"
                    f"選択肢: {field_def['choices']}"
                )
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        デフォルト設定を返す
        
        Returns:
            デフォルト設定辞書
        """
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
            },
            "debug": {
                "enable_logging": True,
                "log_level": "INFO",
                "log_to_file": False,
                "log_file_path": ""
            },
            "window_positions": {
                "basic": {
                    "screen": 0,
                    "x": 100,
                    "y": 100,
                    "width": 400,
                    "height": 300
                },
                "photo": {
                    "screen": 0,
                    "x": 520,
                    "y": 100,
                    "width": 600,
                    "height": 500
                },
                "inspection": {
                    "screen": 0,
                    "x": 100,
                    "y": 420,
                    "width": 500,
                    "height": 600
                }
            }
        }
    
    # ==================== ウィンドウ位置管理 ====================
    
    def save_window_position(self, dialog_type: str, screen: int, x: int, y: int, width: int, height: int):
        """
        ウィンドウ位置・サイズをconfig.jsonに保存する。
        
        Args:
            dialog_type: ダイアログタイプ ('basic', 'photo', 'inspection')
            screen: スクリーン番号
            x: X座標（絶対座標）
            y: Y座標（絶対座標）
            width: 幅
            height: 高さ
        
        Note:
            - 即座にconfig.jsonに書き込む
            - マルチディスプレイ対応（スクリーン番号を保存）
        """
        if 'window_positions' not in self.config:
            self.config['window_positions'] = {}
        
        self.config['window_positions'][dialog_type] = {
            'screen': screen,
            'x': x,
            'y': y,
            'width': width,
            'height': height
        }
        
        self.save_config()
        
        QgsMessageLog.logMessage(
            f"ConfigManager - ウィンドウ位置保存: {dialog_type} screen={screen} x={x} y={y} w={width} h={height}",
            "PoleFacility", Qgis.Info
        )
    
    def get_window_position(self, dialog_type: str) -> Optional[Dict[str, int]]:
        """
        ウィンドウ位置・サイズをconfig.jsonから取得する。
        
        Args:
            dialog_type: ダイアログタイプ ('basic', 'photo', 'inspection')
        
        Returns:
            位置情報辞書 {'screen': int, 'x': int, 'y': int, 'width': int, 'height': int}
            存在しない場合はNone
        
        Note:
            - マルチディスプレイ対応
        """
        window_positions = self.config.get('window_positions', {})
        return window_positions.get(dialog_type)
    
    def reset_window_positions(self):
        """
        全ウィンドウ位置をデフォルトにリセットする。
        
        Note:
            - デフォルト位置は _get_default_config() の値を使用
        """
        default_config = self._get_default_config()
        self.config['window_positions'] = default_config.get('window_positions', {})
        self.save_config()
        
        QgsMessageLog.logMessage(
            "ConfigManager - ウィンドウ位置をリセット",
            "PoleFacility", Qgis.Info
        )
