"""
Logger - ログユーティリティ

QGISメッセージログと連携したアプリケーション用ロガー。
全てのログメッセージは "PoleFacility" タグで出力される。
"""

import traceback
from typing import Optional


class Logger:
    """
    アプリケーション用ロガー。QGISメッセージログと連携。
    
    全てのメソッドはクラスメソッドとして提供され、
    インスタンス化せずに使用可能。
    
    Example:
        from pole_facility_app.utils import Logger
        
        Logger.info("データをインポートしました")
        Logger.warning("未保存の変更があります")
        Logger.error("ファイルが見つかりません", FileNotFoundError("test.csv"))
    """
    
    TAG = "PoleFacility"
    
    @classmethod
    def debug(cls, message: str) -> None:
        """
        デバッグメッセージを出力する。
        
        Args:
            message: デバッグメッセージ
        
        Note:
            開発時のトレース用。本番環境では出力が抑制される場合あり。
        
        Example:
            Logger.debug("変数の値: x=10, y=20")
        """
        try:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(message, cls.TAG, Qgis.Info)
        except ImportError:
            # QGIS環境外（テスト等）での実行時
            print(f"[DEBUG] {cls.TAG}: {message}")
    
    @classmethod
    def info(cls, message: str) -> None:
        """
        情報メッセージを出力する。
        
        Args:
            message: 情報メッセージ
        
        Note:
            正常な処理の進行状況を記録。
        
        Example:
            Logger.info("CSVファイルをインポートしました")
            Logger.info("設定を保存しました")
        """
        try:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(message, cls.TAG, Qgis.Info)
        except ImportError:
            print(f"[INFO] {cls.TAG}: {message}")
    
    @classmethod
    def warning(cls, message: str) -> None:
        """
        警告メッセージを出力する。
        
        Args:
            message: 警告メッセージ
        
        Note:
            注意が必要だが処理は続行可能な状況で使用。
        
        Example:
            Logger.warning("写真ファイルが見つかりません: photo.jpg")
            Logger.warning("未保存の変更があります")
        """
        try:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage(message, cls.TAG, Qgis.Warning)
        except ImportError:
            print(f"[WARNING] {cls.TAG}: {message}")
    
    @classmethod
    def error(cls, message: str, exception: Optional[Exception] = None) -> None:
        """
        エラーメッセージを出力する。
        
        Args:
            message: エラーメッセージ
            exception: 例外オブジェクト（オプション）
        
        Note:
            処理が失敗した場合に使用。例外情報があれば併せて出力。
        
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
    
    @classmethod
    def exception(cls, message: str) -> None:
        """
        例外情報を出力する（スタックトレース付き）。
        
        Args:
            message: エラーメッセージ
        
        Note:
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
