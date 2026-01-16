"""
Import Dialog Module

CSVファイルのインポートを行うダイアログ。
ファイル選択、バリデーション、インポート実行を提供する。
"""

import os
import logging
from typing import Optional

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt, pyqtSignal

# ロガー設定
logger = logging.getLogger(__name__)


class ImportDialog(QDialog):
    """
    CSVインポートダイアログ。
    
    CSVファイルを選択し、インポート処理を実行する。
    
    Signals:
        import_completed: インポート完了時に発行（レイヤIDを渡す）
    """
    
    # シグナル定義
    import_completed = pyqtSignal(str)  # layer_id
    
    def __init__(self, parent, data_manager, config_manager):
        """
        ImportDialogを初期化する。
        
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
        
        logger.debug("ImportDialog initialized")
    
    def _setup_ui(self) -> None:
        """
        UIを構築する。
        
        レイアウト:
            - ファイル選択行（パス入力 + 参照ボタン）
            - プログレスバー
            - ボタン行（インポート、キャンセル）
        """
        self.setWindowTitle("CSVインポート")
        self.setMinimumWidth(500)
        
        # メインレイアウト
        layout = QVBoxLayout()
        
        # ファイル選択セクション
        file_layout = QHBoxLayout()
        
        file_label = QLabel("CSVファイル:")
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("CSVファイルを選択してください")
        self.browse_btn = QPushButton("参照...")
        self.browse_btn.setProperty("data-testid", "browse-csv-btn")
        
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_path_edit, 1)
        file_layout.addWidget(self.browse_btn)
        
        layout.addLayout(file_layout)
        
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
        
        self.import_btn = QPushButton("インポート")
        self.import_btn.setProperty("data-testid", "import-csv-btn")
        self.import_btn.setEnabled(False)
        self.import_btn.setDefault(True)
        
        self.cancel_btn = QPushButton("キャンセル")
        self.cancel_btn.setProperty("data-testid", "cancel-import-btn")
        
        button_layout.addWidget(self.import_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _connect_signals(self) -> None:
        """
        シグナルを接続する。
        """
        self.browse_btn.clicked.connect(self._on_browse_clicked)
        self.file_path_edit.textChanged.connect(self._on_path_changed)
        self.import_btn.clicked.connect(self._on_import_clicked)
        self.cancel_btn.clicked.connect(self.reject)
    
    def _on_browse_clicked(self) -> None:
        """
        参照ボタンクリック時の処理。
        
        ファイル選択ダイアログを表示し、CSVファイルを選択させる。
        """
        # 前回選択したディレクトリを取得
        last_dir = self.config_manager.get("ui.last_import_directory", "")
        
        if not last_dir or not os.path.exists(last_dir):
            last_dir = os.path.expanduser("~")
        
        # ファイル選択ダイアログ
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "CSVファイルを選択",
            last_dir,
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
            
            # 選択したディレクトリを保存
            directory = os.path.dirname(file_path)
            self.config_manager.set("ui.last_import_directory", directory)
            
            logger.debug(f"CSV file selected: {file_path}")
    
    def _on_path_changed(self, path: str) -> None:
        """
        パス入力欄の内容変更時の処理。
        
        Args:
            path: 入力されたパス
        
        Note:
            ファイルの存在とCSV形式をチェックし、インポートボタンの有効/無効を切り替える
        """
        # パスの妥当性チェック
        is_valid = self._validate_path(path)
        self.import_btn.setEnabled(is_valid)
        
        if not path:
            self.info_label.setText("")
        elif not is_valid:
            self.info_label.setText("⚠ 有効なCSVファイルを選択してください")
            self.info_label.setStyleSheet("color: orange;")
        else:
            self.info_label.setText("✓ ファイルを読み込む準備ができました")
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
        
        if not os.path.exists(path):
            return False
        
        if not path.lower().endswith('.csv'):
            return False
        
        return True
    
    def _on_import_clicked(self) -> None:
        """
        インポートボタンクリック時の処理。
        
        CSVファイルをインポートし、結果をダイアログで表示する。
        """
        csv_path = self.file_path_edit.text()
        
        if not csv_path:
            return
        
        # UI更新
        self.import_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不定状態
        self.info_label.setText("インポート中...")
        self.info_label.setStyleSheet("color: blue;")
        
        try:
            # データマネージャでインポート実行
            success = self.data_manager.import_csv(csv_path)
            
            if success:
                # 成功メッセージ
                layer = self.data_manager.get_current_layer()
                feature_count = layer.featureCount() if layer else 0
                
                QMessageBox.information(
                    self,
                    "インポート完了",
                    f"CSVファイルを正常にインポートしました。\n"
                    f"読み込み件数: {feature_count}件"
                )
                
                # シグナル発行
                if layer:
                    self.import_completed.emit(layer.id())
                
                # ダイアログを閉じる
                self.accept()
                
                logger.info(f"CSV import successful: {csv_path}, {feature_count} features")
            else:
                # 失敗メッセージ
                QMessageBox.warning(
                    self,
                    "インポート失敗",
                    "CSVファイルのインポートに失敗しました。\n"
                    "ファイル形式を確認してください。"
                )
                
                logger.warning(f"CSV import failed: {csv_path}")
        
        except Exception as e:
            # エラーメッセージ
            QMessageBox.critical(
                self,
                "エラー",
                f"インポート中にエラーが発生しました:\n{str(e)}"
            )
            
            logger.exception(f"Exception during CSV import: {e}")
        
        finally:
            # UI復元
            self.import_btn.setEnabled(True)
            self.browse_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            self._on_path_changed(csv_path)  # ステータス更新
    
    def get_selected_path(self) -> str:
        """
        選択されたファイルパスを取得する。
        
        Returns:
            str: 選択されたファイルパス
        """
        return self.file_path_edit.text()
    
    def set_path(self, path: str) -> None:
        """
        ファイルパスを設定する。
        
        Args:
            path: 設定するファイルパス
        """
        self.file_path_edit.setText(path)
