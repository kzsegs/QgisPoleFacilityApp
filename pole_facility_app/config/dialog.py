"""
設定画面UIモジュール

SettingsDialogWidgetは設定画面のUIを提供する。
"""

import os
from typing import Optional

try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
        QLineEdit, QPushButton, QFileDialog, QMessageBox,
        QGroupBox, QLabel, QSpinBox, QTabWidget, QWidget
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    # テスト用フォールバック
    class QDialog:
        pass
    class pyqtSignal:
        def __init__(self, *args):
            pass

try:
    from qgis.core import Qgis, QgsMessageLog
    QGIS_AVAILABLE = True
except ImportError:
    QGIS_AVAILABLE = False


class SettingsDialogWidget(QDialog if PYQT5_AVAILABLE else object):
    """
    設定画面ダイアログ。
    
    Signals:
        settings_saved: 設定が保存された時に発行
    
    Attributes:
        config_manager: ConfigManagerインスタンス
        photo_root_edit: 写真ルートパス入力フィールド
        photo_root_browse_btn: 写真ルートパス参照ボタン
        export_path_edit: エクスポートパス入力フィールド
        export_path_browse_btn: エクスポートパス参照ボタン
        save_btn: 保存ボタン
        cancel_btn: キャンセルボタン
    
    Example:
        dialog = SettingsDialogWidget(config_manager, parent)
        if dialog.exec_():
            # 設定が保存された
            pass
    """
    
    # シグナル定義
    if PYQT5_AVAILABLE:
        settings_saved = pyqtSignal()
    
    def __init__(self, config_manager, parent=None):
        """
        コンストラクタ
        
        Args:
            config_manager: ConfigManagerインスタンス
            parent: 親ウィジェット
        """
        if not PYQT5_AVAILABLE:
            return
        
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("設定")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        self._setup_ui()
        self.load_settings()
    
    def _setup_ui(self):
        """UIを構築する"""
        if not PYQT5_AVAILABLE:
            return
        
        layout = QVBoxLayout(self)
        
        # タブウィジェット
        tab_widget = QTabWidget()
        
        # パス設定タブ
        path_tab = self._create_path_tab()
        tab_widget.addTab(path_tab, "パス設定")
        
        # 定数設定タブ
        constants_tab = self._create_constants_tab()
        tab_widget.addTab(constants_tab, "詳細設定")
        
        layout.addWidget(tab_widget)
        
        # ボタン
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self._on_save_clicked)
        button_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("キャンセル")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _create_path_tab(self) -> 'QWidget':
        """
        パス設定タブを作成する
        
        Returns:
            QWidget: パス設定タブウィジェット
        """
        if not PYQT5_AVAILABLE:
            return None
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 写真ルートパス
        photo_group = QGroupBox("写真設定")
        photo_layout = QFormLayout()
        
        photo_path_layout = QHBoxLayout()
        self.photo_root_edit = QLineEdit()
        self.photo_root_edit.setPlaceholderText("写真ファイルのルートディレクトリを指定")
        photo_path_layout.addWidget(self.photo_root_edit)
        
        self.photo_root_browse_btn = QPushButton("参照...")
        self.photo_root_browse_btn.clicked.connect(self._on_photo_browse_clicked)
        photo_path_layout.addWidget(self.photo_root_browse_btn)
        
        photo_layout.addRow("写真ルートパス:", photo_path_layout)
        
        photo_info = QLabel(
            "※ CSVファイルの写真URIフィールドは、このルートパスからの相対パスとして解決されます。\n"
            "例: ルートパス「C:/Data/Photos」+ 写真URI「original/A001/P001_1.jpg」\n"
            "　→ 実際のパス「C:/Data/Photos/original/A001/P001_1.jpg」"
        )
        photo_info.setWordWrap(True)
        photo_info.setStyleSheet("color: gray; font-size: 10px;")
        photo_layout.addRow("", photo_info)
        
        photo_group.setLayout(photo_layout)
        layout.addWidget(photo_group)
        
        # エクスポートパス
        export_group = QGroupBox("エクスポート設定")
        export_layout = QFormLayout()
        
        export_path_layout = QHBoxLayout()
        self.export_path_edit = QLineEdit()
        self.export_path_edit.setPlaceholderText("CSVエクスポート先ディレクトリを指定")
        export_path_layout.addWidget(self.export_path_edit)
        
        self.export_path_browse_btn = QPushButton("参照...")
        self.export_path_browse_btn.clicked.connect(self._on_export_browse_clicked)
        export_path_layout.addWidget(self.export_path_browse_btn)
        
        export_layout.addRow("エクスポート先:", export_path_layout)
        
        export_info = QLabel(
            "※ エクスポート時のデフォルト保存先ディレクトリです。"
        )
        export_info.setStyleSheet("color: gray; font-size: 10px;")
        export_layout.addRow("", export_info)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        layout.addStretch()
        
        return tab
    
    def _create_constants_tab(self) -> 'QWidget':
        """
        定数設定タブを作成する
        
        Returns:
            QWidget: 定数設定タブウィジェット
        """
        if not PYQT5_AVAILABLE:
            return None
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # 制限値設定
        limits_group = QGroupBox("制限値")
        limits_layout = QFormLayout()
        
        self.max_photo_size_spin = QSpinBox()
        self.max_photo_size_spin.setRange(1, 100)
        self.max_photo_size_spin.setSuffix(" MB")
        limits_layout.addRow("最大写真サイズ:", self.max_photo_size_spin)
        
        self.max_records_spin = QSpinBox()
        self.max_records_spin.setRange(100, 10000)
        self.max_records_spin.setSingleStep(100)
        limits_layout.addRow("最大レコード数/CSV:", self.max_records_spin)
        
        limits_group.setLayout(limits_layout)
        layout.addWidget(limits_group)
        
        # 表示設定
        display_group = QGroupBox("表示設定")
        display_layout = QFormLayout()
        
        self.thumbnail_size_spin = QSpinBox()
        self.thumbnail_size_spin.setRange(50, 300)
        self.thumbnail_size_spin.setSingleStep(10)
        self.thumbnail_size_spin.setSuffix(" px")
        display_layout.addRow("サムネイルサイズ:", self.thumbnail_size_spin)
        
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)
        
        # 情報表示
        info_label = QLabel(
            "※ これらの設定は上級ユーザー向けです。\n"
            "※ 変更する場合は、動作への影響を理解した上で行ってください。"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: orange; font-size: 10px; margin-top: 20px;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        return tab
    
    def load_settings(self) -> None:
        """
        現在の設定値をUIに読み込む
        
        Example:
            dialog.load_settings()
        """
        if not PYQT5_AVAILABLE:
            return
        
        # パス設定
        self.photo_root_edit.setText(self.config_manager.get_photo_root_path())
        self.export_path_edit.setText(self.config_manager.get_export_path())
        
        # 定数設定
        self.max_photo_size_spin.setValue(
            self.config_manager.get("constants.max_photo_size_mb", 10)
        )
        self.max_records_spin.setValue(
            self.config_manager.get("constants.max_records_per_csv", 1000)
        )
        self.thumbnail_size_spin.setValue(
            self.config_manager.get("constants.thumbnail_size", 100)
        )
    
    def save_settings(self) -> bool:
        """
        UIの値を設定として保存する
        
        Returns:
            bool: 保存成功時True
        
        Example:
            if dialog.save_settings():
                print("設定を保存しました")
        """
        if not PYQT5_AVAILABLE:
            return False
        
        # バリデーション
        if not self._validate_paths():
            return False
        
        try:
            # パス設定
            photo_root = self.photo_root_edit.text().strip()
            export_path = self.export_path_edit.text().strip()
            
            if photo_root:
                self.config_manager.set_photo_root_path(photo_root)
            else:
                self.config_manager.set("paths.photo_root", "")
            
            if export_path:
                self.config_manager.set_export_path(export_path)
            else:
                self.config_manager.set("paths.export_path", "")
            
            # 定数設定
            self.config_manager.set(
                "constants.max_photo_size_mb",
                self.max_photo_size_spin.value()
            )
            self.config_manager.set(
                "constants.max_records_per_csv",
                self.max_records_spin.value()
            )
            self.config_manager.set(
                "constants.thumbnail_size",
                self.thumbnail_size_spin.value()
            )
            
            # 設定ファイルに保存
            self.config_manager.save_config()
            
            # シグナル発行
            self.settings_saved.emit()
            
            return True
            
        except ValueError as e:
            QMessageBox.warning(
                self,
                "設定エラー",
                f"設定の保存に失敗しました:\n{str(e)}"
            )
            return False
        except Exception as e:
            QMessageBox.critical(
                self,
                "エラー",
                f"予期しないエラーが発生しました:\n{str(e)}"
            )
            if QGIS_AVAILABLE:
                QgsMessageLog.logMessage(
                    f"Settings save error: {str(e)}",
                    "PoleFacility",
                    Qgis.Critical
                )
            return False
    
    def _on_photo_browse_clicked(self):
        """写真ルートパス参照ボタンクリック時の処理"""
        if not PYQT5_AVAILABLE:
            return
        
        current_path = self.photo_root_edit.text()
        if not current_path or not os.path.exists(current_path):
            current_path = os.path.expanduser("~")
        
        directory = QFileDialog.getExistingDirectory(
            self,
            "写真ルートディレクトリを選択",
            current_path,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if directory:
            self.photo_root_edit.setText(directory)
    
    def _on_export_browse_clicked(self):
        """エクスポートパス参照ボタンクリック時の処理"""
        if not PYQT5_AVAILABLE:
            return
        
        current_path = self.export_path_edit.text()
        if not current_path or not os.path.exists(current_path):
            current_path = os.path.expanduser("~")
        
        directory = QFileDialog.getExistingDirectory(
            self,
            "エクスポート先ディレクトリを選択",
            current_path,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if directory:
            self.export_path_edit.setText(directory)
    
    def _validate_paths(self) -> bool:
        """
        パス設定の妥当性を検証する
        
        Returns:
            bool: 検証成功時True
        """
        if not PYQT5_AVAILABLE:
            return False
        
        photo_root = self.photo_root_edit.text().strip()
        export_path = self.export_path_edit.text().strip()
        
        # 写真ルートパスの検証
        if photo_root:
            if not os.path.exists(photo_root):
                QMessageBox.warning(
                    self,
                    "パスエラー",
                    f"写真ルートパスが存在しません:\n{photo_root}"
                )
                return False
            
            if not os.path.isdir(photo_root):
                QMessageBox.warning(
                    self,
                    "パスエラー",
                    f"写真ルートパスがディレクトリではありません:\n{photo_root}"
                )
                return False
        
        # エクスポートパスの検証
        if export_path:
            if not os.path.exists(export_path):
                QMessageBox.warning(
                    self,
                    "パスエラー",
                    f"エクスポート先パスが存在しません:\n{export_path}"
                )
                return False
            
            if not os.path.isdir(export_path):
                QMessageBox.warning(
                    self,
                    "パスエラー",
                    f"エクスポート先パスがディレクトリではありません:\n{export_path}"
                )
                return False
        
        return True
    
    def _on_save_clicked(self):
        """保存ボタンクリック時の処理"""
        if not PYQT5_AVAILABLE:
            return
        
        if self.save_settings():
            QMessageBox.information(
                self,
                "設定保存",
                "設定を保存しました。"
            )
            self.accept()
