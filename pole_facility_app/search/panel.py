"""
Search Panel Widget Module

検索条件入力パネル。
設備番号、検査日範囲、検査状態の入力UIを提供する。
"""

import logging
from typing import List, Optional

from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QFormLayout, QLineEdit,
    QComboBox, QDateEdit, QPushButton, QLabel, QHBoxLayout,
    QCheckBox, QGroupBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QDate

from .filter import SearchFilter

# ロガー設定
logger = logging.getLogger(__name__)


class SearchPanelWidget(QDockWidget):
    """
    検索パネルウィジェット。
    
    検索条件の入力と、検索・クリア操作を提供する。
    
    Signals:
        search_requested: 検索ボタンクリック時 (SearchFilter)
        clear_requested: クリアボタンクリック時
    """
    
    # シグナル定義
    search_requested = pyqtSignal(SearchFilter)
    clear_requested = pyqtSignal()
    
    def __init__(self, parent=None, config_manager=None):
        """
        SearchPanelWidgetを初期化する。
        
        Args:
            parent: 親ウィジェット
            config_manager: 設定マネージャ
        """
        super().__init__("検索・フィルタ", parent)
        
        self.config_manager = config_manager
        
        # 入力ウィジェット
        self.facility_number_edit: QLineEdit = None
        self.date_from_checkbox: QCheckBox = None
        self.date_from_picker: QDateEdit = None
        self.date_to_checkbox: QCheckBox = None
        self.date_to_picker: QDateEdit = None
        self.status_1_combo: QComboBox = None
        self.status_2_combo: QComboBox = None
        self.status_3_combo: QComboBox = None
        
        # ボタン
        self.search_btn: QPushButton = None
        self.clear_btn: QPushButton = None
        
        # 結果ラベル
        self.result_label: QLabel = None
        
        self._setup_ui()
        self._connect_signals()
        
        # ドックウィジェット設定
        self.setAllowedAreas(Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        
        logger.debug("SearchPanelWidget initialized")
    
    def _setup_ui(self) -> None:
        """
        UIを構築する。
        
        レイアウト:
            - 検索条件入力フォーム
            - ボタン行
            - 結果表示ラベル
        """
        # メインウィジェット
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 検索条件グループ
        search_group = QGroupBox("検索条件")
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # 設備番号
        self.facility_number_edit = QLineEdit()
        self.facility_number_edit.setPlaceholderText("設備番号を入力（部分一致）")
        self.facility_number_edit.setProperty("data-testid", "search-facility-number")
        form_layout.addRow("設備番号:", self.facility_number_edit)
        
        # 検査日From
        date_from_layout = QHBoxLayout()
        self.date_from_checkbox = QCheckBox()
        self.date_from_checkbox.setChecked(False)
        self.date_from_picker = QDateEdit()
        self.date_from_picker.setCalendarPopup(True)
        self.date_from_picker.setDisplayFormat("yyyy/MM/dd")
        self.date_from_picker.setDate(QDate.currentDate())
        self.date_from_picker.setEnabled(False)
        self.date_from_picker.setProperty("data-testid", "search-date-from")
        date_from_layout.addWidget(self.date_from_checkbox)
        date_from_layout.addWidget(self.date_from_picker, 1)
        form_layout.addRow("検査日From:", date_from_layout)
        
        # 検査日To
        date_to_layout = QHBoxLayout()
        self.date_to_checkbox = QCheckBox()
        self.date_to_checkbox.setChecked(False)
        self.date_to_picker = QDateEdit()
        self.date_to_picker.setCalendarPopup(True)
        self.date_to_picker.setDisplayFormat("yyyy/MM/dd")
        self.date_to_picker.setDate(QDate.currentDate())
        self.date_to_picker.setEnabled(False)
        self.date_to_picker.setProperty("data-testid", "search-date-to")
        date_to_layout.addWidget(self.date_to_checkbox)
        date_to_layout.addWidget(self.date_to_picker, 1)
        form_layout.addRow("検査日To:", date_to_layout)
        
        # 検査状態1
        self.status_1_combo = QComboBox()
        self.status_1_combo.setProperty("data-testid", "search-status-1")
        self._setup_status_combo(self.status_1_combo, 1)
        form_layout.addRow("検査状態1:", self.status_1_combo)
        
        # 検査状態2
        self.status_2_combo = QComboBox()
        self.status_2_combo.setProperty("data-testid", "search-status-2")
        self._setup_status_combo(self.status_2_combo, 2)
        form_layout.addRow("検査状態2:", self.status_2_combo)
        
        # 検査状態3
        self.status_3_combo = QComboBox()
        self.status_3_combo.setProperty("data-testid", "search-status-3")
        self._setup_status_combo(self.status_3_combo, 3)
        form_layout.addRow("検査状態3:", self.status_3_combo)
        
        search_group.setLayout(form_layout)
        main_layout.addWidget(search_group)
        
        # ボタン行
        button_layout = QHBoxLayout()
        
        self.search_btn = QPushButton("検索")
        self.search_btn.setProperty("data-testid", "search-execute-btn")
        self.search_btn.setDefault(True)
        
        self.clear_btn = QPushButton("クリア")
        self.clear_btn.setProperty("data-testid", "search-clear-btn")
        
        button_layout.addWidget(self.search_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
        
        # 結果ラベル
        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("color: #666; font-size: 11px;")
        main_layout.addWidget(self.result_label)
        
        main_layout.addStretch()
        
        main_widget.setLayout(main_layout)
        self.setWidget(main_widget)
    
    def _setup_status_combo(self, combo: QComboBox, status_num: int) -> None:
        """
        検査状態コンボボックスを設定する。
        
        Args:
            combo: 設定するコンボボックス
            status_num: 検査状態番号 (1-3)
        """
        # 空の選択肢を追加
        combo.addItem("")
        
        # 設定マネージャから選択肢を取得
        if self.config_manager:
            try:
                options = self.config_manager.get_inspection_status_list(status_num)
                combo.addItems(options)
            except Exception as e:
                logger.warning(f"Failed to get status options: {e}")
                # デフォルトの選択肢を追加
                self._add_default_status_options(combo, status_num)
        else:
            # デフォルトの選択肢を追加
            self._add_default_status_options(combo, status_num)
    
    def _add_default_status_options(self, combo: QComboBox, status_num: int) -> None:
        """
        デフォルトの検査状態選択肢を追加する。
        
        Args:
            combo: 追加先コンボボックス
            status_num: 検査状態番号 (1-3)
        """
        default_options = [
            f"状態{status_num}A",
            f"状態{status_num}B",
            f"状態{status_num}C",
            f"状態{status_num}D",
            f"その他{status_num}"
        ]
        combo.addItems(default_options)
    
    def _connect_signals(self) -> None:
        """
        シグナルを接続する。
        """
        # ボタン
        self.search_btn.clicked.connect(self._on_search_clicked)
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        
        # 日付チェックボックス
        self.date_from_checkbox.stateChanged.connect(self._on_date_from_checkbox_changed)
        self.date_to_checkbox.stateChanged.connect(self._on_date_to_checkbox_changed)
        
        # Enterキーで検索
        self.facility_number_edit.returnPressed.connect(self._on_search_clicked)
    
    def get_filter(self) -> SearchFilter:
        """
        現在の入力内容からSearchFilterを生成する。
        
        Returns:
            SearchFilter: 検索フィルタ
        """
        # 日付の取得（チェックボックスがOFFの場合はNone）
        date_from = None
        if self.date_from_checkbox.isChecked():
            date_from = self.date_from_picker.date()
        
        date_to = None
        if self.date_to_checkbox.isChecked():
            date_to = self.date_to_picker.date()
        
        filter_obj = SearchFilter(
            facility_number=self.facility_number_edit.text().strip(),
            date_from=date_from,
            date_to=date_to,
            inspection_status_1=self.status_1_combo.currentText(),
            inspection_status_2=self.status_2_combo.currentText(),
            inspection_status_3=self.status_3_combo.currentText(),
        )
        
        return filter_obj
    
    def set_filter(self, filter_obj: SearchFilter) -> None:
        """
        SearchFilterの内容を入力フィールドに設定する。
        
        Args:
            filter_obj: 設定するフィルタ
        """
        # 設備番号
        self.facility_number_edit.setText(filter_obj.facility_number)
        
        # 検査日From
        if filter_obj.date_from and filter_obj.date_from.isValid():
            self.date_from_checkbox.setChecked(True)
            self.date_from_picker.setDate(filter_obj.date_from)
        else:
            self.date_from_checkbox.setChecked(False)
        
        # 検査日To
        if filter_obj.date_to and filter_obj.date_to.isValid():
            self.date_to_checkbox.setChecked(True)
            self.date_to_picker.setDate(filter_obj.date_to)
        else:
            self.date_to_checkbox.setChecked(False)
        
        # 検査状態1
        index = self.status_1_combo.findText(filter_obj.inspection_status_1)
        self.status_1_combo.setCurrentIndex(index if index >= 0 else 0)
        
        # 検査状態2
        index = self.status_2_combo.findText(filter_obj.inspection_status_2)
        self.status_2_combo.setCurrentIndex(index if index >= 0 else 0)
        
        # 検査状態3
        index = self.status_3_combo.findText(filter_obj.inspection_status_3)
        self.status_3_combo.setCurrentIndex(index if index >= 0 else 0)
    
    def clear(self) -> None:
        """
        全ての入力フィールドをクリアする。
        """
        self.facility_number_edit.clear()
        
        self.date_from_checkbox.setChecked(False)
        self.date_from_picker.setDate(QDate.currentDate())
        
        self.date_to_checkbox.setChecked(False)
        self.date_to_picker.setDate(QDate.currentDate())
        
        self.status_1_combo.setCurrentIndex(0)
        self.status_2_combo.setCurrentIndex(0)
        self.status_3_combo.setCurrentIndex(0)
        
        self.result_label.setText("")
        
        logger.debug("Search panel cleared")
    
    def set_result_count(self, count: int) -> None:
        """
        検索結果件数を表示する。
        
        Args:
            count: 検索結果件数
        """
        if count == 0:
            self.result_label.setText("⚠ 検索条件に一致する地物が見つかりませんでした")
            self.result_label.setStyleSheet("color: orange; font-size: 11px;")
        else:
            self.result_label.setText(f"✓ {count}件の地物が見つかりました")
            self.result_label.setStyleSheet("color: green; font-size: 11px;")
    
    def _on_search_clicked(self) -> None:
        """
        検索ボタンクリック時の処理。
        
        Note:
            入力内容からSearchFilterを生成し、search_requestedシグナルを発行
        """
        filter_obj = self.get_filter()
        
        if filter_obj.is_empty():
            self.result_label.setText("⚠ 検索条件を入力してください")
            self.result_label.setStyleSheet("color: orange; font-size: 11px;")
            return
        
        # シグナル発行
        self.search_requested.emit(filter_obj)
        
        logger.info(f"Search requested: {filter_obj}")
    
    def _on_clear_clicked(self) -> None:
        """
        クリアボタンクリック時の処理。
        
        Note:
            全入力フィールドをクリアし、clear_requestedシグナルを発行
        """
        self.clear()
        
        # シグナル発行
        self.clear_requested.emit()
        
        logger.info("Search cleared")
    
    def _on_date_from_checkbox_changed(self, state: int) -> None:
        """
        検査日Fromチェックボックス変更時の処理。
        
        Args:
            state: チェックボックスの状態
        """
        is_checked = (state == Qt.Checked)
        self.date_from_picker.setEnabled(is_checked)
    
    def _on_date_to_checkbox_changed(self, state: int) -> None:
        """
        検査日Toチェックボックス変更時の処理。
        
        Args:
            state: チェックボックスの状態
        """
        is_checked = (state == Qt.Checked)
        self.date_to_picker.setEnabled(is_checked)
