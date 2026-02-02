"""
地物スタイル設定タブ - 作業状況別のマーカースタイル設定

UI構成:
    ■ ステータス別スタイル設定
      - 未確認: 色・サイズ
      - 確認中: 色・サイズ
      - 完了: 色・サイズ
    ■ カラム名設定
    ■ デフォルトステータス設定

Note:
    - marker_shapeはPhase 3-Bスコープ外（将来フェーズで対応）
    - 当面は丸（circle）固定

v1.9.1改訂:
    - QSpinBox.valueChanged → editingFinished に変更
    - スピンボックス編集完了時のみ設定を更新
    - パフォーマンス向上
"""

from typing import Dict, Any, List
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QLineEdit, QPushButton, QSpinBox,
    QLabel, QColorDialog, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from qgis.core import QgsMessageLog, Qgis


class StyleSettingsTab(QWidget):
    """
    地物スタイル設定タブ
    
    Attributes:
        config: 設定辞書への参照
        column_name_edit: 作業状況カラム名入力
        default_status_combo: デフォルトステータス選択
        status_table: ステータス別スタイル設定テーブル
        status_data: ステータスデータ（内部管理用）
    """
    
    def __init__(self, config: dict, parent=None):
        """
        コンストラクタ
        
        Args:
            config: 現在の設定辞書
            parent: 親ウィジェット
        """
        super().__init__(parent)
        
        self.config = config
        self.status_data: List[Dict[str, Any]] = []
        
        self._create_ui()
        self._load_values()
    
    def _create_ui(self) -> None:
        """UI構築"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # カラム名設定
        column_group = self._create_column_settings_section()
        layout.addWidget(column_group)
        
        # ステータス別スタイル設定
        style_group = self._create_style_settings_section()
        layout.addWidget(style_group)
        
        # 説明
        note_label = QLabel(
            "※ マーカー形状は現在「丸」固定です。\n"
            "※ 将来のバージョンで形状のカスタマイズに対応予定です。"
        )
        note_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(note_label)
        
        layout.addStretch()
    
    def _create_column_settings_section(self) -> QGroupBox:
        """
        カラム名設定セクション作成
        
        Returns:
            QGroupBox
        """
        group = QGroupBox("作業状況カラム設定")
        layout = QFormLayout(group)
        layout.setSpacing(10)
        
        # カラム名
        self.column_name_edit = QLineEdit()
        self.column_name_edit.setPlaceholderText("作業状況")
        layout.addRow("カラム名:", self.column_name_edit)
        
        # デフォルトステータス
        self.default_status_combo = QComboBox()
        layout.addRow("デフォルトステータス:", self.default_status_combo)
        
        return group
    
    def _create_style_settings_section(self) -> QGroupBox:
        """
        ステータス別スタイル設定セクション作成
        
        Returns:
            QGroupBox
        """
        group = QGroupBox("ステータス別スタイル設定")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        
        # テーブルウィジェット
        self.status_table = QTableWidget()
        self.status_table.setColumnCount(3)
        self.status_table.setHorizontalHeaderLabels(["ステータス名", "色", "サイズ(mm)"])
        
        # 列幅設定
        header = self.status_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.status_table.setColumnWidth(1, 100)
        self.status_table.setColumnWidth(2, 100)
        
        # 行の高さ
        self.status_table.verticalHeader().setDefaultSectionSize(40)
        
        layout.addWidget(self.status_table)
        
        # ボタン群
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("ステータス追加")
        add_btn.clicked.connect(self._on_add_status_clicked)
        btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("選択行を削除")
        remove_btn.clicked.connect(self._on_remove_status_clicked)
        btn_layout.addWidget(remove_btn)
        
        btn_layout.addStretch()
        
        reset_btn = QPushButton("デフォルトに戻す")
        reset_btn.clicked.connect(self._on_reset_clicked)
        btn_layout.addWidget(reset_btn)
        
        layout.addLayout(btn_layout)
        
        return group
    
    def _load_values(self) -> None:
        """現在の設定値をUIに反映"""
        progress_config = self.config.get('progress_status', {})
        
        # カラム名
        self.column_name_edit.setText(
            progress_config.get('column_name', '作業状況')
        )
        
        # ステータスリスト
        self.status_data = progress_config.get('statuses', self._get_default_statuses())
        
        # デフォルトステータス
        default_status = progress_config.get('default_status', '未確認')
        
        # テーブルに反映
        self._populate_status_table()
        
        # デフォルトステータスコンボボックス更新
        self._update_default_status_combo()
        
        # デフォルトステータス選択
        index = self.default_status_combo.findText(default_status)
        if index >= 0:
            self.default_status_combo.setCurrentIndex(index)
    
    def _get_default_statuses(self) -> List[Dict[str, Any]]:
        """デフォルトステータス定義を取得"""
        return [
            {"name": "未確認", "color": "#808080", "marker_size": 5},
            {"name": "確認中", "color": "#FFD700", "marker_size": 5},
            {"name": "完了", "color": "#32CD32", "marker_size": 5}
        ]
    
    def _populate_status_table(self) -> None:
        """ステータスデータをテーブルに反映（v1.9.1改訂）"""
        self.status_table.setRowCount(len(self.status_data))
        
        for row, status in enumerate(self.status_data):
            # ステータス名
            name_item = QTableWidgetItem(status.get("name", ""))
            self.status_table.setItem(row, 0, name_item)
            
            # 色ボタン
            color_btn = QPushButton()
            color = status.get("color", "#808080")
            color_btn.setStyleSheet(f"background-color: {color};")
            color_btn.setText(color)
            color_btn.clicked.connect(
                lambda checked, r=row: self._on_color_button_clicked(r)
            )
            self.status_table.setCellWidget(row, 1, color_btn)
            
            # サイズスピンボックス（v1.9.1修正: editingFinished使用）
            size_spin = QSpinBox()
            size_spin.setRange(1, 20)
            size_spin.setValue(status.get("marker_size", 5))
            size_spin.setSuffix(" mm")
            size_spin.editingFinished.connect(
                lambda r=row: self._on_size_editing_finished(r)
            )
            self.status_table.setCellWidget(row, 2, size_spin)
    
    def _update_default_status_combo(self) -> None:
        """デフォルトステータスコンボボックスを更新"""
        current_text = self.default_status_combo.currentText()
        
        self.default_status_combo.clear()
        for status in self.status_data:
            self.default_status_combo.addItem(status.get("name", ""))
        
        # 以前の選択を復元
        index = self.default_status_combo.findText(current_text)
        if index >= 0:
            self.default_status_combo.setCurrentIndex(index)
        elif self.default_status_combo.count() > 0:
            self.default_status_combo.setCurrentIndex(0)
    
    def _on_add_status_clicked(self) -> None:
        """ステータス追加ボタンクリック時"""
        from PyQt5.QtWidgets import QInputDialog
        
        # ステータス名入力
        name, ok = QInputDialog.getText(
            self,
            "ステータス追加",
            "新しいステータス名を入力:"
        )
        
        if not ok or not name:
            return
        
        # 重複チェック
        for status in self.status_data:
            if status.get("name") == name:
                QMessageBox.warning(
                    self,
                    "入力エラー",
                    f"ステータス名「{name}」は既に存在します。"
                )
                return
        
        # 新規ステータスを追加
        new_status = {
            "name": name,
            "color": "#808080",
            "marker_size": 5
        }
        self.status_data.append(new_status)
        
        # テーブル更新
        self._populate_status_table()
        self._update_default_status_combo()
    
    def _on_remove_status_clicked(self) -> None:
        """選択行を削除"""
        current_row = self.status_table.currentRow()
        
        if current_row < 0:
            QMessageBox.warning(
                self,
                "選択エラー",
                "削除する行を選択してください。"
            )
            return
        
        # 最低1ステータス必要
        if len(self.status_data) <= 1:
            QMessageBox.warning(
                self,
                "削除エラー",
                "最低1つのステータスが必要です。"
            )
            return
        
        # 削除確認
        status_name = self.status_data[current_row].get("name", "")
        reply = QMessageBox.question(
            self,
            "確認",
            f"ステータス「{status_name}」を削除しますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            del self.status_data[current_row]
            self._populate_status_table()
            self._update_default_status_combo()
    
    def _on_color_button_clicked(self, row: int) -> None:
        """色ボタンクリック時"""
        if row >= len(self.status_data):
            return
        
        current_color = QColor(self.status_data[row].get("color", "#808080"))
        
        color = QColorDialog.getColor(
            current_color,
            self,
            "色を選択"
        )
        
        if color.isValid():
            color_hex = color.name()
            self.status_data[row]["color"] = color_hex
            
            # ボタンの色を更新
            btn = self.status_table.cellWidget(row, 1)
            if btn:
                btn.setStyleSheet(f"background-color: {color_hex};")
                btn.setText(color_hex)
    
    def _on_size_editing_finished(self, row: int) -> None:
        """
        サイズスピンボックス編集完了時（v1.9.1追加）
        
        Args:
            row: テーブル行番号
        
        Note:
            editingFinishedシグナルから呼ばれるため、
            スピンボックスから値を取得する必要がある
        """
        if row >= len(self.status_data):
            return
        
        # スピンボックスから現在値を取得
        size_spin = self.status_table.cellWidget(row, 2)
        if size_spin and isinstance(size_spin, QSpinBox):
            value = size_spin.value()
            self.status_data[row]["marker_size"] = value
            
            QgsMessageLog.logMessage(
                f"StyleSettingsTab - サイズ更新: row={row}, size={value}",
                "PoleFacility", Qgis.Info
            )
    
    def _on_reset_clicked(self) -> None:
        """デフォルトに戻すボタンクリック時"""
        reply = QMessageBox.question(
            self,
            "確認",
            "スタイル設定をデフォルトに戻しますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.status_data = self._get_default_statuses()
            self._populate_status_table()
            self._update_default_status_combo()
    
    def get_values(self) -> dict:
        """
        入力値を取得
        
        Returns:
            設定辞書
        """
        # テーブルからステータス名を取得（編集可能なため）
        for row in range(len(self.status_data)):
            name_item = self.status_table.item(row, 0)
            if name_item:
                self.status_data[row]["name"] = name_item.text()
        
        return {
            "progress_status": {
                "column_name": self.column_name_edit.text(),
                "statuses": self.status_data,
                "default_status": self.default_status_combo.currentText()
            }
        }
    
    def validate(self) -> bool:
        """
        入力値をバリデーション
        
        Returns:
            True: バリデーション成功
            False: バリデーション失敗
        """
        # カラム名必須チェック
        if not self.column_name_edit.text():
            QMessageBox.warning(
                self,
                "入力エラー",
                "作業状況カラム名を入力してください。"
            )
            return False
        
        # ステータス名必須チェック
        for row, status in enumerate(self.status_data):
            name_item = self.status_table.item(row, 0)
            if not name_item or not name_item.text():
                QMessageBox.warning(
                    self,
                    "入力エラー",
                    f"{row + 1}行目: ステータス名を入力してください。"
                )
                return False
        
        # 最低1ステータス必要
        if len(self.status_data) == 0:
            QMessageBox.warning(
                self,
                "入力エラー",
                "最低1つのステータスを設定してください。"
            )
            return False
        
        # デフォルトステータス選択チェック
        if not self.default_status_combo.currentText():
            QMessageBox.warning(
                self,
                "入力エラー",
                "デフォルトステータスを選択してください。"
            )
            return False
        
        return True
