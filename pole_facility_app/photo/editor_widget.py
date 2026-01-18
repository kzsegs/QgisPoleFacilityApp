# -*- coding: utf-8 -*-
"""
Photo Editor Widget - 編集ウィジェット

写真の表示・編集を行うQGISエディタウィジェット
"""

import os
import re
from datetime import datetime
from pathlib import Path
from qgis.gui import QgsEditorWidgetWrapper
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsLineItem, QGraphicsRectItem, QGraphicsEllipseItem,
    QGraphicsPathItem, QGraphicsTextItem, QToolBar,
    QColorDialog, QSpinBox, QInputDialog
)
from qgis.PyQt.QtGui import (
    QPixmap, QImage, QPainter, QColor, QPen, QBrush,
    QPainterPath, QFont
)
from qgis.PyQt.QtCore import Qt, QPointF, QRectF, QLineF, QTimer
from qgis.core import QgsMessageLog, Qgis

from .graphics_items import GraphicsItemFactory


class DrawingTool:
    """描画ツールの定数"""
    SELECT = 'select'
    PEN = 'pen'
    LINE = 'line'
    ARROW = 'arrow'
    RECT = 'rect'
    ELLIPSE = 'ellipse'
    TEXT = 'text'


class PhotoGraphicsView(QGraphicsView):
    """
    カスタムGraphicsView - マウスイベントを処理して描画を行う
    """
    
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.editor_widget = None
        self.drawing = False
        self.start_point = None
        self.current_item = None
        self.pen_path = None
    
    def set_editor_widget(self, editor_widget):
        """親ウィジェットへの参照を設定"""
        self.editor_widget = editor_widget
    
    def mousePressEvent(self, event):
        """マウス押下"""
        if not self.editor_widget:
            super().mousePressEvent(event)
            return
        
        tool = self.editor_widget.current_tool
        
        if tool == DrawingTool.SELECT:
            super().mousePressEvent(event)
            return
        
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.start_point = self.mapToScene(event.pos())
            
            if tool == DrawingTool.PEN:
                self._start_pen_drawing()
            elif tool == DrawingTool.TEXT:
                self._add_text()
                self.drawing = False
    
    def mouseMoveEvent(self, event):
        """マウス移動"""
        if not self.editor_widget:
            super().mouseMoveEvent(event)
            return
        
        tool = self.editor_widget.current_tool
        
        if tool == DrawingTool.SELECT:
            super().mouseMoveEvent(event)
            return
        
        if self.drawing and self.start_point:
            current_point = self.mapToScene(event.pos())
            
            if tool == DrawingTool.PEN:
                self._continue_pen_drawing(current_point)
            elif tool in [DrawingTool.LINE, DrawingTool.ARROW, DrawingTool.RECT, DrawingTool.ELLIPSE]:
                self._update_shape_preview(current_point)
    
    def mouseReleaseEvent(self, event):
        """マウスリリース"""
        if not self.editor_widget:
            super().mouseReleaseEvent(event)
            return
        
        tool = self.editor_widget.current_tool
        
        if tool == DrawingTool.SELECT:
            super().mouseReleaseEvent(event)
            return
        
        if self.drawing and event.button() == Qt.LeftButton:
            end_point = self.mapToScene(event.pos())
            
            if tool == DrawingTool.PEN:
                self._finish_pen_drawing()
            elif tool == DrawingTool.LINE:
                self._create_line(end_point)
            elif tool == DrawingTool.ARROW:
                self._create_arrow(end_point)
            elif tool == DrawingTool.RECT:
                self._create_rect(end_point)
            elif tool == DrawingTool.ELLIPSE:
                self._create_ellipse(end_point)
            
            self.drawing = False
            self.start_point = None
            self.current_item = None
    
    def _get_pen(self):
        """現在の描画ペンを取得"""
        pen = QPen(self.editor_widget.current_color)
        pen.setWidth(self.editor_widget.line_width)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        return pen
    
    def _start_pen_drawing(self):
        """ペン描画開始"""
        self.pen_path = QPainterPath()
        self.pen_path.moveTo(self.start_point)
        self.current_item = QGraphicsPathItem(self.pen_path)
        self.current_item.setPen(self._get_pen())
        self.scene().addItem(self.current_item)
    
    def _continue_pen_drawing(self, point):
        """ペン描画継続"""
        if self.pen_path and self.current_item:
            self.pen_path.lineTo(point)
            self.current_item.setPath(self.pen_path)
    
    def _finish_pen_drawing(self):
        """ペン描画終了"""
        self.pen_path = None
    
    def _update_shape_preview(self, current_point):
        """図形プレビュー更新"""
        if self.current_item:
            self.scene().removeItem(self.current_item)
        
        tool = self.editor_widget.current_tool
        pen = self._get_pen()
        
        if tool == DrawingTool.LINE:
            self.current_item = QGraphicsLineItem(QLineF(self.start_point, current_point))
            self.current_item.setPen(pen)
        elif tool == DrawingTool.ARROW:
            self.current_item = QGraphicsLineItem(QLineF(self.start_point, current_point))
            self.current_item.setPen(pen)
        elif tool == DrawingTool.RECT:
            rect = QRectF(self.start_point, current_point).normalized()
            self.current_item = QGraphicsRectItem(rect)
            self.current_item.setPen(pen)
            self.current_item.setBrush(QBrush(Qt.transparent))
        elif tool == DrawingTool.ELLIPSE:
            rect = QRectF(self.start_point, current_point).normalized()
            self.current_item = QGraphicsEllipseItem(rect)
            self.current_item.setPen(pen)
            self.current_item.setBrush(QBrush(Qt.transparent))
        
        if self.current_item:
            self.scene().addItem(self.current_item)
    
    def _create_line(self, end_point):
        """直線作成"""
        if self.current_item:
            self.scene().removeItem(self.current_item)
        
        line = GraphicsItemFactory.create_line(
            self.start_point, end_point,
            self.editor_widget.current_color,
            self.editor_widget.line_width
        )
        self.scene().addItem(line)
    
    def _create_arrow(self, end_point):
        """矢印作成"""
        if self.current_item:
            self.scene().removeItem(self.current_item)
        
        arrow = GraphicsItemFactory.create_arrow(
            self.start_point, end_point,
            self.editor_widget.current_color,
            self.editor_widget.line_width
        )
        self.scene().addItem(arrow)
    
    def _create_rect(self, end_point):
        """矩形作成"""
        if self.current_item:
            self.scene().removeItem(self.current_item)
        
        rect = QRectF(self.start_point, end_point).normalized()
        rect_item = GraphicsItemFactory.create_rect(
            rect,
            self.editor_widget.current_color,
            self.editor_widget.line_width
        )
        self.scene().addItem(rect_item)
    
    def _create_ellipse(self, end_point):
        """楕円作成"""
        if self.current_item:
            self.scene().removeItem(self.current_item)
        
        rect = QRectF(self.start_point, end_point).normalized()
        ellipse = GraphicsItemFactory.create_ellipse(
            rect,
            self.editor_widget.current_color,
            self.editor_widget.line_width
        )
        self.scene().addItem(ellipse)
    
    def _add_text(self):
        """テキスト追加"""
        text, ok = QInputDialog.getText(
            self,
            "テキスト入力",
            "追加するテキストを入力してください:"
        )
        
        if ok and text:
            text_item = GraphicsItemFactory.create_text(
                self.start_point,
                text,
                self.editor_widget.current_color,
                self.editor_widget.line_width + 8
            )
            self.scene().addItem(text_item)


