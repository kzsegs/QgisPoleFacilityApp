"""
Search Filter Module

検索条件を表すデータクラス。
QGIS式への変換、辞書形式との相互変換機能を提供する。
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any
from PyQt5.QtCore import QDate

# ロガー設定
logger = logging.getLogger(__name__)


@dataclass
class SearchFilter:
    """
    検索フィルタ条件。
    
    設備番号、検査日範囲、検査状態による絞り込み条件を保持する。
    全てオプショナルで、指定された条件のみAND条件で適用される。
    
    Attributes:
        facility_number: 設備番号（部分一致）
        date_from: 検査日From
        date_to: 検査日To
        inspection_status_1: 検査状態1
        inspection_status_2: 検査状態2
        inspection_status_3: 検査状態3
    """
    
    facility_number: str = ""
    date_from: Optional[QDate] = None
    date_to: Optional[QDate] = None
    inspection_status_1: str = ""
    inspection_status_2: str = ""
    inspection_status_3: str = ""
    
    def is_empty(self) -> bool:
        """
        全ての条件が空かどうかを判定する。
        
        Returns:
            bool: 全条件が空の場合True
        
        Example:
            >>> filter = SearchFilter()
            >>> filter.is_empty()
            True
            >>> filter.facility_number = "P001"
            >>> filter.is_empty()
            False
        """
        return (
            not self.facility_number and
            self.date_from is None and
            self.date_to is None and
            not self.inspection_status_1 and
            not self.inspection_status_2 and
            not self.inspection_status_3
        )
    
    def to_expression(self) -> str:
        """
        QGISフィルタ式に変換する。
        
        Returns:
            str: QGIS式（AND条件で結合）、条件なしの場合は空文字列
        
        Example:
            >>> filter = SearchFilter(
            ...     facility_number="P001",
            ...     inspection_status_1="状態1A"
            ... )
            >>> filter.to_expression()
            '"設備番号" LIKE '%P001%' AND "検査状態1" = '状態1A''
        
        Note:
            - 設備番号: LIKE '%value%'（部分一致）
            - 日付範囲: '>=' および '<='
            - 検査状態: '='（完全一致）
            - 全条件をANDで結合
        """
        conditions = []
        
        # 設備番号（部分一致）
        if self.facility_number:
            escaped_value = self._escape_sql_value(self.facility_number)
            conditions.append(f'"設備番号" LIKE \'%{escaped_value}%\'')
        
        # 検査日From
        if self.date_from and self.date_from.isValid():
            date_str = self.date_from.toString("yyyy/MM/dd")
            conditions.append(f'"検査日" >= \'{date_str}\'')
        
        # 検査日To
        if self.date_to and self.date_to.isValid():
            date_str = self.date_to.toString("yyyy/MM/dd")
            conditions.append(f'"検査日" <= \'{date_str}\'')
        
        # 検査状態1
        if self.inspection_status_1:
            escaped_value = self._escape_sql_value(self.inspection_status_1)
            conditions.append(f'"検査状態1" = \'{escaped_value}\'')
        
        # 検査状態2
        if self.inspection_status_2:
            escaped_value = self._escape_sql_value(self.inspection_status_2)
            conditions.append(f'"検査状態2" = \'{escaped_value}\'')
        
        # 検査状態3
        if self.inspection_status_3:
            escaped_value = self._escape_sql_value(self.inspection_status_3)
            conditions.append(f'"検査状態3" = \'{escaped_value}\'')
        
        # AND条件で結合
        expression = " AND ".join(conditions) if conditions else ""
        
        if expression:
            logger.debug(f"Filter expression: {expression}")
        
        return expression
    
    def _escape_sql_value(self, value: str) -> str:
        """
        SQL値をエスケープする。
        
        Args:
            value: エスケープする値
        
        Returns:
            str: エスケープされた値
        
        Note:
            シングルクォートを2つに変換
        """
        return value.replace("'", "''")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        辞書形式に変換する。
        
        Returns:
            Dict[str, Any]: フィールド名と値の辞書
        
        Example:
            >>> filter = SearchFilter(facility_number="P001")
            >>> filter.to_dict()
            {'facility_number': 'P001', 'date_from': None, ...}
        
        Note:
            QDateはyyyy/MM/dd形式の文字列に変換
        """
        return {
            "facility_number": self.facility_number,
            "date_from": self.date_from.toString("yyyy/MM/dd") if self.date_from and self.date_from.isValid() else None,
            "date_to": self.date_to.toString("yyyy/MM/dd") if self.date_to and self.date_to.isValid() else None,
            "inspection_status_1": self.inspection_status_1,
            "inspection_status_2": self.inspection_status_2,
            "inspection_status_3": self.inspection_status_3,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchFilter':
        """
        辞書形式から生成する。
        
        Args:
            data: フィールド名と値の辞書
        
        Returns:
            SearchFilter: 生成したフィルタオブジェクト
        
        Example:
            >>> data = {'facility_number': 'P001', 'date_from': '2024/12/01'}
            >>> filter = SearchFilter.from_dict(data)
            >>> filter.facility_number
            'P001'
        
        Note:
            - 存在しないキーはデフォルト値で補完
            - 日付文字列はQDateに変換
        """
        # 日付変換
        date_from = None
        if data.get("date_from"):
            date_from = QDate.fromString(data["date_from"], "yyyy/MM/dd")
            if not date_from.isValid():
                date_from = None
        
        date_to = None
        if data.get("date_to"):
            date_to = QDate.fromString(data["date_to"], "yyyy/MM/dd")
            if not date_to.isValid():
                date_to = None
        
        return cls(
            facility_number=data.get("facility_number", ""),
            date_from=date_from,
            date_to=date_to,
            inspection_status_1=data.get("inspection_status_1", ""),
            inspection_status_2=data.get("inspection_status_2", ""),
            inspection_status_3=data.get("inspection_status_3", ""),
        )
    
    def __str__(self) -> str:
        """
        文字列表現を返す。
        
        Returns:
            str: フィルタの文字列表現
        """
        parts = []
        
        if self.facility_number:
            parts.append(f"設備番号:{self.facility_number}")
        
        if self.date_from and self.date_from.isValid():
            parts.append(f"From:{self.date_from.toString('yyyy/MM/dd')}")
        
        if self.date_to and self.date_to.isValid():
            parts.append(f"To:{self.date_to.toString('yyyy/MM/dd')}")
        
        if self.inspection_status_1:
            parts.append(f"状態1:{self.inspection_status_1}")
        
        if self.inspection_status_2:
            parts.append(f"状態2:{self.inspection_status_2}")
        
        if self.inspection_status_3:
            parts.append(f"状態3:{self.inspection_status_3}")
        
        return ", ".join(parts) if parts else "(条件なし)"
    
    def __repr__(self) -> str:
        """
        デバッグ用の文字列表現を返す。
        
        Returns:
            str: デバッグ用文字列
        """
        return (
            f"SearchFilter("
            f"facility_number='{self.facility_number}', "
            f"date_from={self.date_from}, "
            f"date_to={self.date_to}, "
            f"status_1='{self.inspection_status_1}', "
            f"status_2='{self.inspection_status_2}', "
            f"status_3='{self.inspection_status_3}')"
        )
