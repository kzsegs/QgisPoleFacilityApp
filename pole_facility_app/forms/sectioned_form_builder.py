# -*- coding: utf-8 -*-
"""
Sectioned Form Builder Module

セクション構成に基づいて複雑なフォームを生成するビルダークラス。
主に検査項目ダイアログで使用。

機能:
    - セクション単位での詳細なフォーム構築
    - バリデーション機能
    - 必須フィールドチェック
    - 値の取得・設定

使用例:
    from pole_facility_app.forms import SectionedFormBuilder
    
    # フォーム構築
    builder = SectionedFormBuilder(config_manager)
    
    sections_config = [
        {
            "name": "inspection_1",
            "label": "検査箇所1",
            "fields": [
                {
                    "name": "検査箇所1",
                    "label": "検査箇所",
                    "type": "text",
                    "editable": True,
                    "required": False
                },
                {
                    "name": "検査状態1",
                    "label": "検査状態",
                    "type": "dropdown",
                    "editable": True,
                    "choices_key": "status_1",
                    "required": False
                }
            ]
        }
    ]
    
    form_widget = builder.build(sections_config, feature)
    
    # バリデーション
    is_valid, errors = builder.validate()
    
    # 値の取得
    values = builder.get_values()
"""

from typing import Dict, List, Any, Optional, Tuple
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLabel
)
from qgis.core import QgsFeature

from .field_widget_factory import FieldWidgetFactory
from ..utils import ErrorHandler


