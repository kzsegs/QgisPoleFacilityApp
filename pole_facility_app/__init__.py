"""
電柱設備管理アプリケーション

QGISプラグインエントリーポイント。
QGIS起動時にこのファイルが読み込まれ、classFactory()関数が呼ばれる。

Author: kz segs
Version: 1.0.0
QGIS Minimum Version: 3.40
"""


def classFactory(iface):
    """
    QGISプラグインのファクトリ関数。
    
    QGISはプラグイン読み込み時にこの関数を呼び出し、
    プラグインのメインクラスインスタンスを取得する。
    
    Args:
        iface (QgisInterface): QGISアプリケーションインターフェース
        
    Returns:
        PoleFacilityMain: プラグインのメインクラスインスタンス
    """
    from .main.plugin import PoleFacilityMain
    return PoleFacilityMain(iface)
