"""
UI状態管理 - QGIS標準UIの状態を保存・復元

カスタムモード開始時にQGISのUI状態を保存し、
終了時に元の状態に復元する機能を提供する。

使用例:
    # UI状態の保存
    ui_state = UIState()
    ui_state.save_from_main_window(iface.mainWindow())
    
    # UI状態の復元
    ui_state.restore_to_main_window(iface.mainWindow())
"""

from typing import List, Optional, Dict, Any
from PyQt5.QtWidgets import QMainWindow, QToolBar, QDockWidget, QMenuBar, QMenu
from qgis.core import QgsMessageLog, Qgis


class UIState:
    """
    QGIS標準UIの状態を保存・復元するクラス。
    
    カスタムモード開始時にQGISのツールバー・メニュー・ドックウィジェット等の
    表示状態を保存し、終了時に元の状態に復元する。
    
    Attributes:
        visible_toolbars: 表示中のツールバー名リスト
        visible_menus: 表示中のメニュー名リスト
        visible_docks: 表示中のドックウィジェット名リスト
        window_title: ウィンドウタイトル
        _toolbar_objects: ツールバーオブジェクトのリスト（復元用）
        _menu_objects: メニューオブジェクトのリスト（復元用）
        _dock_objects: ドックウィジェットオブジェクトのリスト（復元用）
    """
    
    def __init__(self):
        """UIStateを初期化する。"""
        self.visible_toolbars: List[str] = []
        self.visible_menus: List[str] = []
        self.visible_docks: List[str] = []
        self.window_title: str = ""
        
        # 復元用にオブジェクト参照を保持
        self._toolbar_objects: List[QToolBar] = []
        self._menu_objects: List[QMenu] = []
        self._dock_objects: List[QDockWidget] = []
        
        QgsMessageLog.logMessage(
            "UIState初期化完了",
            "PoleFacility",
            Qgis.Info
        )
    
    def save_from_main_window(self, main_window: QMainWindow) -> None:
        """
        メインウィンドウからUI状態を保存する。
        
        Args:
            main_window: QGISメインウィンドウ
        
        Note:
            カスタムモード開始時に呼び出す
        """
        if not main_window:
            QgsMessageLog.logMessage(
                "警告: main_windowがNullです",
                "PoleFacility",
                Qgis.Warning
            )
            return
        
        try:
            # ウィンドウタイトル保存
            self.window_title = main_window.windowTitle()
            
            # ツールバー状態保存
            self._save_toolbars(main_window)
            
            # メニュー状態保存
            self._save_menus(main_window)
            
            # ドックウィジェット状態保存
            self._save_docks(main_window)
            
            QgsMessageLog.logMessage(
                f"UI状態保存完了:\n"
                f"  ツールバー: {len(self.visible_toolbars)}個\n"
                f"  メニュー: {len(self.visible_menus)}個\n"
                f"  ドック: {len(self.visible_docks)}個",
                "PoleFacility",
                Qgis.Info
            )
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"UI状態保存エラー: {str(e)}",
                "PoleFacility",
                Qgis.Critical
            )
    
    def restore_to_main_window(self, main_window: QMainWindow) -> None:
        """
        メインウィンドウへUI状態を復元する。
        
        Args:
            main_window: QGISメインウィンドウ
        
        Note:
            カスタムモード終了時に呼び出す
        """
        if not main_window:
            QgsMessageLog.logMessage(
                "警告: main_windowがNullです",
                "PoleFacility",
                Qgis.Warning
            )
            return
        
        try:
            # ウィンドウタイトル復元
            if self.window_title:
                main_window.setWindowTitle(self.window_title)
            
            # ツールバー状態復元
            self._restore_toolbars()
            
            # メニュー状態復元
            self._restore_menus()
            
            # ドックウィジェット状態復元
            self._restore_docks()
            
            QgsMessageLog.logMessage(
                f"UI状態復元完了:\n"
                f"  ツールバー: {len(self._toolbar_objects)}個\n"
                f"  メニュー: {len(self._menu_objects)}個\n"
                f"  ドック: {len(self._dock_objects)}個",
                "PoleFacility",
                Qgis.Info
            )
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"UI状態復元エラー: {str(e)}",
                "PoleFacility",
                Qgis.Critical
            )
    
    def _save_toolbars(self, main_window: QMainWindow) -> None:
        """
        ツールバーの状態を保存する。
        
        Args:
            main_window: QGISメインウィンドウ
        """
        self.visible_toolbars.clear()
        self._toolbar_objects.clear()
        
        toolbars = main_window.findChildren(QToolBar)
        for toolbar in toolbars:
            if toolbar.isVisible():
                toolbar_name = toolbar.objectName()
                if toolbar_name:
                    self.visible_toolbars.append(toolbar_name)
                    self._toolbar_objects.append(toolbar)
        
        QgsMessageLog.logMessage(
            f"ツールバー状態保存: {len(self.visible_toolbars)}個",
            "PoleFacility",
            Qgis.Info
        )
    
    def _save_menus(self, main_window: QMainWindow) -> None:
        """
        メニューの状態を保存する。
        
        Args:
            main_window: QGISメインウィンドウ
        """
        self.visible_menus.clear()
        self._menu_objects.clear()
        
        menu_bar = main_window.menuBar()
        if menu_bar:
            for action in menu_bar.actions():
                menu = action.menu()
                if menu and action.isVisible():
                    menu_title = action.text()
                    if menu_title:
                        self.visible_menus.append(menu_title)
                        self._menu_objects.append(action)
        
        QgsMessageLog.logMessage(
            f"メニュー状態保存: {len(self.visible_menus)}個",
            "PoleFacility",
            Qgis.Info
        )
    
    def _save_docks(self, main_window: QMainWindow) -> None:
        """
        ドックウィジェットの状態を保存する。
        
        Args:
            main_window: QGISメインウィンドウ
        """
        self.visible_docks.clear()
        self._dock_objects.clear()
        
        docks = main_window.findChildren(QDockWidget)
        for dock in docks:
            if dock.isVisible():
                dock_name = dock.objectName()
                if dock_name:
                    self.visible_docks.append(dock_name)
                    self._dock_objects.append(dock)
        
        QgsMessageLog.logMessage(
            f"ドック状態保存: {len(self.visible_docks)}個",
            "PoleFacility",
            Qgis.Info
        )
    
    def _restore_toolbars(self) -> None:
        """ツールバーの状態を復元する。"""
        for toolbar in self._toolbar_objects:
            try:
                toolbar.setVisible(True)
            except Exception as e:
                QgsMessageLog.logMessage(
                    f"ツールバー復元エラー: {toolbar.objectName()} - {str(e)}",
                    "PoleFacility",
                    Qgis.Warning
                )
    
    def _restore_menus(self) -> None:
        """メニューの状態を復元する。"""
        for menu_action in self._menu_objects:
            try:
                menu_action.setVisible(True)
            except Exception as e:
                QgsMessageLog.logMessage(
                    f"メニュー復元エラー: {menu_action.text()} - {str(e)}",
                    "PoleFacility",
                    Qgis.Warning
                )
    
    def _restore_docks(self) -> None:
        """ドックウィジェットの状態を復元する。"""
        for dock in self._dock_objects:
            try:
                dock.setVisible(True)
            except Exception as e:
                QgsMessageLog.logMessage(
                    f"ドック復元エラー: {dock.objectName()} - {str(e)}",
                    "PoleFacility",
                    Qgis.Warning
                )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        UI状態を辞書形式で取得する（デバッグ用）。
        
        Returns:
            Dict[str, Any]: UI状態の辞書
        """
        return {
            "window_title": self.window_title,
            "visible_toolbars": self.visible_toolbars.copy(),
            "visible_menus": self.visible_menus.copy(),
            "visible_docks": self.visible_docks.copy(),
        }
    
    def clear(self) -> None:
        """
        保存されたUI状態をクリアする。
        """
        self.visible_toolbars.clear()
        self.visible_menus.clear()
        self.visible_docks.clear()
        self.window_title = ""
        self._toolbar_objects.clear()
        self._menu_objects.clear()
        self._dock_objects.clear()
        
        QgsMessageLog.logMessage(
            "UI状態クリア完了",
            "PoleFacility",
            Qgis.Info
        )
