"""
Forms Module

地物属性の表示・編集を行うフォームウィジェット群を提供するモジュール。
3タブ構成（基本情報、現場状況、判定結果）でデータを管理する。
"""

from .attribute_form import AttributeFormWidget
from .basic_info_tab import BasicInfoTab
from .field_status_tab import FieldStatusTab
from .result_tab import ResultTab
from .photo_thumbnail import PhotoThumbnailWidget

__all__ = [
    'AttributeFormWidget',
    'BasicInfoTab',
    'FieldStatusTab',
    'ResultTab',
    'PhotoThumbnailWidget',
]
