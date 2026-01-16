# -*- coding: utf-8 -*-
"""
Photo Widget Factory

QGISエディタウィジェットのファクトリクラス
"""

from qgis.gui import QgsEditorWidgetFactory, QgsEditorConfigWidget
from qgis.PyQt.QtWidgets import QWidget
from qgis.core import QgsMessageLog, Qgis


class PhotoEditorConfigWidget(QgsEditorConfigWidget):
    """
    設定ウィジェット（空実装）
    
    Note:
        現時点では設定項目なし
        将来的に設定が必要になった場合に実装
    """
    
    def __init__(self, vl, fieldIdx, parent):
        super().__init__(vl, fieldIdx, parent)
    
    def config(self):
        """
        設定を返す
        
        Returns:
            dict: 設定辞書（空）
        """
        return {}
    
    def setConfig(self, config):
        """
        設定を受け取る
        
        Args:
            config: 設定辞書
        """
        pass


class PhotoViewerWidgetFactory(QgsEditorWidgetFactory):
    """
    写真表示専用ウィジェットファクトリ
    
    機能:
        - PhotoViewerWidget のインスタンス生成
        - 読み取り専用の写真表示ウィジェット
    """
    
    def __init__(self, name):
        """
        初期化
        
        Args:
            name: ウィジェット名（"Photo Viewer"）
        """
        super().__init__(name)
    
    def create(self, vl, fieldIdx, editor, parent):
        """
        ウィジェットインスタンスを作成
        
        Args:
            vl: QgsVectorLayer
            fieldIdx: フィールドインデックス
            editor: エディタウィジェット
            parent: 親ウィジェット
        
        Returns:
            PhotoViewerWidget: 写真表示ウィジェット
        """
        from .viewer_widget import PhotoViewerWidget
        return PhotoViewerWidget(vl, fieldIdx, editor, parent)
    
    def configWidget(self, vl, fieldIdx, parent):
        """
        設定ウィジェットを返す
        
        Args:
            vl: QgsVectorLayer
            fieldIdx: フィールドインデックス
            parent: 親ウィジェット
        
        Returns:
            PhotoEditorConfigWidget: 設定ウィジェット
        """
        return PhotoEditorConfigWidget(vl, fieldIdx, parent)


class PhotoEditorWidgetFactory(QgsEditorWidgetFactory):
    """
    写真編集ウィジェットファクトリ
    
    機能:
        - PhotoEditorWidget のインスタンス生成
        - 編集可能な写真ウィジェット（描画ツール付き）
    """
    
    def __init__(self, name):
        """
        初期化
        
        Args:
            name: ウィジェット名（"Photo Editor"）
        """
        super().__init__(name)
    
    def create(self, vl, fieldIdx, editor, parent):
        """
        ウィジェットインスタンスを作成
        
        Args:
            vl: QgsVectorLayer
            fieldIdx: フィールドインデックス
            editor: エディタウィジェット
            parent: 親ウィジェット
        
        Returns:
            PhotoEditorWidget: 写真編集ウィジェット
        """
        from .editor_widget import PhotoEditorWidget
        return PhotoEditorWidget(vl, fieldIdx, editor, parent)
    
    def configWidget(self, vl, fieldIdx, parent):
        """
        設定ウィジェットを返す
        
        Args:
            vl: QgsVectorLayer
            fieldIdx: フィールドインデックス
            parent: 親ウィジェット
        
        Returns:
            PhotoEditorConfigWidget: 設定ウィジェット
        """
        return PhotoEditorConfigWidget(vl, fieldIdx, parent)


class PhotoWidgetFactory:
    """
    写真ウィジェットファクトリ
    
    責務:
        - QgsEditorWidgetRegistry への登録
        - PhotoViewerWidgetFactory 生成
        - PhotoEditorWidgetFactory 生成
    """
    
    @staticmethod
    def register_widgets():
        """
        ウィジェットを登録
        
        呼び出し元:
            plugin.py の run() メソッド
        
        Note:
            QGISの属性フォームで使用可能になる
        """
        try:
            from qgis.gui import QgsGui
            
            registry = QgsGui.editorWidgetRegistry()
            
            # Photo Viewer（表示専用）を登録
            viewer_factory = PhotoViewerWidgetFactory("Photo Viewer")
            registry.registerWidget("Photo Viewer", viewer_factory)
            
            # Photo Editor（編集可能）を登録
            editor_factory = PhotoEditorWidgetFactory("Photo Editor")
            registry.registerWidget("Photo Editor", editor_factory)
            
            QgsMessageLog.logMessage(
                "✓ Photo Viewer / Photo Editor ウィジェットを登録しました",
                "PoleFacility",
                Qgis.Info
            )
            
            return True
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"❌ ウィジェット登録エラー: {str(e)}",
                "PoleFacility",
                Qgis.Critical
            )
            return False
    
    @staticmethod
    def unregister_widgets():
        """
        ウィジェットの登録解除
        
        Note:
            プラグイン終了時に呼び出す
        """
        try:
            # QgsEditorWidgetRegistry は登録解除メソッドを提供していないため、
            # 実質的には何もしない
            # プラグイン再読み込み時にレジストリが自動的にクリアされる
            
            QgsMessageLog.logMessage(
                "✓ Photo Widgets の登録解除完了",
                "PoleFacility",
                Qgis.Info
            )
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"❌ ウィジェット登録解除エラー: {str(e)}",
                "PoleFacility",
                Qgis.Warning
            )
