# -*- coding: utf-8 -*-
"""
Photo Utilities - 写真モジュール共通ユーティリティ

PhotoViewerPanel/PhotoEditorPanelで共通使用するヘルパー関数群。

機能:
    - パス解決（相対パス→絶対パス）
    - 画像読み込み
    - フィールド値の取得・検証
    - 保存パス生成
"""

import os
from typing import Optional, Tuple
from qgis.PyQt.QtGui import QPixmap, QImage
from qgis.core import QgsFeature, QgsMessageLog, Qgis


class PhotoPathResolver:
    """
    写真パス解決ユーティリティ
    
    相対パスから実際のファイルパスを解決する機能を提供
    """
    
    @staticmethod
    def resolve(relative_path: str, config_manager) -> str:
        r"""
        相対パスから実際のファイルパスを解決（OS非依存）
        
        処理:
            1. ConfigManager から photo_root_path 取得
            2. 相対パスのパス区切り文字を正規化（\ → /）
            3. os.path.join() で結合
            4. os.path.normpath() で最終的に正規化
        
        Args:
            relative_path: CSV/GeoPackageのフィールド値
                          例: "original/A001/P001_1.jpg"
                          または "original\A001\P001_1.jpg"
            config_manager: ConfigManager インスタンス
        
        Returns:
            str: 実際のファイルパス
                 例（Mac）: "/Users/.../Photos/original/A001/P001_1.jpg"
                 例（Win）: "C:\Users\...\Photos\original\A001\P001_1.jpg"
        
        Raises:
            ValueError: photo_root_path が未設定の場合
        
        Example:
            >>> resolver = PhotoPathResolver()
            >>> path = resolver.resolve("original/folder/image.jpg", config_manager)
            >>> print(path)
            '/Users/username/Photos/original/folder/image.jpg'
        """
        if not relative_path or relative_path.strip().upper() == 'NULL':
            return None
        
        # ConfigManager からルートパス取得
        photo_root = config_manager.get_photo_root_path()
        
        if not photo_root:
            raise ValueError("写真ルートパスが設定されていません")
        
        # 相対パスのパス区切り文字を正規化
        # Windows形式（\）→ POSIX形式（/）に統一してから os.path.join() を使用
        normalized_relative = relative_path.replace('\\', '/')
        
        # os.path.join() は自動的にOSに応じた区切り文字に変換
        actual_path = os.path.join(photo_root, normalized_relative)
        
        # 最終的に正規化（余分な区切り文字の削除、. や .. の解決）
        actual_path = os.path.normpath(actual_path)
        
        return actual_path
    
    @staticmethod
    def generate_save_path(
        source_field_name: str,
        feature: QgsFeature,
        config_manager
    ) -> Tuple[str, str]:
        """
        編集済み写真の保存パスを生成
        
        パス形式:
            edited/[元フォルダ名]/[元ファイル名]
        
        例:
            元の相対パス: original/2700012345局前_1/images-1.jpeg
            保存先相対パス: edited/2700012345局前_1/images-1.jpeg
        
        Args:
            source_field_name: 修正前フィールド名（例: "設備写真1URI_修正前"）
            feature: 地物オブジェクト
            config_manager: ConfigManager インスタンス
        
        Returns:
            tuple: (相対パス, 実際のパス)
        
        Raises:
            ValueError: 元画像パスが取得できない場合、ルートパス未設定の場合
        
        Example:
            >>> relative, actual = PhotoPathResolver.generate_save_path(
            ...     "設備写真1URI_修正前", feature, config_manager
            ... )
            >>> print(relative)
            'edited/2700012345局前_1/images-1.jpeg'
        """
        # 修正前フィールドから相対パス取得
        source_relative_path = feature[source_field_name]
        
        if not source_relative_path or str(source_relative_path).strip().upper() == 'NULL':
            raise ValueError(f"元画像パスが取得できません（フィールド: {source_field_name}）")
        
        # original/ プレフィックスを除去
        source_path_normalized = str(source_relative_path)
        if source_path_normalized.startswith("original/"):
            source_path_normalized = source_path_normalized[len("original/"):]
        elif source_path_normalized.startswith("original\\"):
            source_path_normalized = source_path_normalized[len("original\\"):]
        
        # 相対パス: edited/[元フォルダ名]/[元ファイル名]
        relative_path = f"edited/{source_path_normalized}"
        
        # 実際のパス
        photo_root = config_manager.get_photo_root_path()
        
        if not photo_root:
            raise ValueError("写真ルートパスが設定されていません")
        
        actual_path = os.path.join(photo_root, relative_path)
        actual_path = os.path.normpath(actual_path)
        
        return relative_path, actual_path


