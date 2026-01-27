"""
Logger - ログユーティリティ（v1.9.1改訂）

QGISメッセージログと連携したアプリケーション用ロガー。
全てのログメッセージは "PoleFacility" タグで出力される。

v1.9.1変更点:
    - ファイル出力機能追加
    - configure()メソッド追加
    - 設定に基づくログレベル制御
    - cleanup()メソッド追加
"""

import os
import traceback
from datetime import datetime
from typing import Optional


class Logger:
    """
    アプリケーション用ロガー。QGISメッセージログと連携。
    
    v1.9.1新機能:
        - ファイル出力対応
        - 設定ベースの制御
        - ログレベルフィルタリング
    
    全てのメソッドはクラスメソッドとして提供され、
    インスタンス化せずに使用可能。
    
    Example:
        # プラグイン起動時
        Logger.configure(config_manager)
        
        # ログ出力
        Logger.info("データをインポートしました")
        Logger.warning("未保存の変更があります")
        Logger.error("ファイルが見つかりません", FileNotFoundError("test.csv"))
        
        # プラグイン終了時
        Logger.cleanup()
    """
    
    TAG = "PoleFacility"
    
    # クラス変数
    _log_file = None
    _log_to_file = False
    _log_directory = ""
    _log_level = "INFO"
    _initialized = False
    
    # ログレベル定義
    LOG_LEVELS = {
        "DEBUG": 0,
        "INFO": 1,
        "WARNING": 2,
        "ERROR": 3,
        "CRITICAL": 4
    }
    
    @classmethod
    def configure(cls, config_manager, force_reconfigure: bool = False) -> None:
        """
        設定を読み込んでロガーを構成する。
        
        Args:
            config_manager: ConfigManagerインスタンス
            force_reconfigure: 強制的に再構成する（設定変更時に使用）
        
        Note:
            Plugin.initGui()内で、ConfigManager初期化直後に呼び出すこと。
            設定変更時は force_reconfigure=True で呼び出すと再構成される。
        
        Example:
            # 初回初期化
            def initGui(self):
                self.config_manager = ConfigManager.get_instance()
                Logger.configure(self.config_manager)
            
            # 設定変更時
            def on_settings_changed(self):
                Logger.configure(self.config_manager, force_reconfigure=True)
        """
        if cls._initialized and not force_reconfigure:
            return
        
        # 既存のログファイルを閉じる（再構成時）
        if force_reconfigure and cls._log_file is not None:
            try:
                cls._write_to_file("INFO", "=== 設定変更により再構成 ===")
                cls._log_file.close()
            except Exception:
                pass
            cls._log_file = None
        
        debug_config = config_manager.get("debug", {})
        cls._log_to_file = debug_config.get("log_to_file", False)
        cls._log_directory = debug_config.get("log_directory", "")
        cls._log_level = debug_config.get("log_level", "INFO")
        
        if cls._log_to_file and cls._log_directory:
            cls._initialize_log_file()
        elif not cls._log_to_file and cls._log_file is not None:
            # ファイル出力無効化時はファイルを閉じる
            try:
                cls._write_to_file("INFO", "=== ファイル出力を無効化 ===")
                cls._log_file.close()
            except Exception:
                pass
            cls._log_file = None
        
        cls._initialized = True
    
    @classmethod
    def _initialize_log_file(cls) -> None:
        """
        ログファイルを初期化する。
        
        ファイル名: pole_facility_YYYYMMDD_HHMMSS.log
        エンコーディング: UTF-8
        
        Note:
            ディレクトリが存在しない場合は自動作成する。
            ファイル作成に失敗した場合はログファイルをNoneにし、
            QGISログのみに出力する。
        """
        # デバッグ：処理開始をログ出力
        try:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(
                f"[DEBUG] _initialize_log_file() 開始: directory={cls._log_directory}",
                cls.TAG, Qgis.Info
            )
        except ImportError:
            pass
        
        try:
            # ステップ1: ディレクトリ確認
            dir_exists = os.path.exists(cls._log_directory)
            try:
                from qgis.core import QgsMessageLog, Qgis
                QgsMessageLog.logMessage(
                    f"[DEBUG] ディレクトリ存在チェック: {dir_exists}",
                    cls.TAG, Qgis.Info
                )
            except ImportError:
                pass
            
            if not dir_exists:
                try:
                    from qgis.core import QgsMessageLog, Qgis
                    QgsMessageLog.logMessage(
                        f"[DEBUG] ディレクトリ作成を試行: {cls._log_directory}",
                        cls.TAG, Qgis.Info
                    )
                except ImportError:
                    pass
                os.makedirs(cls._log_directory)
                try:
                    from qgis.core import QgsMessageLog, Qgis
                    QgsMessageLog.logMessage(
                        f"[DEBUG] ディレクトリ作成成功",
                        cls.TAG, Qgis.Info
                    )
                except ImportError:
                    pass
            
            # ステップ2: ファイルパス生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pole_facility_{timestamp}.log"
            filepath = os.path.join(cls._log_directory, filename)
            
            try:
                from qgis.core import QgsMessageLog, Qgis
                QgsMessageLog.logMessage(
                    f"[DEBUG] ファイルパス生成: {filepath}",
                    cls.TAG, Qgis.Info
                )
            except ImportError:
                pass
            
            # ステップ3: ファイルオープン
            try:
                from qgis.core import QgsMessageLog, Qgis
                QgsMessageLog.logMessage(
                    f"[DEBUG] ファイルオープンを試行",
                    cls.TAG, Qgis.Info
                )
            except ImportError:
                pass
            
            cls._log_file = open(filepath, 'w', encoding='utf-8')
            
            try:
                from qgis.core import QgsMessageLog, Qgis
                QgsMessageLog.logMessage(
                    f"[DEBUG] ファイルオープン成功: {cls._log_file}",
                    cls.TAG, Qgis.Info
                )
            except ImportError:
                pass
            
            # ステップ4: 初期メッセージ書き込み
            cls._write_to_file("INFO", f"=== ログ開始: {filepath} ===")
            
            try:
                from qgis.core import QgsMessageLog, Qgis
                QgsMessageLog.logMessage(
                    f"[DEBUG] _initialize_log_file() 完了",
                    cls.TAG, Qgis.Info
                )
            except ImportError:
                pass
            
        except Exception as e:
            cls._log_file = None
            # ファイル作成失敗はQGISログのみに記録
            import traceback
            error_detail = traceback.format_exc()
            try:
                from qgis.core import QgsMessageLog, Qgis
                QgsMessageLog.logMessage(
                    f"[ERROR] ログファイルの作成に失敗しました:\n"
                    f"  エラー: {str(e)}\n"
                    f"  ディレクトリ: {cls._log_directory}\n"
                    f"  詳細:\n{error_detail}",
                    cls.TAG, Qgis.Critical
                )
            except ImportError:
                print(f"[WARNING] {cls.TAG}: ログファイルの作成に失敗しました: {str(e)}\n{error_detail}")
    
    @classmethod
    def _write_to_file(cls, level: str, message: str) -> None:
        """
        ファイルにログを書き込む。
        
        Args:
            level: ログレベル（DEBUG/INFO/WARNING/ERROR/EXCEPTION）
            message: ログメッセージ
        
        フォーマット: [YYYY-MM-DD HH:MM:SS] [LEVEL] message
        
        Note:
            flush()を即時実行してクラッシュ時もログを保持する。
        """
        if cls._log_file is None:
            return
        
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cls._log_file.write(f"[{timestamp}] [{level}] {message}\n")
            cls._log_file.flush()  # 即時書き込み
        except Exception:
            # ファイル書き込みエラーは無視（QGISログは残る）
            pass
    
    @classmethod
    def _should_log(cls, level: str) -> bool:
        """
        ログレベルフィルタリング。
        
        Args:
            level: メッセージのログレベル
        
        Returns:
            bool: 出力すべき場合True
        
        Note:
            設定されたログレベル以上のメッセージのみ出力する。
            例: log_level="WARNING"の場合、WARNING/ERROR/CRITICALのみ出力
        """
        current_level = cls.LOG_LEVELS.get(cls._log_level, 1)
        message_level = cls.LOG_LEVELS.get(level, 1)
        return message_level >= current_level
    
    @classmethod
    def debug(cls, message: str) -> None:
        """
        デバッグメッセージを出力する。
        
        Args:
            message: デバッグメッセージ
        
        Note:
            v1.9.1: log_to_fileが有効な場合のみファイル出力
            QGISログには出力しない（ファイルのみ）
        
        Example:
            Logger.debug("変数の値: x=10, y=20")
        """
        if cls._should_log("DEBUG") and cls._log_to_file:
            cls._write_to_file("DEBUG", message)
    
    @classmethod
    def info(cls, message: str) -> None:
        """
        情報メッセージを出力する。
        
        Args:
            message: 情報メッセージ
        
        Note:
            v1.9.1: ログレベルチェック追加、ファイル出力追加
        
        Example:
            Logger.info("CSVファイルをインポートしました")
            Logger.info("設定を保存しました")
        """
        if not cls._should_log("INFO"):
            return
        
        try:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(message, cls.TAG, Qgis.Info)
        except ImportError:
            print(f"[INFO] {cls.TAG}: {message}")
        
        if cls._log_to_file:
            cls._write_to_file("INFO", message)
    
    @classmethod
    def warning(cls, message: str) -> None:
        """
        警告メッセージを出力する。
        
        Args:
            message: 警告メッセージ
        
        Note:
            v1.9.1: ファイル出力追加
        
        Example:
            Logger.warning("写真ファイルが見つかりません: photo.jpg")
            Logger.warning("未保存の変更があります")
        """
        try:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(message, cls.TAG, Qgis.Warning)
        except ImportError:
            print(f"[WARNING] {cls.TAG}: {message}")
        
        if cls._log_to_file:
            cls._write_to_file("WARNING", message)
    
    @classmethod
    def error(cls, message: str, exception: Optional[Exception] = None) -> None:
        """
        エラーメッセージを出力する。
        
        Args:
            message: エラーメッセージ
            exception: 例外オブジェクト（オプション）
        
        Note:
            v1.9.1: ファイル出力追加
        
        Example:
            Logger.error("ファイルの読み込みに失敗しました")
            Logger.error("CSV解析エラー", ValueError("Invalid format"))
        """
        if exception:
            message = f"{message}: {str(exception)}"
        
        try:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(message, cls.TAG, Qgis.Critical)
        except ImportError:
            print(f"[ERROR] {cls.TAG}: {message}")
        
        if cls._log_to_file:
            cls._write_to_file("ERROR", message)
    
    @classmethod
    def exception(cls, message: str) -> None:
        """
        例外情報を出力する（スタックトレース付き）。
        
        Args:
            message: エラーメッセージ
        
        Note:
            v1.9.1: 新規追加
            例外が発生したコンテキストで呼び出す。
            スタックトレースが自動的に取得され、メッセージに追加される。
        
        Example:
            try:
                risky_operation()
            except Exception:
                Logger.exception("予期しないエラーが発生しました")
        """
        stack_trace = traceback.format_exc()
        full_message = f"{message}\n{stack_trace}"
        
        try:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(full_message, cls.TAG, Qgis.Critical)
        except ImportError:
            print(f"[EXCEPTION] {cls.TAG}: {full_message}")
        
        if cls._log_to_file:
            cls._write_to_file("EXCEPTION", full_message)
    
    @classmethod
    def critical(cls, message: str, exception: Optional[Exception] = None) -> None:
        """
        重大なエラーメッセージを出力する。
        
        Args:
            message: エラーメッセージ
            exception: 例外オブジェクト（オプション）
        
        Note:
            アプリケーションの継続が困難な重大エラーで使用。
            error()のエイリアスとして機能。
        
        Example:
            Logger.critical("データベースが破損しています")
        """
        cls.error(message, exception)
    
    @classmethod
    def cleanup(cls) -> None:
        """
        ログファイルをクローズする。
        
        Note:
            v1.9.1: 新規追加
            プラグイン終了時（Plugin.unload()またはUIController._do_exit()）
            に呼び出すこと。
        
        Example:
            def unload(self):
                Logger.cleanup()
                # その他のクリーンアップ処理
        """
        if cls._log_file is not None:
            try:
                cls._write_to_file("INFO", "=== ログ終了 ===")
                cls._log_file.close()
            except Exception:
                pass
            cls._log_file = None
        
        cls._initialized = False


