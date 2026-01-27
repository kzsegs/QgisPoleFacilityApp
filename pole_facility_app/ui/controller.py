"""
UI制御 - QGIS標準UIの表示/非表示制御とカスタムUIの管理

カスタムモード開始時にQGISの標準UI要素を非表示にし、
終了時に元の状態に復元する機能を提供する。

使用例:
    # 2引数での初期化（後方互換性）
    ui_controller = UIController(iface, event_bus)
    
    # 3引数での初期化（plugin.pyから）
    ui_controller = UIController(iface, event_bus, ui_state)
    
    ui_controller.initialize()
    ui_controller.enable_custom_mode()
    
    # 終了時
    ui_controller.disable_custom_mode()
"""

from typing import List, Optional
from PyQt5.QtWidgets import QToolBar, QDockWidget, QMainWindow, QStatusBar
from PyQt5.QtCore import QTimer
from qgis.gui import QgisInterface

from ..main.event_bus import EventBus, EventNames
from ..main.ui_state import UIState
from .toolbar import CustomToolbarWidget
from ..utils.logger import Logger


class UIController:
    """
    QGIS標準UIの表示/非表示制御およびカスタムUIの管理を行う。
    
    Attributes:
        iface: QGISインターフェース
        main_window: QGISメインウィンドウ
        event_bus: イベントバス
        hidden_toolbars: 非表示にしたツールバーのリスト
        hidden_dock_widgets: 非表示にしたドックウィジェットのリスト
        hidden_menus: 非表示にしたメニューのリスト
        custom_toolbar: カスタムツールバー
        is_custom_mode: カスタムモード状態フラグ
        ui_state: UI状態管理
        original_window_title: 元のウィンドウタイトル
    """
    
    # 非表示にするツールバー（QGIS標準）
    HIDDEN_TOOLBARS = [
        "mFileToolBar",
        "mLayerToolBar",
        "mDigitizeToolBar",
        "mAdvancedDigitizeToolBar",
        "mMapNavToolBar",
        "mAttributesToolBar",
        "mPluginToolBar",
        "mHelpToolBar",
        "mRasterToolBar",
        "mLabelToolBar",
        "mVectorToolBar",
        "mDatabaseToolBar",
        "mWebToolBar",
        "mSnappingToolBar",
        "mDataSourceManagerToolBar",
        "mShapeDigitizeToolBar",
        "mSelectionToolBar",
    ]
    
    # 表示を維持するドックウィジェット
    ALLOWED_DOCK_WIDGETS = [
        "Layers",  # レイヤパネル
    ]
    
    # 非表示にするドックウィジェット
    HIDDEN_DOCK_WIDGETS = [
        "Browser",
        "Browser2",
        "GPS Information",
        "Log Messages",
        "Overview",
        "Processing Toolbox",
        "Statistics",
        "Undo",
    ]
    
    def __init__(self, iface: QgisInterface, event_bus: EventBus, ui_state: UIState = None):
        """
        UIControllerを初期化する。
        
        Args:
            iface: QGISインターフェース
            event_bus: イベントバス
            ui_state: UI状態管理（オプショナル、Noneの場合は新規作成）
        
        Note:
            ui_stateを渡すことで、plugin.pyと同じUIStateインスタンスを共有可能。
            渡さない場合は内部で新規作成する（後方互換性）。
        """
        self.iface = iface
        self.main_window: QMainWindow = iface.mainWindow()
        self.event_bus = event_bus
        
        # 非表示にした要素のリスト
        self.hidden_toolbars: List[QToolBar] = []
        self.hidden_dock_widgets: List[QDockWidget] = []
        self.hidden_menus: List = []
        
        # カスタムUI
        self.custom_toolbar: Optional[CustomToolbarWidget] = None
        
        # 状態管理
        self.is_custom_mode: bool = False
        # ui_stateが渡されていればそれを使用、なければ新規作成
        self.ui_state = ui_state if ui_state is not None else UIState()
        self.original_window_title: str = ""
        
        Logger.info("UIController初期化完了")
    
    def initialize(self) -> None:
        """
        UIControllerの初期化処理を行う。
        
        処理内容:
            - カスタムツールバーの作成
        """
        try:
            # カスタムツールバー作成
            self._create_custom_toolbar()
            
            Logger.info("UIController初期化処理完了")
            
        except Exception as e:
            Logger.error(f"UIController初期化処理エラー: {str(e)}")
            raise
    
    def enable_custom_mode(self) -> None:
        """
        カスタムUIモードを有効化する。
        
        処理内容:
            1. UI状態を保存
            2. QGIS標準メニューバーを非表示
            3. QGIS標準ツールバーを非表示
            4. 不要なドックウィジェットを非表示
            5. ステータスバーを非表示
            6. カスタムツールバーを表示
            7. ウィンドウタイトルを変更
        
        Note:
            - レイヤパネルは表示維持
            - 既にカスタムモードの場合は何もしない
        """
        if self.is_custom_mode:
            Logger.info("既にカスタムモードです")
            return
        
        try:
            Logger.info("カスタムモード有効化開始")
            
            # 1. UI状態を保存
            self.ui_state.save_from_main_window(self.main_window)
            self.original_window_title = self.main_window.windowTitle()
            
            # 2. メニューバーを非表示
            self._hide_qgis_menus()
            
            # 3. ツールバーを非表示
            self._hide_qgis_toolbars()
            
            # 4. ドックウィジェットを非表示
            self._hide_qgis_dock_widgets()
            
            # 5. ステータスバーを非表示
            self._hide_status_bar()
            
            # 6. カスタムツールバーを表示
            if self.custom_toolbar:
                self.custom_toolbar.show()
            
            # 7. ウィンドウタイトルを変更
            self.main_window.setWindowTitle("電柱設備管理アプリケーション")
            
            self.is_custom_mode = True
            
            Logger.info("カスタムモード有効化完了")
            
        except Exception as e:
            Logger.error(f"カスタムモード有効化エラー: {str(e)}")
            raise
    
    def disable_custom_mode(self) -> None:
        """
        カスタムUIモードを無効化し、QGIS標準UIを復元する。
        
        処理内容:
            1. カスタムツールバーを非表示
            2. QGIS標準メニューバーを復元
            3. QGIS標準ツールバーを復元
            4. ドックウィジェットを復元
            5. ステータスバーを復元
            6. ウィンドウタイトルを復元
        
        Note:
            カスタムモードでない場合は何もしない
        """
        if not self.is_custom_mode:
            Logger.info("カスタムモードではありません")
            return
        
        try:
            Logger.info("カスタムモード無効化開始")
            
            # 1. カスタムツールバーを非表示
            if self.custom_toolbar:
                self.custom_toolbar.hide()
            
            # 2. UI状態を復元
            self.ui_state.restore_to_main_window(self.main_window)
            
            # 3. メニューバーを復元
            self._restore_qgis_menus()
            
            # 4. ツールバーを復元
            self._restore_qgis_toolbars()
            
            # 5. ドックウィジェットを復元
            self._restore_qgis_dock_widgets()
            
            # 6. ステータスバーを復元
            self._restore_status_bar()
            
            # 7. ウィンドウタイトルを復元
            if self.original_window_title:
                self.main_window.setWindowTitle(self.original_window_title)
            
            # リストをクリア
            self.hidden_toolbars.clear()
            self.hidden_dock_widgets.clear()
            self.hidden_menus.clear()
            
            self.is_custom_mode = False
            
            Logger.info("カスタムモード無効化完了")
            
        except Exception as e:
            Logger.error(f"カスタムモード無効化エラー: {str(e)}")
            raise
    
    def is_in_custom_mode(self) -> bool:
        """
        カスタムモード状態を取得する。
        
        Returns:
            bool: カスタムモード中の場合True
        """
        return self.is_custom_mode
    
    def show_status_message(self, message: str, duration: int = 5000) -> None:
        """
        ステータスバーにメッセージを表示する。
        
        Args:
            message: 表示するメッセージ
            duration: 表示時間（ミリ秒）、0で無期限
        """
        if self.main_window.statusBar():
            self.main_window.statusBar().showMessage(message, duration)
    
    def cleanup(self) -> None:
        """
        UIControllerのクリーンアップを行う。
        
        処理内容:
            - カスタムモード無効化（有効時）
            - カスタムツールバー削除
        """
        try:
            # カスタムモード無効化
            if self.is_custom_mode:
                self.disable_custom_mode()
            
            # カスタムツールバー削除
            if self.custom_toolbar:
                self.main_window.removeToolBar(self.custom_toolbar)
                self.custom_toolbar.deleteLater()
                self.custom_toolbar = None
            
            Logger.info("UIControllerクリーンアップ完了")
            
        except Exception as e:
            Logger.warning(f"UIControllerクリーンアップエラー: {str(e)}")
    
    def _hide_qgis_toolbars(self) -> None:
        """QGIS標準ツールバーを非表示にする。"""
        toolbars = self.main_window.findChildren(QToolBar)
        
        for toolbar in toolbars:
            toolbar_name = toolbar.objectName()
            
            # 非表示対象のツールバーかチェック
            if toolbar_name in self.HIDDEN_TOOLBARS and toolbar.isVisible():
                toolbar.hide()
                self.hidden_toolbars.append(toolbar)
        
        Logger.info(f"ツールバー非表示: {len(self.hidden_toolbars)}個")
    
    def _hide_qgis_menus(self) -> None:
        """QGIS標準メニューバーを非表示にする。"""
        menu_bar = self.main_window.menuBar()
        if menu_bar:
            menu_bar.hide()
        
        Logger.info("メニューバー非表示")
    
    def _hide_qgis_dock_widgets(self) -> None:
        """不要なドックウィジェットを非表示にする。"""
        docks = self.main_window.findChildren(QDockWidget)
        
        for dock in docks:
            dock_name = dock.objectName()
            
            # 表示維持対象でない かつ 表示中
            if (dock_name not in self.ALLOWED_DOCK_WIDGETS and 
                dock.isVisible()):
                dock.hide()
                self.hidden_dock_widgets.append(dock)
        
        Logger.info(f"ドックウィジェット非表示: {len(self.hidden_dock_widgets)}個")
    
    def _hide_status_bar(self) -> None:
        """ステータスバーを非表示にする。"""
        status_bar = self.main_window.statusBar()
        if status_bar:
            status_bar.hide()
        
        Logger.info("ステータスバー非表示")
    
    def _restore_qgis_toolbars(self) -> None:
        """QGIS標準ツールバーを復元する。"""
        for toolbar in self.hidden_toolbars:
            try:
                toolbar.show()
            except Exception as e:
                Logger.warning(f"ツールバー復元エラー: {toolbar.objectName()} - {str(e)}")
        
        Logger.info(f"ツールバー復元: {len(self.hidden_toolbars)}個")
    
    def _restore_qgis_menus(self) -> None:
        """QGIS標準メニューバーを復元する。"""
        menu_bar = self.main_window.menuBar()
        if menu_bar:
            menu_bar.show()
        
        Logger.info("メニューバー復元")
    
    def _restore_qgis_dock_widgets(self) -> None:
        """ドックウィジェットを復元する。"""
        for dock in self.hidden_dock_widgets:
            try:
                dock.show()
            except Exception as e:
                Logger.warning(f"ドック復元エラー: {dock.objectName()} - {str(e)}")
        
        Logger.info(f"ドックウィジェット復元: {len(self.hidden_dock_widgets)}個")
    
    def _restore_status_bar(self) -> None:
        """ステータスバーを復元する。"""
        status_bar = self.main_window.statusBar()
        if status_bar:
            status_bar.show()
        
        Logger.info("ステータスバー復元")
    
    def _create_custom_toolbar(self) -> CustomToolbarWidget:
        """
        カスタムツールバーを作成する。
        
        Returns:
            CustomToolbarWidget: 作成したカスタムツールバー
        """
        self.custom_toolbar = CustomToolbarWidget(
            self.main_window,
            self.event_bus
        )
        
        # メインウィンドウに追加
        self.main_window.addToolBar(self.custom_toolbar)
        
        # 初期状態は非表示
        self.custom_toolbar.hide()
        
        Logger.info("カスタムツールバー作成完了")
        
        return self.custom_toolbar
    
    def _get_allowed_dock_widgets(self) -> List[str]:
        """
        表示を維持するドックウィジェットのリストを取得する。
        
        Returns:
            List[str]: ドックウィジェット名のリスト
        """
        return self.ALLOWED_DOCK_WIDGETS.copy()
