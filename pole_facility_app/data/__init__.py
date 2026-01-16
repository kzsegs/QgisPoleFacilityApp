"""
データ管理モジュール

CSV読み込み、GeoPackage保存、CSVエクスポートを管理する。
データ層の中核コンポーネント。

主要クラス:
    - DataManager: データ管理のメインクラス
    - CSVParser: CSV解析とバリデーション
    - GeoPackageHandler: GeoPackage読み書き
"""

from .manager import DataManager
from .csv_parser import CSVParser, ValidationResult, ValidationError as CSVValidationError
from .gpkg_handler import GeoPackageHandler

__all__ = [
    'DataManager',
    'CSVParser',
    'ValidationResult',
    'CSVValidationError',
    'GeoPackageHandler',
]