class PhotoImageLoader:
    """
    写真画像読み込みユーティリティ
    
    画像ファイルをQPixmapとして読み込む機能を提供
    """
    
    @staticmethod
    def load(photo_path: str) -> Optional[QPixmap]:
        """
        画像をQPixmapとして読み込む
        
        処理:
            1. QImage として読み込み
            2. RGB32 フォーマットに変換
            3. QPixmap に変換
        
        Args:
            photo_path: 画像ファイルパス
        
        Returns:
            QPixmap: QPixmap オブジェクト、失敗時は None
        
        Note:
            QImage.Format_RGB32 に変換することで、
            各種画像形式に対応
        
        Example:
            >>> pixmap = PhotoImageLoader.load("/path/to/image.jpg")
            >>> if pixmap and not pixmap.isNull():
            ...     # 画像読み込み成功
            ...     pass
        """
        try:
            qimage = QImage(photo_path)
            
            if not qimage.isNull():
                # RGB32フォーマットに変換
                qimage = qimage.convertToFormat(QImage.Format_RGB32)
                return QPixmap.fromImage(qimage)
            
        except Exception as e:
            QgsMessageLog.logMessage(
                f"画像読み込み失敗: {str(e)}",
                "PoleFacility", Qgis.Warning
            )
        
        return None
    
    @staticmethod
    def save(pixmap: QPixmap, file_path: str, quality: int = 90) -> bool:
        """
        QPixmapを画像ファイルとして保存
        
        Args:
            pixmap: 保存するQPixmap
            file_path: 保存先ファイルパス
            quality: JPEG品質（1-100、デフォルト: 90）
        
        Returns:
            bool: 保存成功時 True、失敗時 False
        
        Note:
            保存先ディレクトリは事前に作成しておくこと
        
        Example:
            >>> os.makedirs(os.path.dirname(save_path), exist_ok=True)
            >>> success = PhotoImageLoader.save(pixmap, save_path, 90)
        """
        try:
            image = pixmap.toImage()
            return image.save(file_path, "JPEG", quality)
        except Exception as e:
            QgsMessageLog.logMessage(
                f"画像保存失敗: {str(e)}",
                "PoleFacility", Qgis.Warning
            )
            return False


class PhotoFieldValidator:
    """
    写真フィールド検証ユーティリティ
    
    フィールド値の取得・検証機能を提供
    """
    
    @staticmethod
    def get_field_value(
        feature: QgsFeature, 
        field_name: str
    ) -> Optional[str]:
        """
        フィールド値取得（空・NULLチェック）
        
        Args:
            feature: 地物オブジェクト
            field_name: フィールド名
        
        Returns:
            str: フィールド値、または None
        
        Raises:
            ValueError: フィールドが見つからない場合
        
        処理:
            1. フィールド値を取得
            2. 空文字・NULL・'NULL'文字列をチェック
            3. 有効な値のみ返す
        
        Example:
            >>> try:
            ...     value = PhotoFieldValidator.get_field_value(
            ...         feature, "設備写真1URI_修正前"
            ...     )
            ...     if value:
            ...         print(f"Value: {value}")
            ... except ValueError as e:
            ...     print(f"Error: {e}")
        """
        try:
            value = feature[field_name]
        except KeyError:
            QgsMessageLog.logMessage(
                f"PhotoFieldValidator - フィールドが見つかりません: {field_name}",
                "PoleFacility", Qgis.Warning
            )
            raise ValueError(f"フィールドが見つかりません: {field_name}")
        
        if not value:
            return None
        
        value_str = str(value).strip()
        
        if value_str.upper() == 'NULL' or not value_str:
            return None
        
        return value_str
    
    @staticmethod
    def validate_photo_fields(
        feature: QgsFeature,
        field_names: list
    ) -> dict:
        """
        複数の写真フィールドをまとめて検証
        
        Args:
            feature: 地物オブジェクト
            field_names: フィールド名のリスト
        
        Returns:
            dict: {field_name: value or None, ...}
        
        Example:
            >>> fields = [
            ...     "設備写真1URI_修正前",
            ...     "設備写真2URI_修正前",
            ...     "設備写真3URI_修正前"
            ... ]
            >>> values = PhotoFieldValidator.validate_photo_fields(feature, fields)
            >>> for field, value in values.items():
            ...     if value:
            ...         print(f"{field}: {value}")
        """
        result = {}
        
        for field_name in field_names:
            try:
                value = PhotoFieldValidator.get_field_value(feature, field_name)
                result[field_name] = value
            except ValueError:
                result[field_name] = None
        
        return result
    
    @staticmethod
    def is_valid_photo_path(path: str) -> bool:
        """
        写真パスの妥当性チェック
        
        Args:
            path: チェック対象のパス
        
        Returns:
            bool: 有効なパスの場合 True
        
        チェック内容:
            - 空でない
            - 'NULL'文字列でない
            - ファイルが存在する
        
        Example:
            >>> if PhotoFieldValidator.is_valid_photo_path(photo_path):
            ...     # パスが有効
            ...     pixmap = PhotoImageLoader.load(photo_path)
        """
        if not path:
            return False
        
        if str(path).strip().upper() == 'NULL':
            return False
        
        return os.path.exists(path)


