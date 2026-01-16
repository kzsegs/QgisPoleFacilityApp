"""
メインプラグインモジュール

アプリケーション全体の起動・終了制御を行うコアコンポーネント。

主要クラス:
    - PoleFacilityMain: メインプラグインクラス
    - EventBus: イベント通信管理（Observerパターン）
    - UIState: UI状態の保存・復元
"""

from .plugin import PoleFacilityMain
from .event_bus import EventBus
from .ui_state import UIState

__all__ = [
    'PoleFacilityMain',
    'EventBus',
    'UIState',
]