class PhotoEditorWidget(QgsEditorWidgetWrapper):
    """
    写真編集ウィジェット
    
    機能:
        - 元画像（修正前）を読み込み
        - 描画ツールで編集
        - 編集結果を画像ファイルとして保存
        - 相対パスをフィールドに保存
    
    対象フィールド:
        - 設備写真1URI_修正後
        - 設備写真2URI_修正後
        - 設備写真3URI_修正後
    
    描画ツール:
        - ペン、直線、矢印、四角形、楕円、テキスト
        - 色選択、線幅変更
        - オブジェクト削除、全削除
    """
    
    def __init__(self, vl, fieldIdx, editor, parent):
        """
        初期化
        
        Args:
            vl: QgsVectorLayer
            fieldIdx: フィールドインデックス
            editor: エディタウィジェット
            parent: 親ウィジェット
        """
        super().__init__(vl, fieldIdx, editor, parent)
        self.widget = None
        self.graphics_view = None
        self.graphics_scene = None
        self.pixmap_item = None
        self.status_label = None
        self.toolbar = None
        self.save_button = None
        self._current_feature = None
        self.current_photo_path = None
        self._saved_relative_path = None
        
        # 描画設定
        self.current_tool = DrawingTool.SELECT
        self.current_color = QColor(255, 0, 0)  # 赤
        self.line_width = 3
    
    def createWidget(self, parent):
        """
        ウィジェット作成
        
        レイアウト:
            [ステータスラベル]
            [ツールバー]
            [QGraphicsView]
            [保存ボタン]
        
        Args:
            parent: 親ウィジェット
        
        Returns:
            QWidget: 作成したウィジェット
        """
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # ステータス表示
        self.status_label = QLabel("修正後写真", widget)
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # ツールバー作成
        self.toolbar = self._create_toolbar(widget)
        layout.addWidget(self.toolbar)
        
        # QGraphicsView（画像表示・編集エリア）
        self.graphics_scene = QGraphicsScene(widget)
        self.graphics_view = PhotoGraphicsView(self.graphics_scene, widget)
        self.graphics_view.set_editor_widget(self)
        self.graphics_view.setMinimumSize(300, 200)
        self.graphics_view.setMaximumSize(600, 400)
        self.graphics_view.setRenderHint(QPainter.Antialiasing, True)
        self.graphics_view.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.graphics_view.setStyleSheet("""
            QGraphicsView {
                border: 1px solid #ccc;
                background-color: white;
            }
        """)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        layout.addWidget(self.graphics_view)
        
        # 保存ボタン
        self.save_button = QPushButton("💾 保存", widget)
        self.save_button.clicked.connect(self.save_edited_photo)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0051D5;
            }
        """)
        layout.addWidget(self.save_button)
        
        self.widget = widget
        return widget
    
    def _create_toolbar(self, parent) -> QToolBar:
        """
        描画ツールバー作成
        
        Args:
            parent: 親ウィジェット
        
        Returns:
            QToolBar: ツールバー
        """
        toolbar = QToolBar(parent)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        
        # 選択ツール
        select_action = toolbar.addAction("🖱️ 選択")
        select_action.triggered.connect(lambda: self._set_tool(DrawingTool.SELECT))
        
        toolbar.addSeparator()
        
        # ペンツール
        pen_action = toolbar.addAction("🖊️ ペン")
        pen_action.triggered.connect(lambda: self._set_tool(DrawingTool.PEN))
        
        # 直線ツール
        line_action = toolbar.addAction("📏 直線")
        line_action.triggered.connect(lambda: self._set_tool(DrawingTool.LINE))
        
        # 矢印ツール
        arrow_action = toolbar.addAction("➡️ 矢印")
        arrow_action.triggered.connect(lambda: self._set_tool(DrawingTool.ARROW))
        
        # 四角形ツール
        rect_action = toolbar.addAction("▭ 四角形")
        rect_action.triggered.connect(lambda: self._set_tool(DrawingTool.RECT))
        
        # 楕円ツール
        ellipse_action = toolbar.addAction("⭕ 楕円")
        ellipse_action.triggered.connect(lambda: self._set_tool(DrawingTool.ELLIPSE))
        
        # テキストツール
        text_action = toolbar.addAction("🔤 テキスト")
        text_action.triggered.connect(lambda: self._set_tool(DrawingTool.TEXT))
        
        toolbar.addSeparator()
        
        # 色選択
        color_action = toolbar.addAction("🎨 色")
        color_action.triggered.connect(self._on_color_clicked)
        
        # 線幅選択
        toolbar.addWidget(QLabel(" 線幅:"))
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setMinimum(1)
        self.width_spinbox.setMaximum(20)
        self.width_spinbox.setValue(3)
        self.width_spinbox.valueChanged.connect(self._on_width_changed)
        toolbar.addWidget(self.width_spinbox)
        
        toolbar.addSeparator()
        
        # 削除
        delete_action = toolbar.addAction("🗑️ 削除")
        delete_action.triggered.connect(self._on_delete_clicked)
        
        # 全削除
        clear_action = toolbar.addAction("🗑️✕ 全削除")
        clear_action.triggered.connect(self._on_clear_all_clicked)
        
        return toolbar
    
    def _set_tool(self, tool):
        """描画ツール設定"""
        self.current_tool = tool
        
        if tool == DrawingTool.SELECT:
            self.graphics_view.setCursor(Qt.ArrowCursor)
            self.graphics_view.setDragMode(QGraphicsView.RubberBandDrag)
        else:
            self.graphics_view.setCursor(Qt.CrossCursor)
            self.graphics_view.setDragMode(QGraphicsView.NoDrag)
    
    def _on_color_clicked(self):
        """色選択"""
        color = QColorDialog.getColor(self.current_color, self.widget)
        if color.isValid():
            self.current_color = color
    
    def _on_width_changed(self, value):
        """線幅変更"""
        self.line_width = value
    
    def _on_delete_clicked(self):
        """選択オブジェクト削除"""
        selected_items = self.graphics_scene.selectedItems()
        for item in selected_items:
            if item != self.pixmap_item:  # 背景画像は削除しない
                self.graphics_scene.removeItem(item)
    
    def _on_clear_all_clicked(self):
        """全オブジェクト削除"""
        for item in self.graphics_scene.items():
            if item != self.pixmap_item:  # 背景画像は削除しない
                self.graphics_scene.removeItem(item)
    
    def initWidget(self, editor):
        """初期化（QgsEditorWidgetWrapperインターフェース）"""
        pass
    
    def setFeature(self, feature):
        """
        地物がセットされた時
        
        Args:
            feature: 地物オブジェクト
        """
        super().setFeature(feature)
        self._current_feature = feature
        self.load_source_photo()
    
    def value(self):
        """
        現在の値（相対パス）を返す
        
        Returns:
            str: 保存した相対パス
        """
        return self._saved_relative_path
    
    def valid(self):
        """
        バリデーション（常にTrue）
        
        Returns:
            bool: True
        """
        return True
    
    def load_source_photo(self):
        """
        元画像または編集済み画像を読み込む
        
        処理フロー:
            1. 修正後フィールド（自分自身）の値をチェック
               - 値がある → 編集済み画像を表示
               - 値がない → 修正前画像を表示
            2. パス解決
            3. 画像読み込み
            4. QGraphicsScene に背景として追加
        
        Note:
            修正後カラムに値がある場合は編集済み画像を優先表示
        """
        try:
            feature = self._get_feature()
            
            if not feature or not feature.isValid():
                self._update_status("地物未選択", "#999")
                return
            
            # ★修正: 修正後フィールド（自分自身）から値を取得
            field_name = self.field().name()
            edited_path = feature[field_name]
            
            # 修正後フィールドに値がある場合は、編集済み画像を表示
            if edited_path and str(edited_path).strip() and str(edited_path).strip().upper() != 'NULL':
                QgsMessageLog.logMessage(
                    f"PhotoEditor - 編集済み画像を読み込み: {edited_path}",
                    "PoleFacility", Qgis.Info
                )
                
                actual_path = self._resolve_photo_path(str(edited_path))
                
                if os.path.exists(actual_path):
                    pixmap = self._load_image_as_pixmap(actual_path)
                    if pixmap and not pixmap.isNull():
                        self._display_pixmap(pixmap, "編集済み")
                        self.current_photo_path = actual_path
                        return
                else:
                    QgsMessageLog.logMessage(
                        f"PhotoEditor - 編集済み画像が見つかりません: {actual_path}",
                        "PoleFacility", Qgis.Warning
                    )
            
            # 修正後フィールドに値がない場合は、修正前画像を表示
            source_field_name = field_name.replace("修正後", "修正前")
            source_path = feature[source_field_name]
            
            if not source_path:
                self._update_status("元画像: 未設定", "#999")
                return
            
            QgsMessageLog.logMessage(
                f"PhotoEditor - 修正前画像を読み込み: {source_path}",
                "PoleFacility", Qgis.Info
            )
            
            actual_path = self._resolve_photo_path(str(source_path))
            
            if not os.path.exists(actual_path):
                self._update_status("❌ 元画像なし", "#FF3B30")
                return
            
            pixmap = self._load_image_as_pixmap(actual_path)
            
            if pixmap and not pixmap.isNull():
                self._display_pixmap(pixmap, "元画像")
                self.current_photo_path = actual_path
            else:
                self._update_status("❌ 読み込み失敗", "#FF3B30")
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"元画像読み込みエラー: {str(e)}",
                "PoleFacility", Qgis.Warning
            )
    
    def _display_pixmap(self, pixmap, label):
        """
        Pixmapを表示
        
        Args:
            pixmap: QPixmap
            label: ステータスラベル用テキスト
        """
        self.graphics_scene.clear()
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.pixmap_item.setZValue(-1)  # 背景として最背面に
        self.graphics_scene.addItem(self.pixmap_item)
        
        # シーン範囲設定
        rect = pixmap.rect()
        self.graphics_scene.setSceneRect(
            QRectF(rect.x(), rect.y(), rect.width(), rect.height())
        )
        
        # フィット
        QTimer.singleShot(100, self._fit_to_view)
        
        self._update_status(f"✓ {label}", "#34C759")
    
    def save_edited_photo(self):
        """
        編集済み写真を保存
        
        処理フロー:
            1. シーンをレンダリング（_render_scene_to_pixmap）
            2. 保存パス生成（_generate_save_path）
            3. ディレクトリ作成
            4. 画像ファイルとして保存（JPEG 90%品質）
            5. 相対パスをフィールドに設定（setValue）
            6. EventBus でイベント発行
        
        Raises:
            各種例外（ファイルシステム、権限エラー等）
        """
        try:
            # シーンをレンダリング
            pixmap = self._render_scene_to_pixmap()
            
            if pixmap is None or pixmap.isNull():
                QgsMessageLog.logMessage(
                    "レンダリング失敗",
                    "PoleFacility", Qgis.Warning
                )
                return
            
            # 保存パス生成
            relative_path, actual_path = self._generate_save_path()
            
            # ディレクトリ作成
            os.makedirs(os.path.dirname(actual_path), exist_ok=True)
            
            # 画像保存（JPEG 90%品質）
            image = pixmap.toImage()
            success = image.save(actual_path, "JPEG", 90)
            
            if not success:
                QgsMessageLog.logMessage(
                    f"画像保存失敗: {actual_path}",
                    "PoleFacility", Qgis.Critical
                )
                return
            
            # 相対パスをフィールドに保存
            self.setValue(relative_path)
            self._saved_relative_path = relative_path
            
            # EventBus でイベント発行
            from pole_facility_app.main.event_bus import EventBus
            EventBus.get_instance().emit("photo.saved", {
                "feature_id": self.formFeature().id(),
                "field_name": self.field().name(),
                "path": relative_path
            })
            
            # ステータス更新
            filename = os.path.basename(actual_path)
            self._update_status(f"✓ 保存: {filename}", "#34C759")
            
            QgsMessageLog.logMessage(
                f"写真を保存しました: {relative_path}",
                "PoleFacility", Qgis.Info
            )
            
        except Exception as e:
            self._update_status("❌ 保存失敗", "#FF3B30")
            QgsMessageLog.logMessage(
                f"写真保存エラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
    
    def _render_scene_to_pixmap(self) -> QPixmap:
        """
        QGraphicsScene を QPixmap にレンダリング
        
        Returns:
            QPixmap: レンダリングされた QPixmap
        """
        scene_rect = self.graphics_scene.sceneRect()
        width = int(scene_rect.width())
        height = int(scene_rect.height())
        
        # QPixmap 作成
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.white)  # 背景を白で塗りつぶし
        
        # レンダリング
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        self.graphics_scene.render(
            painter,
            QRectF(0, 0, width, height),
            scene_rect
        )
        painter.end()
        
        return pixmap
    
    def _generate_save_path(self) -> tuple:
        """
        編集済み写真の保存パスを生成
        
        パス形式:
            edited/[元フォルダ名]/[元ファイル名]
        
        例:
            元の相対パス: 2700012345局前_1/images-1.jpeg
            保存先相対パス: edited/2700012345局前_1/images-1.jpeg
        
        Returns:
            tuple: (相対パス, 実際のパス)
        
        Raises:
            ValueError: 元画像パスが取得できない場合
        
        Note:
            - ファイル名・フォルダ名は編集前と同じものを使用
            - タイムスタンプは付与しない
            - 上書き保存される
        """
        # 地物情報取得
        feature = self.formFeature()
        
        # 修正前フィールド名を生成
        field_name = self.field().name()
        source_field_name = field_name.replace("修正後", "修正前")
        
        # 修正前フィールドから相対パス取得
        source_relative_path = feature[source_field_name]
        
        if not source_relative_path or str(source_relative_path).strip().upper() == 'NULL':
            raise ValueError(f"元画像パスが取得できません（フィールド: {source_field_name}）")
        
        # original/ プレフィックスを除去
        # 例: "original/2700012345局前_1/images-1.jpeg" → "2700012345局前_1/images-1.jpeg"
        source_path_normalized = str(source_relative_path)
        if source_path_normalized.startswith("original/"):
            source_path_normalized = source_path_normalized[len("original/"):]
        elif source_path_normalized.startswith("original\\"):
            source_path_normalized = source_path_normalized[len("original\\"):]
        
        # 相対パス: edited/[元フォルダ名]/[元ファイル名]
        # 例: "2700012345局前_1/images-1.jpeg" → "edited/2700012345局前_1/images-1.jpeg"
        relative_path = f"edited/{source_path_normalized}"
        
        # 実際のパス
        from pole_facility_app.config.manager import ConfigManager
        config_manager = ConfigManager.get_instance()
        photo_root = config_manager.get_photo_root_path()
        
        if not photo_root:
            raise ValueError("写真ルートパスが設定されていません")
        
        actual_path = os.path.join(photo_root, relative_path)
        
        return relative_path, actual_path

    
    def _get_feature(self):
        """地物取得"""
        try:
            return self.formFeature()
        except AttributeError:
            return getattr(self, '_current_feature', None)
        except:
            return None
    
    def _resolve_photo_path(self, relative_path: str) -> str:
        r"""
        相対パスから実際のパスを解決（OS非依存）
        
        処理:
            1. ConfigManager から photo_root_path 取得
            2. 相対パスのパス区切り文字を正規化（\ → /）
            3. os.path.join() で結合
            4. os.path.normpath() で最終的に正規化
        
        Args:
            relative_path: CSV/GeoPackageのフィールド値
                          例: "original/A001/P001_1.jpg"
                          または "original\\A001\\P001_1.jpg"
        
        Returns:
            str: 実際のファイルパス
                 例（Mac）: "/Users/.../Photos/original/A001/P001_1.jpg"
                 例（Win）: "C:\\Users\\...\\Photos\\original\\A001\\P001_1.jpg"
        
        Raises:
            ValueError: photo_root_path が未設定の場合
        """
        if not relative_path or relative_path.strip().upper() == 'NULL':
            return None
        
        from pole_facility_app.config.manager import ConfigManager
        config_manager = ConfigManager.get_instance()
        photo_root = config_manager.get_photo_root_path()
        
        if not photo_root:
            raise ValueError("写真ルートパスが設定されていません")
        
        # 相対パスのパス区切り文字を正規化
        # Windows形式（\）→ POSIX形式（/）に統一してから os.path.join() を使用
        normalized_relative = relative_path.replace('\\', '/')
        
        # os.path.join() は自動的にOSに応じた区切り文字に変換
        actual_path = os.path.join(photo_root, normalized_relative)
        
        # 最終的に正規化（余分な区切り文字の削除、. や .. の解決）
        actual_path = os.path.normpath(actual_path)
        
        return actual_path
    
    def _load_image_as_pixmap(self, photo_path: str) -> QPixmap:
        """画像をQPixmapとして読み込む"""
        try:
            qimage = QImage(photo_path)
            if not qimage.isNull():
                qimage = qimage.convertToFormat(QImage.Format_RGB32)
                return QPixmap.fromImage(qimage)
        except Exception as e:
            QgsMessageLog.logMessage(
                f"画像読み込み失敗: {str(e)}",
                "PoleFacility", Qgis.Warning
            )
        return None
    
    def _fit_to_view(self):
        """画像をビューにフィット"""
        if self.pixmap_item and self.graphics_scene:
            self.graphics_view.fitInView(
                self.graphics_scene.sceneRect(),
                Qt.KeepAspectRatio
            )
    
    def _update_status(self, text: str, color: str):
        """ステータスラベル更新"""
        if self.status_label:
            self.status_label.setText(text)
            self.status_label.setStyleSheet(f"color: {color}; font-size: 11px;")
