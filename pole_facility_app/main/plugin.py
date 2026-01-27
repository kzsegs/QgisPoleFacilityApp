"""
Pole Facility Main Plugin

電柱設備管理アプリケーションのメインプラグイン。
他プラグインの初期化・連携調整を行う。
"""

import os
from pathlib import Path

from qgis.PyQt.QtCore import QCoreApplication, QTranslator, QLocale
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsMessageLog, Qgis, QgsProject

from .event_bus import EventBus
from .ui_state import UIState
from ..ui.controller import UIController
from ..data.manager import DataManager
from ..navigation.controller import NavigationController
from ..search.manager import SearchManager
from ..config.manager import ConfigManager
from ..photo.widget_factory import PhotoWidgetFactory


class PoleFacilityMain:
    """
    電柱設備管理アプリケーションのメインプラグイン。
    
    責務:
        - アプリケーション全体の起動・終了制御
        - 他プラグインの初期化・連携調整
        - イベントバスの管理
        - UI状態の保存・復元
    """

    def __init__(self, iface):
        """
        プラグインを初期化する。
        
        Args:
            iface: QGISインターフェース
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        
        # トランスレータの初期化
        locale = QLocale.system().name()
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            f'PoleFacilityMain_{locale}.qm'
        )
        
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)
        
        # アクションリスト
        self.actions = []
        
        # メニュー名
        self.menu = self.tr('&Pole Facility')
        
        # コンポーネント
        self.event_bus = None
        self.ui_state = None
        self.ui_controller = None
        self.data_manager = None
        self.navigator = None
        self.search_manager = None
        self.config_manager = None
        
        QgsMessageLog.logMessage(
            "PoleFacilityMain plugin initialized",
            "PoleFacility",
            Qgis.Info
        )

    def tr(self, message):
        """
        翻訳を取得する。
        
        Args:
            message: 翻訳するメッセージ
        
        Returns:
            str: 翻訳されたメッセージ
        """
        return QCoreApplication.translate('PoleFacilityMain', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None
    ):
        """
        プラグインにアクションを追加する。
        
        Args:
            icon_path: アイコンのパス
            text: アクションのテキスト
            callback: コールバック関数
            enabled_flag: 有効/無効フラグ
            add_to_menu: メニューに追加するか
            add_to_toolbar: ツールバーに追加するか
            status_tip: ステータスチップ
            whats_this: What's This
            parent: 親ウィジェット
        
        Returns:
            QAction: 作成されたアクション
        """
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action
            )

        self.actions.append(action)

        return action

    def initGui(self):
        """
        プラグインのGUIを初期化する。
        
        Note:
            メニュー項目とアクションを追加するのみ。
            実際のカスタムUIモード起動はrun()で行う。
        """
        try:
            # アイコンパス
            icon_path = os.path.join(
                self.plugin_dir,
                'icon.png'
            )
            
            # プラグイン起動アクションを追加
            self.add_action(
                icon_path,
                text=self.tr('電柱設備管理'),
                callback=self.run,
                parent=self.iface.mainWindow(),
                add_to_toolbar=True,
                add_to_menu=True,
                status_tip=self.tr('電柱設備管理アプリケーションを起動')
            )
            
            QgsMessageLog.logMessage(
                "PoleFacilityMain plugin menu initialized",
                "PoleFacility",
                Qgis.Info
            )
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error initializing plugin menu: {str(e)}",
                "PoleFacility",
                Qgis.Critical
            )
            raise

    def run(self):
        """
        プラグインを実行する（メニュークリック時）。
        
        Note:
            - シングルトン取得
            - 各コンポーネントの初期化
            - シグナル接続
            - カスタムUIモード開始
        """
        try:
            # 既に実行中の場合は何もしない
            if hasattr(self, '_is_running') and self._is_running:
                QgsMessageLog.logMessage(
                    "Plugin is already running",
                    "PoleFacility",
                    Qgis.Warning
                )
                return
            
            # シングルトンを取得
            self.event_bus = EventBus.get_instance()
            self.config_manager = ConfigManager.get_instance()
            
            # Logger を初期化（ConfigManagerに依存） - v1.9.1追加
            from ..utils.logger import Logger
            Logger.configure(self.config_manager)
            
            # 写真ウィジェットを登録
            PhotoWidgetFactory.register_widgets()
            
            # UI状態管理を初期化
            self.ui_state = UIState()
            
            # UIコントローラーを初期化
            self.ui_controller = UIController(
                self.iface,
                self.event_bus,
                self.ui_state
            )
            
            # データマネージャーを初期化
            self.data_manager = DataManager(
                self.iface,
                self.event_bus
            )
            
            # ナビゲーションコントローラーを初期化
            self.navigator = NavigationController(
                self.iface,
                self.event_bus,
                self.config_manager,
                self.data_manager
            )
            
            # 検索マネージャーを初期化
            self.search_manager = SearchManager(
                self.iface,
                self.event_bus,
                self.config_manager,
                self.data_manager
            )
            
            # UIコントローラーを初期化（QGIS標準UIを非表示）
            self.ui_controller.initialize()
            
            # ナビゲーションコントローラーを初期化
            self.navigator.initialize()
            
            # 検索マネージャーを初期化
            # ※パネルは作成するが表示はしない
            self.search_manager.initialize()
            
            # シグナル接続
            self._connect_signals()
            
            # カスタムUIモードを有効化
            self.ui_controller.enable_custom_mode()
            
            # 実行中フラグ
            self._is_running = True
            
            QgsMessageLog.logMessage(
                "PoleFacilityMain plugin started",
                "PoleFacility",
                Qgis.Info
            )
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error starting plugin: {str(e)}",
                "PoleFacility",
                Qgis.Critical
            )
            # エラー時はクリーンアップ
            self._cleanup_on_error()
            raise

    def _connect_signals(self):
        """
        シグナルを接続する。
        
        Note:
            各コンポーネント間のシグナル/スロット接続
        """
        # カスタムツールバーのシグナル接続
        if self.ui_controller.custom_toolbar:
            toolbar = self.ui_controller.custom_toolbar
            
            # インポートボタン
            toolbar.import_clicked.connect(self._on_import_clicked)
            
            # 保存ボタン
            toolbar.save_clicked.connect(self._on_save_clicked)
            
            # エクスポートボタン
            toolbar.export_clicked.connect(self._on_export_clicked)
            
            # 選択ボタン
            toolbar.select_clicked.connect(self._on_select_clicked)
            
            # 検索ボタン
            toolbar.search_clicked.connect(self._on_search_clicked)
            
            # 設定ボタン
            toolbar.settings_clicked.connect(self._on_settings_clicked)
            
            # 終了ボタン
            toolbar.exit_clicked.connect(self.exit_custom_mode)
        
        # データマネージャーのイベント購読
        if self.event_bus:
            self.event_bus.subscribe('data.imported', self._on_data_imported)
            self.event_bus.subscribe('data.saved', self._on_data_saved)
            self.event_bus.subscribe('data.exported', self._on_data_exported)

    def _on_import_clicked(self):
        """
        インポートボタンクリック時の処理。
        """
        QgsMessageLog.logMessage(
            "インポートボタンクリック",
            "PoleFacility",
            Qgis.Info
        )
        
        # CSVファイル選択ダイアログを表示
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self.iface.mainWindow(),
            "CSVファイルを選択",
            "",
            "CSV Files (*.csv)"
        )
        
        if file_path:
            # CSVインポート
            success = self.data_manager.import_csv(file_path)
            
            if success:
                QMessageBox.information(
                    self.iface.mainWindow(),
                    "インポート成功",
                    f"CSVファイルをインポートしました:\n{file_path}"
                )
            else:
                QMessageBox.warning(
                    self.iface.mainWindow(),
                    "インポートエラー",
                    "CSVファイルのインポートに失敗しました"
                )

    def _on_save_clicked(self):
        """
        保存ボタンクリック時の処理。
        """
        QgsMessageLog.logMessage(
            "保存ボタンクリック",
            "PoleFacility",
            Qgis.Info
        )
        
        # GeoPackageに保存
        success = self.data_manager.save_to_gpkg()
        
        if success:
            QMessageBox.information(
                self.iface.mainWindow(),
                "保存成功",
                "データを保存しました"
            )
        else:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "保存エラー",
                "データの保存に失敗しました"
            )

    def _on_export_clicked(self):
        """
        エクスポートボタンクリック時の処理。
        """
        QgsMessageLog.logMessage(
            "エクスポートボタンクリック",
            "PoleFacility",
            Qgis.Info
        )
        
        # CSVファイル保存ダイアログを表示
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self.iface.mainWindow(),
            "CSVファイルを保存",
            "",
            "CSV Files (*.csv)"
        )
        
        if file_path:
            # CSVエクスポート
            success = self.data_manager.export_to_csv(file_path)
            
            if success:
                QMessageBox.information(
                    self.iface.mainWindow(),
                    "エクスポート成功",
                    f"CSVファイルをエクスポートしました:\n{file_path}"
                )
            else:
                QMessageBox.warning(
                    self.iface.mainWindow(),
                    "エクスポートエラー",
                    "CSVファイルのエクスポートに失敗しました"
                )

    def _on_select_clicked(self, checked: bool):
        """
        選択ボタンクリック時の処理。
        
        Args:
            checked: チェック状態
        """
        QgsMessageLog.logMessage(
            f"選択ボタンクリック（チェック状態: {checked}）",
            "PoleFacility",
            Qgis.Info
        )
        
        if checked:
            # 選択ツールを有効化
            self.navigator.activate_select_tool()
        else:
            # 選択ツールを無効化
            self.navigator.deactivate_select_tool()

    def _on_search_clicked(self):
        """
        検索ボタンクリック時の処理。
        """
        QgsMessageLog.logMessage(
            "検索ボタンクリック",
            "PoleFacility",
            Qgis.Info
        )
        
        # 検索パネルを表示
        self.search_manager.show_search_panel()

    def _on_settings_clicked(self):
        """
        設定ボタンクリック時の処理。
        
        Note:
            toolbar.py の _on_settings_clicked() で
            既に設定ダイアログを表示しているため、
            ここでは何もしない
        """
        QgsMessageLog.logMessage(
            "設定ボタンクリック（toolbar経由で設定画面表示済み）",
            "PoleFacility",
            Qgis.Info
        )

    def _on_data_imported(self, data: dict):
        """
        データインポート時の処理。
        
        Args:
            data: イベントデータ
        """
        QgsMessageLog.logMessage(
            f"データインポート完了: {data}",
            "PoleFacility",
            Qgis.Info
        )
        
        # ボタン状態を更新
        if self.ui_controller.custom_toolbar:
            self.ui_controller.custom_toolbar.update_button_states(has_data=True)

    def _on_data_saved(self, data: dict):
        """
        データ保存時の処理。
        
        Args:
            data: イベントデータ
        """
        QgsMessageLog.logMessage(
            f"データ保存完了: {data}",
            "PoleFacility",
            Qgis.Info
        )

    def _on_data_exported(self, data: dict):
        """
        データエクスポート時の処理。
        
        Args:
            data: イベントデータ
        """
        QgsMessageLog.logMessage(
            f"データエクスポート完了: {data}",
            "PoleFacility",
            Qgis.Info
        )

    def exit_custom_mode(self):
        """
        カスタムUIモードを終了する。
        
        Note:
            - 未保存変更の確認
            - QGIS標準UIの復元
            - シングルトンのクリーンアップ
            - 実行中フラグのリセット
        """
        QgsMessageLog.logMessage(
            "カスタムUIモード終了",
            "PoleFacility",
            Qgis.Info
        )
        
        # 未保存変更の確認
        if self.data_manager and self.data_manager.is_data_modified():
            reply = QMessageBox.question(
                self.iface.mainWindow(),
                "未保存の変更",
                "保存されていない変更があります。保存しますか？",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )
            
            if reply == QMessageBox.Save:
                # 保存
                self.data_manager.save_to_gpkg()
            elif reply == QMessageBox.Cancel:
                # キャンセル
                return
        
        # カスタムUIモードを無効化
        if self.ui_controller:
            self.ui_controller.disable_custom_mode()
        
        # 各コンポーネントのクリーンアップ
        if self.search_manager:
            self.search_manager.cleanup()
        
        if self.navigator:
            self.navigator.cleanup()
        
        if self.data_manager:
            self.data_manager.cleanup()
        
        # 実行中フラグをリセット
        self._is_running = False
        
        QMessageBox.information(
            self.iface.mainWindow(),
            "終了",
            "カスタムUIモードを終了しました"
        )

    def _cleanup_on_error(self):
        """
        エラー時のクリーンアップ処理。
        """
        try:
            if hasattr(self, 'ui_controller') and self.ui_controller:
                self.ui_controller.disable_custom_mode()
            
            if hasattr(self, 'search_manager') and self.search_manager:
                self.search_manager.cleanup()
            
            if hasattr(self, 'navigator') and self.navigator:
                self.navigator.cleanup()
            
            if hasattr(self, 'data_manager') and self.data_manager:
                self.data_manager.cleanup()
            
            # 実行中フラグをリセット
            self._is_running = False
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error during cleanup: {str(e)}",
                "PoleFacility",
                Qgis.Warning
            )

    def unload(self):
        """
        プラグインをアンロードする。
        
        Note:
            - カスタムUIモードを終了
            - シングルトンをクリア
            - リソースをクリーンアップ
        """
        try:
            # カスタムUIモードを無効化
            if hasattr(self, 'ui_controller') and self.ui_controller:
                self.ui_controller.disable_custom_mode()
            
            # 各コンポーネントのクリーンアップ
            if hasattr(self, 'search_manager') and self.search_manager:
                self.search_manager.cleanup()
            
            if hasattr(self, 'navigator') and self.navigator:
                self.navigator.cleanup()
            
            if hasattr(self, 'data_manager') and self.data_manager:
                self.data_manager.cleanup()
            
            # メニューからアクションを削除
            for action in self.actions:
                self.iface.removePluginMenu(
                    self.menu,
                    action
                )
                self.iface.removeToolBarIcon(action)
            
            # Logger をクリーンアップ - v1.9.1追加
            from ..utils.logger import Logger
            Logger.cleanup()
            
            # シングルトンをクリア
            EventBus.clear_instance()
            ConfigManager.clear_instance()
            
            # 写真ウィジェットの登録解除
            PhotoWidgetFactory.unregister_widgets()
            
            # 実行中フラグをリセット
            if hasattr(self, '_is_running'):
                self._is_running = False
            
            QgsMessageLog.logMessage(
                "PoleFacilityMain plugin unloaded",
                "PoleFacility",
                Qgis.Info
            )
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Error unloading plugin: {str(e)}",
                "PoleFacility",
                Qgis.Critical
            )
