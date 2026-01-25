# -*- coding: utf-8 -*-
"""
Inspection Form Dialog - 検査項目ダイアログ

検査箇所・検査状態・総合判定・検査情報を管理するダイアログ。
複数ウィンドウUIの3つ目のダイアログ。

機能:
    - セクション分けされた検査項目フォーム
    - バリデーション（必須フィールドチェック）
    - データ保存（レイヤへの直接保存）
    - 変更検知とロールバック対応
"""

from typing import Optional
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QScrollArea, QWidget, QMessageBox
)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QTimer
from qgis.core import QgsFeature, QgsVectorLayer, QgsMessageLog, Qgis

from ..forms.sectioned_form_builder import SectionedFormBuilder


class InspectionFormDialog(QDialog):
    """
    検査項目ダイアログ
    
    使用例:
        dialog = InspectionFormDialog(config_manager, data_manager, parent)
        dialog.set_layer(layer)        # 必須：保存に必要
        dialog.set_feature(feature)    # 地物をセット
        dialog.show()
    
    表示セクション（デフォルト）:
        ■ 検査箇所1
            - 検査箇所1 (text)
            - 検査状態1 (dropdown)
            - 検査状態1備考 (textarea)
        
        ■ 検査箇所2
            - 検査箇所2 (text)
            - 検査状態2 (dropdown)
            - 検査状態2備考 (textarea)
        
        ■ 検査箇所3
            - 検査箇所3 (text)
            - 検査状態3 (dropdown)
            - 検査状態3備考 (textarea)
        
        ■ 総合判定
            - 総合判定結果1 (dropdown)
            - 総合判定結果1備考 (textarea)
        
        ■ 検査情報
            - 備考 (textarea)
            - 検査日 (date)
            - 検査者氏名 (text)
            - 確認者氏名 (text)
    """
    
    closed = pyqtSignal()  # ダイアログクローズ時のシグナル
    data_saved = pyqtSignal()  # データ保存完了時のシグナル
    
    def __init__(self, config_manager, data_manager, parent=None):
        """
        初期化
        
        Args:
            config_manager: ConfigManager インスタンス
            data_manager: DataManager インスタンス
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self._config_manager = config_manager
        self._data_manager = data_manager
        self._feature = None
        self._layer = None
        
        # フォームビルダー
        self._form_builder = None
        
        # セクション設定
        self._sections_config = []
        
        self._setup_window()
        self._load_sections_config()
        self._create_ui()
    
    def _setup_window(self):
        """ウィンドウ設定"""
        self.setWindowTitle("検査項目")
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowCloseButtonHint |
            Qt.WindowMinimizeButtonHint
        )
        self.resize(600, 700)
    
    def _load_sections_config(self):
        """
        セクション設定を読み込み
        
        default_config.json の field_categories.inspection.sections から取得
        
        デフォルト設定:
            [
                {
                    "name": "inspection_1",
                    "label": "検査箇所1",
                    "fields": [
                        {"name": "検査箇所1", "label": "検査箇所", "type": "text", ...},
                        {"name": "検査状態1", "label": "検査状態", "type": "dropdown", ...},
                        ...
                    ]
                },
                ...
            ]
        """
        try:
            # field_categories.inspection 取得
            field_categories = self._config_manager.get("field_categories", {})
            inspection_config = field_categories.get("inspection", {})
            
            if not inspection_config:
                QgsMessageLog.logMessage(
                    "InspectionFormDialog - field_categories.inspection が設定されていません",
                    "PoleFacility", Qgis.Warning
                )
                self._sections_config = self._get_default_config()
                return
            
            self._sections_config = inspection_config.get("sections", [])
            
            if not self._sections_config:
                QgsMessageLog.logMessage(
                    "InspectionFormDialog - セクション設定が空です",
                    "PoleFacility", Qgis.Warning
                )
                self._sections_config = self._get_default_config()
            
            QgsMessageLog.logMessage(
                f"InspectionFormDialog - セクション設定読み込み完了: {len(self._sections_config)}件",
                "PoleFacility", Qgis.Info
            )
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"InspectionFormDialog - 設定読み込みエラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
            self._sections_config = self._get_default_config()
    
    def _get_default_config(self) -> list:
        """
        デフォルトのセクション設定を返す
        
        Returns:
            list: セクション設定のリスト
        """
        return [
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
                        "choices_key": "status_choices",
                        "required": False
                    },
                    {
                        "name": "検査状態1備考",
                        "label": "備考",
                        "type": "textarea",
                        "editable": True,
                        "required": False
                    }
                ]
            },
            {
                "name": "inspection_2",
                "label": "検査箇所2",
                "fields": [
                    {
                        "name": "検査箇所2",
                        "label": "検査箇所",
                        "type": "text",
                        "editable": True,
                        "required": False
                    },
                    {
                        "name": "検査状態2",
                        "label": "検査状態",
                        "type": "dropdown",
                        "editable": True,
                        "choices_key": "status_choices",
                        "required": False
                    },
                    {
                        "name": "検査状態2備考",
                        "label": "備考",
                        "type": "textarea",
                        "editable": True,
                        "required": False
                    }
                ]
            },
            {
                "name": "inspection_3",
                "label": "検査箇所3",
                "fields": [
                    {
                        "name": "検査箇所3",
                        "label": "検査箇所",
                        "type": "text",
                        "editable": True,
                        "required": False
                    },
                    {
                        "name": "検査状態3",
                        "label": "検査状態",
                        "type": "dropdown",
                        "editable": True,
                        "choices_key": "status_choices",
                        "required": False
                    },
                    {
                        "name": "検査状態3備考",
                        "label": "備考",
                        "type": "textarea",
                        "editable": True,
                        "required": False
                    }
                ]
            },
            {
                "name": "judgment",
                "label": "総合判定",
                "fields": [
                    {
                        "name": "総合判定結果1",
                        "label": "判定結果",
                        "type": "dropdown",
                        "editable": True,
                        "choices": ["合格", "要注意", "要修繕", "不合格"],
                        "required": False
                    },
                    {
                        "name": "総合判定結果1備考",
                        "label": "備考",
                        "type": "textarea",
                        "editable": True,
                        "required": False
                    }
                ]
            },
            {
                "name": "inspection_info",
                "label": "検査情報",
                "fields": [
                    {
                        "name": "備考",
                        "label": "全体備考",
                        "type": "textarea",
                        "editable": True,
                        "required": False
                    },
                    {
                        "name": "検査日",
                        "label": "検査日",
                        "type": "date",
                        "editable": True,
                        "required": False
                    },
                    {
                        "name": "検査者氏名",
                        "label": "検査者",
                        "type": "text",
                        "editable": True,
                        "required": False
                    },
                    {
                        "name": "確認者氏名",
                        "label": "確認者",
                        "type": "text",
                        "editable": True,
                        "required": False
                    }
                ]
            }
        ]
    
    def _create_ui(self):
        """
        UI作成
        
        レイアウト:
            [タイトル]
            [スクロールエリア]
                [フォーム（SectionedFormBuilder）]
            [保存][キャンセル][閉じる]
        """
        # メインレイアウト
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        # タイトル
        title_label = QLabel("検査項目", self)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #333;
                padding-bottom: 8px;
                border-bottom: 2px solid #007AFF;
            }
        """)
        main_layout.addWidget(title_label)
        
        # スクロールエリア（インスタンス変数として保持）
        self._scroll_area = QScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # フォームビルダー初期化
        self._form_builder = SectionedFormBuilder(self._config_manager)
        
        # フォームは set_feature() で構築
        # ここではプレースホルダーのみ配置
        self._form_placeholder = None  # 明示的にNone初期化
        placeholder = QWidget()
        placeholder.setStyleSheet("background-color: #f8f9fa;")
        self._scroll_area.setWidget(placeholder)
        self._form_placeholder = placeholder
        
        main_layout.addWidget(self._scroll_area)
        
        # ボタンエリア
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 保存ボタン
        save_button = QPushButton("保存", self)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                padding: 8px 24px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0051D5;
            }
            QPushButton:pressed {
                background-color: #004BB5;
            }
        """)
        save_button.clicked.connect(self._on_save_clicked)
        button_layout.addWidget(save_button)
        
        # キャンセルボタン
        cancel_button = QPushButton("キャンセル", self)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: #333;
                border: none;
                padding: 8px 24px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
            QPushButton:pressed {
                background-color: #d39e00;
            }
        """)
        cancel_button.clicked.connect(self._on_cancel_clicked)
        button_layout.addWidget(cancel_button)
        
        # 閉じるボタン
        close_button = QPushButton("閉じる", self)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 24px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
        """)
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)
        
        main_layout.addLayout(button_layout)
    
    def set_layer(self, layer: QgsVectorLayer):
        """
        レイヤをセット
        
        Args:
            layer: 対象レイヤ
        
        Note:
            データ保存に使用するため必須。
            set_featureの前に呼び出すこと。
        """
        self._layer = layer
        
        QgsMessageLog.logMessage(
            f"InspectionFormDialog - レイヤ設定完了: {layer.name() if layer else 'None'}",
            "PoleFacility", Qgis.Info
        )
    
    def set_feature(self, feature: QgsFeature):
        """
        地物をセット
        
        Args:
            feature: 地物オブジェクト
        
        処理フロー:
            1. 地物を保存
            2. フォームを構築（SectionedFormBuilder.build()）
            3. ウィンドウタイトルを更新
        """
        try:
            self._feature = feature
            
            if not feature or not feature.isValid():
                QgsMessageLog.logMessage(
                    "InspectionFormDialog - 無効な地物が指定されました",
                    "PoleFacility", Qgis.Warning
                )
                return
            
            # レイヤチェック
            if not self._layer:
                QgsMessageLog.logMessage(
                    "InspectionFormDialog - レイヤが設定されていません。set_layer()を先に呼び出してください。",
                    "PoleFacility", Qgis.Warning
                )
            
            # フォーム構築
            form_widget = self._form_builder.build(self._sections_config, feature)
            
            # 既存のフォームを置き換え
            if self._form_placeholder is not None:
                # 古いウィジェットを保存
                old_widget = self._form_placeholder
                
                # 新しいウィジェットをセット
                self._scroll_area.setWidget(form_widget)
                self._form_placeholder = form_widget
                
                # 古いウィジェットを削除（安全にチェック）
                try:
                    if not old_widget.isWidgetType():
                        # 既に削除されている
                        pass
                    else:
                        # タイミングをずらして削除
                        QTimer.singleShot(0, old_widget.deleteLater)
                except RuntimeError:
                    # 既に削除済み
                    pass
            else:
                # 初回作成
                self._scroll_area.setWidget(form_widget)
                self._form_placeholder = form_widget
            
            # タイトル更新
            self._update_title()
            
            QgsMessageLog.logMessage(
                f"InspectionFormDialog - 地物設定完了: feature_id={feature.id()}, "
                f"セクション数={self._form_builder.get_section_count()}, "
                f"フィールド数={self._form_builder.get_field_count()}",
                "PoleFacility", Qgis.Info
            )
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"InspectionFormDialog - set_feature エラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
    
    def refresh(self):
        """
        表示を更新
        
        現在の地物で再構築
        """
        if self._feature:
            self.set_feature(self._feature)
    
    def _update_title(self):
        """
        ウィンドウタイトルを更新
        
        タイトル形式: "検査項目 - 設備番号: X"
        """
        if not self._feature:
            return
        
        try:
            # 設備番号を取得
            equipment_number = self._feature["設備番号"] if "設備番号" in self._feature.fields().names() else ""
            
            if equipment_number:
                self.setWindowTitle(f"検査項目 - 設備番号: {equipment_number}")
            else:
                self.setWindowTitle("検査項目")
        
        except Exception as e:
            QgsMessageLog.logMessage(
                f"InspectionFormDialog - タイトル更新エラー: {str(e)}",
                "PoleFacility", Qgis.Warning
            )
            self.setWindowTitle("検査項目")
    
    def _on_save_clicked(self):
        """
        保存ボタンクリック時の処理
        
        処理フロー:
            1. バリデーション
            2. 編集モード開始（必要な場合）
            3. データ更新
            4. コミット
            5. イベント発行
        
        エラー処理:
            - バリデーションエラー → 警告ダイアログ表示
            - 保存エラー → ロールバック + エラーダイアログ表示
        """
        try:
            # 1. バリデーション
            is_valid, errors = self._form_builder.validate()
            if not is_valid:
                error_message = "入力エラーがあります:\n\n" + "\n".join(errors)
                QMessageBox.warning(self, "入力エラー", error_message)
                QgsMessageLog.logMessage(
                    f"InspectionFormDialog - バリデーションエラー: {len(errors)}件",
                    "PoleFacility", Qgis.Warning
                )
                return
            
            # レイヤチェック
            if not self._layer:
                raise RuntimeError("レイヤが設定されていません")
            
            if not self._feature:
                raise RuntimeError("地物が設定されていません")
            
            # 2. 編集モード開始（必要な場合）
            was_editing = self._layer.isEditable()
            if not was_editing:
                if not self._layer.startEditing():
                    raise RuntimeError("編集モードを開始できません")
            
            try:
                # 3. データ更新
                values = self._form_builder.get_values()
                
                for field_name, value in values.items():
                    field_idx = self._layer.fields().indexOf(field_name)
                    if field_idx >= 0:
                        success = self._layer.changeAttributeValue(
                            self._feature.id(), field_idx, value
                        )
                        if not success:
                            QgsMessageLog.logMessage(
                                f"InspectionFormDialog - フィールド更新失敗: {field_name}",
                                "PoleFacility", Qgis.Warning
                            )
                    else:
                        QgsMessageLog.logMessage(
                            f"InspectionFormDialog - フィールドが見つかりません: {field_name}",
                            "PoleFacility", Qgis.Warning
                        )
                
                # 4. コミット（編集モードを開始した場合のみ）
                if not was_editing:
                    if not self._layer.commitChanges():
                        errors = self._layer.commitErrors()
                        error_message = "\n".join(errors) if errors else "不明なエラー"
                        raise RuntimeError(f"コミット失敗: {error_message}")
                
                # 5. 成功通知
                QMessageBox.information(self, "保存完了", "検査項目を保存しました。")
                
                QgsMessageLog.logMessage(
                    f"InspectionFormDialog - 保存完了: feature_id={self._feature.id()}, "
                    f"更新フィールド数={len(values)}",
                    "PoleFacility", Qgis.Info
                )
                
                # イベント発行
                self.data_saved.emit()
                
            except Exception as e:
                # ロールバック
                if not was_editing and self._layer.isEditable():
                    self._layer.rollBack()
                    QgsMessageLog.logMessage(
                        "InspectionFormDialog - ロールバック実行",
                        "PoleFacility", Qgis.Warning
                    )
                raise
        
        except Exception as e:
            error_message = f"保存中にエラーが発生しました:\n\n{str(e)}"
            QMessageBox.critical(self, "保存エラー", error_message)
            QgsMessageLog.logMessage(
                f"InspectionFormDialog - 保存エラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
    
    def _on_cancel_clicked(self):
        """
        キャンセルボタンクリック時の処理
        
        処理:
            フォームを初期値にリセット
        """
        if self._feature and self._form_builder:
            reply = QMessageBox.question(
                self,
                "キャンセル確認",
                "変更を破棄して初期値に戻しますか？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self._form_builder.reset_to_initial_values(self._feature)
                QgsMessageLog.logMessage(
                    "InspectionFormDialog - キャンセル: 初期値にリセットしました",
                    "PoleFacility", Qgis.Info
                )
    
    def closeEvent(self, event):
        """
        クローズイベント
        
        Args:
            event: QCloseEvent
        
        処理:
            closed シグナルを発行してから閉じる
        """
        QgsMessageLog.logMessage(
            "InspectionFormDialog - ダイアログを閉じます",
            "PoleFacility", Qgis.Info
        )
        
        self.closed.emit()
        super().closeEvent(event)
    
    def get_values(self) -> dict:
        """
        フォームの値を取得
        
        Returns:
            dict: {field_name: value, ...}
        
        Note:
            編集可能なフィールドのみ取得
        """
        if self._form_builder:
            return self._form_builder.get_values()
        return {}
    
    def get_modified_fields(self) -> dict:
        """
        変更されたフィールドのみを取得
        
        Returns:
            dict: {field_name: value, ...}
        """
        if self._form_builder and self._feature:
            return self._form_builder.get_modified_fields(self._feature)
        return {}
