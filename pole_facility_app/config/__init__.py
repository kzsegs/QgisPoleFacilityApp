"""
設定管理モジュール

このパッケージは、アプリケーション設定の管理を行う。

Classes:
    ConfigManager: 設定管理（Singleton）
    SettingsDialogWidget: 設定画面UI

Constants:
    DEFAULT_CONFIG: デフォルト設定
"""

from .manager import ConfigManager

__all__ = [
    'ConfigManager',
]
