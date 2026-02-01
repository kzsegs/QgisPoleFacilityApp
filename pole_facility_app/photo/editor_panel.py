# -*- coding: utf-8 -*-
"""
Photo Editor Panel - 写真編集パネル

QgsEditorWidgetWrapperに依存しない独立した写真編集パネル。
複数ウィンドウUIのPhotoManagementDialogで使用。

機能:
    - 修正前写真の読み込み・表示
    - 描画ツール（ペン/直線/矢印/矩形/楕円/テキスト/削除）
    - 色・線幅の設定
    - 編集済み写真の保存
"""

import os
from datetime import datetime
from typing import Optional
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsLineItem, QGraphicsRectItem, QGraphicsEllipseItem,
    QGraphicsPathItem, QGraphicsTextItem, QToolBar, QAction,
    QColorDialog, QSpinBox, QInputDialog, QMessageBox
)
from qgis.PyQt.QtGui import (
    QPixmap, QImage, QPainter, QColor, QPen, QBrush,
    QPainterPath, QFont, QIcon
)
from qgis.PyQt.QtCore import Qt, QPointF, QRectF, QLineF, QTimer, pyqtSignal, QVariant
from qgis.core import QgsFeature, QgsVectorLayer, QgsMessageLog, Qgis

from ..photo.graphics_items import GraphicsItemFactory


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
        self.editor_panel = None
        self.drawing = False
        self.start_point = None
        self.current_item = None
        self.pen_path = None
    
    def set_editor_panel(self, editor_panel):
        """親パネルへの参照を設定"""
        self.editor_panel = editor_panel
    
    def mousePressEvent(self, event):
        """マウス押下"""
        if not self.editor_panel:
            super().mousePressEvent(event)
            return
        
        tool = self.editor_panel.current_tool
        
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
        if not self.editor_panel:
            super().mouseMoveEvent(event)
            return
        
        tool = self.editor_panel.current_tool
        
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
        if not self.editor_panel:
            super().mouseReleaseEvent(event)
            return
        
        tool = self.editor_panel.current_tool
        
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
        pen = QPen(self.editor_panel.current_color)
        pen.setWidth(self.editor_panel.line_width)
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
        
        tool = self.editor_panel.current_tool
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
            self.editor_panel.current_color,
            self.editor_panel.line_width
        )
        self.scene().addItem(line)
    
    def _create_arrow(self, end_point):
        """矢印作成"""
        if self.current_item:
            self.scene().removeItem(self.current_item)
        
        arrow = GraphicsItemFactory.create_arrow(
            self.start_point, end_point,
            self.editor_panel.current_color,
            self.editor_panel.line_width
        )
        self.scene().addItem(arrow)
    
    def _create_rect(self, end_point):
        """矩形作成"""
        if self.current_item:
            self.scene().removeItem(self.current_item)
        
        rect = QRectF(self.start_point, end_point).normalized()
        rect_item = GraphicsItemFactory.create_rect(
            rect,
            self.editor_panel.current_color,
            self.editor_panel.line_width
        )
        self.scene().addItem(rect_item)
    
    def _create_ellipse(self, end_point):
        """楕円作成"""
        if self.current_item:
            self.scene().removeItem(self.current_item)
        
        rect = QRectF(self.start_point, end_point).normalized()
        ellipse = GraphicsItemFactory.create_ellipse(
            rect,
            self.editor_panel.current_color,
            self.editor_panel.line_width
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
                self.editor_panel.current_color,
                self.editor_panel.font_size
            )
            self.scene().addItem(text_item)


