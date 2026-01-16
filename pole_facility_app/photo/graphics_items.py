# -*- coding: utf-8 -*-
"""
Graphics Items - カスタム描画アイテム

矢印など、QGraphicsItemを継承したカスタム描画オブジェクト
"""

import math
from qgis.PyQt.QtWidgets import QGraphicsLineItem, QGraphicsPolygonItem
from qgis.PyQt.QtCore import QPointF, QRectF
from qgis.PyQt.QtGui import QPen, QBrush, QPolygonF, QColor
from qgis.PyQt.QtCore import Qt


class ArrowGraphicsItem(QGraphicsLineItem):
    """
    矢印描画アイテム
    
    直線 + 矢印の先端を描画
    """
    
    def __init__(self, start_point: QPointF, end_point: QPointF, 
                 color: QColor, pen_width: int):
        """
        初期化
        
        Args:
            start_point: 始点
            end_point: 終点
            color: 色
            pen_width: 線幅
        """
        super().__init__()
        
        # 直線部分を設定
        self.setLine(start_point.x(), start_point.y(), 
                     end_point.x(), end_point.y())
        
        # ペン設定
        pen = QPen(color, pen_width)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        self.setPen(pen)
        
        # 矢印の先端を計算
        self.arrow_head_polygon = self._calculate_arrow_head(
            start_point, end_point, pen_width, color
        )
        
        # 選択・移動可能に
        self.setFlag(QGraphicsLineItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsLineItem.ItemIsMovable, True)
    
    def _calculate_arrow_head(self, start: QPointF, end: QPointF, 
                              pen_width: int, color: QColor) -> QGraphicsPolygonItem:
        """
        矢印の先端（三角形）を計算
        
        Args:
            start: 始点
            end: 終点
            pen_width: 線幅
            color: 色
        
        Returns:
            QGraphicsPolygonItem: 矢印の先端
        """
        # 矢印の先端サイズ（線幅の4倍）
        arrow_size = pen_width * 4
        
        # 方向ベクトル
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = math.sqrt(dx**2 + dy**2)
        
        if length < 0.001:  # ゼロ除算回避
            return None
        
        # 角度計算
        angle = math.atan2(dy, dx)
        
        # 矢印の先端の3点を計算
        p1 = end
        p2 = QPointF(
            end.x() - arrow_size * math.cos(angle - math.pi / 6),
            end.y() - arrow_size * math.sin(angle - math.pi / 6)
        )
        p3 = QPointF(
            end.x() - arrow_size * math.cos(angle + math.pi / 6),
            end.y() - arrow_size * math.sin(angle + math.pi / 6)
        )
        
        # 三角形のポリゴン作成
        polygon = QPolygonF([p1, p2, p3])
        arrow_head = QGraphicsPolygonItem(polygon)
        arrow_head.setBrush(QBrush(color))
        arrow_head.setPen(QPen(Qt.NoPen))
        
        return arrow_head
    
    def paint(self, painter, option, widget=None):
        """
        描画
        
        Args:
            painter: QPainter
            option: QStyleOptionGraphicsItem
            widget: QWidget
        """
        # 直線部分を描画
        super().paint(painter, option, widget)
        
        # 矢印の先端を描画
        if self.arrow_head_polygon:
            painter.setBrush(self.pen().color())
            painter.setPen(Qt.NoPen)
            painter.drawPolygon(self.arrow_head_polygon.polygon())
    
    def boundingRect(self) -> QRectF:
        """
        バウンディングボックス
        
        Returns:
            QRectF: 矢印全体を含む矩形
        """
        # 直線のバウンディングボックス取得
        rect = super().boundingRect()
        
        # 矢印の先端を含めた範囲に拡張
        if self.arrow_head_polygon:
            arrow_rect = self.arrow_head_polygon.boundingRect()
            rect = rect.united(arrow_rect)
        
        return rect


class GraphicsItemFactory:
    """
    描画アイテムファクトリ
    
    各種描画アイテムを生成
    """
    
    @staticmethod
    def create_arrow(start: QPointF, end: QPointF, 
                     color: QColor, width: int) -> ArrowGraphicsItem:
        """
        矢印作成
        
        Args:
            start: 始点
            end: 終点
            color: 色
            width: 線幅
        
        Returns:
            ArrowGraphicsItem: 矢印アイテム
        """
        return ArrowGraphicsItem(start, end, color, width)
    
    @staticmethod
    def create_line(start: QPointF, end: QPointF, 
                    color: QColor, width: int) -> QGraphicsLineItem:
        """
        直線作成
        
        Args:
            start: 始点
            end: 終点
            color: 色
            width: 線幅
        
        Returns:
            QGraphicsLineItem: 直線アイテム
        """
        from qgis.PyQt.QtCore import QLineF
        
        line = QGraphicsLineItem(QLineF(start, end))
        
        pen = QPen(color, width)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        line.setPen(pen)
        
        line.setFlag(QGraphicsLineItem.ItemIsSelectable, True)
        line.setFlag(QGraphicsLineItem.ItemIsMovable, True)
        
        return line
    
    @staticmethod
    def create_rect(rect: QRectF, color: QColor, width: int):
        """
        矩形作成
        
        Args:
            rect: 矩形範囲
            color: 色
            width: 線幅
        
        Returns:
            QGraphicsRectItem: 矩形アイテム
        """
        from qgis.PyQt.QtWidgets import QGraphicsRectItem
        
        rect_item = QGraphicsRectItem(rect)
        
        pen = QPen(color, width)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        rect_item.setPen(pen)
        
        rect_item.setBrush(QBrush(Qt.transparent))
        
        rect_item.setFlag(QGraphicsRectItem.ItemIsSelectable, True)
        rect_item.setFlag(QGraphicsRectItem.ItemIsMovable, True)
        
        return rect_item
    
    @staticmethod
    def create_ellipse(rect: QRectF, color: QColor, width: int):
        """
        楕円作成
        
        Args:
            rect: 矩形範囲（楕円が内接）
            color: 色
            width: 線幅
        
        Returns:
            QGraphicsEllipseItem: 楕円アイテム
        """
        from qgis.PyQt.QtWidgets import QGraphicsEllipseItem
        
        ellipse = QGraphicsEllipseItem(rect)
        
        pen = QPen(color, width)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        ellipse.setPen(pen)
        
        ellipse.setBrush(QBrush(Qt.transparent))
        
        ellipse.setFlag(QGraphicsEllipseItem.ItemIsSelectable, True)
        ellipse.setFlag(QGraphicsEllipseItem.ItemIsMovable, True)
        
        return ellipse
    
    @staticmethod
    def create_text(pos: QPointF, text: str, color: QColor, size: int):
        """
        テキスト作成
        
        Args:
            pos: 位置
            text: テキスト内容
            color: 色
            size: フォントサイズ
        
        Returns:
            QGraphicsTextItem: テキストアイテム
        """
        from qgis.PyQt.QtWidgets import QGraphicsTextItem
        from qgis.PyQt.QtGui import QFont
        
        text_item = QGraphicsTextItem(text)
        text_item.setPos(pos)
        
        # フォント設定
        font = QFont()
        font.setPointSize(size)
        font.setBold(True)
        text_item.setFont(font)
        
        # 色設定
        text_item.setDefaultTextColor(color)
        
        text_item.setFlag(QGraphicsTextItem.ItemIsSelectable, True)
        text_item.setFlag(QGraphicsTextItem.ItemIsMovable, True)
        
        return text_item