class SectionedFormBuilder:
    """
    セクション分けフォームビルダー
    
    責務:
        - セクション構成からフォームUIを生成
        - 各セクション内にフィールドを配置
        - フィールド値のバリデーション
        - 値の取得・設定
    
    Attributes:
        _config_manager: 設定マネージャ
        _widgets: フィールド名 → ウィジェットのマッピング
        _field_configs: フィールド名 → フィールド設定のマッピング
        _section_configs: セクション名 → セクション設定のマッピング
    
    Note:
        検査項目ダイアログで使用
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
        self._section_configs: Dict[str, Dict] = {}
    
    def build(
        self,
        sections_config: List[Dict[str, Any]],
        feature: Optional[QgsFeature] = None
    ) -> QWidget:
        """
        セクション構成からフォームを構築
        
        Args:
            sections_config: セクション設定リスト
                [
                    {
                        "name": "inspection_1",
                        "label": "検査箇所1",
                        "fields": [
                            {
                                "name": "検査箇所1",
                                "label": "検査箇所",
                                "type": "text",
                                "editable": True,
                                "required": False
                            },
                            ...
                        ]
                    },
                    ...
                ]
            feature: 初期値をセットする地物（オプション）
        
        Returns:
            構築されたフォームウィジェット
        
        処理フロー:
            1. ウィジェット管理辞書をクリア
            2. 各セクションのグループボックスを作成
            3. セクション内の各フィールドウィジェットを生成
            4. featureが指定されていれば初期値をセット
        
        Example:
            builder = SectionedFormBuilder(config_manager)
            form = builder.build(sections_config, feature)
            parent_layout.addWidget(form)
        """
        # ウィジェット管理辞書をクリア
        self._widgets.clear()
        self._field_configs.clear()
        self._section_configs.clear()
        
        # メインコンテナ
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 各セクションを作成
        for section_config in sections_config:
            section_name = section_config.get("name")
            if section_name:
                self._section_configs[section_name] = section_config
            
            group_box = self._create_section(section_config, feature)
            layout.addWidget(group_box)
        
        layout.addStretch()
        
        ErrorHandler.log_debug(
            f"SectionedFormBuilder: {len(sections_config)}個のセクション、"
            f"{len(self._widgets)}個のフィールドを構築"
        )
        
        return container
    
    def _create_section(
        self,
        section_config: Dict[str, Any],
        feature: Optional[QgsFeature] = None
    ) -> QGroupBox:
        """
        セクションのグループボックスを作成
        
        Args:
            section_config: セクション設定
                {
                    "name": "inspection_1",
                    "label": "検査箇所1",
                    "fields": [...]
                }
            feature: 初期値をセットする地物（オプション）
        
        Returns:
            グループボックス
        
        処理:
            1. QGroupBoxを作成（セクションラベル）
            2. QFormLayoutでフィールドを配置
            3. 各フィールドウィジェットを生成・追加
        """
        section_label = section_config.get("label", "セクション")
        
        group_box = QGroupBox(section_label)
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
        
        # セクション内の各フィールドを追加
        fields = section_config.get("fields", [])
        for field_config in fields:
            self._add_field_to_section(form_layout, field_config, feature)
        
        return group_box
    
    def _add_field_to_section(
        self,
        form_layout: QFormLayout,
        field_config: Dict[str, Any],
        feature: Optional[QgsFeature] = None
    ) -> None:
        """
        セクションにフィールドを追加
        
        Args:
            form_layout: フォームレイアウト
            field_config: フィールド設定
            feature: 初期値をセットする地物（オプション）
        
        処理:
            1. フィールド設定を保存
            2. 初期値を取得（featureから）
            3. FieldWidgetFactoryでウィジェット生成
            4. フォームレイアウトに追加
            5. 必須フィールドの場合はラベルにマーク
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
            
            # ラベル（必須フィールドの場合は*マーク）
            label_text = field_config.get("label", field_name)
            required = field_config.get("required", False)
            
            if required:
                label_text += " *"
            
            label = QLabel(f"{label_text}:")
            
            # 必須フィールドのラベルスタイル
            if required:
                label.setStyleSheet("QLabel { color: #dc3545; }")
            
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
            編集可能なフィールドのみ取得
        
        Example:
            values = builder.get_values()
            # → {"検査箇所1": "設備1", "検査状態1": "状態1A"}
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
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        フォームのバリデーション
        
        Returns:
            (is_valid, errors)
            - is_valid: バリデーション成功ならTrue
            - errors: エラーメッセージのリスト
        
        バリデーションルール:
            1. 必須フィールドが入力されているか
            2. 将来的に追加可能な他のルール
        
        Example:
            is_valid, errors = builder.validate()
            if not is_valid:
                ErrorHandler.handle_validation_error(errors, self)
        """
        errors = []
        
        for field_name, widget in self._widgets.items():
            field_config = self._field_configs.get(field_name, {})
            
            # 必須チェック
            required = field_config.get("required", False)
            if required:
                try:
                    value = FieldWidgetFactory.get_widget_value(widget)
                    
                    # 値が空かチェック
                    is_empty = False
                    if value is None:
                        is_empty = True
                    elif isinstance(value, str) and not value.strip():
                        is_empty = True
                    elif isinstance(value, bool):
                        # チェックボックスの場合はFalseでもOK
                        is_empty = False
                    
                    if is_empty:
                        label = field_config.get("label", field_name)
                        errors.append(f"{label}は必須項目です")
                
                except Exception as e:
                    ErrorHandler.log_error(
                        f"バリデーションエラー: {field_name} - {str(e)}"
                    )
                    errors.append(f"{field_name}の検証中にエラーが発生しました")
        
        # 将来的なバリデーションルール
        # - 数値範囲チェック
        # - 日付の妥当性チェック
        # - フィールド間の整合性チェック
        # などを追加可能
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            ErrorHandler.log_warning(
                f"バリデーションエラー: {len(errors)}件"
            )
        
        return is_valid, errors
    
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
        
        Example:
            widget = builder.get_widget("検査箇所1")
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
            if builder.has_field("検査箇所1"):
                value = builder.get_widget("検査箇所1").text()
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
    
    def get_section_count(self) -> int:
        """
        セクション数を取得
        
        Returns:
            セクション数
        
        Example:
            count = builder.get_section_count()
        """
        return len(self._section_configs)
    
    def reset_to_initial_values(self, feature: QgsFeature) -> None:
        """
        フォームを初期値（地物の元の値）にリセット
        
        Args:
            feature: 地物
        
        Note:
            キャンセル機能で使用
        
        Example:
            # キャンセルボタン押下時
            builder.reset_to_initial_values(original_feature)
        """
        self.set_values(feature)
        ErrorHandler.log_debug("フォームを初期値にリセットしました")
    
    def get_modified_fields(self, feature: QgsFeature) -> Dict[str, Any]:
        """
        変更されたフィールドのみを取得
        
        Args:
            feature: 元の地物（比較用）
        
        Returns:
            変更されたフィールド名 → 新しい値の辞書
        
        Note:
            差分保存機能で使用可能
        
        Example:
            modified = builder.get_modified_fields(original_feature)
            if modified:
                # 変更があった場合のみ保存
                save_changes(modified)
        """
        modified = {}
        current_values = self.get_values()
        
        for field_name, new_value in current_values.items():
            try:
                original_value = feature[field_name]
                
                # 値が変更されているかチェック
                if new_value != original_value:
                    modified[field_name] = new_value
            
            except KeyError:
                # フィールドが存在しない場合は変更とみなす
                modified[field_name] = new_value
            except Exception as e:
                ErrorHandler.log_error(
                    f"変更チェックエラー: {field_name} - {str(e)}"
                )
        
        return modified
