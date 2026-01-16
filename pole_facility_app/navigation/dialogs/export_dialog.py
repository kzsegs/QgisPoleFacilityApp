"""
Export Dialog Module

CSVファイルへのエクスポートを行うダイアログ。
保存先選択、バリデーション、エクスポート実行を提供する。
"""

import os
import logging
from typing import Optional
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QProgressBar, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal

# ロガー設定
logger = logging.getLogger(__name__)


class ExportDialog(QDialog):
    """
    CSVエクスポートダイアログ。
    
    現在のレイヤデータをCSVファイルにエクスポートする。
    
    Signals:
        export_completed: エクスポート完了時に発行（ファイルパスを渡す）
    """
    
    # シグナル定義
    export_completed = pyqtSignal(str)  # output_path
    
    def __init__(self, parent, data_manager, config_manager):
        """
        ExportDialogを初期化する。
        
        Args:
            parent: 親ウィジェット
            data_manager: データマネージャ
            config_manager: 設定マネージャ
        """
        super().__init__(parent)
        
        self.data_manager = data_manager
        self.config_manager = config_manager
        
        self._setup_ui()
        self._connect_signals()
        
        logger.debug("ExportDialog initialized")
    
    def _setup_ui(self) -> None:
        """
        UIを構築する。
        
        レイアウト:
            - ファイル選択行（パス入力 + 参照ボタン）
            - オプション（タイムスタンプ追加）
            - プログレスバー
            - ボタン行（エクスポート、キャンセル）
        """
        self.setWindowTitle("CSVエクスポート")
        self.setMinimumWidth(500)
        
        # メインレイアウト
        layout = QVBoxLayout()
        
        # ファイル選択セクション
        file_layout = QHBoxLayout()
        
        file_label = QLabel("保存先:")
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("保存先を選択してください")
        self.browse_btn = QPushButton("参照...")
        self.browse_btn.setProperty("data-testid", "browse-export-btn")
        
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_path_edit, 1)
        file_layout.addWidget(self.browse_btn)
        
        layout.addLayout(file_layout)
        
        # オプション
        self.timestamp_checkbox = QCheckBox("ファイル名にタイムスタンプを追加")
        self.timestamp_checkbox.setChecked(True)
        layout.addWidget(self.timestamp_checkbox)
        
        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 情報ラベル
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        # ボタン行
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.export_btn = QPushButton("エクスポート")
        self.export_btn.setProperty("data-testid", "export-csv-btn")
        self.export_btn.setEnabled(False)
        self.export_btn.setDefault(True)
        
        self.cancel_btn = QPushButton("キャンセル")
        self.cancel_btn.setProperty("data-testid", "cancel-export-btn")
        
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # デフォルトパスを設定
        self._set_default_path()
    
    def _connect_signals(self) -> None:
        """
        シグナルを接続する。
        """
        self.browse_btn.clicked.connect(self._on_browse_clicked)
        self.file_path_edit.textChanged.connect(self._on_path_changed)
        self.timestamp_checkbox.stateChanged.connect(self._on_timestamp_changed)
        self.export_btn.clicked.connect(self._on_export_clicked)
        self.cancel_btn.clicked.connect(self.reject)
    
    def _set_default_path(self) -> None:
        """
        デフォルトの保存先パスを設定する。
        
        Note:
            設定から保存先ディレクトリを取得し、タイムスタンプ付きファイル名を生成
        """
        # 設定から保存先ディレクトリを取得
        export_dir = self.config_manager.get("paths.export_path", "")
        
        if not export_dir or not os.path.exists(export_dir):
            # デフォルトはホームディレクトリ
            export_dir = os.path.expanduser("~")
        
        # ファイル名を生成
        filename = self._generate_filename()
        
        # フルパスを設定
        full_path = os.path.join(export_dir, filename)
        self.file_path_edit.setText(full_path)
    
    def _generate_filename(self) -> str:
        """
        エクスポートファイル名を生成する。
        
        Returns:
            str: 生成されたファイル名
        
        Note:
            タイムスタンプオプションがONの場合、日時を含むファイル名を生成
        """
        base_name = "pole_facilities"
        
        if self.timestamp_checkbox.isChecked():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{base_name}_{timestamp}.csv"
        else:
            return f"{base_name}.csv"
    
    def _on_browse_clicked(self) -> None:
        """
        参照ボタンクリック時の処理。
        
        ファイル保存ダイアログを表示し、保存先を選択させる。
        """
        # 現在のパスからディレクトリを取得
        current_path = self.file_path_edit.text()
        if current_path:
            default_dir = os.path.dirname(current_path)
            default_name = os.path.basename(current_path)
        else:
            default_dir = self.config_manager.get("paths.export_path", "")
            if not default_dir or not os.path.exists(default_dir):
                default_dir = os.path.expanduser("~")
            default_name = self._generate_filename()
        
        # ファイル保存ダイアログ
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "CSVファイルを保存",
            os.path.join(default_dir, default_name),
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            # .csv拡張子を強制
            if not file_path.lower().endswith('.csv'):
                file_path += '.csv'
            
            self.file_path_edit.setText(file_path)
            
            # 選択したディレクトリを保存
            directory = os.path.dirname(file_path)
            self.config_manager.set("paths.export_path", directory)
            
            logger.debug(f"Export path selected: {file_path}")
    
    def _on_path_changed(self, path: str) -> None:
        """
        パス入力欄の内容変更時の処理。
        
        Args:
            path: 入力されたパス
        
        Note:
            ディレクトリの存在と書き込み権限をチェックし、エクスポートボタンの有効/無効を切り替える
        """
        # パスの妥当性チェック
        is_valid = self._validate_path(path)
        self.export_btn.setEnabled(is_valid)
        
        if not path:
            self.info_label.setText("")
        elif not is_valid:
            self.info_label.setText("⚠ 有効な保存先を選択してください")
            self.info_label.setStyleSheet("color: orange;")
        else:
            # ファイルが既に存在する場合は警告
            if os.path.exists(path):
                self.info_label.setText("⚠ ファイルは上書きされます")
                self.info_label.setStyleSheet("color: orange;")
            else:
                self.info_label.setText("✓ ファイルを保存する準備ができました")
                self.info_label.setStyleSheet("color: green;")
    
    def _validate_path(self, path: str) -> bool:
        """
        パスの妥当性を検証する。
        
        Args:
            path: 検証するパス
        
        Returns:
            bool: 有効な場合True
        """
        if not path:
            return False
        
        # ディレクトリの存在チェック
        directory = os.path.dirname(path)
        if not directory or not os.path.exists(directory):
            return False
        
        # .csv拡張子チェック
        if not path.lower().endswith('.csv'):
            return False
        
        return True
    
    def _on_timestamp_changed(self, state: int) -> None:
        """
        タイムスタンプチェックボックス変更時の処理。
        
        Args:
            state: チェックボックスの状態
        
        Note:
            ファイル名を再生成して更新
        """
        current_path = self.file_path_edit.text()
        if current_path:
            directory = os.path.dirname(current_path)
            filename = self._generate_filename()
            new_path = os.path.join(directory, filename)
            self.file_path_edit.setText(new_path)
    
    def _on_export_clicked(self) -> None:
        """
        エクスポートボタンクリック時の処理。
        
        現在のレイヤデータをCSVファイルにエクスポートする。
        """
        output_path = self.file_path_edit.text()
        
        if not output_path:
            return
        
        # ファイルが既に存在する場合は確認
        if os.path.exists(output_path):
            reply = QMessageBox.question(
                self,
                "確認",
                f"ファイルは既に存在します。上書きしますか?\n\n{output_path}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
        
        # UI更新
        self.export_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不定状態
        self.info_label.setText("エクスポート中...")
        self.info_label.setStyleSheet("color: blue;")
        
        try:
            # データマネージャでエクスポート実行
            success = self.data_manager.export_to_csv(output_path)
            
            if success:
                # 成功メッセージ
                layer = self.data_manager.get_current_layer()
                feature_count = layer.featureCount() if layer else 0
                
                QMessageBox.information(
                    self,
                    "エクスポート完了",
                    f"CSVファイルを正常にエクスポートしました。\n"
                    f"出力件数: {feature_count}件\n"
                    f"保存先: {output_path}"
                )
                
                # シグナル発行
                self.export_completed.emit(output_path)
                
                # ダイアログを閉じる
                self.accept()
                
                logger.info(f"CSV export successful: {output_path}, {feature_count} features")
            else:
                # 失敗メッセージ
                QMessageBox.warning(
                    self,
                    "エクスポート失敗",
                    "CSVファイルのエクスポートに失敗しました。\n"
                    "保存先の書き込み権限を確認してください。"
                )
                
                logger.warning(f"CSV export failed: {output_path}")
        
        except Exception as e:
            # エラーメッセージ
            QMessageBox.critical(
                self,
                "エラー",
                f"エクスポート中にエラーが発生しました:\n{str(e)}"
            )
            
            logger.exception(f"Exception during CSV export: {e}")
        
        finally:
            # UI復元
            self.export_btn.setEnabled(True)
            self.browse_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            self._on_path_changed(output_path)  # ステータス更新
    
    def get_output_path(self) -> str:
        """
        選択された保存先パスを取得する。
        
        Returns:
            str: 保存先パス
        """
        return self.file_path_edit.text()
    
    def set_path(self, path: str) -> None:
        """
        保存先パスを設定する。
        
        Args:
            path: 設定する保存先パス
        """
        self.file_path_edit.setText(path)
