"""
CSV解析 - CSVファイルのパースとバリデーション

CSVファイルを読み込み、データの妥当性を検証する。
エンコーディング自動検出、型変換、バリデーションを提供。

使用例:
    parser = CSVParser(config_manager)
    data = parser.parse("facilities.csv")
    result = parser.validate(data)
    if not result.is_valid:
        for error in result.errors:
            print(f"Row {error.row}: {error.message}")
"""

import csv
import os
import chardet
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from PyQt5.QtCore import QDate
from qgis.core import QgsMessageLog, Qgis


@dataclass
class ValidationError:
    """バリデーションエラー情報"""
    row: int          # 行番号（1始まり）
    field: str        # フィールド名
    message: str      # エラーメッセージ
    value: Any = None # 不正な値


@dataclass
class ValidationWarning:
    """バリデーション警告情報"""
    row: int
    field: str
    message: str
    value: Any = None


@dataclass
class ValidationResult:
    """バリデーション結果"""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)
    
    def add_error(self, row: int, field: str, message: str, value: Any = None):
        """エラーを追加"""
        self.errors.append(ValidationError(row, field, message, value))
        self.is_valid = False
    
    def add_warning(self, row: int, field: str, message: str, value: Any = None):
        """警告を追加"""
        self.warnings.append(ValidationWarning(row, field, message, value))


