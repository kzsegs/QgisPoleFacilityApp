"""
Validators - バリデーション関数群

ファイルパス、ディレクトリ、座標、日付などのバリデーションを提供。
全ての関数は (bool, str) のタプルを返す。
"""

import os
import re
from typing import Tuple, Optional


def validate_csv_path(path: str) -> Tuple[bool, str]:
    """
    CSVファイルパスをバリデーションする。
    
    Args:
        path: ファイルパス
    
    Returns:
        tuple[bool, str]: (有効かどうか, エラーメッセージ)
    
    チェック項目:
        1. パスが空でないこと
        2. ファイルが存在すること
        3. 拡張子が .csv であること
    
    Example:
        valid, error = validate_csv_path("data/facilities.csv")
        if not valid:
            print(f"エラー: {error}")
    """
    if not path:
        return False, "ファイルパスが指定されていません"
    
    if not os.path.exists(path):
        return False, f"ファイルが存在しません: {path}"
    
    if not path.lower().endswith('.csv'):
        return False, "CSVファイルを指定してください"
    
    return True, ""


def validate_directory_path(path: str) -> Tuple[bool, str]:
    """
    ディレクトリパスをバリデーションする。
    
    Args:
        path: ディレクトリパス
    
    Returns:
        tuple[bool, str]: (有効かどうか, エラーメッセージ)
    
    チェック項目:
        1. パスが空でないこと
        2. ディレクトリが存在すること
        3. パスがディレクトリであること
    
    Example:
        valid, error = validate_directory_path("C:/Data/Photos")
        if not valid:
            print(f"エラー: {error}")
    """
    if not path:
        return False, "パスが指定されていません"
    
    if not os.path.exists(path):
        return False, f"ディレクトリが存在しません: {path}"
    
    if not os.path.isdir(path):
        return False, f"ディレクトリではありません: {path}"
    
    return True, ""


def validate_coordinate(lat: float, lon: float) -> Tuple[bool, str]:
    """
    座標値をバリデーションする。
    
    Args:
        lat: 緯度（-90 ～ 90）
        lon: 経度（-180 ～ 180）
    
    Returns:
        tuple[bool, str]: (有効かどうか, エラーメッセージ)
    
    チェック項目:
        1. 緯度が -90 ～ 90 の範囲内
        2. 経度が -180 ～ 180 の範囲内
    
    Example:
        valid, error = validate_coordinate(35.6762, 139.6503)
        if not valid:
            print(f"エラー: {error}")
    """
    if not (-90 <= lat <= 90):
        return False, f"緯度が範囲外です: {lat}"
    
    if not (-180 <= lon <= 180):
        return False, f"経度が範囲外です: {lon}"
    
    return True, ""


def validate_date_string(date_str: str) -> Tuple[bool, str]:
    """
    日付文字列をバリデーションする。
    
    Args:
        date_str: 日付文字列（yyyy/mm/dd形式）
    
    Returns:
        tuple[bool, str]: (有効かどうか, エラーメッセージ)
    
    チェック項目:
        1. 形式が yyyy/mm/dd であること
        2. 実在する日付であること
    
    Note:
        空文字列は有効（オプション項目として扱う）
    
    Example:
        valid, error = validate_date_string("2024/12/01")
        if not valid:
            print(f"エラー: {error}")
    """
    if not date_str:
        return True, ""  # 空は許可
    
    # 形式チェック
    pattern = r'^\d{4}/\d{2}/\d{2}$'
    if not re.match(pattern, date_str):
        return False, f"日付形式が不正です（yyyy/mm/dd）: {date_str}"
    
    # 日付の妥当性チェック
    try:
        year, month, day = map(int, date_str.split('/'))
        
        # QDateを使った検証（QGIS環境）
        try:
            from PyQt5.QtCore import QDate
            date = QDate(year, month, day)
            if not date.isValid():
                return False, f"無効な日付です: {date_str}"
        except ImportError:
            # QGIS環境外の場合はdatetimeで検証
            from datetime import datetime
            datetime(year, month, day)
    except (ValueError, TypeError):
        return False, f"無効な日付です: {date_str}"
    
    return True, ""


def validate_file_size(path: str, max_size_mb: float = 10.0) -> Tuple[bool, str]:
    """
    ファイルサイズをバリデーションする。
    
    Args:
        path: ファイルパス
        max_size_mb: 最大サイズ（MB）
    
    Returns:
        tuple[bool, str]: (有効かどうか, エラーメッセージ)
    
    Example:
        valid, error = validate_file_size("photo.jpg", max_size_mb=10.0)
        if not valid:
            print(f"エラー: {error}")
    """
    if not os.path.exists(path):
        return False, f"ファイルが存在しません: {path}"
    
    if not os.path.isfile(path):
        return False, f"ファイルではありません: {path}"
    
    file_size_mb = os.path.getsize(path) / (1024 * 1024)
    
    if file_size_mb > max_size_mb:
        return False, f"ファイルサイズが大きすぎます（{file_size_mb:.1f}MB > {max_size_mb}MB）"
    
    return True, ""


