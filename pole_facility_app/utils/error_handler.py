# -*- coding: utf-8 -*-
"""
Error Handler Module

統一的なエラーハンドリングを提供するユーティリティクラス。
ログ記録とユーザー通知を一元管理する。

使用例:
    # 基本的な使用
    ErrorHandler.log_and_show(
        "保存エラー", 
        "ファイルの保存に失敗しました", 
        Qgis.Critical, 
        parent_widget
    )
    
    # ファイルエラーのハンドリング
    try:
        with open(path, 'r') as f:
            data = f.read()
    except Exception as e:
        ErrorHandler.handle_file_error(path, e, parent_widget)
    
    # データ保存エラーのハンドリング
    try:
        layer.startEditing()
        # ... データ更新処理
        layer.commitChanges()
    except Exception as e:
        ErrorHandler.handle_data_save_error(layer, e, parent_widget)
"""

import os
from typing import Optional
from PyQt5.QtWidgets import QWidget, QMessageBox
from qgis.core import QgsMessageLog, Qgis, QgsVectorLayer


class ErrorHandler:
    """
    エラーハンドリングユーティリティクラス
    
    機能:
        - ログ記録とユーザー通知の統一
        - ファイル操作エラーの処理
        - データ保存エラーの処理
        - 標準的なエラーメッセージの提供
    
    Note:
        全てのメソッドはstaticmethodとして実装
    """
    
    @staticmethod
    def log_and_show(
        title: str,
        message: str,
        level: Qgis.MessageLevel,
        parent: Optional[QWidget] = None,
        show_dialog: bool = True
    ) -> None:
        """
        ログ記録とユーザー通知を同時に行う
        
        Args:
            title: ダイアログのタイトル
            message: メッセージ本文
            level: ログレベル (Qgis.Info/Warning/Critical)
            parent: 親ウィジェット（ダイアログの親）
            show_dialog: ダイアログを表示するか（デフォルト: True）
        
        処理フロー:
            1. QgsMessageLog にログを記録
            2. show_dialog が True の場合、レベルに応じたダイアログを表示
               - Critical → QMessageBox.critical
               - Warning → QMessageBox.warning
               - Info → QMessageBox.information
        
        Example:
            ErrorHandler.log_and_show(
                "保存完了",
                "データを保存しました",
                Qgis.Info,
                self
            )
        """
        # ログに記録
        QgsMessageLog.logMessage(
            f"{title}: {message}",
            "PoleFacility",
            level
        )
        
        # ダイアログ表示
        if show_dialog and parent is not None:
            if level == Qgis.Critical:
                QMessageBox.critical(parent, title, message)
            elif level == Qgis.Warning:
                QMessageBox.warning(parent, title, message)
            elif level == Qgis.Info:
                QMessageBox.information(parent, title, message)
    
    @staticmethod
    def handle_file_error(
        file_path: str,
        error: Exception,
        parent: Optional[QWidget] = None
    ) -> None:
        """
        ファイル操作エラーのハンドリング
        
        Args:
            file_path: 操作対象のファイルパス
            error: 発生した例外
            parent: 親ウィジェット
        
        処理:
            1. エラーの種類を判定
               - FileNotFoundError → ファイルが見つかりません
               - PermissionError → アクセス権限がありません
               - IsADirectoryError → ディレクトリです
               - その他 → ファイル操作エラー
            2. 適切なメッセージを構築してlog_and_show()を呼び出す
        
        Example:
            try:
                with open(photo_path, 'rb') as f:
                    data = f.read()
            except Exception as e:
                ErrorHandler.handle_file_error(photo_path, e, self)
        """
        filename = os.path.basename(file_path)
        
        # エラー種別に応じたメッセージ
        if isinstance(error, FileNotFoundError):
            message = f"ファイルが見つかりません:\n{filename}"
        elif isinstance(error, PermissionError):
            message = f"ファイルへのアクセス権限がありません:\n{filename}"
        elif isinstance(error, IsADirectoryError):
            message = f"指定されたパスはディレクトリです:\n{filename}"
        elif isinstance(error, OSError):
            message = f"ファイル操作エラー:\n{filename}\n\n詳細: {str(error)}"
        else:
            message = f"ファイル処理中にエラーが発生しました:\n{filename}\n\n{str(error)}"
        
        ErrorHandler.log_and_show(
            "ファイルエラー",
            message,
            Qgis.Critical,
            parent
        )
    
    @staticmethod
    def handle_data_save_error(
        layer: Optional[QgsVectorLayer],
        error: Exception,
        parent: Optional[QWidget] = None
    ) -> None:
        """
        データ保存エラーのハンドリング
        
        Args:
            layer: 対象レイヤ（ロールバック用）
            error: 発生した例外
            parent: 親ウィジェット
        
        処理:
            1. レイヤが編集モードならロールバック
            2. エラーメッセージを構築
            3. コミットエラーの場合は詳細情報を付加
            4. log_and_show()でユーザーに通知
        
        Example:
            try:
                layer.startEditing()
                layer.changeAttributeValue(fid, idx, value)
                if not layer.commitChanges():
                    raise RuntimeError("コミット失敗")
            except Exception as e:
                ErrorHandler.handle_data_save_error(layer, e, self)
        """
        # ロールバック処理
        if layer is not None and layer.isEditable():
            layer.rollBack()
            QgsMessageLog.logMessage(
                "データ保存エラーのため変更をロールバックしました",
                "PoleFacility",
                Qgis.Warning
            )
        
        # エラーメッセージ構築
        message = "データの保存に失敗しました。\n変更は破棄されました。"
        
        # コミットエラーの詳細情報
        if layer is not None:
            commit_errors = layer.commitErrors()
            if commit_errors:
                message += f"\n\n詳細:\n" + "\n".join(commit_errors)
        
        # 例外情報を追加
        if error:
            message += f"\n\nエラー: {str(error)}"
        
        ErrorHandler.log_and_show(
            "データ保存エラー",
            message,
            Qgis.Critical,
            parent
        )
    
    @staticmethod
    def handle_validation_error(
        errors: list,
        parent: Optional[QWidget] = None
    ) -> None:
        """
        バリデーションエラーのハンドリング
        
        Args:
            errors: エラーメッセージのリスト
            parent: 親ウィジェット
        
        処理:
            複数のバリデーションエラーを整形して表示
        
        Example:
            errors = []
            if not value1:
                errors.append("フィールド1は必須です")
            if value2 < 0:
                errors.append("フィールド2は0以上である必要があります")
            
            if errors:
                ErrorHandler.handle_validation_error(errors, self)
        """
        if not errors:
            return
        
        message = "入力内容に誤りがあります:\n\n"
        message += "\n".join(f"• {error}" for error in errors)
        
        ErrorHandler.log_and_show(
            "入力エラー",
            message,
            Qgis.Warning,
            parent
        )
    
    @staticmethod
    def handle_photo_load_error(
        field_name: str,
        file_path: str,
        error: Exception,
        parent: Optional[QWidget] = None
    ) -> None:
        """
        写真読み込みエラーのハンドリング
        
        Args:
            field_name: フィールド名
            file_path: 写真ファイルパス
            error: 発生した例外
            parent: 親ウィジェット
        
        処理:
            写真読み込み失敗時の専用エラーメッセージを表示
        
        Example:
            try:
                pixmap = QPixmap(photo_path)
                if pixmap.isNull():
                    raise ValueError("画像の読み込みに失敗しました")
            except Exception as e:
                ErrorHandler.handle_photo_load_error(
                    "設備写真1URI_修正前",
                    photo_path,
                    e,
                    self
                )
        """
        filename = os.path.basename(file_path)
        
        message = f"写真の読み込みに失敗しました\n\n"
        message += f"フィールド: {field_name}\n"
        message += f"ファイル: {filename}\n\n"
        
        # エラー種別に応じた追加情報
        if isinstance(error, FileNotFoundError):
            message += "ファイルが見つかりません。\n"
            message += "パス設定を確認してください。"
        elif isinstance(error, PermissionError):
            message += "ファイルへのアクセス権限がありません。"
        else:
            message += f"詳細: {str(error)}"
        
        ErrorHandler.log_and_show(
            "写真読み込みエラー",
            message,
            Qgis.Warning,
            parent
        )
    
    @staticmethod
    def handle_config_error(
        key: str,
        error: Exception,
        parent: Optional[QWidget] = None
    ) -> None:
        """
        設定読み込みエラーのハンドリング
        
        Args:
            key: 設定キー
            error: 発生した例外
            parent: 親ウィジェット
        
        処理:
            設定ファイル関連のエラーを処理
        
        Example:
            try:
                value = config_manager.get("paths.photo_root")
                if not value:
                    raise ValueError("設定されていません")
            except Exception as e:
                ErrorHandler.handle_config_error(
                    "paths.photo_root",
                    e,
                    self
                )
        """
        message = f"設定の読み込みに失敗しました\n\n"
        message += f"設定項目: {key}\n"
        message += f"詳細: {str(error)}\n\n"
        message += "設定画面から設定を確認してください。"
        
        ErrorHandler.log_and_show(
            "設定エラー",
            message,
            Qgis.Warning,
            parent
        )
    
    @staticmethod
    def log_debug(message: str) -> None:
        """
        デバッグログを記録（ダイアログ表示なし）
        
        Args:
            message: ログメッセージ
        
        Example:
            ErrorHandler.log_debug(f"処理開始: feature_id={feature.id()}")
        """
        QgsMessageLog.logMessage(
            message,
            "PoleFacility",
            Qgis.Info
        )
    
    @staticmethod
    def log_warning(message: str) -> None:
        """
        警告ログを記録（ダイアログ表示なし）
        
        Args:
            message: ログメッセージ
        
        Example:
            ErrorHandler.log_warning("フィールドが見つかりません")
        """
        QgsMessageLog.logMessage(
            message,
            "PoleFacility",
            Qgis.Warning
        )
    
    @staticmethod
    def log_error(message: str) -> None:
        """
        エラーログを記録（ダイアログ表示なし）
        
        Args:
            message: ログメッセージ
        
        Example:
            ErrorHandler.log_error(f"処理失敗: {str(e)}")
        """
        QgsMessageLog.logMessage(
            message,
            "PoleFacility",
            Qgis.Critical
        )


class ValidationError(Exception):
    """バリデーションエラー専用例外"""
    
    def __init__(self, errors: list):
        """
        初期化
        
        Args:
            errors: エラーメッセージのリスト
        """
        self.errors = errors
        super().__init__("\n".join(errors))


class ConfigurationError(Exception):
    """設定エラー専用例外"""
    
    def __init__(self, key: str, message: str):
        """
        初期化
        
        Args:
            key: 設定キー
            message: エラーメッセージ
        """
        self.key = key
        self.message = message
        super().__init__(f"設定エラー [{key}]: {message}")
