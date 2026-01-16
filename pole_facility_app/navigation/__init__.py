"""
Navigation Module

画面遷移制御とダイアログ管理を担当するモジュール。
地物選択時の属性フォーム表示、各種ダイアログの管理を行う。
"""

from .controller import NavigationController
from .form_strategy import IFormStrategy, QgsFormStrategy

__all__ = [
    'NavigationController',
    'IFormStrategy',
    'QgsFormStrategy',
]
