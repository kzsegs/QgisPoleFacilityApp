# -*- coding: utf-8 -*-
"""
Dynamic Form Builder Module

フィールド設定リストから動的にフォームを生成するビルダークラス。
主に基本属性ダイアログで使用。

機能:
    - フィールド設定に基づくフォーム自動生成
    - セクション（グループ）単位での表示
    - 値の取得・設定
    - 読み取り専用/編集可能の制御

使用例:
    from pole_facility_app.forms import DynamicFormBuilder
    
    # フォーム構築
    builder = DynamicFormBuilder(config_manager)
    
    fields_config = [
        {
            "name": "収容区域コード",
            "label": "収容区域コード",
            "type": "text",
            "editable": False,
            "section": "識別情報"
        },
        {
            "name": "緯度座標",
            "label": "緯度",
            "type": "number",
            "editable": False,
            "section": "位置情報"
        }
    ]
    
    form_widget = builder.build(fields_config, feature)
    
    # 値の取得
    values = builder.get_values()
    # → {"収容区域コード": "2700012345", "緯度座標": 34.60305778}
"""

from typing import Dict, List, Any, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLabel
)
from qgis.core import QgsFeature

from .field_widget_factory import FieldWidgetFactory
from ..utils import ErrorHandler


class DynamicFormBuilder:
    """
    動的フォームビルダー
    
    責務:
        - フィールド設定リストからフォームUIを生成
        - セクション単位でグループボックスを作成
        - フィールド値の取得・設定
    
    Attributes:
        _config_manager: 設定マネージャ
        _widgets: フィールド名 → ウィジェットのマッピング
        _field_configs: フィールド名 → フィールド設定のマッピング
    
    Note:
        基本属性ダイアログで使用
    """
    
    def __init__(self, config_manager):
        """
        初期化
        
        Args:
            config_manager: 設定マネージャ
        """
        self._config_manager = config_manager
        self._widgets: Dict[str, QWidget] = {}
        self._field_configs: Dict[str, Dict] = {}
    
    def build(
        self,
        fields_config: List[Dict[str, Any]],
        feature: Optional[QgsFeature] = None
    ) -> QWidget:
        """
        フィールド設定からフォームを構築
        
        Args:
            fields_config: フィールド設定リスト
                [
                    {
                        "name": "収容区域コード",
                        "label": "収容区域コード",
                        "type": "text",
                        "editable": False,
                        "section": "識別情報"
                    },
                    ...
                ]
            feature: 初期値をセットする地物（オプション）
        
        Returns:
            構築されたフォームウィジェット
        
        処理フロー:
            1. セクションごとにフィールドをグループ化
            2. 各セクションのグループボックスを作成
            3. フィールドウィジェットを生成・配置
            4. featureが指定されていれば初期値をセット
        
        Example:
            builder = DynamicFormBuilder(config_manager)
            form = builder.build(fields_config, feature)
            parent_layout.addWidget(form)
        """
        # ウィジェット管理辞書をクリア
        self._widgets.clear()
        self._field_configs.clear()
        
        # メインコンテナ
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # セクションごとにグループ化
        sections = self._group_by_section(fields_config)
        
        # 各セクションのグループボックスを作成
        for section_name, fields in sections.items():
            group_box = self._create_section_group(section_name, fields, feature)
            layout.addWidget(group_box)
        
        layout.addStretch()
        
        ErrorHandler.log_debug(
            f"DynamicFormBuilder: {len(self._widgets)}個のフィールドを構築"
        )
        
        return container
    
    def _group_by_section(
        self,
        fields_config: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        フィールドをセクションごとにグループ化
        
        Args:
            fields_config: フィールド設定リスト
        
        Returns:
            セクション名 → フィールド設定リストの辞書
        
        Note:
            sectionが指定されていないフィールドは"その他"セクションに分類
        
        Example:
            sections = {
                "識別情報": [field1, field2],
                "位置情報": [field3, field4],
                "その他": [field5]
            }
        """
        sections: Dict[str, List[Dict[str, Any]]] = {}
        
        for field_config in fields_config:
            section_name = field_config.get("section", "その他")
            
            if section_name not in sections:
                sections[section_name] = []
            
            sections[section_name].append(field_config)
        
        return sections
    
    def _create_section_group(
        self,
        section_name: str,
        fields: List[Dict[str, Any]],
        feature: Optional[QgsFeature] = None
    ) -> QGroupBox:
        """
        セクションのグループボックスを作成
        
        Args:
            section_name: セクション名
            fields: このセクションのフィールド設定リスト
            feature: 初期値をセットする地物（オプション）
        
        Returns:
            グループボックス
        
        処理:
            1. QGroupBoxを作成
            2. QFormLayoutでフィールドを配置
            3. 各フィールドのラベルとウィジェットを追加
        """
        group_box = QGroupBox(section_name)
        group_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        form_layout = QFormLayout(group_box)
        form_layout.setContentsMargins(12, 20, 12, 12)
        form_layout.setSpacing(8)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        # 各フィールドを追加
        for field_config in fields:
            self._add_field_to_form(form_layout, field_config, feature)
        
        return group_box
    
    def _add_field_to_form(
        self,
        form_layout: QFormLayout,
        field_config: Dict[str, Any],
        feature: Optional[QgsFeature] = None
    ) -> None:
        """
        フォームレイアウトにフィールドを追加
        
        Args:
            form_layout: フォームレイアウト
            field_config: フィールド設定
            feature: 初期値をセットする地物（オプション）
        
        処理:
            1. フィールド設定を保存
            2. 初期値を取得（featureから）
            3. FieldWidgetFactoryでウィジェット生成
            4. フォームレイアウトに追加
        """
        field_name = field_config.get("name")
        if not field_name:
            ErrorHandler.log_warning("フィールド名が指定されていません")
            return
        
        # フィールド設定を保存
        self._field_configs[field_name] = field_config
        
        # 初期値を取得
        value = None
        if feature:
            try:
                value = feature[field_name]
            except KeyError:
                ErrorHandler.log_warning(
                    f"フィールドが地物に存在しません: {field_name}"
                )
        
        # ウィジェット生成
        field_type = field_config.get("type", "text")
        try:
            widget = FieldWidgetFactory.create(
                field_type,
                field_config,
                value,
                self._config_manager
            )
            
            # ウィジェットを保存
            self._widgets[field_name] = widget
            
            # ラベル
            label_text = field_config.get("label", field_name)
            label = QLabel(f"{label_text}:")
            
            # フォームに追加
            form_layout.addRow(label, widget)
            
        except Exception as e:
            ErrorHandler.log_error(
                f"フィールドウィジェット生成エラー: {field_name} - {str(e)}"
            )
    
    def set_values(self, feature: QgsFeature) -> None:
        """
        地物の値をフォームにセット
        
        Args:
            feature: 地物
        
        処理:
            全ウィジェットに対応する地物の属性値をセット
        
        Example:
            builder.set_values(feature)
        """
        for field_name, widget in self._widgets.items():
            try:
                value = feature[field_name]
                FieldWidgetFactory.set_widget_value(widget, value)
            except KeyError:
                ErrorHandler.log_warning(
                    f"フィールドが地物に存在しません: {field_name}"
                )
            except Exception as e:
                ErrorHandler.log_error(
                    f"値の設定エラー: {field_name} - {str(e)}"
                )
    
    def get_values(self) -> Dict[str, Any]:
        """
        フォームから値を取得
        
        Returns:
            フィールド名 → 値の辞書
        
        Note:
            編集可能なフィールドのみ取得することも可能
            （現状は全フィールドを取得）
        
        Example:
            values = builder.get_values()
            # → {"収容区域コード": "2700012345", "設備番号": "1"}
        """
        values = {}
        
        for field_name, widget in self._widgets.items():
            try:
                value = FieldWidgetFactory.get_widget_value(widget)
                values[field_name] = value
            except Exception as e:
                ErrorHandler.log_error(
                    f"値の取得エラー: {field_name} - {str(e)}"
                )
        
        return values
    
    def get_editable_values(self) -> Dict[str, Any]:
        """
        編集可能なフィールドの値のみを取得
        
        Returns:
            フィールド名 → 値の辞書（編集可能なもののみ）
        
        Note:
            データ保存時に使用
        
        Example:
            editable_values = builder.get_editable_values()
        """
        values = {}
        
        for field_name, widget in self._widgets.items():
            # 編集可能かチェック
            field_config = self._field_configs.get(field_name, {})
            editable = field_config.get("editable", True)
            
            if editable:
                try:
                    value = FieldWidgetFactory.get_widget_value(widget)
                    values[field_name] = value
                except Exception as e:
                    ErrorHandler.log_error(
                        f"値の取得エラー: {field_name} - {str(e)}"
                    )
        
        return values
    
    def clear(self) -> None:
        """
        フォームをクリア（全ウィジェットを空にする）
        
        Example:
            builder.clear()
        """
        for field_name, widget in self._widgets.items():
            try:
                FieldWidgetFactory.set_widget_value(widget, None)
            except Exception as e:
                ErrorHandler.log_error(
                    f"クリアエラー: {field_name} - {str(e)}"
                )
    
    def get_widget(self, field_name: str) -> Optional[QWidget]:
        """
        フィールド名からウィジェットを取得
        
        Args:
            field_name: フィールド名
        
        Returns:
            ウィジェット（存在しない場合はNone）
        
        Note:
            特定のウィジェットに直接アクセスする必要がある場合に使用
        
        Example:
            widget = builder.get_widget("設備番号")
            if widget:
                widget.setFocus()
        """
        return self._widgets.get(field_name)
    
    def has_field(self, field_name: str) -> bool:
        """
        指定したフィールドが存在するか確認
        
        Args:
            field_name: フィールド名
        
        Returns:
            存在すればTrue
        
        Example:
            if builder.has_field("設備番号"):
                value = builder.get_widget("設備番号").text()
        """
        return field_name in self._widgets
    
    def get_field_count(self) -> int:
        """
        フィールド数を取得
        
        Returns:
            フィールド数
        
        Example:
            count = builder.get_field_count()
        """
        return len(self._widgets)