def validate_field_value(
    value: str,
    field_name: str,
    required: bool = False,
    max_length: Optional[int] = None
) -> Tuple[bool, str]:
    """
    フィールド値をバリデーションする。
    
    Args:
        value: フィールド値
        field_name: フィールド名（エラーメッセージ用）
        required: 必須かどうか
        max_length: 最大文字数（オプション）
    
    Returns:
        tuple[bool, str]: (有効かどうか, エラーメッセージ)
    
    Example:
        valid, error = validate_field_value(
            "P001",
            "設備番号",
            required=True,
            max_length=20
        )
    """
    # 必須チェック
    if required and not value:
        return False, f"{field_name}は必須です"
    
    # 長さチェック
    if max_length and len(value) > max_length:
        return False, f"{field_name}が長すぎます（{len(value)}文字 > {max_length}文字）"
    
    return True, ""


def validate_inspection_status(status: str, valid_statuses: list) -> Tuple[bool, str]:
    """
    検査状態の値をバリデーションする。
    
    Args:
        status: 検査状態の値
        valid_statuses: 有効な状態のリスト
    
    Returns:
        tuple[bool, str]: (有効かどうか, エラーメッセージ)
    
    Example:
        valid_statuses = ["状態1A", "状態1B", "状態1C", "状態1D", "その他1"]
        valid, error = validate_inspection_status("状態1A", valid_statuses)
    """
    if not status:
        return True, ""  # 空は許可（オプション）
    
    if status not in valid_statuses:
        return False, f"無効な検査状態です: {status}"
    
    return True, ""


def validate_email(email: str) -> Tuple[bool, str]:
    """
    メールアドレスをバリデーションする。
    
    Args:
        email: メールアドレス
    
    Returns:
        tuple[bool, str]: (有効かどうか, エラーメッセージ)
    
    Note:
        簡易的な形式チェックのみ。完全なRFC準拠ではない。
    
    Example:
        valid, error = validate_email("user@example.com")
    """
    if not email:
        return True, ""  # 空は許可
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, f"メールアドレスの形式が不正です: {email}"
    
    return True, ""


def validate_numeric_range(
    value: float,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    field_name: str = "値"
) -> Tuple[bool, str]:
    """
    数値の範囲をバリデーションする。
    
    Args:
        value: 検証する値
        min_value: 最小値（オプション）
        max_value: 最大値（オプション）
        field_name: フィールド名（エラーメッセージ用）
    
    Returns:
        tuple[bool, str]: (有効かどうか, エラーメッセージ)
    
    Example:
        valid, error = validate_numeric_range(
            35.5,
            min_value=0,
            max_value=100,
            field_name="進捗率"
        )
    """
    if min_value is not None and value < min_value:
        return False, f"{field_name}が小さすぎます（{value} < {min_value}）"
    
    if max_value is not None and value > max_value:
        return False, f"{field_name}が大きすぎます（{value} > {max_value}）"
    
    return True, ""


def validate_photo_extension(path: str) -> Tuple[bool, str]:
    """
    写真ファイルの拡張子をバリデーションする。
    
    Args:
        path: ファイルパス
    
    Returns:
        tuple[bool, str]: (有効かどうか, エラーメッセージ)
    
    サポートされる拡張子:
        .jpg, .jpeg, .png, .gif, .bmp, .webp
    
    Example:
        valid, error = validate_photo_extension("photo.jpg")
    """
    if not path:
        return True, ""  # 空は許可
    
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    ext = os.path.splitext(path)[1].lower()
    
    if ext not in valid_extensions:
        return False, f"サポートされていない画像形式です: {ext}"
    
    return True, ""


class ValidationResult:
    """
    複数のバリデーション結果をまとめて管理するクラス。
    
    Example:
        result = ValidationResult()
        result.add_error("設備番号", "設備番号は必須です")
        result.add_warning("写真", "写真ファイルが見つかりません")
        
        if not result.is_valid:
            for error in result.errors:
                print(f"エラー: {error.field} - {error.message}")
    """
    
    def __init__(self):
        """ValidationResultを初期化する"""
        self.errors = []
        self.warnings = []
    
    def add_error(self, field: str, message: str):
        """
        エラーを追加する。
        
        Args:
            field: フィールド名
            message: エラーメッセージ
        """
        self.errors.append(ValidationError(field, message))
    
    def add_warning(self, field: str, message: str):
        """
        警告を追加する。
        
        Args:
            field: フィールド名
            message: 警告メッセージ
        """
        self.warnings.append(ValidationWarning(field, message))
    
    @property
    def is_valid(self) -> bool:
        """
        バリデーション結果が有効かどうか。
        
        Returns:
            bool: エラーがない場合True
        """
        return len(self.errors) == 0
    
    def get_error_messages(self) -> list:
        """
        全エラーメッセージのリストを取得する。
        
        Returns:
            list: エラーメッセージのリスト
        """
        return [f"{e.field}: {e.message}" for e in self.errors]
    
    def get_warning_messages(self) -> list:
        """
        全警告メッセージのリストを取得する。
        
        Returns:
            list: 警告メッセージのリスト
        """
        return [f"{w.field}: {w.message}" for w in self.warnings]


class ValidationError:
    """バリデーションエラー"""
    
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
    
    def __str__(self):
        return f"{self.field}: {self.message}"


class ValidationWarning:
    """バリデーション警告"""
    
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
    
    def __str__(self):
        return f"{self.field}: {self.message}"
