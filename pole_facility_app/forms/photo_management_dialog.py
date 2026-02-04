# -*- coding: utf-8 -*-
"""
Photo Management Dialog - 写真管理ダイアログ（Phase 3-A完成版）

Phase 3-A対応: 4列レイアウト + マウス座標中心の拡大表示
既存のPhotoViewerPanel/PhotoEditorPanelを維持しつつ、
美しく整ったレイアウトを実現。

レイアウト:
    [サムネイル] [修正前(Viewer)] [拡大表示(Zoom)] [修正後(Editor)]
    各行ごとに拡大表示パネルを配置
    マウス座標を中心に拡大表示（100x100px基準、倍率で変化）
"""

from typing import Optional, List
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QScrollArea, QWidget, QFrame, QGraphicsView
)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QEvent, QPointF, QTimer
from qgis.PyQt.QtGui import QCursor
from qgis.core import QgsFeature, QgsVectorLayer, QgsMessageLog, Qgis

from ..photo.viewer_panel import PhotoViewerPanel
from ..photo.editor_panel import PhotoEditorPanel
from ..photo.thumbnail_widget import ThumbnailWidget
from ..photo.zoom_panel import ZoomPanel


class HoverDetector(QWidget):
    """
    hover検出用ラッパーウィジェット（Phase 3-A完成版 - リアルタイム座標追跡）
    
    マウス座標をリアルタイムで取得してZoomPanelに渡す
    """
    hovered = pyqtSignal(str, object)  # (image_path, mouse_pos: QPointF)
    
    def __init__(self, wrapped_widget, image_path_getter, parent=None):
        super().__init__(parent)
        self._wrapped_widget = wrapped_widget
        self._image_path_getter = image_path_getter
        self._graphics_view = None
        self._is_hovering = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(wrapped_widget)
        
        # マウストラッキングを有効化
        self.setMouseTracking(True)
        wrapped_widget.setMouseTracking(True)
        
        # QGraphicsViewを一度だけ検索
        self._graphics_view = self._find_graphics_view(wrapped_widget)
        
        # 子ウィジェットにもマウストラッキング設定
        self._enable_mouse_tracking_recursive(wrapped_widget)
    
    def _enable_mouse_tracking_recursive(self, widget):
        """再帰的にマウストラッキングを有効化"""
        widget.setMouseTracking(True)
        widget.installEventFilter(self)
        for child in widget.findChildren(QWidget):
            child.setMouseTracking(True)
            child.installEventFilter(self)
    
    def _get_mouse_position(self):
        """
        マウス座標を元画像座標系に変換（高速化版）
        
        Returns:
            QPointF: 元画像座標系のマウス位置、取得できない場合はNone
        """
        if not self._graphics_view:
            return None
        
        try:
            # グローバル座標からビュー座標に変換
            global_pos = QCursor.pos()
            view_pos = self._graphics_view.mapFromGlobal(global_pos)
            
            # ビュー座標からシーン座標（元画像座標系）に変換
            scene_pos = self._graphics_view.mapToScene(view_pos)
            
            return scene_pos
            
        except Exception:
            return None
    
    def _find_graphics_view(self, widget):
        """QGraphicsViewを再帰的に探す（一度だけ実行）"""
        if isinstance(widget, QGraphicsView):
            return widget
        
        for child in widget.findChildren(QGraphicsView):
            return child
        
        return None
    
    def eventFilter(self, obj, event):
        """イベントフィルタ - マウス移動を検出"""
        if event.type() == QEvent.Enter:
            self._is_hovering = True
            image_path = self._image_path_getter()
            if image_path:
                mouse_pos = self._get_mouse_position()
                self.hovered.emit(image_path, mouse_pos)
        elif event.type() == QEvent.Leave:
            # 親ウィジェットの外に出た場合のみクリア
            if not self.rect().contains(self.mapFromGlobal(QCursor.pos())):
                self._is_hovering = False
                self.hovered.emit("", None)
        elif event.type() == QEvent.MouseMove and self._is_hovering:
            # マウス移動中も座標を更新
            image_path = self._image_path_getter()
            if image_path:
                mouse_pos = self._get_mouse_position()
                self.hovered.emit(image_path, mouse_pos)
        
        return super().eventFilter(obj, event)
    
    def enterEvent(self, event):
        """マウスオーバー時"""
        super().enterEvent(event)
        self._is_hovering = True
        image_path = self._image_path_getter()
        if image_path:
            mouse_pos = self._get_mouse_position()
            self.hovered.emit(image_path, mouse_pos)
    
    def leaveEvent(self, event):
        """マウスアウト時"""
        super().leaveEvent(event)
        self._is_hovering = False
        self.hovered.emit("", None)
    
    def mouseMoveEvent(self, event):
        """マウス移動時"""
        super().mouseMoveEvent(event)
        if self._is_hovering:
            image_path = self._image_path_getter()
            if image_path:
                mouse_pos = self._get_mouse_position()
                self.hovered.emit(image_path, mouse_pos)


