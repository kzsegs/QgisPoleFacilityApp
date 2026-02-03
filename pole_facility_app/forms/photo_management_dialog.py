# -*- coding: utf-8 -*-
"""
Photo Management Dialog - 写真管理ダイアログ（Phase 3-A統合版・美的改善）

Phase 3-A対応: 4列レイアウト + 各行に拡大表示
既存のPhotoViewerPanel/PhotoEditorPanelを維持しつつ、
美しく整ったレイアウトを実現。

レイアウト:
    [サムネイル] [修正前(Viewer)] [拡大表示(Zoom)] [修正後(Editor)]
    各行ごとに拡大表示パネルを配置
"""

from typing import Optional, List
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QScrollArea, QWidget, QFrame
)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QEvent
from qgis.core import QgsFeature, QgsVectorLayer, QgsMessageLog, Qgis

from ..photo.viewer_panel import PhotoViewerPanel
from ..photo.editor_panel import PhotoEditorPanel
from ..photo.thumbnail_widget import ThumbnailWidget
from ..photo.zoom_panel import ZoomPanel


class HoverDetector(QWidget):
    """
    hover検出用ラッパーウィジェット
    """
    hovered = pyqtSignal(str)  # image_path
    
    def __init__(self, wrapped_widget, image_path_getter, parent=None):
        super().__init__(parent)
        self._wrapped_widget = wrapped_widget
        self._image_path_getter = image_path_getter
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(wrapped_widget)
        
        self.setMouseTracking(True)
        wrapped_widget.setMouseTracking(True)
        
        # 子ウィジェットにもイベントフィルタを設定
        self._install_event_filter_recursive(wrapped_widget)
    
    def _install_event_filter_recursive(self, widget):
        """再帰的にイベントフィルタを設定"""
        widget.installEventFilter(self)
        for child in widget.findChildren(QWidget):
            child.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """イベントフィルタ"""
        if event.type() == QEvent.Enter:
            image_path = self._image_path_getter()
            if image_path:
                self.hovered.emit(image_path)
        elif event.type() == QEvent.Leave:
            # 親ウィジェットの外に出た場合のみクリア
            if not self.rect().contains(self.mapFromGlobal(self.cursor().pos())):
                self.hovered.emit("")
        return super().eventFilter(obj, event)
    
    def enterEvent(self, event):
        """マウスオーバー時"""
        super().enterEvent(event)
        image_path = self._image_path_getter()
        if image_path:
            self.hovered.emit(image_path)
    
    def leaveEvent(self, event):
        """マウスアウト時"""
        super().leaveEvent(event)
        self.hovered.emit("")


