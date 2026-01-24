# -*- coding: utf-8 -*-
"""
Field Widget Factory Module

フォームフィールドのウィジェットを生成するファクトリクラス。
設定に基づいて適切な入力ウィジェットを動的に作成する。

対応する入力タイプ:
    - text: 単一行テキスト入力 (QLineEdit)
    - textarea: 複数行テキスト入力 (QTextEdit)
    - dropdown: 選択肢からの選択 (QComboBox)
    - checkbox: チェックボックス (QCheckBox)
    - date: 日付選択 (QDateEdit)
    - number: 数値入力 (QSpinBox)

使用例:
    from pole_facility_app.forms import FieldWidgetFactory
    
    # テキスト入力
    widget = FieldWidgetFactory.create(
        "text",
        {"editable": True, "placeholder": "入力してください"},
        "初期値"
    )
    
    # ドロップダウン（choices_key指定）
    widget = FieldWidgetFactory.create(
        "dropdown",
        {"choices_key": "status_1", "editable": True},
        "状態1A",
        config_manager
    )
    
    # ドロップダウン（choices直接指定）
    widget = FieldWidgetFactory.create(
        "dropdown",
        {"choices": ["合格", "不合格"], "editable": True},
        "合格"
    )
"""

from typing import Any, Optional, Dict
from PyQt5.QtWidgets import (
    QWidget, QLineEdit, QTextEdit, QComboBox, 
    QCheckBox, QDateEdit, QSpinBox
)
from PyQt5.QtCore import QDate

from ..utils import ErrorHandler