class PhotoManagementDialog(QDialog):
    """
    写真管理ダイアログ（Phase 3-A完成版）
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
        
        # 写真フィールド定義
        self._before_fields = []
        self._after_fields = []
        self._before_image_paths = ["", "", ""]
        self._after_image_paths = ["", "", ""]
        
        # 位置保存タイマー
        self._save_timer = None
        
        self._load_photo_fields()
        self._create_ui()
        self._restore_window_position()
    
    def _load_photo_fields(self):
        """写真フィールド定義を読み込み"""
        photo_fields = self._config_manager.get("photo_fields", {})
        
        self._before_fields = [
            photo_fields.get("before_field_1", "設備写真1URI_修正前"),
            photo_fields.get("before_field_2", "設備写真2URI_修正前"),
            photo_fields.get("before_field_3", "設備写真3URI_修正前")
        ]
        
        self._after_fields = [
            photo_fields.get("after_field_1", "設備写真1URI_修正後"),
            photo_fields.get("after_field_2", "設備写真2URI_修正後"),
            photo_fields.get("after_field_3", "設備写真3URI_修正後")
        ]
    
    def _create_ui(self):
        """UI作成"""
        self.setWindowTitle("写真管理")
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.resize(1600, 900)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        # スクロールエリア
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # コンテンツウィジェット
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(16)
        content_layout.setContentsMargins(8, 8, 8, 8)
        
        # 3行のレイアウト
        for i in range(3):
            row_widget = self._create_photo_row(i)
            content_layout.addWidget(row_widget)
        
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area, 1)
        
        # 閉じるボタン
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_button = QPushButton("閉じる", self)
        close_button.setFixedSize(120, 36)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 11pt;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #5a6268; }
        """)
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)
        
        main_layout.addLayout(button_layout)
    
    def _create_photo_row(self, index: int) -> QWidget:
        """
        1行分の写真管理UIを作成
        
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
        viewer_wrapper.hovered.connect(lambda path, pos, idx=index: self._on_viewer_hovered(idx, path, pos))
        
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
        editor_wrapper.hovered.connect(lambda path, pos, idx=index: self._on_editor_hovered(idx, path, pos))
        
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
    
    def _on_viewer_hovered(self, index: int, image_path: str, mouse_pos):
        """修正前パネルhover時（マウス座標付き）"""
        if index < len(self._zoom_panels):
            self._zoom_panels[index].show_image(image_path, None, mouse_pos)
    
    def _on_editor_hovered(self, index: int, image_path: str, mouse_pos):
        """修正後パネルhover時（シーン込み・マウス座標付き）"""
        if index < len(self._zoom_panels) and index < len(self._editor_panels):
            editor_panel = self._editor_panels[index]
            # EditorPanelのシーン全体を渡す
            scene = editor_panel.graphics_scene if hasattr(editor_panel, 'graphics_scene') else None
            self._zoom_panels[index].show_image(image_path, scene, mouse_pos)
    
    def _on_editor_scene_changed(self, index: int):
        """EditorPanelのシーン変更時（リアルタイム更新）"""
        # 現在hoverしているパネルのみ更新
        if index < len(self._zoom_panels) and index < len(self._editor_panels):
            zoom_panel = self._zoom_panels[index]
            # 現在表示中のソースがこのパネルのシーンの場合のみ更新
            if zoom_panel._current_source_type == "scene":
                editor_panel = self._editor_panels[index]
                scene = editor_panel.graphics_scene if hasattr(editor_panel, 'graphics_scene') else None
                # マウス座標は保持されているので再利用
                zoom_panel.show_image("", scene, zoom_panel._current_mouse_pos)
    
    def _generate_display_name(self, field_name: str) -> str:
        """フィールド名から表示名を生成"""
        if "1" in field_name:
            return "設備正面"
        elif "2" in field_name:
            return "設備背面"
        elif "3" in field_name:
            return "設備側面"
        return "写真"
    
    def set_layer(self, layer: QgsVectorLayer):
        """レイヤーを設定（互換性のため）"""
        self._layer = layer
    
    def set_feature(self, feature: QgsFeature, layer: QgsVectorLayer):
        """地物を設定して写真を読み込み"""
        self._feature = feature
        self._layer = layer
        
        if not feature or not layer:
            self._clear_photos()
            return
        
        try:
            # 修正前の写真パスを取得してViewerPanelに設定
            for i, field_name in enumerate(self._before_fields):
                field_index = layer.fields().indexFromName(field_name)
                if field_index >= 0:
                    path = feature[field_index] or ""
                    self._before_image_paths[i] = path
                    
                    if i < len(self._viewer_panels):
                        # ViewerPanelはfeatureとfield_nameを渡す
                        self._viewer_panels[i].set_photo(feature, field_name)
                    
                    if i < len(self._thumbnail_widgets):
                        self._thumbnail_widgets[i].set_image(path)
            
            # 修正後の写真パスを取得してEditorPanelに設定
            for i, field_name in enumerate(self._after_fields):
                field_index = layer.fields().indexFromName(field_name)
                if field_index >= 0:
                    path = feature[field_index] or ""
                    self._after_image_paths[i] = path
                    
                    if i < len(self._editor_panels):
                        self._editor_panels[i].set_layer(layer)
                        # EditorPanelはfeature, field_name, source_field_nameを渡す
                        source_field_name = self._before_fields[i]
                        self._editor_panels[i].set_photo(feature, field_name, source_field_name)
            
            QgsMessageLog.logMessage(
                f"PhotoManagementDialog - 写真読み込み完了: feature_id={feature.id()}",
                "PoleFacility", Qgis.Info
            )
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"PhotoManagementDialog - 写真読み込みエラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
            self._clear_photos()
    
    def _clear_photos(self):
        """写真表示をクリア"""
        # ViewerPanelはset_photo(None, "")で空フィールドを渡す
        for i, panel in enumerate(self._viewer_panels):
            # 空のQgsFeatureを作成して渡す
            from qgis.core import QgsFields
            empty_feature = QgsFeature(QgsFields())
            panel.set_photo(empty_feature, self._before_fields[i] if i < len(self._before_fields) else "")
        
        # EditorPanelも同様
        for i, panel in enumerate(self._editor_panels):
            from qgis.core import QgsFields
            empty_feature = QgsFeature(QgsFields())
            source_field = self._before_fields[i] if i < len(self._before_fields) else ""
            after_field = self._after_fields[i] if i < len(self._after_fields) else ""
            panel.set_photo(empty_feature, after_field, source_field)
        
        for thumbnail in self._thumbnail_widgets:
            thumbnail.set_image("")
        
        for zoom_panel in self._zoom_panels:
            zoom_panel.clear()
        
        self._before_image_paths = ["", "", ""]
        self._after_image_paths = ["", "", ""]
    
    def _on_photo_saved(self, field_name: str, photo_path: str):
        """写真保存時の処理"""
        self.photo_saved.emit(field_name, photo_path)
        
        QgsMessageLog.logMessage(
            f"PhotoManagementDialog - 写真保存: field={field_name}, path={photo_path}",
            "PoleFacility", Qgis.Info
        )
    
    def _restore_window_position(self):
        """ウィンドウ位置を復元"""
        position = self._config_manager.get_window_position("photo_management")
        
        if position:
            x = position.get('x', 100)
            y = position.get('y', 100)
            width = position.get('width', 1600)
            height = position.get('height', 900)
            
            self.move(x, y)
            self.resize(width, height)
    
    def _schedule_save_position(self):
        """座標保存をスケジュール（500ms遅延）"""
        if self._save_timer is not None:
            self._save_timer.stop()
        
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_current_position)
        self._save_timer.start(500)
    
    def _save_current_position(self):
        """現在のウィンドウ位置を保存"""
        from qgis.PyQt.QtWidgets import QApplication
        
        screen = QApplication.desktop().screenNumber(self)
        pos = self.pos()
        size = self.size()
        
        self._config_manager.save_window_position(
            "photo_management", screen,
            pos.x(), pos.y(),
            size.width(), size.height()
        )
    
    def moveEvent(self, event):
        """ウィンドウ移動時"""
        super().moveEvent(event)
        self._schedule_save_position()
    
    def resizeEvent(self, event):
        """ウィンドウリサイズ時"""
        super().resizeEvent(event)
        self._schedule_save_position()
    
    def closeEvent(self, event):
        """閉じる時"""
        self._save_current_position()
        self.closed.emit()
        super().closeEvent(event)