class PhotoManagementDialog(QDialog):
    """
    写真管理ダイアログ（Phase 3-A統合版・美的改善）
    """
    
    closed = pyqtSignal()
    photo_saved = pyqtSignal(str, str)
    
    def __init__(self, config_manager, data_manager, parent=None):
        super().__init__(parent)
        
        self._config_manager = config_manager
        self._data_manager = data_manager
        self._feature = None
        self._layer = None
        
        # ウィジェットリスト
        self._thumbnail_widgets: List[ThumbnailWidget] = []
        self._viewer_panels: List[PhotoViewerPanel] = []
        self._editor_panels: List[PhotoEditorPanel] = []
        self._zoom_panels: List[ZoomPanel] = []
        
        # 画像パス保持用
        self._before_image_paths = ["", "", ""]
        self._after_image_paths = ["", "", ""]
        
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
        
        self._save_timer = None
        
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
        self.resize(1600, 900)
    
    def _create_ui(self):
        """UI作成"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        # タイトル
        title_label = QLabel("写真管理", self)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding-bottom: 12px;
                border-bottom: 3px solid #3498db;
            }
        """)
        main_layout.addWidget(title_label)
        
        # スクロールエリア
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background: transparent; }")
        
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("QWidget { background: white; }")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(12)
        
        # 各写真行を作成
        for i in range(len(self._before_fields)):
            row_widget = self._create_photo_row(i)
            scroll_layout.addWidget(row_widget)
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)
        
        # ボタンエリア
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_button = QPushButton("閉じる", self)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 10px 32px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7f8c8d; }
            QPushButton:pressed { background-color: #6c7a89; }
        """)
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)
        
        main_layout.addLayout(button_layout)
    
    def _create_photo_row(self, index: int) -> QWidget:
        """
        1行分の写真表示ウィジェットを作成
        
        Args:
            index: 行インデックス（0-2）
        
        Returns:
            QWidget: 1行分のウィジェット
        """
        row_widget = QFrame()
        row_widget.setFrameShape(QFrame.Box)
        row_widget.setStyleSheet("""
            QFrame {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        
        layout = QHBoxLayout(row_widget)
        layout.setSpacing(16)
        layout.setContentsMargins(12, 12, 12, 12)
        
        display_name = self._generate_display_name(self._before_fields[index])
        
        # 1. サムネイル列（固定幅100px）
        thumbnail_container = QWidget()
        thumbnail_container.setFixedWidth(100)
        thumbnail_layout = QVBoxLayout(thumbnail_container)
        thumbnail_layout.setContentsMargins(0, 0, 0, 0)
        thumbnail_layout.setSpacing(4)
        
        thumbnail = ThumbnailWidget(display_name, self._config_manager)
        self._thumbnail_widgets.append(thumbnail)
        thumbnail_layout.addWidget(thumbnail)
        thumbnail_layout.addStretch()
        
        layout.addWidget(thumbnail_container)
        
        # 2. 修正前列（固定幅320px）
        viewer_container = self._create_panel_container("修正前")
        viewer_container.setFixedWidth(320)
        
        viewer_panel = PhotoViewerPanel(self._config_manager)
        if viewer_panel.graphics_view:
            viewer_panel.graphics_view.setFixedSize(300, 200)
        
        # hover検出ラッパー
        viewer_wrapper = HoverDetector(
            viewer_panel,
            lambda idx=index: self._before_image_paths[idx]
        )
        viewer_wrapper.hovered.connect(lambda path, idx=index: self._on_viewer_hovered(idx, path))
        
        self._viewer_panels.append(viewer_panel)
        viewer_container.layout().addWidget(viewer_wrapper)
        
        layout.addWidget(viewer_container)
        
        # 3. 拡大表示列（固定幅440px）
        zoom_panel = ZoomPanel()
        zoom_panel.setFixedSize(440, 360)
        self._zoom_panels.append(zoom_panel)
        
        zoom_container = QWidget()
        zoom_container.setFixedWidth(440)
        zoom_layout = QVBoxLayout(zoom_container)
        zoom_layout.setContentsMargins(0, 0, 0, 0)
        zoom_layout.addWidget(zoom_panel)
        
        layout.addWidget(zoom_container)
        
        # 4. 修正後列（固定幅320px）
        editor_container = self._create_panel_container("修正後")
        editor_container.setFixedWidth(320)
        
        editor_panel = PhotoEditorPanel(self._config_manager, self._data_manager)
        if editor_panel.graphics_view:
            editor_panel.graphics_view.setFixedSize(300, 200)
        
        # シーン変更をリアルタイム監視
        if hasattr(editor_panel, 'graphics_scene') and editor_panel.graphics_scene:
            editor_panel.graphics_scene.changed.connect(
                lambda region, idx=index: self._on_editor_scene_changed(idx)
            )
        
        # hover検出ラッパー
        editor_wrapper = HoverDetector(
            editor_panel,
            lambda idx=index: self._after_image_paths[idx]
        )
        editor_wrapper.hovered.connect(lambda path, idx=index: self._on_editor_hovered(idx, path))
        
        # シグナル接続
        after_field = self._after_fields[index]
        editor_panel.photo_saved.connect(
            lambda path, fname=after_field: self._on_photo_saved(fname, path)
        )
        
        self._editor_panels.append(editor_panel)
        editor_container.layout().addWidget(editor_wrapper)
        
        layout.addWidget(editor_container)
        
        layout.addStretch()
        
        return row_widget
    
    def _create_panel_container(self, title: str) -> QWidget:
        """パネル用コンテナ作成"""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)
        
        # タイトルラベル（ファイルパス表示用の高さを確保）
        title_label = QLabel(title)
        title_label.setFixedHeight(20)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 11pt;
                color: #495057;
                background: #e9ecef;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        container_layout.addWidget(title_label)
        
        return container
    
    def _on_viewer_hovered(self, index: int, image_path: str):
        """修正前パネルhover時"""
        if index < len(self._zoom_panels):
            self._zoom_panels[index].show_image(image_path)
    
    def _on_editor_hovered(self, index: int, image_path: str):
        """修正後パネルhover時（シーン込み）"""
        if index < len(self._zoom_panels) and index < len(self._editor_panels):
            editor_panel = self._editor_panels[index]
            # EditorPanelのシーン全体を渡す
            scene = editor_panel.graphics_scene if hasattr(editor_panel, 'graphics_scene') else None
            self._zoom_panels[index].show_image(image_path, scene)
    
    def _on_editor_scene_changed(self, index: int):
        """EditorPanelのシーン変更時（リアルタイム更新）"""
        # 現在hoverしているパネルのみ更新
        if index < len(self._zoom_panels) and index < len(self._editor_panels):
            zoom_panel = self._zoom_panels[index]
            # 現在表示中のソースがこのパネルのシーンの場合のみ更新
            if zoom_panel._current_source_type == "scene":
                editor_panel = self._editor_panels[index]
                scene = editor_panel.graphics_scene if hasattr(editor_panel, 'graphics_scene') else None
                if scene:
                    zoom_panel.show_image("", scene)
    
    def _generate_display_name(self, field_name: str) -> str:
        """フィールド名から表示名を生成"""
        parts = field_name.split('_')
        if len(parts) > 1 and parts[-1] in ["修正前", "修正後"]:
            return '_'.join(parts[:-1])
        return field_name
    
    def set_layer(self, layer: QgsVectorLayer):
        """レイヤをセット"""
        self._layer = layer
        
        for panel in self._editor_panels:
            panel.set_layer(layer)
        
        QgsMessageLog.logMessage(
            f"PhotoManagementDialog - レイヤ設定完了: {layer.name() if layer else 'None'}",
            "PoleFacility", Qgis.Info
        )
    
    def set_feature(self, feature: QgsFeature):
        """地物をセット"""
        try:
            self._feature = feature
            
            if not feature or not feature.isValid():
                return
            
            if not self._layer:
                QgsMessageLog.logMessage(
                    "PhotoManagementDialog - レイヤが設定されていません",
                    "PoleFacility", Qgis.Warning
                )
            
            # 画像パスを取得・保存
            field_names = [f.name() for f in feature.fields()]
            
            for i, field_name in enumerate(self._before_fields):
                if field_name in field_names:
                    self._before_image_paths[i] = self._resolve_path(feature[field_name] or "")
            
            for i, field_name in enumerate(self._after_fields):
                if field_name in field_names:
                    source_field = self._before_fields[i]
                    if source_field in field_names:
                        self._after_image_paths[i] = self._resolve_path(feature[source_field] or "")
            
            # ViewerPanel設定
            for i, (panel, field_name) in enumerate(zip(self._viewer_panels, self._before_fields)):
                try:
                    panel.set_photo(feature, field_name)
                    
                    # サムネイル設定
                    if i < len(self._thumbnail_widgets):
                        self._thumbnail_widgets[i].set_image(self._before_image_paths[i])
                    
                except Exception as e:
                    QgsMessageLog.logMessage(
                        f"PhotoManagementDialog - ViewerPanel[{i}] エラー: {str(e)}",
                        "PoleFacility", Qgis.Warning
                    )
            
            # EditorPanel設定
            for i, (panel, field_name, source_field_name) in enumerate(
                zip(self._editor_panels, self._after_fields, self._before_fields)
            ):
                try:
                    panel.set_photo(feature, field_name, source_field_name)
                except Exception as e:
                    QgsMessageLog.logMessage(
                        f"PhotoManagementDialog - EditorPanel[{i}] エラー: {str(e)}",
                        "PoleFacility", Qgis.Warning
                    )
            
            self._update_title()
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"PhotoManagementDialog - set_feature エラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
    
    def _resolve_path(self, relative_path: str) -> str:
        """パス解決"""
        if not relative_path or not self._config_manager:
            return ""
        
        import os
        
        if os.path.isabs(relative_path):
            return relative_path
        
        photo_root = self._config_manager.get_photo_root_path()
        if not photo_root:
            return relative_path
        
        normalized_relative = relative_path.replace('\\', '/')
        actual_path = os.path.join(photo_root, normalized_relative)
        return os.path.normpath(actual_path)
    
    def refresh(self):
        """表示を更新"""
        if self._feature:
            self.set_feature(self._feature)
    
    def _update_title(self):
        """ウィンドウタイトルを更新"""
        if not self._feature:
            return
        
        try:
            equipment_number = self._feature["設備番号"] if "設備番号" in self._feature.fields().names() else ""
            
            if equipment_number:
                self.setWindowTitle(f"写真管理 - 設備番号: {equipment_number}")
            else:
                self.setWindowTitle("写真管理")
        
        except Exception:
            self.setWindowTitle("写真管理")
    
    def _on_photo_saved(self, field_name: str, relative_path: str):
        """写真保存完了時のハンドラ"""
        self.photo_saved.emit(field_name, relative_path)
    
    def closeEvent(self, event):
        """クローズイベント"""
        self.closed.emit()
        super().closeEvent(event)
    
    def moveEvent(self, event):
        """ウィンドウ移動イベント"""
        super().moveEvent(event)
        self._schedule_save_position()
    
    def resizeEvent(self, event):
        """ウィンドウリサイズイベント"""
        super().resizeEvent(event)
        self._schedule_save_position()
    
    def _schedule_save_position(self):
        """座標保存をスケジュール"""
        from PyQt5.QtCore import QTimer
        
        if self._save_timer is not None:
            self._save_timer.stop()
            self._save_timer.deleteLater()
        
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_current_position)
        self._save_timer.start(500)
    
    def _save_current_position(self):
        """現在のウィンドウ位置・サイズを保存"""
        from PyQt5.QtWidgets import QApplication
        
        if self._config_manager is None:
            return
        
        try:
            screen = QApplication.desktop().screenNumber(self)
            pos = self.pos()
            size = self.size()
            
            self._config_manager.save_window_position(
                'photo', screen, pos.x(), pos.y(), size.width(), size.height()
            )
        except Exception:
            pass
    
    def get_viewer_panel(self, index: int) -> Optional[PhotoViewerPanel]:
        """指定インデックスのViewerPanelを取得"""
        if 0 <= index < len(self._viewer_panels):
            return self._viewer_panels[index]
        return None
    
    def get_editor_panel(self, index: int) -> Optional[PhotoEditorPanel]:
        """指定インデックスのEditorPanelを取得"""
        if 0 <= index < len(self._editor_panels):
            return self._editor_panels[index]
        return None
