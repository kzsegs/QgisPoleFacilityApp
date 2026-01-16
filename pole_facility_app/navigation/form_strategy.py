"""
Form Strategy Module

属性フォーム表示方式を抽象化するStrategyパターン実装。
Phase 1ではQGIS標準フォーム、Phase 2でQt独自フォームへの切り替えを想定。
"""

from abc import ABC, abstractmethod
from typing import Optional

from qgis.core import QgsVectorLayer, QgsFeature
from qgis.gui import QgsAttributeDialog
from PyQt5.QtWidgets import QWidget


class IFormStrategy(ABC):
    """
    属性フォーム表示戦略インターフェース。
    
    異なるフォーム表示方式を統一的に扱うための抽象基底クラス。
    """
    
    @abstractmethod
    def show_form(self, layer: QgsVectorLayer, feature: QgsFeature, 
                  parent: Optional[QWidget] = None) -> None:
        """
        属性フォームを表示する。
        
        Args:
            layer: 対象レイヤ
            feature: 表示する地物
            parent: 親ウィジェット（オプション）
        """
        pass
    
    @abstractmethod
    def close_form(self) -> None:
        """
        現在表示中のフォームを閉じる。
        """
        pass
    
    @abstractmethod
    def is_form_visible(self) -> bool:
        """
        フォームが表示中かどうかを返す。
        
        Returns:
            bool: 表示中の場合True
        """
        pass


class QgsFormStrategy(IFormStrategy):
    """
    QGIS標準属性フォームを使用する戦略実装（Phase 1）。
    
    QgsAttributeDialogを使用して、QGIS標準のフォームを表示する。
    """
    
    def __init__(self):
        """QgsFormStrategyを初期化する。"""
        self._current_dialog: Optional[QgsAttributeDialog] = None
    
    def show_form(self, layer: QgsVectorLayer, feature: QgsFeature,
                  parent: Optional[QWidget] = None) -> None:
        """
        QGIS標準属性フォームを表示する。
        
        Args:
            layer: 対象レイヤ
            feature: 表示する地物
            parent: 親ウィジェット（オプション）
        
        Note:
            - 既存のダイアログがある場合は閉じてから新しいダイアログを表示
            - モーダルダイアログとして表示
        """
        # 既存のダイアログを閉じる
        self.close_form()
        
        # 新しいダイアログを作成
        # False = 属性削除ボタンを非表示
        self._current_dialog = QgsAttributeDialog(
            layer,
            feature,
            False,  # featureOwner
            parent,
            True,   # showDialogButtons
        )
        
        # ダイアログのタイトルを設定
        facility_number = feature.attribute("設備番号") or "不明"
        self._current_dialog.setWindowTitle(f"設備情報 - {facility_number}")
        
        # モーダルダイアログとして表示
        self._current_dialog.exec_()
        
        # ダイアログが閉じられたらクリア
        self._current_dialog = None
    
    def close_form(self) -> None:
        """
        現在表示中のフォームを閉じる。
        
        Note:
            表示中のダイアログがない場合は何もしない
        """
        if self._current_dialog is not None:
            self._current_dialog.close()
            self._current_dialog = None
    
    def is_form_visible(self) -> bool:
        """
        フォームが表示中かどうかを返す。
        
        Returns:
            bool: ダイアログが存在し、表示中の場合True
        """
        return (self._current_dialog is not None and 
                self._current_dialog.isVisible())


class QtFormStrategy(IFormStrategy):
    """
    Qt独自属性フォームを使用する戦略実装（Phase 2実装予定）。
    
    カスタムQtウィジェットを使用して、独自デザインのフォームを表示する。
    現在は未実装。
    """
    
    def __init__(self):
        """QtFormStrategyを初期化する。"""
        self._current_form: Optional[QWidget] = None
    
    def show_form(self, layer: QgsVectorLayer, feature: QgsFeature,
                  parent: Optional[QWidget] = None) -> None:
        """
        Qt独自フォームを表示する（未実装）。
        
        Args:
            layer: 対象レイヤ
            feature: 表示する地物
            parent: 親ウィジェット（オプション）
        
        Raises:
            NotImplementedError: Phase 2で実装予定
        """
        raise NotImplementedError("QtFormStrategy is planned for Phase 2")
    
    def close_form(self) -> None:
        """
        現在表示中のフォームを閉じる（未実装）。
        
        Raises:
            NotImplementedError: Phase 2で実装予定
        """
        raise NotImplementedError("QtFormStrategy is planned for Phase 2")
    
    def is_form_visible(self) -> bool:
        """
        フォームが表示中かどうかを返す（未実装）。
        
        Returns:
            bool: 常にFalse（未実装）
        """
        return False