class PhotoFileHelper:
    """
    写真ファイル操作ヘルパー
    
    ファイル・ディレクトリ操作の補助機能を提供
    """
    
    @staticmethod
    def ensure_directory(file_path: str) -> bool:
        """
        ファイルパスのディレクトリが存在することを保証
        
        Args:
            file_path: ファイルパス
        
        Returns:
            bool: ディレクトリ作成成功時 True
        
        処理:
            親ディレクトリが存在しない場合は作成する
        
        Example:
            >>> save_path = "/path/to/edited/folder/image.jpg"
            >>> if PhotoFileHelper.ensure_directory(save_path):
            ...     # ディレクトリ準備完了、保存可能
            ...     PhotoImageLoader.save(pixmap, save_path)
        """
        try:
            dir_path = os.path.dirname(file_path)
            os.makedirs(dir_path, exist_ok=True)
            return True
        except Exception as e:
            QgsMessageLog.logMessage(
                f"ディレクトリ作成失敗: {str(e)}",
                "PoleFacility", Qgis.Warning
            )
            return False
    
    @staticmethod
    def get_file_info(file_path: str) -> dict:
        """
        ファイル情報を取得
        
        Args:
            file_path: ファイルパス
        
        Returns:
            dict: ファイル情報
                {
                    'exists': bool,
                    'size': int (bytes),
                    'extension': str,
                    'filename': str,
                    'dirname': str
                }
        
        Example:
            >>> info = PhotoFileHelper.get_file_info("/path/to/image.jpg")
            >>> if info['exists']:
            ...     print(f"Size: {info['size']} bytes")
        """
        return {
            'exists': os.path.exists(file_path),
            'size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            'extension': os.path.splitext(file_path)[1],
            'filename': os.path.basename(file_path),
            'dirname': os.path.dirname(file_path)
        }
    
    @staticmethod
    def normalize_path(path: str) -> str:
        """
        パスを正規化
        
        Args:
            path: 正規化対象のパス
        
        Returns:
            str: 正規化されたパス
        
        処理:
            - パス区切り文字を統一
            - 余分な区切り文字を削除
            - . や .. を解決
        
        Example:
            >>> path = "folder\\subfolder/./file.jpg"
            >>> normalized = PhotoFileHelper.normalize_path(path)
            >>> print(normalized)
            'folder/subfolder/file.jpg'  # OS依存
        """
        # まず / に統一
        normalized = path.replace('\\', '/')
        # OS標準の形式に変換
        normalized = os.path.normpath(normalized)
        return normalized


class PhotoConstants:
    """
    写真モジュール定数
    
    写真フィールド名、パスプレフィックスなどの定数を定義
    """
    
    # フィールド名パターン
    FIELD_BEFORE_SUFFIX = "_修正前"
    FIELD_AFTER_SUFFIX = "_修正後"
    
    # パスプレフィックス
    PATH_ORIGINAL_PREFIX = "original/"
    PATH_EDITED_PREFIX = "edited/"
    
    # デフォルト設定
    DEFAULT_JPEG_QUALITY = 90
    DEFAULT_IMAGE_FORMAT = "JPEG"
    
    @staticmethod
    def get_before_field_name(after_field_name: str) -> str:
        """
        修正後フィールド名から修正前フィールド名を生成
        
        Args:
            after_field_name: 修正後フィールド名
                            例: "設備写真1URI_修正後"
        
        Returns:
            str: 修正前フィールド名
                 例: "設備写真1URI_修正前"
        
        Example:
            >>> before = PhotoConstants.get_before_field_name("設備写真1URI_修正後")
            >>> print(before)
            '設備写真1URI_修正前'
        """
        return after_field_name.replace(
            PhotoConstants.FIELD_AFTER_SUFFIX,
            PhotoConstants.FIELD_BEFORE_SUFFIX
        )
    
    @staticmethod
    def get_after_field_name(before_field_name: str) -> str:
        """
        修正前フィールド名から修正後フィールド名を生成
        
        Args:
            before_field_name: 修正前フィールド名
                             例: "設備写真1URI_修正前"
        
        Returns:
            str: 修正後フィールド名
                 例: "設備写真1URI_修正後"
        
        Example:
            >>> after = PhotoConstants.get_after_field_name("設備写真1URI_修正前")
            >>> print(after)
            '設備写真1URI_修正後'
        """
        return before_field_name.replace(
            PhotoConstants.FIELD_BEFORE_SUFFIX,
            PhotoConstants.FIELD_AFTER_SUFFIX
        )
    
    @staticmethod
    def is_before_field(field_name: str) -> bool:
        """
        修正前フィールドか判定
        
        Args:
            field_name: フィールド名
        
        Returns:
            bool: 修正前フィールドの場合 True
        """
        return field_name.endswith(PhotoConstants.FIELD_BEFORE_SUFFIX)
    
    @staticmethod
    def is_after_field(field_name: str) -> bool:
        """
        修正後フィールドか判定
        
        Args:
            field_name: フィールド名
        
        Returns:
            bool: 修正後フィールドの場合 True
        """
        return field_name.endswith(PhotoConstants.FIELD_AFTER_SUFFIX)


# エイリアス（後方互換性のため）
resolve_photo_path = PhotoPathResolver.resolve
load_image_as_pixmap = PhotoImageLoader.load
get_field_value = PhotoFieldValidator.get_field_value