class PhotoEditorPanel(QWidget):
    """
    写真編集パネル
    
    使用例:
        panel = PhotoEditorPanel(config_manager, data_manager, parent)
        panel.set_layer(layer)  # 保存に必要
        panel.set_photo(feature, "設備写真1URI_修正後", "設備写真1URI_修正前")
    
    対象フィールド:
        - 設備写真1URI_修正後
        - 設備写真2URI_修正後
        - 設備写真3URI_修正後
    
    Note:
        保存処理に必要なため、set_photoの前に必ずset_layerを呼び出すこと
    """
    
    photo_saved = pyqtSignal(str)  # 保存完了時に相対パスを通知
    
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
        self._field_name = None
        self._source_field_name = None
        
        # UI要素
        self.graphics_view = None
        self.graphics_scene = None
        self.pixmap_item = None
        self.status_label = None
        self.toolbar = None
        self.save_button = None
        
        # 描画設定
        self.current_tool = DrawingTool.SELECT
        self.current_color = QColor(255, 0, 0)  # 赤
        self.line_width = 3
        self.font_size = 12
        
        # 描画アイテム管理（v1.6.1修正: 初期化追加）
        self._drawing_items = []
        
        self._create_ui()
    
    def _create_ui(self):
        """
        UI作成
        
        レイアウト:
            [ツールバー]
            [ステータスラベル]
            [QGraphicsView]
            [保存ボタン]
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # ツールバー
        self.toolbar = self._create_toolbar()
        layout.addWidget(self.toolbar)
        
        # ステータス表示
        self.status_label = QLabel("写真", self)
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # QGraphicsView（画像表示・編集エリア）
        self.graphics_scene = QGraphicsScene(self)
        self.graphics_view = PhotoGraphicsView(self.graphics_scene, self)
        self.graphics_view.set_editor_panel(self)
        self.graphics_view.setMinimumSize(300, 200)
        self.graphics_view.setMaximumSize(600, 400)
        self.graphics_view.setRenderHint(QPainter.Antialiasing, True)
        self.graphics_view.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.graphics_view.setStyleSheet("""
            QGraphicsView {
                border: 1px solid #ccc;
                background-color: #ffffff;
            }
        """)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        layout.addWidget(self.graphics_view)
        
        # 保存ボタン
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_button = QPushButton("保存", self)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                padding: 6px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0051D5;
            }
            QPushButton:pressed {
                background-color: #004FC4;
            }
        """)
        self.save_button.clicked.connect(self._on_save_clicked)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
    
    def _create_toolbar(self) -> QToolBar:
        """
        ツールバー作成（v1.9.1改訂: QGISテーマアイコン使用）
        
        Returns:
            QToolBar: 描画ツールバー
        """
        from qgis.core import QgsApplication
        
        toolbar = QToolBar(self)
        toolbar.setIconSize(toolbar.iconSize() * 0.8)
        
        # 選択ツール
        select_action = QAction(
            QgsApplication.getThemeIcon("mActionSelect.svg"),
            "選択",
            self
        )
        select_action.setCheckable(True)
        select_action.setChecked(True)
        select_action.setToolTip("選択ツール")
        select_action.triggered.connect(lambda: self._set_tool(DrawingTool.SELECT))
        toolbar.addAction(select_action)
        
        toolbar.addSeparator()
        
        # ペンツール
        pen_action = QAction(
            QgsApplication.getThemeIcon("mActionEditPencil.svg"),
            "ペン",
            self
        )
        pen_action.setCheckable(True)
        pen_action.setToolTip("ペンツール - フリーハンド描画")
        pen_action.triggered.connect(lambda: self._set_tool(DrawingTool.PEN))
        toolbar.addAction(pen_action)
        
        # 直線ツール
        line_action = QAction(
            QgsApplication.getThemeIcon("mIconLineLayer.svg"),
            "直線",
            self
        )
        line_action.setCheckable(True)
        line_action.setToolTip("直線ツール")
        line_action.triggered.connect(lambda: self._set_tool(DrawingTool.LINE))
        toolbar.addAction(line_action)
        
        # 矢印ツール
        arrow_action = QAction(
            QgsApplication.getThemeIcon("mActionArrowRight.svg"),
            "矢印",
            self
        )
        arrow_action.setCheckable(True)
        arrow_action.setToolTip("矢印ツール")
        arrow_action.triggered.connect(lambda: self._set_tool(DrawingTool.ARROW))
        toolbar.addAction(arrow_action)
        
        # 矩形ツール
        rect_action = QAction(
            QgsApplication.getThemeIcon("mIconPolygonLayer.svg"),
            "矩形",
            self
        )
        rect_action.setCheckable(True)
        rect_action.setToolTip("矩形ツール")
        rect_action.triggered.connect(lambda: self._set_tool(DrawingTool.RECT))
        toolbar.addAction(rect_action)
        
        # 楕円ツール
        ellipse_action = QAction(
            QgsApplication.getThemeIcon("mIconPointLayer.svg"),
            "楕円",
            self
        )
        ellipse_action.setCheckable(True)
        ellipse_action.setToolTip("楕円ツール")
        ellipse_action.triggered.connect(lambda: self._set_tool(DrawingTool.ELLIPSE))
        toolbar.addAction(ellipse_action)
        
        # テキストツール
        text_action = QAction(
            QgsApplication.getThemeIcon("mActionLabel.svg"),
            "テキスト",
            self
        )
        text_action.setCheckable(True)
        text_action.setToolTip("テキストツール")
        text_action.triggered.connect(lambda: self._set_tool(DrawingTool.TEXT))
        toolbar.addAction(text_action)
        
        toolbar.addSeparator()
        
        # 色選択
        color_action = QAction(
            QgsApplication.getThemeIcon("mIconColorBox.svg"),
            "色",
            self
        )
        color_action.setToolTip("描画色を選択")
        color_action.triggered.connect(self._choose_color)
        toolbar.addAction(color_action)
        
        # 線幅選択
        toolbar.addWidget(QLabel("線幅:", self))
        width_spinbox = QSpinBox(self)
        width_spinbox.setMinimum(1)
        width_spinbox.setMaximum(20)
        width_spinbox.setValue(self.line_width)
        width_spinbox.setToolTip("線の太さ（1-20）")
        width_spinbox.valueChanged.connect(self._set_line_width)
        toolbar.addWidget(width_spinbox)
        
        toolbar.addSeparator()
        
        # 削除
        delete_action = QAction(
            QgsApplication.getThemeIcon("mActionDeleteSelected.svg"),
            "削除",
            self
        )
        delete_action.setToolTip("選択したアイテムを削除")
        delete_action.triggered.connect(self._delete_selected)
        toolbar.addAction(delete_action)
        
        # 全削除
        clear_action = QAction(
            QgsApplication.getThemeIcon("mActionDeleteSelected.svg"),
            "全削除",
            self
        )
        clear_action.setToolTip("すべての描画を削除")
        clear_action.triggered.connect(self._clear_all_drawings)
        toolbar.addAction(clear_action)
        
        toolbar.addSeparator()
        
        # 元画像差替（v1.9.1追加）
        replace_action = QAction(
            QgsApplication.getThemeIcon("mActionRefresh.svg"),
            "元画像差替",
            self
        )
        replace_action.setToolTip("編集済み画像で元画像を差し替え")
        replace_action.triggered.connect(self._on_replace_original_clicked)
        toolbar.addAction(replace_action)
        
        # アクショングループ化（排他的選択）
        from qgis.PyQt.QtWidgets import QActionGroup
        tool_group = QActionGroup(self)
        for action in [select_action, pen_action, line_action, arrow_action,
                      rect_action, ellipse_action, text_action]:
            tool_group.addAction(action)
        
        return toolbar
    
    def set_layer(self, layer: QgsVectorLayer):
        """
        レイヤをセット
        
        Args:
            layer: 対象レイヤ
        
        Note:
            保存処理に必要なため、set_photoの前に呼び出すこと
        """
        self._layer = layer
    
    def set_photo(self, feature: QgsFeature, field_name: str, 
                  source_field_name: str):
        """
        写真を設定（編集用）
        
        Args:
            feature: 地物オブジェクト
            field_name: 保存先フィールド名（例: "設備写真1URI_修正後"）
            source_field_name: 参照元フィールド名（例: "設備写真1URI_修正前"）
        
        Raises:
            ValueError: フィールド名が不正な場合
            FileNotFoundError: 画像ファイルが見つからない場合
        
        処理フロー:
            1. 参照元フィールドから相対パス取得
            2. パス解決
            3. 画像読み込み
            4. QGraphicsSceneに追加
            5. 既存の編集内容があればロード
        """
        self._feature = feature
        self._field_name = field_name
        self._source_field_name = source_field_name
        
        # 描画アイテムをクリア（v1.6.1修正: 新しい画像読み込み時にリセット）
        self._drawing_items = []
        
        try:
            # バリデーション
            if not feature or not feature.isValid():
                self._update_status("写真: なし", "#999")
                self.graphics_scene.clear()
                return
            
            # 画像パス取得 - 編集済み画像を優先
            # 1. まず修正後フィールド（編集済み）を確認
            edited_value = self._get_field_value(feature, field_name)
            
            # 2. 編集済み画像があればそれを使用
            # None, 空文字, QVariant(NULL)を除外
            if edited_value and edited_value not in (None, '', QVariant()):
                relative_path = edited_value
                QgsMessageLog.logMessage(
                    f"PhotoEditorPanel - 編集済み画像を読み込み: {edited_value}",
                    "PoleFacility", Qgis.Info
                )
            else:
                # 3. なければ元画像（修正前）を読み込み
                relative_path = self._get_field_value(feature, source_field_name)
                QgsMessageLog.logMessage(
                    f"PhotoEditorPanel - 元画像を読み込み: {relative_path}",
                    "PoleFacility", Qgis.Info
                )
            
            if not relative_path:
                self._update_status("写真: 未設定", "#999")
                self.graphics_scene.clear()
                return
            
            # 実際のパス解決
            actual_path = self._resolve_photo_path(relative_path)
            
            QgsMessageLog.logMessage(
                f"PhotoEditorPanel - パス解決: '{relative_path}' → '{actual_path}'",
                "PoleFacility", Qgis.Info
            )
            
            # ファイル存在チェック
            if not os.path.exists(actual_path):
                # 編集後画像が見つからない場合、元画像にフォールバック
                if field_name != source_field_name:  # 編集後を探していた場合
                    QgsMessageLog.logMessage(
                        f"PhotoEditorPanel - 編集後画像が見つかりません、元画像を使用: {actual_path}",
                        "PoleFacility", Qgis.Warning
                    )
                    
                    # 元画像を再取得
                    source_value = self._get_field_value(feature, source_field_name)
                    if source_value:
                        relative_path = source_value
                        actual_path = self._resolve_photo_path(source_value)
                        
                        QgsMessageLog.logMessage(
                            f"PhotoEditorPanel - 元画像パスに切り替え: {actual_path}",
                            "PoleFacility", Qgis.Info
                        )
                        
                        if not os.path.exists(actual_path):
                            # 元画像もない場合はエラー
                            filename = os.path.basename(actual_path)
                            self._update_status(f"❌ ファイルなし: {filename}", "#FF3B30")
                            self.graphics_scene.clear()
                            raise FileNotFoundError(f"元写真ファイルが見つかりません: {actual_path}")
                    else:
                        # 元画像パスもない場合はエラー
                        filename = os.path.basename(actual_path)
                        self._update_status(f"❌ ファイルなし: {filename}", "#FF3B30")
                        self.graphics_scene.clear()
                        raise FileNotFoundError(f"写真ファイルが設定されていません")
                else:
                    # 元画像が見つからない場合はエラー
                    filename = os.path.basename(actual_path)
                    self._update_status(f"❌ ファイルなし: {filename}", "#FF3B30")
                    self.graphics_scene.clear()
                    
                    QgsMessageLog.logMessage(
                        f"PhotoEditorPanel - ファイルが存在しません: {actual_path}",
                        "PoleFacility", Qgis.Warning
                    )
                    
                    raise FileNotFoundError(f"元写真ファイルが見つかりません: {actual_path}")
            
            # 画像読み込み
            pixmap = self._load_image_as_pixmap(actual_path)
            
            if pixmap is None or pixmap.isNull():
                self._update_status("❌ 読み込み失敗", "#FF3B30")
                raise ValueError(f"画像の読み込みに失敗しました: {actual_path}")
            
            # シーンに追加
            self.graphics_scene.clear()
            self.pixmap_item = QGraphicsPixmapItem(pixmap)
            self.graphics_scene.addItem(self.pixmap_item)
            
            # シーン範囲設定
            rect = pixmap.rect()
            self.graphics_scene.setSceneRect(
                QRectF(rect.x(), rect.y(), rect.width(), rect.height())
            )
            
            # フィット（少し遅延させる）
            QTimer.singleShot(100, self._fit_to_view)
            
            # ステータス更新
            filename = os.path.basename(actual_path)
            self._update_status(f"編集可能: {filename}", "#007AFF")
            
            QgsMessageLog.logMessage(
                f"PhotoEditorPanel - 画像読み込み成功: {filename}",
                "PoleFacility", Qgis.Info
            )
            
        except FileNotFoundError:
            pass
        except Exception as e:
            self._update_status("❌ エラー", "#FF3B30")
            QgsMessageLog.logMessage(
                f"PhotoEditorPanel エラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
    
    def refresh(self):
        """
        表示を更新
        
        現在の地物とフィールド名で再読み込み
        """
        if self._feature and self._field_name and self._source_field_name:
            self.set_photo(self._feature, self._field_name, self._source_field_name)
    
    def _set_tool(self, tool: str):
        """描画ツールを設定"""
        self.current_tool = tool
    
    def _choose_color(self):
        """色選択ダイアログ"""
        color = QColorDialog.getColor(self.current_color, self, "色を選択")
        if color.isValid():
            self.current_color = color
    
    def _set_line_width(self, width: int):
        """線幅を設定"""
        self.line_width = width
    
    def _delete_selected(self):
        """選択されたアイテムを削除"""
        selected_items = self.graphics_scene.selectedItems()
        for item in selected_items:
            if item != self.pixmap_item:  # 背景画像は削除しない
                self.graphics_scene.removeItem(item)
    
    def _clear_all_drawings(self):
        """全描画オブジェクトを削除（確認あり）"""
        reply = QMessageBox.question(
            self,
            "確認",
            "全ての描画を削除しますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 背景画像以外を削除
            for item in list(self.graphics_scene.items()):
                if item != self.pixmap_item:
                    self.graphics_scene.removeItem(item)
    
    def _on_save_clicked(self):
        """
        保存ボタンクリック
        
        処理フロー:
            1. シーンをQPixmapにレンダリング
            2. 保存パス生成
            3. ディレクトリ作成
            4. 画像保存（JPEG 90%品質）
            5. レイヤに相対パスを保存
            6. イベント発行
        """
        try:
            # レイヤチェック
            if not self._layer:
                raise ValueError("レイヤが設定されていません。set_layer()を呼び出してください。")
            
            # 地物チェック
            if not self._feature:
                raise ValueError("地物が設定されていません")
            
            # シーンをレンダリング
            pixmap = self._render_scene_to_pixmap()
            
            if pixmap is None or pixmap.isNull():
                raise ValueError("レンダリングに失敗しました")
            
            # 保存パス生成
            relative_path, actual_path = self._generate_save_path()
            
            # ディレクトリ作成
            os.makedirs(os.path.dirname(actual_path), exist_ok=True)
            
            # 画像保存（JPEG 90%品質）
            image = pixmap.toImage()
            success = image.save(actual_path, "JPEG", 90)
            
            if not success:
                raise IOError(f"画像の保存に失敗しました: {actual_path}")
            
            # レイヤに保存
            was_editing = self._layer.isEditable()
            if not was_editing:
                if not self._layer.startEditing():
                    raise RuntimeError("編集モードを開始できません")
            
            try:
                # フィールドインデックス取得
                field_idx = self._layer.fields().indexOf(self._field_name)
                if field_idx < 0:
                    raise ValueError(f"フィールドが見つかりません: {self._field_name}")
                
                # 属性値更新（修正後フィールド）
                self._layer.changeAttributeValue(
                    self._feature.id(), 
                    field_idx, 
                    relative_path
                )
                
                # コミット
                if not was_editing:
                    if not self._layer.commitChanges():
                        errors = self._layer.commitErrors()
                        raise RuntimeError(f"コミット失敗: {', '.join(errors)}")
                
                QgsMessageLog.logMessage(
                    f"PhotoEditorPanel - フィールド更新: feature_id={self._feature.id()}, "
                    f"field={self._field_name}, value={relative_path}",
                    "PoleFacility", Qgis.Info
                )
                
            except Exception as e:
                # エラー時はロールバック
                if not was_editing and self._layer.isEditable():
                    self._layer.rollBack()
                raise
            
            # ★画像を保存後のファイルで再読み込み（表示更新）★
            self._reload_saved_photo(actual_path)
            
            # イベント発行
            from pole_facility_app.main.event_bus import EventBus
            EventBus.get_instance().emit("photo.saved", {
                "feature_id": self._feature.id(),
                "field_name": self._field_name,
                "path": relative_path
            })
            
            # シグナル発行
            self.photo_saved.emit(relative_path)
            
            # ステータス更新
            filename = os.path.basename(actual_path)
            self._update_status(f"✓ 保存: {filename}", "#34C759")
            
            QgsMessageLog.logMessage(
                f"写真を保存しました: {relative_path}",
                "PoleFacility", Qgis.Info
            )
            
            QMessageBox.information(
                self,
                "保存完了",
                f"写真を保存しました\n{filename}"
            )
            
            # v1.9.1追加: データ編集をマーク
            from pole_facility_app.utils.export_tracker import ExportTracker
            ExportTracker.get_instance().mark_modified()
            
        except Exception as e:
            self._update_status("❌ 保存失敗", "#FF3B30")
            QgsMessageLog.logMessage(
                f"写真保存エラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
            
            QMessageBox.critical(
                self,
                "保存エラー",
                f"写真の保存に失敗しました\n\n{str(e)}"
            )
    
    def _on_replace_original_clicked(self):
        """
        元画像差替ボタンクリック（v1.9.1追加）
        
        処理フロー:
            1. 確認ダイアログ表示
            2. 修正前フィールドの値を取得
            3. 修正後フィールドに修正前フィールドの値をコピー
            4. 元画像を再読み込み（表示更新）
            5. 完了メッセージ表示
        
        Note:
            修正前フィールドの値は変更しない
            現在の編集内容は破棄される
        """
        try:
            # レイヤチェック
            if not self._layer:
                raise ValueError("レイヤが設定されていません。set_layer()を呼び出してください。")
            
            # 地物チェック
            if not self._feature:
                raise ValueError("地物が設定されていません")
            
            # 修正前フィールド名チェック
            if not self._source_field_name:
                raise ValueError("修正前フィールド名が設定されていません")
            
            # 確認ダイアログ
            reply = QMessageBox.question(
                self,
                "元画像差替の確認",
                "元画像で差し替えますか？\n\n"
                "修正後の画像が元画像に置き換わります。\n"
                "現在の編集内容は破棄されます。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # 修正前フィールドの値を取得
            source_value = self._get_field_value(self._feature, self._source_field_name)
            
            if not source_value:
                QMessageBox.warning(
                    self,
                    "差替エラー",
                    "元画像が設定されていません"
                )
                return
            
            # レイヤに保存
            was_editing = self._layer.isEditable()
            if not was_editing:
                if not self._layer.startEditing():
                    raise RuntimeError("編集モードを開始できません")
            
            try:
                # 修正後フィールドインデックス取得
                field_idx = self._layer.fields().indexOf(self._field_name)
                if field_idx < 0:
                    raise ValueError(f"修正後フィールドが見つかりません: {self._field_name}")
                
                # 修正後フィールドに修正前の値をコピー
                self._layer.changeAttributeValue(
                    self._feature.id(),
                    field_idx,
                    source_value
                )
                
                # コミット
                if not was_editing:
                    if not self._layer.commitChanges():
                        errors = self._layer.commitErrors()
                        raise RuntimeError(f"コミット失敗: {', '.join(errors)}")
                
                QgsMessageLog.logMessage(
                    f"PhotoEditorPanel - 元画像差替完了: {self._field_name} ← {source_value}",
                    "PoleFacility", Qgis.Info
                )
                
            except Exception as e:
                # エラー時はロールバック
                if not was_editing and self._layer.isEditable():
                    self._layer.rollBack()
                raise
            
            # ★元画像を再読み込み（表示更新）★
            photo_path = self._resolve_photo_path(source_value)
            if photo_path and os.path.exists(photo_path):
                pixmap = self._load_image_as_pixmap(photo_path)
                
                if pixmap and not pixmap.isNull():
                    # シーンをクリア
                    self.graphics_scene.clear()
                    
                    # 新しい画像をセット
                    self.pixmap_item = QGraphicsPixmapItem(pixmap)
                    self.graphics_scene.addItem(self.pixmap_item)
                    
                    # 描画アイテムをクリア
                    self._drawing_items.clear()
                    
                    # シーン範囲設定
                    rect = pixmap.rect()
                    self.graphics_scene.setSceneRect(
                        QRectF(rect.x(), rect.y(), rect.width(), rect.height())
                    )
                    
                    # フィット表示
                    QTimer.singleShot(100, self._fit_to_view)
            
            # ステータス更新
            self._update_status(f"✓ 元画像に差替", "#34C759")
            
            QgsMessageLog.logMessage(
                f"元画像に差し替えました: {source_value}",
                "PoleFacility", Qgis.Info
            )
            
            QMessageBox.information(
                self,
                "差替完了",
                f"元画像に差し替えました\n\n"
                f"編集内容は破棄されました。"
            )
            
            # v1.9.1追加: データ編集をマーク
            from pole_facility_app.utils.export_tracker import ExportTracker
            ExportTracker.get_instance().mark_modified()
            
        except Exception as e:
            self._update_status("❌ 差替失敗", "#FF3B30")
            QgsMessageLog.logMessage(
                f"元画像差替エラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
            
            QMessageBox.critical(
                self,
                "差替エラー",
                f"元画像の差し替えに失敗しました\n\n{str(e)}"
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
            元の相対パス: original/2700012345局前_1/images-1.jpeg
            保存先相対パス: edited/2700012345局前_1/images-1.jpeg
        
        Returns:
            tuple: (相対パス, 実際のパス)
        
        Raises:
            ValueError: 元画像パスが取得できない場合
        """
        # 修正前フィールドから相対パス取得
        source_relative_path = self._feature[self._source_field_name]
        
        if not source_relative_path or str(source_relative_path).strip().upper() == 'NULL':
            raise ValueError(f"元画像パスが取得できません（フィールド: {self._source_field_name}）")
        
        # original/ プレフィックスを除去
        source_path_normalized = str(source_relative_path)
        if source_path_normalized.startswith("original/"):
            source_path_normalized = source_path_normalized[len("original/"):]
        elif source_path_normalized.startswith("original\\"):
            source_path_normalized = source_path_normalized[len("original\\"):]
        
        # 相対パス: edited/[元フォルダ名]/[元ファイル名]
        relative_path = f"edited/{source_path_normalized}"
        
        # 実際のパス
        photo_root = self._config_manager.get_photo_root_path()
        
        if not photo_root:
            raise ValueError("写真ルートパスが設定されていません")
        
        actual_path = os.path.join(photo_root, relative_path)
        actual_path = os.path.normpath(actual_path)
        
        return relative_path, actual_path
    
    def _get_field_value(self, feature: QgsFeature, field_name: str) -> Optional[str]:
        """
        フィールド値取得（空・NULLチェック）
        
        Args:
            feature: 地物オブジェクト
            field_name: フィールド名
        
        Returns:
            str: フィールド値、または None
        
        Raises:
            ValueError: フィールドが見つからない場合
        """
        try:
            value = feature[field_name]
        except KeyError:
            QgsMessageLog.logMessage(
                f"PhotoEditorPanel - フィールドが見つかりません: {field_name}",
                "PoleFacility", Qgis.Warning
            )
            raise ValueError(f"フィールドが見つかりません: {field_name}")
        
        if not value:
            return None
        
        value_str = str(value).strip()
        
        if value_str.upper() == 'NULL' or not value_str:
            return None
        
        return value_str
    
    def _resolve_photo_path(self, relative_path: str) -> str:
        r"""
        相対パスから実際のファイルパスを解決（OS非依存）
        
        Args:
            relative_path: CSV/GeoPackageのフィールド値
        
        Returns:
            str: 実際のファイルパス
        
        Raises:
            ValueError: photo_root_path が未設定の場合
        """
        if not relative_path or relative_path.strip().upper() == 'NULL':
            return None
        
        photo_root = self._config_manager.get_photo_root_path()
        
        if not photo_root:
            raise ValueError("写真ルートパスが設定されていません")
        
        normalized_relative = relative_path.replace('\\', '/')
        actual_path = os.path.join(photo_root, normalized_relative)
        actual_path = os.path.normpath(actual_path)
        
        return actual_path
    
    def _load_image_as_pixmap(self, photo_path: str) -> Optional[QPixmap]:
        """
        画像をQPixmapとして読み込む
        
        Args:
            photo_path: 画像ファイルパス
        
        Returns:
            QPixmap: QPixmap オブジェクト、失敗時は None
        """
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
    
    def _reload_saved_photo(self, saved_path: str):
        """
        保存後の画像を再読み込みして表示更新
        
        Args:
            saved_path: 保存先の絶対パス
        
        処理:
            1. 保存した画像を再読み込み
            2. QGraphicsSceneをクリア
            3. 新しい画像をセット
            4. 描画アイテムをクリア（保存済みのため）
            5. フィット表示
        
        Note:
            このメソッドにより、保存ボタン押下後に
            編集後の画像が表示されるようになる
        """
        try:
            QgsMessageLog.logMessage(
                f"PhotoEditorPanel - 保存後の画像を再読み込み: {saved_path}",
                "PoleFacility", Qgis.Info
            )
            
            # 画像を再読み込み
            pixmap = self._load_image_as_pixmap(saved_path)
            
            if pixmap and not pixmap.isNull():
                # シーンをクリア
                self.graphics_scene.clear()
                
                # 新しい画像をセット
                self.pixmap_item = QGraphicsPixmapItem(pixmap)
                self.graphics_scene.addItem(self.pixmap_item)
                
                # 描画アイテムをクリア（保存済みのため編集状態をリセット）
                self._drawing_items.clear()
                
                # シーン範囲設定
                rect = pixmap.rect()
                self.graphics_scene.setSceneRect(
                    QRectF(rect.x(), rect.y(), rect.width(), rect.height())
                )
                
                # フィット表示（少し遅延）
                QTimer.singleShot(100, self._fit_to_view)
                
                QgsMessageLog.logMessage(
                    "PhotoEditorPanel - 保存後の画像を正常に再読み込みしました",
                    "PoleFacility", Qgis.Info
                )
            else:
                QgsMessageLog.logMessage(
                    f"PhotoEditorPanel - 画像の再読み込みに失敗: {saved_path}",
                    "PoleFacility", Qgis.Warning
                )
        
        except Exception as e:
            QgsMessageLog.logMessage(
                f"PhotoEditorPanel - 画像再読み込みエラー: {str(e)}",
                "PoleFacility", Qgis.Warning
            )
    
    def _fit_to_view(self):
        """画像をビューにフィット表示"""
        if self.pixmap_item and self.graphics_scene:
            self.graphics_view.fitInView(
                self.graphics_scene.sceneRect(),
                Qt.KeepAspectRatio
            )
    
    def _update_status(self, text: str, color: str):
        """
        ステータスラベル更新
        
        Args:
            text: 表示テキスト
            color: 色（CSSカラーコード）
        """
        if self.status_label:
            self.status_label.setText(text)
            self.status_label.setStyleSheet(f"color: {color}; font-size: 11px;")
