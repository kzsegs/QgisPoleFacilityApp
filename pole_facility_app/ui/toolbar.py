"""
カスタムツールバー - アプリケーション専用のツールバー

インポート、保存、エクスポート、選択、検索、設定、終了ボタンを提供する。
シンプルで直感的なUIを実現する。

使用例:
    toolbar = CustomToolbarWidget(parent, event_bus)
    toolbar.update_button_states(has_data=True)
"""

from typing import Optional
from PyQt5.QtWidgets import QToolBar, QAction, QWidget
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSignal, Qt
from qgis.core import QgsMessageLog, Qgis

from ..main.event_bus import EventBus, EventNames


class CustomToolbarWidget(QToolBar):
    """
    アプリケーション専用のカスタムツールバー。
    シンプルな操作ボタンのみを提供する。
    
    Signals:
        import_clicked: インポートボタンクリック時
        save_clicked: 保存ボタンクリック時
        export_clicked: エクスポートボタンクリック時
        select_clicked: 選択ボタンクリック時（トグル動作）
        search_clicked: 検索ボタンクリック時
        settings_clicked: 設定ボタンクリック時
        exit_clicked: 終了ボタンクリック時
    
    Attributes:
        event_bus: イベントバス
        import_action: インポートアクション
        save_action: 保存アクション
        export_action: エクスポートアクション
        select_action: 選択アクション
        search_action: 検索アクション
        settings_action: 設定アクション
        exit_action: 終了アクション
    """
    
    # シグナル定義
    import_clicked = pyqtSignal()
    save_clicked = pyqtSignal()
    export_clicked = pyqtSignal()
    select_clicked = pyqtSignal(bool)  # ★修正: bool引数を追加（checked状態を渡す）
    search_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()
    exit_clicked = pyqtSignal()
    
    def __init__(self, parent: QWidget, event_bus: EventBus):
        """
        カスタムツールバーを初期化する。
        
        Args:
            parent: 親ウィジェット
            event_bus: イベントバス
        """
        super().__init__("電柱設備管理ツールバー", parent)
        
        self.event_bus = event_bus
        
        # アクション
        self.import_action: Optional[QAction] = None
        self.save_action: Optional[QAction] = None
        self.export_action: Optional[QAction] = None
        self.select_action: Optional[QAction] = None  # 選択アクション追加
        self.search_action: Optional[QAction] = None
        self.settings_action: Optional[QAction] = None
        self.exit_action: Optional[QAction] = None
        
        # セットアップ
        self._setup_toolbar()
        self._setup_actions()
        self._connect_signals()
        
        # 初期状態：データなし
        self.update_button_states(has_data=False)
        
        QgsMessageLog.logMessage(
            "CustomToolbarWidget初期化完了（全7ボタン）",
            "PoleFacility",
            Qgis.Info
        )
    
    def _setup_toolbar(self) -> None:
        """
        ツールバーの基本設定を行う。
        """
        self.setObjectName("pole_facility_custom_toolbar")
        self.setMovable(False)  # 移動不可
        self.setFloatable(False)  # フロート不可
        
        # アイコンサイズ
        from PyQt5.QtCore import QSize
        self.setIconSize(QSize(32, 32))
        
        # ツールボタンスタイル（アイコン + テキスト）
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    
    def _setup_actions(self) -> None:
        """
        ツールバーアクションを設定する。
        """
        # インポートボタン
        self.import_action = self._create_action(
            "📁",
            "インポート",
            "CSVファイルを読み込み",
            "Ctrl+O"
        )
        self.addAction(self.import_action)
        
        # 保存ボタン
        self.save_action = self._create_action(
            "💾",
            "保存",
            "GeoPackageに保存",
            "Ctrl+S"
        )
        self.addAction(self.save_action)
        
        # エクスポートボタン
        self.export_action = self._create_action(
            "📤",
            "エクスポート",
            "CSV形式でエクスポート",
            "Ctrl+E"
        )
        self.addAction(self.export_action)
        
        # セパレータ
        self.addSeparator()
        
        # 選択ボタン（トグル動作）
        self.select_action = self._create_action(
            "🖱️",
            "選択",
            "地物選択モードON/OFF",
            ""
        )
        self.select_action.setCheckable(True)  # トグル可能に設定
        self.addAction(self.select_action)
        
        # 検索ボタン
        self.search_action = self._create_action(
            "🔍",
            "検索",
            "検索・フィルタパネルを表示",
            "Ctrl+F"
        )
        self.addAction(self.search_action)
        
        # セパレータ
        self.addSeparator()
        
        # 設定ボタン
        self.settings_action = self._create_action(
            "⚙️",
            "設定",
            "設定画面を表示",
            ""
        )
        self.addAction(self.settings_action)
        
        # 終了ボタン
        self.exit_action = self._create_action(
            "❌",
            "終了",
            "カスタムUIを終了しQGIS標準UIに復帰",
            ""
        )
        self.addAction(self.exit_action)
        
        QgsMessageLog.logMessage(
            "ツールバーアクション設定完了（全7ボタン）",
            "PoleFacility",
            Qgis.Info
        )
    
    def _create_action(
        self, 
        icon_text: str, 
        text: str, 
        tooltip: str,
        shortcut: str = ""
    ) -> QAction:
        """
        アクションを作成する。
        
        Args:
            icon_text: アイコンテキスト（絵文字）
            text: ボタンテキスト
            tooltip: ツールチップ
            shortcut: ショートカットキー
        
        Returns:
            QAction: 作成したアクション
        """
        action = QAction(icon_text + " " + text, self)
        action.setToolTip(tooltip)
        action.setStatusTip(tooltip)
        
        if shortcut:
            action.setShortcut(shortcut)
        
        # data-testid設定（テスト用）
        action.setProperty("data-testid", f"{text.lower()}-btn")
        
        return action
    
    def _connect_signals(self) -> None:
        """
        シグナルを接続する。
        """
        if self.import_action:
            self.import_action.triggered.connect(self._on_import_clicked)
        
        if self.save_action:
            self.save_action.triggered.connect(self._on_save_clicked)
        
        if self.export_action:
            self.export_action.triggered.connect(self._on_export_clicked)
        
        if self.select_action:
            # ★修正: toggledシグナルを使用（checked引数が渡される）
            self.select_action.toggled.connect(self._on_select_clicked)
        
        if self.search_action:
            self.search_action.triggered.connect(self._on_search_clicked)
        
        if self.settings_action:
            self.settings_action.triggered.connect(self._on_settings_clicked)
        
        if self.exit_action:
            self.exit_action.triggered.connect(self._on_exit_clicked)
    
    def update_button_states(self, has_data: bool) -> None:
        """
        データ有無に応じてボタンの有効/無効を更新する。
        
        Args:
            has_data: データが読み込まれているかどうか
        
        状態:
            - has_data=False: 保存・エクスポート・選択・検索ボタン無効
            - has_data=True: 全ボタン有効
        
        Note:
            インポート、設定、終了ボタンは常に有効
        """
        # 保存・エクスポート・選択・検索はデータがある場合のみ有効
        if self.save_action:
            self.save_action.setEnabled(has_data)
        
        if self.export_action:
            self.export_action.setEnabled(has_data)
        
        if self.select_action:
            self.select_action.setEnabled(has_data)
        
        if self.search_action:
            self.search_action.setEnabled(has_data)
        
        # インポート、設定、終了は常に有効
        if self.import_action:
            self.import_action.setEnabled(True)
        
        if self.settings_action:
            self.settings_action.setEnabled(True)
        
        if self.exit_action:
            self.exit_action.setEnabled(True)
        
        QgsMessageLog.logMessage(
            f"ボタン状態更新: has_data={has_data}",
            "PoleFacility",
            Qgis.Info
        )
    
    def set_button_states(self, has_data: bool) -> None:
        """
        ボタンの有効/無効状態を設定する（update_button_statesのエイリアス）。
        
        Args:
            has_data: データが読み込まれているかどうか
        
        Note:
            plugin.pyの_update_button_states()から呼ばれるメソッド
        """
        self.update_button_states(has_data)
    
    def set_save_enabled(self, enabled: bool) -> None:
        """
        保存ボタンの有効/無効を設定する。
        
        Args:
            enabled: 有効にする場合True
        """
        if self.save_action:
            self.save_action.setEnabled(enabled)
    
    def set_export_enabled(self, enabled: bool) -> None:
        """
        エクスポートボタンの有効/無効を設定する。
        
        Args:
            enabled: 有効にする場合True
        """
        if self.export_action:
            self.export_action.setEnabled(enabled)
    
    def set_select_checked(self, checked: bool) -> None:
        """
        選択ボタンのチェック状態を設定する（外部からの制御用）。
        
        Args:
            checked: チェック状態にする場合True
        """
        if self.select_action:
            self.select_action.setChecked(checked)
    
    def is_select_checked(self) -> bool:
        """
        選択ボタンがチェックされているか確認する。
        
        Returns:
            bool: チェックされている場合True
        """
        if self.select_action:
            return self.select_action.isChecked()
        return False
    
    def _on_import_clicked(self) -> None:
        """
        インポートボタンクリック時の処理。
        """
        QgsMessageLog.logMessage(
            "インポートボタンクリック",
            "PoleFacility",
            Qgis.Info
        )
        
        # シグナル発行
        self.import_clicked.emit()
    
    def _on_save_clicked(self) -> None:
        """
        保存ボタンクリック時の処理。
        """
        QgsMessageLog.logMessage(
            "保存ボタンクリック",
            "PoleFacility",
            Qgis.Info
        )
        
        # シグナル発行
        self.save_clicked.emit()
    
    def _on_export_clicked(self) -> None:
        """
        エクスポートボタンクリック時の処理。
        """
        QgsMessageLog.logMessage(
            "エクスポートボタンクリック",
            "PoleFacility",
            Qgis.Info
        )
        
        # シグナル発行
        self.export_clicked.emit()
    
    def _on_select_clicked(self, checked: bool) -> None:
        """
        選択ボタンクリック時の処理（トグル動作）。
        
        Args:
            checked: チェック状態（True=ON、False=OFF）
        
        Note:
            ★修正: toggledシグナルから呼ばれるためchecked引数を受け取る
        """
        QgsMessageLog.logMessage(
            f"選択ボタンクリック（チェック状態: {checked}）",
            "PoleFacility",
            Qgis.Info
        )
        
        # シグナル発行（plugin.pyで状態に応じて処理）
        self.select_clicked.emit(checked)
    
    def _on_search_clicked(self) -> None:
        """
        検索ボタンクリック時の処理。
        """
        QgsMessageLog.logMessage(
            "検索ボタンクリック",
            "PoleFacility",
            Qgis.Info
        )
        
        # シグナル発行
        self.search_clicked.emit()
    
    def _on_settings_clicked(self) -> None:
        """
        設定ボタンクリック時の処理。
        設定ダイアログを表示する。
        """
        QgsMessageLog.logMessage(
            "設定ボタンクリック",
            "PoleFacility",
            Qgis.Info
        )
        
        # 設定ダイアログを表示
        from pole_facility_app.config.dialog import SettingsDialogWidget
        
        dialog = SettingsDialogWidget(self)
        dialog.exec_()
        
        # シグナル発行
        self.settings_clicked.emit()
    
    def _on_exit_clicked(self) -> None:
        """
        終了ボタンクリック時の処理。
        """
        QgsMessageLog.logMessage(
            "終了ボタンクリック",
            "PoleFacility",
            Qgis.Info
        )
        
        # シグナル発行
        self.exit_clicked.emit()
        
        # イベント発行
        self.event_bus.emit(EventNames.APP_EXIT_REQUESTED)
