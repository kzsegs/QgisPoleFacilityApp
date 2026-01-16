# -*- coding: utf-8 -*-
"""
Photo Viewer Widget - 表示専用ウィジェット

修正前および修正後の写真を表示するための読み取り専用ウィジェット
"""

import os
from qgis.gui import QgsEditorWidgetWrapper
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGraphicsView, 
    QGraphicsScene, QGraphicsPixmapItem
)
from qgis.PyQt.QtGui import QPixmap, QImage, QPainter
from qgis.PyQt.QtCore import Qt, QRectF, QTimer
from qgis.core import QgsMessageLog, Qgis


class PhotoViewerWidget(QgsEditorWidgetWrapper):
    """
    写真表示専用ウィジェット（編集不可）
    
    機能:
        - 相対パスから実際のパスを解決
        - 画像を QGraphicsView に表示
        - 読み取り専用（編集不可）
        - フィット表示
    
    対象フィールド:
        - 設備写真1URI_修正前
        - 設備写真2URI_修正前
        - 設備写真3URI_修正前
        - 設備写真1URI_修正後（編集済み画像の表示）
        - 設備写真2URI_修正後（編集済み画像の表示）
        - 設備写真3URI_修正後（編集済み画像の表示）
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
        self._current_feature = None
    
    def createWidget(self, parent):
        """
        ウィジェット作成
        
        レイアウト:
            [ステータスラベル]
            [QGraphicsView]
        
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
        self.status_label = QLabel("写真", widget)
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # QGraphicsView（画像表示エリア）- 読み取り専用
        self.graphics_scene = QGraphicsScene(widget)
        self.graphics_view = QGraphicsView(self.graphics_scene, widget)
        self.graphics_view.setMinimumSize(300, 200)
        self.graphics_view.setMaximumSize(600, 400)
        self.graphics_view.setRenderHint(QPainter.Antialiasing, True)
        self.graphics_view.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.graphics_view.setStyleSheet("""
            QGraphicsView {
                border: 1px solid #ccc;
                background-color: #f8f8f8;
            }
        """)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # インタラクションを無効化（読み取り専用）
        self.graphics_view.setInteractive(False)
        
        layout.addWidget(self.graphics_view)
        
        self.widget = widget
        return widget
    
    def initWidget(self, editor):
        """初期化（QgsEditorWidgetWrapperインターフェース）"""
        pass
    
    def setFeature(self, feature):
        """
        地物がセットされた時
        
        処理フロー:
            1. 親クラスの setFeature() 呼び出し
            2. load_photo() で画像読み込み
        
        Args:
            feature: 地物オブジェクト
        """
        super().setFeature(feature)
        self._current_feature = feature
        self.load_photo()
    
    def value(self):
        """
        現在の値を返す（表示専用のためNone）
        
        Returns:
            None: 表示専用のため値を返さない
        """
        return None
    
    def valid(self):
        """
        バリデーション（常にTrue）
        
        Returns:
            bool: True
        """
        return True
    
    def load_photo(self):
        """
        写真読み込み・表示
        
        処理フロー:
            1. 地物からフィールド値取得（相対パス）
            2. パス解決（_resolve_photo_path）
            3. 画像読み込み（_load_image_as_pixmap）
            4. QGraphicsScene に追加
            5. フィット表示（_fit_to_view）
            6. ステータス更新
        
        エラーハンドリング:
            - フィールド値が空 → ステータス: "なし"
            - ファイルが存在しない → ステータス: "❌ ファイルなし"
            - 読み込み失敗 → ステータス: "❌ 読み込み失敗"
        """
        try:
            # 地物取得
            feature = self._get_feature()
            
            if not feature or not feature.isValid():
                self._update_status("写真: なし", "#999")
                self.graphics_scene.clear()
                return
            
            # 相対パス取得（★修正: field()メソッドを使用）
            relative_path = self._get_field_value(feature)
            
            if not relative_path:
                self._update_status("写真: 未設定", "#999")
                self.graphics_scene.clear()
                return
            
            # 実際のパス解決
            actual_path = self._resolve_photo_path(relative_path)
            
            QgsMessageLog.logMessage(
                f"PhotoViewer - パス解決: '{relative_path}' → '{actual_path}'",
                "PoleFacility", Qgis.Info
            )
            
            if not os.path.exists(actual_path):
                self._update_status(f"❌ ファイルなし: {os.path.basename(actual_path)}", "#FF3B30")
                self.graphics_scene.clear()
                
                QgsMessageLog.logMessage(
                    f"PhotoViewer - ファイルが存在しません: {actual_path}",
                    "PoleFacility", Qgis.Warning
                )
                
                # エラーイベント発行
                from pole_facility_app.main.event_bus import EventBus
                EventBus.get_instance().emit("photo.load_error", {
                    "feature_id": feature.id(),
                    "field_name": self.field().name(),
                    "path": actual_path,
                    "error": "File not found"
                })
                return
            
            # 画像読み込み
            pixmap = self._load_image_as_pixmap(actual_path)
            
            if pixmap is None or pixmap.isNull():
                self._update_status("❌ 読み込み失敗", "#FF3B30")
                return
            
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
            self._update_status(f"✓ {filename}", "#34C759")
            
            QgsMessageLog.logMessage(
                f"PhotoViewer - 画像読み込み成功: {filename}",
                "PoleFacility", Qgis.Info
            )
            
        except Exception as e:
            self._update_status("❌ エラー", "#FF3B30")
            QgsMessageLog.logMessage(
                f"PhotoViewer エラー: {str(e)}",
                "PoleFacility", Qgis.Critical
            )
    
    def _get_feature(self):
        """
        地物取得（formFeature() が使えない場合の対応）
        
        Returns:
            QgsFeature: 地物オブジェクト
        """
        try:
            return self.formFeature()
        except AttributeError:
            return getattr(self, '_current_feature', None)
        except:
            return None
    
    def _get_field_value(self, feature):
        """
        フィールド値取得（空・NULL チェック）
        
        Args:
            feature: 地物オブジェクト
        
        Returns:
            str: フィールド値、または None
        """
        # ★修正: self.field().name() を使用してフィールド名を取得
        field_name = self.field().name()
        
        try:
            value = feature[field_name]
        except KeyError:
            QgsMessageLog.logMessage(
                f"PhotoViewer - フィールドが見つかりません: {field_name}",
                "PoleFacility", Qgis.Warning
            )
            return None
        
        if not value:
            return None
        
        value_str = str(value).strip()
        
        if value_str.upper() == 'NULL' or not value_str:
            return None
        
        return value_str
    
    def _resolve_photo_path(self, relative_path: str) -> str:
        r"""
        相対パスから実際のファイルパスを解決（OS非依存）
        
        処理:
            1. ConfigManager から photo_root_path 取得
            2. 相対パスのパス区切り文字を正規化（\ → /）
            3. os.path.join() で結合
            4. os.path.normpath() で最終的に正規化
        
        Args:
            relative_path: CSV/GeoPackageのフィールド値
                          例: "original/A001/P001_1.jpg"
                          または "original\A001\P001_1.jpg"
        
        Returns:
            str: 実際のファイルパス
                 例（Mac）: "/Users/.../Photos/original/A001/P001_1.jpg"
                 例（Win）: "C:\Users\...\Photos\original\A001\P001_1.jpg"
        
        Raises:
            ValueError: photo_root_path が未設定の場合
        """
        if not relative_path or relative_path.strip().upper() == 'NULL':
            return None
        
        # ConfigManager からルートパス取得
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
        """
        画像をQPixmapとして読み込む
        
        処理:
            1. QImage として読み込み
            2. RGB32 フォーマットに変換
            3. QPixmap に変換
        
        Args:
            photo_path: 画像ファイルパス
        
        Returns:
            QPixmap: QPixmap オブジェクト、失敗時は None
        
        Note:
            QImage.Format_RGB32 に変換することで、
            各種画像形式に対応
        """
        try:
            qimage = QImage(photo_path)
            
            if not qimage.isNull():
                # RGB32フォーマットに変換
                qimage = qimage.convertToFormat(QImage.Format_RGB32)
                return QPixmap.fromImage(qimage)
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"画像読み込み失敗: {str(e)}",
                "PoleFacility", Qgis.Warning
            )
        
        return None
    
    def _fit_to_view(self):
        """
        画像をビューにフィット表示
        
        処理:
            QGraphicsView.fitInView() を使用して
            アスペクト比を保持したまま表示範囲を調整
        
        Note:
            QTimer.singleShot() で少し遅延させて呼ぶこと
            （ウィジェットのサイズが確定してから実行）
        """
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