class LogContext:
    """
    コンテキストマネージャーを使ったログ記録。
    
    処理の開始・終了を自動的にログ記録する。
    
    Example:
        with LogContext("CSVインポート処理"):
            import_csv_file("data.csv")
        # 自動的に開始・終了がログ記録される
    """
    
    def __init__(self, operation: str, logger: type = Logger):
        """
        LogContextを初期化する。
        
        Args:
            operation: 処理名
            logger: 使用するロガークラス（デフォルト: Logger）
        """
        self.operation = operation
        self.logger = logger
    
    def __enter__(self):
        """コンテキスト開始時の処理"""
        self.logger.info(f"{self.operation} を開始")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキスト終了時の処理"""
        if exc_type is None:
            self.logger.info(f"{self.operation} が完了しました")
        else:
            self.logger.error(
                f"{self.operation} 中にエラーが発生しました",
                exc_val
            )
        return False  # 例外を再スロー


def log_function_call(func):
    """
    関数呼び出しをログ記録するデコレータ。
    
    Args:
        func: デコレート対象の関数
    
    Returns:
        ラップされた関数
    
    Example:
        @log_function_call
        def import_csv(path):
            # 処理
            pass
        
        # 関数呼び出し時に自動的にログ記録される
    """
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        Logger.debug(f"関数呼び出し: {func_name}")
        try:
            result = func(*args, **kwargs)
            Logger.debug(f"関数完了: {func_name}")
            return result
        except Exception as e:
            Logger.error(f"関数エラー: {func_name}", e)
            raise
    
    return wrapper
