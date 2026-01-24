# -*- coding: utf-8 -*-
"""
Forms Module

フォーム構築関連のコンポーネントを提供するモジュール。

提供クラス:
    - FieldWidgetFactory: フィールドウィジェット生成ファクトリ
    - DynamicFormBuilder: 基本属性用動的フォームビルダー
    - SectionedFormBuilder: 検査項目用セクション分けフォームビルダー

使用例:
    from pole_facility_app.forms import (
        FieldWidgetFactory,
        DynamicFormBuilder,
        SectionedFormBuilder
    )
    
    # 基本属性フォーム
    builder = DynamicFormBuilder(config_manager)
    form = builder.build(fields_config, feature)
    
    # 検査項目フォーム
    sectioned_builder = SectionedFormBuilder(config_manager)
    form = sectioned_builder.build(sections_config, feature)
"""

from .field_widget_factory import FieldWidgetFactory
from .dynamic_form_builder import DynamicFormBuilder
from .sectioned_form_builder import SectionedFormBuilder

__all__ = [
    'FieldWidgetFactory',
    'DynamicFormBuilder',
    'SectionedFormBuilder',
]