class CSVParser:
    """
    CSVファイルの解析とバリデーションを行う。
    
    Attributes:
        config_manager: 設定マネージャー
        required_fields: 必須フィールドのリスト
        date_fields: 日付フィールドのリスト
        numeric_fields: 数値フィールドのリスト
    """
    
    # 必須フィールド（要件定義書 3.3.2節より）
    REQUIRED_FIELDS = [
        "収容区域コード",
        "収容区域名",
        "設備名",
        "設備番号",
        "緯度座標",
        "経度座標",
    ]
    
    # 日付フィールド
    DATE_FIELDS = [
        "検査日",
    ]
    
    # 数値フィールド
    NUMERIC_FIELDS = [
        "緯度座標",
        "経度座標",
    ]
    
    # 最大レコード数（要件定義書 3.1.1節より）
    MAX_RECORDS = 1000
    
    def __init__(self, config_manager=None):
        """
        CSVParserを初期化する。
        
        Args:
            config_manager: 設定マネージャー（オプション）
        """
        self.config_manager = config_manager
        self.required_fields = self.REQUIRED_FIELDS.copy()
        self.date_fields = self.DATE_FIELDS.copy()
        self.numeric_fields = self.NUMERIC_FIELDS.copy()
        
        QgsMessageLog.logMessage(
            "CSVParser初期化完了",
            "PoleFacility",
            Qgis.Info
        )
    
    def parse(self, csv_path: str) -> List[Dict[str, Any]]:
        """
        CSVファイルをパースする。
        
        Args:
            csv_path: CSVファイルのパス
        
        Returns:
            List[Dict[str, Any]]: パース結果（行ごとの辞書リスト）
        
        Raises:
            FileNotFoundError: ファイルが存在しない場合
            ValueError: ファイル形式が不正な場合
        
        Example:
            parser = CSVParser()
            data = parser.parse("facilities.csv")
        """
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"ファイルが見つかりません: {csv_path}")
        
        try:
            # エンコーディング検出
            encoding = self._detect_encoding(csv_path)
            
            QgsMessageLog.logMessage(
                f"CSV読み込み開始: {csv_path} (エンコーディング: {encoding})",
                "PoleFacility",
                Qgis.Info
            )
            
            # CSVファイル読み込み
            data = []
            with open(csv_path, 'r', encoding=encoding, newline='') as f:
                reader = csv.DictReader(f)
                
                for row_index, row in enumerate(reader, start=1):
                    parsed_row = self._parse_row(row, row_index)
                    data.append(parsed_row)
            
            QgsMessageLog.logMessage(
                f"CSV読み込み完了: {len(data)}件",
                "PoleFacility",
                Qgis.Info
            )
            
            return data
            
        except UnicodeDecodeError as e:
            raise ValueError(f"エンコーディングエラー: {str(e)}")
        except Exception as e:
            QgsMessageLog.logMessage(
                f"CSV読み込みエラー: {str(e)}",
                "PoleFacility",
                Qgis.Critical
            )
            raise
    
    def validate(self, data: List[Dict[str, Any]]) -> ValidationResult:
        """
        パース済みデータをバリデーションする。
        
        Args:
            data: パース済みデータ
        
        Returns:
            ValidationResult: バリデーション結果
        
        チェック項目:
            1. 必須フィールドの存在確認
            2. 座標値の範囲チェック（緯度: -90～90, 経度: -180～180）
            3. 日付形式チェック（yyyy/mm/dd）
            4. レコード数上限チェック
        """
        result = ValidationResult(is_valid=True)
        
        # レコード数チェック
        if len(data) > self.MAX_RECORDS:
            result.add_error(
                0,
                "全体",
                f"最大レコード数を超えています: {len(data)} > {self.MAX_RECORDS}",
                len(data)
            )
        
        # 各行のバリデーション
        for row_index, row in enumerate(data, start=1):
            # 必須フィールドチェック
            self._validate_required_fields(row, row_index, result)
            
            # 座標チェック
            self._validate_coordinates(row, row_index, result)
            
            # 日付形式チェック
            self._validate_date_format(row, row_index, result)
        
        if result.is_valid:
            QgsMessageLog.logMessage(
                f"バリデーション成功: {len(data)}件",
                "PoleFacility",
                Qgis.Info
            )
        else:
            QgsMessageLog.logMessage(
                f"バリデーションエラー: {len(result.errors)}件",
                "PoleFacility",
                Qgis.Warning
            )
        
        return result
    
    def _detect_encoding(self, path: str) -> str:
        """
        ファイルのエンコーディングを自動検出する。
        
        Args:
            path: ファイルパス
        
        Returns:
            str: エンコーディング名
        
        対応エンコーディング:
            - UTF-8 (with/without BOM)
            - Shift-JIS
            - CP932 (Windows日本語)
        """
        with open(path, 'rb') as f:
            raw_data = f.read(10000)  # 最初の10KBを読む
        
        # chardetで検出
        detected = chardet.detect(raw_data)
        encoding = detected['encoding']
        confidence = detected['confidence']
        
        QgsMessageLog.logMessage(
            f"エンコーディング検出: {encoding} (信頼度: {confidence:.2f})",
            "PoleFacility",
            Qgis.Info
        )
        
        # エンコーディング正規化
        if encoding:
            encoding_lower = encoding.lower()
            if 'utf-8' in encoding_lower or 'utf8' in encoding_lower:
                return 'utf-8-sig'  # BOM付きUTF-8にも対応
            elif 'shift' in encoding_lower or 'sjis' in encoding_lower:
                return 'shift-jis'
            elif 'cp932' in encoding_lower:
                return 'cp932'
        
        # デフォルトはUTF-8
        return 'utf-8-sig'
    
    def _parse_row(self, row: Dict[str, str], row_index: int) -> Dict[str, Any]:
        """
        CSV行を解析し、適切な型に変換する。
        
        Args:
            row: CSV行（辞書）
            row_index: 行番号
        
        Returns:
            Dict[str, Any]: 型変換済み行データ
        """
        parsed_row = {}
        
        for field, value in row.items():
            # 空文字列はNoneに変換
            if value == '':
                parsed_row[field] = None
                continue
            
            # 日付フィールド
            if field in self.date_fields:
                parsed_row[field] = self._parse_date(value)
            # 数値フィールド
            elif field in self.numeric_fields:
                parsed_row[field] = self._parse_coordinate(value)
            # その他（文字列）
            else:
                parsed_row[field] = value.strip() if value else None
        
        return parsed_row
    
    def _parse_date(self, value: str) -> Optional[QDate]:
        """
        日付文字列をQDateに変換する。
        
        Args:
            value: 日付文字列（yyyy/mm/dd）
        
        Returns:
            Optional[QDate]: QDateオブジェクト、変換失敗時はNone
        """
        if not value:
            return None
        
        try:
            # yyyy/mm/dd形式を想定
            parts = value.split('/')
            if len(parts) == 3:
                year, month, day = map(int, parts)
                return QDate(year, month, day)
        except (ValueError, AttributeError):
            pass
        
        return None
    
    def _parse_coordinate(self, value: str) -> Optional[float]:
        """
        座標文字列をfloatに変換する。
        
        Args:
            value: 座標文字列
        
        Returns:
            Optional[float]: 座標値、変換失敗時はNone
        """
        if not value:
            return None
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _validate_required_fields(
        self,
        row: Dict[str, Any],
        row_index: int,
        result: ValidationResult
    ) -> None:
        """
        必須フィールドの存在を検証する。
        
        Args:
            row: 行データ
            row_index: 行番号
            result: バリデーション結果
        """
        for field in self.required_fields:
            value = row.get(field)
            if value is None or value == '':
                result.add_error(
                    row_index,
                    field,
                    f"必須フィールドが空です",
                    value
                )
    
    def _validate_coordinates(
        self,
        row: Dict[str, Any],
        row_index: int,
        result: ValidationResult
    ) -> None:
        """
        座標値の範囲を検証する。
        
        Args:
            row: 行データ
            row_index: 行番号
            result: バリデーション結果
        """
        # 緯度チェック（-90～90）
        lat = row.get("緯度座標")
        if lat is not None:
            try:
                lat_float = float(lat) if not isinstance(lat, float) else lat
                if not (-90 <= lat_float <= 90):
                    result.add_error(
                        row_index,
                        "緯度座標",
                        f"緯度が範囲外です: {lat_float} (範囲: -90～90)",
                        lat_float
                    )
            except (ValueError, TypeError):
                result.add_error(
                    row_index,
                    "緯度座標",
                    f"緯度の形式が不正です: {lat}",
                    lat
                )
        
        # 経度チェック（-180～180）
        lon = row.get("経度座標")
        if lon is not None:
            try:
                lon_float = float(lon) if not isinstance(lon, float) else lon
                if not (-180 <= lon_float <= 180):
                    result.add_error(
                        row_index,
                        "経度座標",
                        f"経度が範囲外です: {lon_float} (範囲: -180～180)",
                        lon_float
                    )
            except (ValueError, TypeError):
                result.add_error(
                    row_index,
                    "経度座標",
                    f"経度の形式が不正です: {lon}",
                    lon
                )
    
    def _validate_date_format(
        self,
        row: Dict[str, Any],
        row_index: int,
        result: ValidationResult
    ) -> None:
        """
        日付形式を検証する。
        
        Args:
            row: 行データ
            row_index: 行番号
            result: バリデーション結果
        """
        for field in self.date_fields:
            value = row.get(field)
            
            # 日付フィールドが空の場合はスキップ（必須でない）
            if value is None:
                continue
            
            # QDateでない場合はエラー
            if not isinstance(value, QDate):
                result.add_error(
                    row_index,
                    field,
                    f"日付形式が不正です（yyyy/mm/dd形式で入力してください）",
                    value
                )
            elif not value.isValid():
                result.add_error(
                    row_index,
                    field,
                    f"無効な日付です",
                    value
                )


class DataImportError(Exception):
    """CSVインポートエラー"""
    pass