class FieldWidgetFactory:
    """
    フィールドウィジェットファクトリ
    
    機能:
        - 入力タイプに応じた適切なウィジェットを生成
        - 初期値のセット
        - 編集可否の制御
        - ドロップダウンの選択肢管理（設定ファイル参照/直接指定）
    
    Note:
        全メソッドはstaticmethodとして実装
    """
    
    @staticmethod
    def create(
        field_type: str,
        config: Dict[str, Any],
        value: Any = None,
        config_manager = None
    ) -> QWidget:
        """
        フィールドタイプに応じたウィジェットを生成
        
        Args:
            field_type: フィールドタイプ ("text", "dropdown", etc.)
            config: フィールド設定辞書
                - editable (bool): 編集可否
                - placeholder (str): プレースホルダ（text用）
                - choices (list): 選択肢リスト（dropdown用）
                - choices_key (str): 選択肢参照キー（dropdown用）
                - min_value (int): 最小値（number用）
                - max_value (int): 最大値（number用）
            value: 初期値
            config_manager: 設定マネージャ（choices_key使用時に必要）
        
        Returns:
            生成されたウィジェット
        
        Raises:
            ValueError: 未対応のフィールドタイプ
        
        Example:
            # テキストフィールド
            widget = FieldWidgetFactory.create(
                "text",
                {"editable": True, "placeholder": "設備名を入力"},
                "局前"
            )
            
            # ドロップダウン（設定ファイル参照）
            widget = FieldWidgetFactory.create(
                "dropdown",
                {"choices_key": "status_1", "editable": True},
                "状態1A",
                config_manager
            )
        """
        # タイプごとに対応するメソッドを呼び出し
        if field_type == "text":
            return FieldWidgetFactory._create_text(config, value)
        elif field_type == "textarea":
            return FieldWidgetFactory._create_textarea(config, value)
        elif field_type == "dropdown":
            return FieldWidgetFactory._create_dropdown(config, value, config_manager)
        elif field_type == "checkbox":
            return FieldWidgetFactory._create_checkbox(config, value)
        elif field_type == "date":
            return FieldWidgetFactory._create_date(config, value)
        elif field_type == "number":
            return FieldWidgetFactory._create_number(config, value)
        else:
            ErrorHandler.log_error(f"未対応のフィールドタイプ: {field_type}")
            raise ValueError(f"未対応のフィールドタイプ: {field_type}")
    
    @staticmethod
    def _create_text(config: Dict[str, Any], value: Any) -> QLineEdit:
        """
        テキスト入力ウィジェットを生成
        
        Args:
            config: フィールド設定
                - editable (bool): 編集可否
                - placeholder (str): プレースホルダテキスト
            value: 初期値
        
        Returns:
            QLineEdit
        
        設定例:
            {
                "type": "text",
                "editable": True,
                "placeholder": "設備名を入力してください"
            }
        """
        widget = QLineEdit()
        
        # 初期値セット
        if value is not None:
            widget.setText(str(value))
        
        # プレースホルダ
        placeholder = config.get("placeholder", "")
        if placeholder:
            widget.setPlaceholderText(placeholder)
        
        # 編集可否
        editable = config.get("editable", True)
        widget.setReadOnly(not editable)
        
        # 読み取り専用時のスタイル
        if not editable:
            widget.setStyleSheet("""
                QLineEdit {
                    background-color: #f8f9fa;
                    border: 1px solid #ced4da;
                    color: #6c757d;
                }
            """)
        
        return widget
    
    @staticmethod
    def _create_textarea(config: Dict[str, Any], value: Any) -> QTextEdit:
        """
        複数行テキスト入力ウィジェットを生成
        
        Args:
            config: フィールド設定
                - editable (bool): 編集可否
                - placeholder (str): プレースホルダテキスト
            value: 初期値
        
        Returns:
            QTextEdit
        
        設定例:
            {
                "type": "textarea",
                "editable": True,
                "placeholder": "備考を入力してください"
            }
        """
        widget = QTextEdit()
        
        # 初期値セット
        if value is not None:
            widget.setPlainText(str(value))
        
        # プレースホルダ
        placeholder = config.get("placeholder", "")
        if placeholder:
            widget.setPlaceholderText(placeholder)
        
        # 編集可否
        editable = config.get("editable", True)
        widget.setReadOnly(not editable)
        
        # 読み取り専用時のスタイル
        if not editable:
            widget.setStyleSheet("""
                QTextEdit {
                    background-color: #f8f9fa;
                    border: 1px solid #ced4da;
                    color: #6c757d;
                }
            """)
        
        return widget
    
    @staticmethod
    def _create_dropdown(
        config: Dict[str, Any], 
        value: Any,
        config_manager = None
    ) -> QComboBox:
        """
        ドロップダウンウィジェットを生成
        
        Args:
            config: フィールド設定
                - choices (list): 選択肢リスト（直接指定）
                - choices_key (str): 選択肢参照キー（設定ファイル参照）
                - editable (bool): 編集可否
            value: 初期値
            config_manager: 設定マネージャ（choices_key使用時に必要）
        
        Returns:
            QComboBox
        
        設定例:
            # 直接指定
            {
                "type": "dropdown",
                "choices": ["合格", "要注意", "不合格"],
                "editable": True
            }
            
            # 設定ファイル参照
            {
                "type": "dropdown",
                "choices_key": "status_1",
                "editable": True
            }
            # → default_config.json の inspection_status.status_1 を参照
        
        Note:
            choices_keyとchoicesの両方が指定された場合、choices_keyを優先
        """
        widget = QComboBox()
        
        # 選択肢の取得
        choices = []
        
        # 1. choices_key から取得（優先）
        choices_key = config.get("choices_key")
        if choices_key and config_manager:
            try:
                # inspection_status.{choices_key} から取得
                inspection_status = config_manager.get("inspection_status", {})
                choices = inspection_status.get(choices_key, [])
                
                if not choices:
                    ErrorHandler.log_warning(
                        f"選択肢が見つかりません: inspection_status.{choices_key}"
                    )
            except Exception as e:
                ErrorHandler.log_error(
                    f"選択肢の取得に失敗: {choices_key} - {str(e)}"
                )
        
        # 2. choices から取得（フォールバック）
        if not choices:
            choices = config.get("choices", [])
        
        # 選択肢をセット
        if choices:
            widget.addItems([str(choice) for choice in choices])
        else:
            ErrorHandler.log_warning("ドロップダウンの選択肢が空です")
        
        # 初期値の選択
        if value is not None:
            value_str = str(value)
            index = widget.findText(value_str)
            if index >= 0:
                widget.setCurrentIndex(index)
            else:
                ErrorHandler.log_debug(
                    f"初期値が選択肢に存在しません: {value_str}"
                )
        
        # 編集可否
        editable = config.get("editable", True)
        widget.setEnabled(editable)
        
        # 無効時のスタイル
        if not editable:
            widget.setStyleSheet("""
                QComboBox {
                    background-color: #f8f9fa;
                    color: #6c757d;
                }
            """)
        
        return widget
    
    @staticmethod
    def _create_checkbox(config: Dict[str, Any], value: Any) -> QCheckBox:
        """
        チェックボックスウィジェットを生成
        
        Args:
            config: フィールド設定
                - editable (bool): 編集可否
                - label (str): チェックボックスのラベル
            value: 初期値（bool, int, str等）
        
        Returns:
            QCheckBox
        
        設定例:
            {
                "type": "checkbox",
                "label": "完了",
                "editable": True
            }
        
        Note:
            value の真偽判定:
                True: True, 1, "1", "true", "True", "yes", "Yes"
                False: その他
        """
        widget = QCheckBox()
        
        # ラベル
        label = config.get("label", "")
        if label:
            widget.setText(label)
        
        # 初期値セット（真偽値に変換）
        if value is not None:
            checked = False
            if isinstance(value, bool):
                checked = value
            elif isinstance(value, int):
                checked = bool(value)
            elif isinstance(value, str):
                checked = value.lower() in ("1", "true", "yes")
            
            widget.setChecked(checked)
        
        # 編集可否
        editable = config.get("editable", True)
        widget.setEnabled(editable)
        
        return widget
    
    @staticmethod
    def _create_date(config: Dict[str, Any], value: Any) -> QDateEdit:
        """
        日付選択ウィジェットを生成
        
        Args:
            config: フィールド設定
                - editable (bool): 編集可否
                - format (str): 日付フォーマット（デフォルト: "yyyy/MM/dd"）
            value: 初期値（QDate, str等）
        
        Returns:
            QDateEdit
        
        設定例:
            {
                "type": "date",
                "editable": True,
                "format": "yyyy/MM/dd"
            }
        
        Note:
            valueがstrの場合、format指定に従ってパース
        """
        widget = QDateEdit()
        
        # カレンダーポップアップ有効化
        widget.setCalendarPopup(True)
        
        # 日付フォーマット
        date_format = config.get("format", "yyyy/MM/dd")
        widget.setDisplayFormat(date_format)
        
        # 初期値セット
        if value is not None:
            if isinstance(value, QDate):
                widget.setDate(value)
            elif isinstance(value, str) and value:
                try:
                    # 文字列から日付をパース
                    qdate = QDate.fromString(value, date_format)
                    if qdate.isValid():
                        widget.setDate(qdate)
                    else:
                        ErrorHandler.log_warning(
                            f"日付の解析に失敗: {value} (format: {date_format})"
                        )
                except Exception as e:
                    ErrorHandler.log_error(
                        f"日付の設定に失敗: {value} - {str(e)}"
                    )
        
        # 初期値がない場合は現在日付
        if value is None:
            widget.setDate(QDate.currentDate())
        
        # 編集可否
        editable = config.get("editable", True)
        widget.setReadOnly(not editable)
        widget.setEnabled(editable)
        
        # 読み取り専用時のスタイル
        if not editable:
            widget.setStyleSheet("""
                QDateEdit {
                    background-color: #f8f9fa;
                    color: #6c757d;
                }
            """)
        
        return widget
    
    @staticmethod
    def _create_number(config: Dict[str, Any], value: Any) -> QSpinBox:
        """
        数値入力ウィジェットを生成
        
        Args:
            config: フィールド設定
                - editable (bool): 編集可否
                - min_value (int): 最小値（デフォルト: 0）
                - max_value (int): 最大値（デフォルト: 99999）
            value: 初期値
        
        Returns:
            QSpinBox
        
        設定例:
            {
                "type": "number",
                "editable": True,
                "min_value": 0,
                "max_value": 1000
            }
        """
        widget = QSpinBox()
        
        # 範囲設定
        min_value = config.get("min_value", 0)
        max_value = config.get("max_value", 99999)
        widget.setRange(min_value, max_value)
        
        # 初期値セット
        if value is not None:
            try:
                int_value = int(value)
                widget.setValue(int_value)
            except (ValueError, TypeError):
                ErrorHandler.log_warning(
                    f"数値への変換に失敗: {value}"
                )
        
        # 編集可否
        editable = config.get("editable", True)
        widget.setReadOnly(not editable)
        widget.setEnabled(editable)
        
        # 読み取り専用時のスタイル
        if not editable:
            widget.setStyleSheet("""
                QSpinBox {
                    background-color: #f8f9fa;
                    color: #6c757d;
                }
            """)
        
        return widget
    
    @staticmethod
    def get_widget_value(widget: QWidget) -> Any:
        """
        ウィジェットから値を取得
        
        Args:
            widget: 対象ウィジェット
        
        Returns:
            ウィジェットの現在値
        
        Note:
            FormBuilderから呼び出されることを想定
        
        Example:
            value = FieldWidgetFactory.get_widget_value(line_edit)
        """
        if isinstance(widget, QLineEdit):
            return widget.text()
        elif isinstance(widget, QTextEdit):
            return widget.toPlainText()
        elif isinstance(widget, QComboBox):
            return widget.currentText()
        elif isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QDateEdit):
            return widget.date().toString("yyyy/MM/dd")
        elif isinstance(widget, QSpinBox):
            return widget.value()
        else:
            ErrorHandler.log_warning(
                f"未対応のウィジェットタイプ: {type(widget)}"
            )
            return None
    
    @staticmethod
    def set_widget_value(widget: QWidget, value: Any) -> bool:
        """
        ウィジェットに値をセット
        
        Args:
            widget: 対象ウィジェット
            value: セットする値
        
        Returns:
            成功した場合True
        
        Note:
            FormBuilderから呼び出されることを想定
        
        Example:
            success = FieldWidgetFactory.set_widget_value(line_edit, "新しい値")
        """
        try:
            if isinstance(widget, QLineEdit):
                widget.setText(str(value) if value is not None else "")
                return True
            elif isinstance(widget, QTextEdit):
                widget.setPlainText(str(value) if value is not None else "")
                return True
            elif isinstance(widget, QComboBox):
                if value is not None:
                    index = widget.findText(str(value))
                    if index >= 0:
                        widget.setCurrentIndex(index)
                        return True
                return False
            elif isinstance(widget, QCheckBox):
                checked = bool(value) if value is not None else False
                widget.setChecked(checked)
                return True
            elif isinstance(widget, QDateEdit):
                if isinstance(value, QDate):
                    widget.setDate(value)
                    return True
                elif isinstance(value, str) and value:
                    qdate = QDate.fromString(value, widget.displayFormat())
                    if qdate.isValid():
                        widget.setDate(qdate)
                        return True
                return False
            elif isinstance(widget, QSpinBox):
                widget.setValue(int(value) if value is not None else 0)
                return True
            else:
                ErrorHandler.log_warning(
                    f"未対応のウィジェットタイプ: {type(widget)}"
                )
                return False
        except Exception as e:
            ErrorHandler.log_error(
                f"ウィジェット値の設定に失敗: {str(e)}"
            )
            return False
