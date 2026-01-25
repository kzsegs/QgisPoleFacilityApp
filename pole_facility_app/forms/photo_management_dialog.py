# -*- coding: utf-8 -*-
"""
Photo Management Dialog - 写真管理ダイアログ

修正前写真3枚（読み取り専用）と修正後写真3枚（編集可能）を
同時に表示・管理するダイアログ。複数ウィンドウUIの2つ目のダイアログ。

機能:
    - 修正前写真3枚を PhotoViewerPanel で表示
    - 修正後写真3枚を PhotoEditorPanel で編集
    - 各写真の個別保存
    - レイヤへのデータ保存
"""

from typing import Optional, List
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QScrollArea, QWidget
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.core import QgsFeature, QgsVectorLayer, QgsMessageLog, Qgis

from ..photo.viewer_panel import PhotoViewerPanel
from ..photo.editor_panel import PhotoEditorPanel


class PhotoManagementDialog(QDialog):
    """
    写真管理ダイアログ
    
    使用例:
        dialog = PhotoManagementDialog(config_manager, data_manager, parent)
        dialog.set_layer(layer)        # 必須：保存に必要
        dialog.set_feature(feature)    # 地物をセット
        dialog.show()
    
    表示フィールド:
        修正前（ViewerPanel×3）:
            - 設備写真1URI_修正前
            - 設備写真2URI_修正前
            - 設備写真3URI_修正前
        
        修正後（EditorPanel×3）:
            - 設備写真1URI_修正後
            - 設備写真2URI_修正後
            - 設備写真3URI_修正後
    
    レイアウト:
        ┌─────────────────────────────────────────┐
        │ ■ 修正前写真                            │
        │ [Viewer1] [Viewer2] [Viewer3]           │
        │                                         │
        │ ■ 修正後写真                            │
        │ [Editor1] [Editor2] [Editor3]           │
        │                                         │
        │                         [閉じる]        │
        └─────────────────────────────────────────┘
    """
    
    closed = pyqtSignal()  # ダイアログクローズ時のシグナル
    photo_saved = pyqtSignal(str, str)  # (field_name, relative_path)
    
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
        
        # PhotoPanel リスト
        self._viewer_panels: List[PhotoViewerPanel] = []
        self._editor_panels: List[PhotoEditorPanel] = []
        
        # フィールド名定義
        self._before_fields = [
            "設備写真1URI_修正前",
            "設備写真2URI_修正前",
            "設備写真3URI_修正前"
        ]
        
        self._after_fields = [
            "設備写真1URI_修正後",
            "設備写真2URI_修正後",
            "設備写真3URI_修正後"
        ]
        
        self._setup_window()
        self._create_ui()
    
    def _setup_window(self):
        """ウィンドウ設定"""
        self.setWindowTitle("写真管理")
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowCloseButtonHint |
            Qt.WindowMinimizeButtonHint
        )
        self.resize(1000, 700)
    
    def _create_ui(self):
        """
        UI作成
        
        レイアウト:
            [タイトル]
            [修正前写真セクション]
                [Viewer1] [Viewer2] [Viewer3]
            [修正後写真セクション]
                [Editor1] [Editor2] [Editor3]
            [閉じるボタン]
        """
        # メインレイアウト
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        # タイトル
        title_label = QLabel("写真管理", self)
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
        
        # スクロールエリア
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(16)
        
        # ■ 修正前写真セクション
        before_group = self._create_before_section()
        scroll_layout.addWidget(before_group)
        
        # ■ 修正後写真セクション
        after_group = self._create_after_section()
        scroll_layout.addWidget(after_group)
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)
        
        # ボタンエリア
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
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
    
    def _create_before_section(self) -> QGroupBox:
        """
        修正前写真セクション作成
        
        Returns:
            QGroupBox: 修正前写真セクション
        
        レイアウト:
            [Viewer1] [Viewer2] [Viewer3]
        """
        group = QGroupBox("■ 修正前写真", self)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QHBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 20, 12, 12)
        
        # ViewerPanel × 3
        for i, field_name in enumerate(self._before_fields):
            panel = PhotoViewerPanel(self._config_manager, self)
            self._viewer_panels.append(panel)
            layout.addWidget(panel)
        
        return group
    
    def _create_after_section(self) -> QGroupBox:
        """
        修正後写真セクション作成
        
        Returns:
            QGroupBox: 修正後写真セクション
        
        レイアウト:
            [Editor1] [Editor2] [Editor3]
        """
        group = QGroupBox("■ 修正後写真", self)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        layout = QHBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 20, 12, 12)
        
        # EditorPanel × 3
        for i, field_name in enumerate(self._after_fields):
            panel = PhotoEditorPanel(
                self._config_manager,
                self._data_manager,
                self
            )
            
            # シグナル接続
            panel.photo_saved.connect(
                lambda path, fname=field_name: self._on_photo_saved(fname, path)
            )
            
            self._editor_panels.append(panel)
            layout.addWidget(panel)
        
        return group
    
    def set_layer(self, layer: QgsVectorLayer):
        """
        レイヤをセット
        
        Args:
            layer: 対象レイヤ
        
        Note:
            PhotoEditorPanelがデータ保存に使用するため必須。
            set_featureの前に呼び出すこと。
        
        処理フロー:
            1. レイヤを保存
            2. 各EditorPanelにレイヤをセット
        """
        self._layer = layer
        
        # 各EditorPanelにレイヤをセット
        for panel in self._editor_panels:
            panel.set_layer(layer)
        
        QgsMessageLog.logMessage(
            f"PhotoManagementDialog - レイヤ設定完了: {layer.name() if layer else 'None'}",
            "PoleFacility", Qgis.Info
        )
    
    def set_feature(self, feature: QgsFeature):
        """
        地物をセット
        
        Args:
            feature: 地物オブジェクト
        
        処理フロー:
            1. 地物を保存
            2. ViewerPanel × 3 に写真をセット
            3. EditorPanel × 3 に写真をセット
            4. ウィンドウタイトルを更新
        
        Note:
            set_layer()を先に呼び出す必要がある
        """
        try:
            self._feature = feature
            
            if not feature or not feature.isValid():
                QgsMessageLog.logMessage(
                    "PhotoManagementDialog - 無効な地物が指定されました",
                    "PoleFacility", Qgis.Warning
                )
                return
            
            # レイヤチェック
            if not self._layer:
                QgsMessageLog.logMessage(
                    "PhotoManagementDialog - レイヤが設定されていません。set_layer()を先に呼び出してください。",
                    "PoleFacility", Qgis.Warning
                )
            
            # ViewerPanel × 3 に写真をセット
            for i, (panel, field_name) in enumerate(zip(self._viewer_panels, self._before_fields)):
                try:
                    panel.set_photo(feature, field_name)
                    QgsMessageLog.logMessage(
                        f"PhotoManagementDialog - ViewerPanel[{i}] 設定完了: {field_name}",
                        "PoleFacility", Qgis.Info
                    )
                except Exception as e:
                    QgsMessageLog.logMessage(
                        f"PhotoManagementDialog - ViewerPanel[{i}] エラー: {str(e)}",
                        "PoleFacility", Qgis.Warning
                    )
            
            # EditorPanel × 3 に写真をセット
            for i, (panel, field_name, source_field_name) in enumerate(
                zip(self._editor_panels, self._after_fields, self._before_fields)
            ):
                try:
                    # 注: set_layer()は既に呼び出し済み
                    panel.set_photo(feature, field_name, source_field_name)
                    QgsMessageLog.logMessage(
                        f"PhotoManagementDialog - EditorPanel[{i}] 設定完了: {field_name} (source: {source_field_name})",
                        "PoleFacility", Qgis.Info
                    )
                except Exception as e:
                    QgsMessageLog.logMessage(
                        f"PhotoManagementDialog - EditorPanel[{i}] エラー: {str(e)}",
                        "PoleFacility", Qgis.Warning
                    )
            
            # タイトル更新
            self._update_title()
            
            QgsMessageLog.logMessage(
                f"PhotoManagementDialog - 地物設定完了: feature_id={feature.id()}",
                "PoleFacility", Qgis.Info
            )
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"PhotoManagementDialog - set_feature エラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
    
    def refresh(self):
        """
        表示を更新
        
        現在の地物で再読み込み
        """
        if self._feature:
            self.set_feature(self._feature)
    
    def _update_title(self):
        """
        ウィンドウタイトルを更新
        
        タイトル形式: "写真管理 - 設備番号: X"
        """
        if not self._feature:
            return
        
        try:
            # 設備番号を取得
            equipment_number = self._feature["設備番号"] if "設備番号" in self._feature.fields().names() else ""
            
            if equipment_number:
                self.setWindowTitle(f"写真管理 - 設備番号: {equipment_number}")
            else:
                self.setWindowTitle("写真管理")
        
        except Exception as e:
            QgsMessageLog.logMessage(
                f"PhotoManagementDialog - タイトル更新エラー: {str(e)}",
                "PoleFacility", Qgis.Warning
            )
            self.setWindowTitle("写真管理")
    
    def _on_photo_saved(self, field_name: str, relative_path: str):
        """
        写真保存完了時のハンドラ
        
        Args:
            field_name: フィールド名
            relative_path: 保存された相対パス
        
        処理:
            photo_saved シグナルを発行
        """
        QgsMessageLog.logMessage(
            f"PhotoManagementDialog - 写真保存完了: {field_name} → {relative_path}",
            "PoleFacility", Qgis.Info
        )
        
        # 外部にシグナル発行
        self.photo_saved.emit(field_name, relative_path)
    
    def closeEvent(self, event):
        """
        クローズイベント
        
        Args:
            event: QCloseEvent
        
        処理:
            closed シグナルを発行してから閉じる
        """
        QgsMessageLog.logMessage(
            "PhotoManagementDialog - ダイアログを閉じます",
            "PoleFacility", Qgis.Info
        )
        
        self.closed.emit()
        super().closeEvent(event)
    
    def get_viewer_panel(self, index: int) -> Optional[PhotoViewerPanel]:
        """
        指定インデックスのViewerPanelを取得
        
        Args:
            index: インデックス（0-2）
        
        Returns:
            PhotoViewerPanel: パネル、範囲外の場合は None
        """
        if 0 <= index < len(self._viewer_panels):
            return self._viewer_panels[index]
        return None
    
    def get_editor_panel(self, index: int) -> Optional[PhotoEditorPanel]:
        """
        指定インデックスのEditorPanelを取得
        
        Args:
            index: インデックス（0-2）
        
        Returns:
            PhotoEditorPanel: パネル、範囲外の場合は None
        """
        if 0 <= index < len(self._editor_panels):
            return self._editor_panels[index]
        return None
