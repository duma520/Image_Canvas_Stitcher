# -*- coding: utf-8 -*-
"""
图片自由拼接工具 - Image Canvas Stitcher (PySide6 版本)
功能：
- 从剪贴板粘贴图片 (Ctrl+V)
- 拖拽文件导入图片
- 鼠标拖动自由摆放图片位置
- 滚轮缩放选中的图片（选中时）或缩放整个视图（未选中时 / Ctrl+滚轮）
- 大画布可平移（按住空格+鼠标拖动 / 中键拖动）
- 右键菜单：删除、置顶、置底、缩放重置、透明度调整、旋转
- 导出拼接后的完整大图
- 视图整体缩放，方便看全貌和细节
- 【新增】单张/整体透明度调整
- 【新增】图片差异比对与红色标记
- 【新增】自动保存，下次启动自动恢复上次画面
- 【新增】历史记录管理，可保存、预览、加载历史项目
- 【新增】选项设置：自定义背景、自动保存间隔、历史数量、性能模式
- 【新增】单张/多张/整体图片旋转功能，支持90°、45°等常用角度
- 【新增】图片水平/垂直镜像翻转功能（单张/整体）
- 【优化】工具栏自适应布局，适配各种分辨率
- 【修复】右键菜单后鼠标移动卡顿问题
- 【新增】工具栏自定义：可显示/隐藏任意按钮和组件
- 【修复】工具栏自定义设置后组件未隐藏的问题
- 【新增】背景方案：纯色、网格、点阵、自定义图片
"""
import sys
import os
import json
import time
import uuid
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsItem, QToolBar, QPushButton,
    QLabel, QStatusBar, QMenu, QFileDialog, QMessageBox, QWidget,
    QHBoxLayout, QSlider, QVBoxLayout, QListWidget, QListWidgetItem,
    QDialog, QDialogButtonBox, QSplitter, QGraphicsRectItem,
    QGroupBox, QFormLayout, QSpinBox, QCheckBox, QColorDialog,
    QComboBox, QTabWidget, QScrollArea, QGridLayout, QFrame,
    QButtonGroup, QRadioButton, QLineEdit
)
from PySide6.QtGui import (
    QPixmap, QImage, QClipboard, QPainter, QAction, QCursor,
    QPen, QColor, QBrush, QIcon, QPixmap, QTransform, QPainterPath
)
from PySide6.QtCore import Qt, QPointF, QRectF, QSizeF, QTimer, QSize, QRect

# ==================== 配置常量 ====================
# 自动保存和历史记录都保存在程序所在目录的子目录下，方便管理
PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
AUTOSAVE_DIR = os.path.join(PROGRAM_DIR, "autosave")
HISTORY_DIR = os.path.join(PROGRAM_DIR, "history")
SETTINGS_FILE = os.path.join(PROGRAM_DIR, "settings.json")
BACKGROUNDS_DIR = os.path.join(PROGRAM_DIR, "backgrounds")  # 自定义背景图片目录

# 默认配置
DEFAULT_SETTINGS = {
    "background_type": "solid",  # solid / grid / dots / image
    "background_color": "#2b2b2b",
    "background_color_light": "#3a3a3a",  # 网格或点阵的辅助色
    "background_image": "",  # 自定义背景图片路径
    "background_image_scale": "fit",  # fit / stretch / tile
    "grid_size": 30,  # 网格大小（像素）
    "grid_opacity": 0.3,  # 网格透明度
    "autosave_delay_ms": 1500,
    "max_history_items": None,  # None 表示不限制
    "performance_mode": "balanced",  # quality / balanced / performance
    "antialiasing": True,
    "smooth_pixmap": True,
    # 工具栏可见性配置
    "toolbar_visibility": {
        # 文件操作
        "btn_import": True,
        "btn_paste": True,
        "btn_del": True,
        # 图片缩放
        "btn_zoom_in": True,
        "btn_zoom_out": True,
        "btn_reset": True,
        # 图片旋转
        "btn_rot_left": True,
        "btn_rot_right": True,
        # 镜像翻转
        "btn_flip_h": True,
        "btn_flip_v": True,
        # 视图缩放
        "btn_view_in": True,
        "btn_view_out": True,
        "btn_view_fit": True,
        # 图层
        "btn_front": True,
        "btn_back": True,
        # 透明度
        "item_opacity": True,
        "global_opacity": True,
        # 差异比对
        "btn_diff": True,
        "btn_clear_diff": True,
        # 历史记录
        "btn_save_hist": True,
        "btn_history": True,
        # 导出和设置
        "btn_export": True,
        "btn_clear": True,
        "btn_settings": True,
    }
}


def ensure_dirs():
    """确保数据目录存在"""
    for d in [AUTOSAVE_DIR, HISTORY_DIR, BACKGROUNDS_DIR,
              os.path.join(AUTOSAVE_DIR, "images"),
              os.path.join(HISTORY_DIR, "images")]:
        os.makedirs(d, exist_ok=True)


# ==================== 背景渲染器 ====================
class BackgroundRenderer:
    """背景渲染器 - 支持多种背景方案"""
    
    @staticmethod
    def render_background(settings, width, height):
        """根据设置渲染背景图片"""
        bg_type = settings.get("background_type", "solid")
        
        if bg_type == "solid":
            return BackgroundRenderer._render_solid(settings, width, height)
        elif bg_type == "grid":
            return BackgroundRenderer._render_grid(settings, width, height)
        elif bg_type == "dots":
            return BackgroundRenderer._render_dots(settings, width, height)
        elif bg_type == "image":
            return BackgroundRenderer._render_image(settings, width, height)
        else:
            return BackgroundRenderer._render_solid(settings, width, height)
    
    @staticmethod
    def _render_solid(settings, width, height):
        """纯色背景"""
        img = QImage(width, height, QImage.Format_RGB32)
        color = QColor(settings.get("background_color", "#2b2b2b"))
        img.fill(color)
        return img
    
    @staticmethod
    def _render_grid(settings, width, height):
        """网格背景"""
        img = QImage(width, height, QImage.Format_RGB32)
        bg_color = QColor(settings.get("background_color", "#2b2b2b"))
        grid_color = QColor(settings.get("background_color_light", "#3a3a3a"))
        grid_color.setAlpha(int(255 * settings.get("grid_opacity", 0.3)))
        grid_size = settings.get("grid_size", 30)
        
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(grid_color, 1))
        
        # 绘制垂直线
        x = grid_size
        while x < width:
            painter.drawLine(x, 0, x, height)
            x += grid_size
        
        # 绘制水平线
        y = grid_size
        while y < height:
            painter.drawLine(0, y, width, y)
            y += grid_size
        
        painter.end()
        return img
    
    @staticmethod
    def _render_dots(settings, width, height):
        """点阵背景"""
        img = QImage(width, height, QImage.Format_RGB32)
        bg_color = QColor(settings.get("background_color", "#2b2b2b"))
        dot_color = QColor(settings.get("background_color_light", "#3a3a3a"))
        dot_color.setAlpha(int(255 * settings.get("grid_opacity", 0.3)))
        grid_size = settings.get("grid_size", 30)
        dot_radius = 1.5
        
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(dot_color, 1))
        painter.setBrush(QBrush(dot_color))
        
        # 绘制点阵
        x = grid_size / 2
        while x < width:
            y = grid_size / 2
            while y < height:
                painter.drawEllipse(QPointF(x, y), dot_radius, dot_radius)
                y += grid_size
            x += grid_size
        
        painter.end()
        return img
    
    @staticmethod
    def _render_image(settings, width, height):
        """自定义图片背景"""
        img_path = settings.get("background_image", "")
        if not img_path or not os.path.exists(img_path):
            # 如果没有有效图片，回退到纯色
            return BackgroundRenderer._render_solid(settings, width, height)
        
        try:
            pixmap = QPixmap(img_path)
            if pixmap.isNull():
                return BackgroundRenderer._render_solid(settings, width, height)
            
            img = QImage(width, height, QImage.Format_RGB32)
            bg_color = QColor(settings.get("background_color", "#2b2b2b"))
            img.fill(bg_color)
            
            painter = QPainter(img)
            scale_mode = settings.get("background_image_scale", "fit")
            
            if scale_mode == "fit":
                # 保持比例适配
                scaled = pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                x = (width - scaled.width()) // 2
                y = (height - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
            elif scale_mode == "stretch":
                # 拉伸填充
                scaled = pixmap.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                painter.drawPixmap(0, 0, scaled)
            elif scale_mode == "tile":
                # 平铺
                pw = pixmap.width()
                ph = pixmap.height()
                for y in range(0, height, ph):
                    for x in range(0, width, pw):
                        painter.drawPixmap(x, y, pixmap)
            
            painter.end()
            return img
        except Exception:
            return BackgroundRenderer._render_solid(settings, width, height)


# ==================== 背景缓存 ====================
class BackgroundCache:
    """背景缓存，避免频繁重新渲染"""
    _instance = None
    _cache = {}  # key: (width, height, settings_hash) -> QImage
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_background(self, settings, width, height):
        """获取背景图片（带缓存）"""
        # 生成缓存键
        key = self._make_key(settings, width, height)
        if key in self._cache:
            return self._cache[key]
        
        # 渲染新背景
        img = BackgroundRenderer.render_background(settings, width, height)
        self._cache[key] = img
        
        # 限制缓存大小
        if len(self._cache) > 10:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        
        return img
    
    def _make_key(self, settings, width, height):
        """生成缓存键"""
        bg_type = settings.get("background_type", "solid")
        if bg_type == "solid":
            color = settings.get("background_color", "#2b2b2b")
            return f"solid_{width}_{height}_{color}"
        elif bg_type == "grid":
            color = settings.get("background_color", "#2b2b2b")
            light = settings.get("background_color_light", "#3a3a3a")
            size = settings.get("grid_size", 30)
            opacity = settings.get("grid_opacity", 0.3)
            return f"grid_{width}_{height}_{color}_{light}_{size}_{opacity}"
        elif bg_type == "dots":
            color = settings.get("background_color", "#2b2b2b")
            light = settings.get("background_color_light", "#3a3a3a")
            size = settings.get("grid_size", 30)
            opacity = settings.get("grid_opacity", 0.3)
            return f"dots_{width}_{height}_{color}_{light}_{size}_{opacity}"
        elif bg_type == "image":
            img_path = settings.get("background_image", "")
            scale = settings.get("background_image_scale", "fit")
            return f"image_{width}_{height}_{img_path}_{scale}"
        return f"unknown_{width}_{height}"
    
    def clear(self):
        """清空缓存"""
        self._cache.clear()


# ==================== 设置管理器 ====================
class SettingsManager:
    """全局设置管理器（单例模式简化版）"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        """从文件加载设置"""
        self._settings = dict(DEFAULT_SETTINGS)
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    # 合并，保留默认值
                    for key, value in DEFAULT_SETTINGS.items():
                        if key not in saved:
                            saved[key] = value
                    self._settings.update(saved)
            except Exception:
                pass
        self._save_defaults()

    def _save_defaults(self):
        """保存默认设置（确保文件存在）"""
        if not os.path.exists(SETTINGS_FILE):
            self.save()

    def save(self):
        """保存设置到文件"""
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get(self, key, default=None):
        return self._settings.get(key, default)

    def set(self, key, value):
        self._settings[key] = value

    def get_all(self):
        return dict(self._settings)

    def update(self, settings_dict):
        self._settings.update(settings_dict)

    def get_background_color(self):
        return QColor(self._settings.get("background_color", "#2b2b2b"))

    def get_background_color_light(self):
        return QColor(self._settings.get("background_color_light", "#3a3a3a"))

    def get_autosave_delay(self):
        return int(self._settings.get("autosave_delay_ms", 1500))

    def get_max_history(self):
        return self._settings.get("max_history_items", None)

    def get_performance_mode(self):
        return self._settings.get("performance_mode", "balanced")

    def get_toolbar_visibility(self):
        """获取工具栏可见性配置"""
        return self._settings.get("toolbar_visibility", dict(DEFAULT_SETTINGS["toolbar_visibility"]))

    def set_toolbar_visibility(self, visibility_dict):
        """设置工具栏可见性配置"""
        self._settings["toolbar_visibility"] = visibility_dict


# ==================== 工具栏自定义对话框 ====================
class ToolbarCustomizeDialog(QDialog):
    """工具栏自定义对话框 - 选择显示哪些按钮"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("自定义工具栏")
        self.resize(550, 500)
        self._settings = SettingsManager()
        self._visibility = self._settings.get_toolbar_visibility().copy()
        self._main_window = None
        # 查找主窗口
        self._find_main_window(parent)
        self._build_ui()
        self._load_values()

    def _find_main_window(self, widget):
        """向上查找主窗口"""
        while widget is not None:
            if isinstance(widget, MainWindow):
                self._main_window = widget
                break
            widget = widget.parent()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # 说明标签
        info_label = QLabel("勾选要在工具栏中显示的按钮和组件：")
        info_label.setStyleSheet("font-weight: bold; padding: 5px 0;")
        layout.addWidget(info_label)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content_widget = QWidget()
        # 使用 QVBoxLayout 作为主布局，每个组使用 QGroupBox
        main_layout = QVBoxLayout(content_widget)
        main_layout.setSpacing(12)

        # 定义所有可配置项（分组）
        groups = [
            ("📁 文件操作", [
                ("btn_import", "导入图片"),
                ("btn_paste", "粘贴图片"),
                ("btn_del", "删除"),
            ]),
            ("🔍 图片缩放", [
                ("btn_zoom_in", "放大+"),
                ("btn_zoom_out", "缩小-"),
                ("btn_reset", "重置大小"),
            ]),
            ("🔄 图片旋转", [
                ("btn_rot_left", "↺ 左旋"),
                ("btn_rot_right", "↻ 右旋"),
            ]),
            ("🪞 镜像翻转", [
                ("btn_flip_h", "⇆ 水平镜像"),
                ("btn_flip_v", "⇅ 垂直镜像"),
            ]),
            ("🔎 视图缩放", [
                ("btn_view_in", "视图+"),
                ("btn_view_out", "视图-"),
                ("btn_view_fit", "适配"),
            ]),
            ("📐 图层", [
                ("btn_front", "置顶"),
                ("btn_back", "置底"),
            ]),
            ("🎨 透明度", [
                ("item_opacity", "单图透明度滑块"),
                ("global_opacity", "整体透明度滑块"),
            ]),
            ("📊 差异比对", [
                ("btn_diff", "比对差异"),
                ("btn_clear_diff", "清除标记"),
            ]),
            ("📜 历史记录", [
                ("btn_save_hist", "保存历史"),
                ("btn_history", "历史记录"),
            ]),
            ("💾 导出与设置", [
                ("btn_export", "导出"),
                ("btn_clear", "清空"),
                ("btn_settings", "设置"),
            ]),
        ]

        self.checkboxes = {}

        for group_name, items in groups:
            # 每个组使用 QGroupBox
            group_box = QGroupBox(group_name)
            group_layout = QGridLayout(group_box)
            group_layout.setSpacing(6)
            
            # 每行显示2个复选框
            cols = 2
            for idx, (key, label) in enumerate(items):
                row = idx // cols
                col = idx % cols
                cb = QCheckBox(label)
                cb.setObjectName(key)
                self.checkboxes[key] = cb
                group_layout.addWidget(cb, row, col, Qt.AlignLeft)
            
            main_layout.addWidget(group_box)

        # 添加弹性空间
        main_layout.addStretch()

        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        # 全选/取消全选按钮
        btn_layout = QHBoxLayout()
        btn_select_all = QPushButton("✅ 全选")
        btn_select_all.clicked.connect(self._select_all)
        btn_deselect_all = QPushButton("❌ 取消全选")
        btn_deselect_all.clicked.connect(self._deselect_all)
        btn_reset_default = QPushButton("↩️ 恢复默认")
        btn_reset_default.clicked.connect(self._reset_default)
        btn_layout.addWidget(btn_select_all)
        btn_layout.addWidget(btn_deselect_all)
        btn_layout.addWidget(btn_reset_default)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 底部按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Apply).clicked.connect(self._on_apply)
        layout.addWidget(buttons)

    def _load_values(self):
        for key, cb in self.checkboxes.items():
            cb.setChecked(self._visibility.get(key, True))

    def _collect_values(self):
        result = {}
        for key, cb in self.checkboxes.items():
            result[key] = cb.isChecked()
        return result

    def _select_all(self):
        for cb in self.checkboxes.values():
            cb.setChecked(True)

    def _deselect_all(self):
        for cb in self.checkboxes.values():
            cb.setChecked(False)

    def _reset_default(self):
        default = DEFAULT_SETTINGS["toolbar_visibility"]
        for key, cb in self.checkboxes.items():
            cb.setChecked(default.get(key, True))

    def _on_apply(self):
        self._visibility = self._collect_values()
        self._settings.set_toolbar_visibility(self._visibility)
        self._settings.save()
        # 直接调用主窗口的 apply_toolbar_visibility
        if self._main_window:
            self._main_window.apply_toolbar_visibility()

    def _on_ok(self):
        self._on_apply()
        self.accept()


# ==================== 设置对话框 ====================
class SettingsDialog(QDialog):
    """选项设置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选项设置")
        self.resize(520, 600)
        self._settings = SettingsManager()
        self._main_window = None
        self._find_main_window(parent)
        self._build_ui()
        self._load_values()

    def _find_main_window(self, widget):
        """向上查找主窗口"""
        while widget is not None:
            if isinstance(widget, MainWindow):
                self._main_window = widget
                break
            widget = widget.parent()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._build_background_tab(), "🎨 背景")
        tabs.addTab(self._build_general_tab(), "⚙️ 通用")
        tabs.addTab(self._build_performance_tab(), "🚀 性能")
        tabs.addTab(self._build_toolbar_tab(), "🔧 工具栏")
        layout.addWidget(tabs, 1)

        # 底部按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Apply).clicked.connect(self._on_apply)
        layout.addWidget(buttons)

    def _build_background_tab(self):
        """背景设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 背景类型选择
        type_group = QGroupBox("背景类型")
        type_layout = QHBoxLayout()
        self.bg_type_btns = QButtonGroup(self)
        
        self.bg_solid = QRadioButton("纯色")
        self.bg_grid = QRadioButton("网格")
        self.bg_dots = QRadioButton("点阵")
        self.bg_image = QRadioButton("自定义图片")
        
        self.bg_type_btns.addButton(self.bg_solid, 0)
        self.bg_type_btns.addButton(self.bg_grid, 1)
        self.bg_type_btns.addButton(self.bg_dots, 2)
        self.bg_type_btns.addButton(self.bg_image, 3)
        
        type_layout.addWidget(self.bg_solid)
        type_layout.addWidget(self.bg_grid)
        type_layout.addWidget(self.bg_dots)
        type_layout.addWidget(self.bg_image)
        type_layout.addStretch()
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # 纯色设置
        self.solid_frame = QFrame()
        solid_layout = QFormLayout(self.solid_frame)
        
        bg_layout = QHBoxLayout()
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setFixedSize(60, 28)
        self.bg_color_btn.clicked.connect(self._choose_bg_color)
        self.bg_color_label = QLabel("")
        bg_layout.addWidget(self.bg_color_btn)
        bg_layout.addWidget(self.bg_color_label)
        bg_layout.addStretch()
        solid_layout.addRow("背景颜色:", bg_layout)
        
        layout.addWidget(self.solid_frame)
        
        # 网格/点阵设置
        self.grid_frame = QFrame()
        grid_layout = QFormLayout(self.grid_frame)
        
        light_layout = QHBoxLayout()
        self.bg_light_btn = QPushButton()
        self.bg_light_btn.setFixedSize(60, 28)
        self.bg_light_btn.clicked.connect(self._choose_bg_light_color)
        self.bg_light_label = QLabel("")
        light_layout.addWidget(self.bg_light_btn)
        light_layout.addWidget(self.bg_light_label)
        light_layout.addStretch()
        grid_layout.addRow("线条/点颜色:", light_layout)
        
        self.grid_size_spin = QSpinBox()
        self.grid_size_spin.setRange(5, 200)
        self.grid_size_spin.setSuffix(" px")
        grid_layout.addRow("网格大小:", self.grid_size_spin)
        
        self.grid_opacity_slider = QSlider(Qt.Horizontal)
        self.grid_opacity_slider.setRange(5, 100)
        self.grid_opacity_slider.setValue(30)
        self.grid_opacity_label = QLabel("30%")
        grid_opacity_layout = QHBoxLayout()
        grid_opacity_layout.addWidget(self.grid_opacity_slider)
        grid_opacity_layout.addWidget(self.grid_opacity_label)
        grid_layout.addRow("透明度:", grid_opacity_layout)
        
        layout.addWidget(self.grid_frame)
        
        # 自定义图片设置
        self.image_frame = QFrame()
        image_layout = QFormLayout(self.image_frame)
        
        img_path_layout = QHBoxLayout()
        self.bg_image_edit = QLineEdit()
        self.bg_image_edit.setReadOnly(True)
        self.bg_image_edit.setPlaceholderText("选择背景图片...")
        self.bg_image_btn = QPushButton("浏览...")
        self.bg_image_btn.clicked.connect(self._choose_bg_image)
        img_path_layout.addWidget(self.bg_image_edit)
        img_path_layout.addWidget(self.bg_image_btn)
        image_layout.addRow("图片路径:", img_path_layout)
        
        self.bg_image_scale = QComboBox()
        self.bg_image_scale.addItems(["适配 (保持比例)", "拉伸填充", "平铺"])
        self.bg_image_scale.setCurrentIndex(0)
        image_layout.addRow("缩放模式:", self.bg_image_scale)
        
        # 预览按钮
        preview_btn = QPushButton("预览背景")
        preview_btn.clicked.connect(self._preview_background)
        image_layout.addRow("", preview_btn)
        
        layout.addWidget(self.image_frame)
        
        # 连接信号
        self.bg_type_btns.idClicked.connect(self._on_bg_type_changed)
        
        layout.addStretch()
        return widget

    def _build_general_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        # 自动保存间隔
        self.autosave_spin = QSpinBox()
        self.autosave_spin.setRange(100, 30000)
        self.autosave_spin.setSingleStep(100)
        self.autosave_spin.setSuffix(" 毫秒")
        self.autosave_spin.setToolTip("操作停止后多久自动保存一次（防抖延迟）")
        layout.addRow("自动保存延迟:", self.autosave_spin)

        # 历史记录数量
        hist_layout = QHBoxLayout()
        self.history_check = QCheckBox("限制历史记录数量")
        self.history_check.stateChanged.connect(self._on_history_check_changed)
        self.history_spin = QSpinBox()
        self.history_spin.setRange(1, 1000)
        self.history_spin.setEnabled(False)
        hist_layout.addWidget(self.history_check)
        hist_layout.addWidget(self.history_spin)
        hist_layout.addStretch()
        layout.addRow("历史记录:", hist_layout)

        return widget

    def _build_performance_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        # 性能模式
        self.perf_combo = QComboBox()
        self.perf_combo.addItem("🌟 高质量（渲染精细，稍慢）", "quality")
        self.perf_combo.addItem("⚖️ 平衡（推荐）", "balanced")
        self.perf_combo.addItem("⚡ 高性能（流畅优先）", "performance")
        self.perf_combo.currentIndexChanged.connect(self._on_perf_mode_changed)
        layout.addRow("性能模式:", self.perf_combo)

        # 抗锯齿
        self.aa_check = QCheckBox("启用抗锯齿（边缘更平滑）")
        layout.addRow("", self.aa_check)

        # 平滑像素变换
        self.smooth_check = QCheckBox("平滑图片缩放（缩放更细腻）")
        layout.addRow("", self.smooth_check)

        # 说明
        tip = QLabel(
            "提示：\n"
            "• 高质量模式适合图片少、追求精细效果的场景\n"
            "• 高性能模式适合大量图片、追求流畅操作的场景\n"
            "• 修改后重新加载图片或重启程序生效最明显"
        )
        tip.setStyleSheet("color: #888; font-size: 11px; padding: 10px;")
        tip.setWordWrap(True)
        layout.addRow(tip)

        return widget

    def _build_toolbar_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 打开自定义对话框的按钮
        btn_customize = QPushButton("🔧 打开工具栏自定义...")
        btn_customize.setFixedHeight(40)
        btn_customize.setStyleSheet("font-size: 14px; font-weight: bold;")
        btn_customize.clicked.connect(self._open_toolbar_customize)
        layout.addWidget(btn_customize)

        info = QLabel(
            "点击上方按钮可以自定义工具栏中显示哪些按钮和组件。\n"
            "修改后点击「应用」或「确定」即可生效。"
        )
        info.setStyleSheet("color: #888; font-size: 12px; padding: 10px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addStretch()
        return widget

    def _open_toolbar_customize(self):
        dlg = ToolbarCustomizeDialog(self)
        dlg.exec()

    def _load_values(self):
        s = self._settings
        bg_type = s.get("background_type", "solid")
        
        # 背景类型
        type_map = {"solid": 0, "grid": 1, "dots": 2, "image": 3}
        self.bg_type_btns.button(type_map.get(bg_type, 0)).setChecked(True)
        self._on_bg_type_changed(type_map.get(bg_type, 0))
        
        # 颜色
        color = s.get_background_color()
        self._update_bg_color_button(color)
        
        light = s.get_background_color_light()
        self._update_bg_light_button(light)
        
        # 网格
        self.grid_size_spin.setValue(s.get("grid_size", 30))
        opacity = s.get("grid_opacity", 0.3)
        self.grid_opacity_slider.setValue(int(opacity * 100))
        self.grid_opacity_label.setText(f"{int(opacity * 100)}%")
        
        # 图片
        self.bg_image_edit.setText(s.get("background_image", ""))
        scale_map = {"fit": 0, "stretch": 1, "tile": 2}
        self.bg_image_scale.setCurrentIndex(scale_map.get(s.get("background_image_scale", "fit"), 0))
        
        # 自动保存
        self.autosave_spin.setValue(s.get_autosave_delay())
        
        # 历史数量
        max_hist = s.get_max_history()
        if max_hist is not None:
            self.history_check.setChecked(True)
            self.history_spin.setValue(max_hist)
            self.history_spin.setEnabled(True)
        else:
            self.history_check.setChecked(False)
            self.history_spin.setEnabled(False)
        
        # 性能
        mode = s.get_performance_mode()
        idx = self.perf_combo.findData(mode)
        if idx >= 0:
            self.perf_combo.setCurrentIndex(idx)
        self.aa_check.setChecked(s.get("antialiasing", True))
        self.smooth_check.setChecked(s.get("smooth_pixmap", True))

    def _on_bg_type_changed(self, type_id):
        """切换背景类型时显示/隐藏对应的设置区域"""
        self.solid_frame.setVisible(type_id == 0)
        self.grid_frame.setVisible(type_id in (1, 2))
        self.image_frame.setVisible(type_id == 3)

    def _choose_bg_color(self):
        current = self._settings.get_background_color()
        color = QColorDialog.getColor(current, self, "选择背景颜色")
        if color.isValid():
            self._update_bg_color_button(color)

    def _choose_bg_light_color(self):
        current = self._settings.get_background_color_light()
        color = QColorDialog.getColor(current, self, "选择网格/点阵颜色")
        if color.isValid():
            self._update_bg_light_button(color)

    def _choose_bg_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff);;所有文件 (*.*)"
        )
        if file_path:
            self.bg_image_edit.setText(file_path)

    def _preview_background(self):
        """预览当前背景设置"""
        if self._main_window:
            self._on_apply()
            self._main_window.view.update_background()

    def _update_bg_color_button(self, color):
        self.bg_color_btn.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid #888;"
        )
        self.bg_color_label.setText(color.name())

    def _update_bg_light_button(self, color):
        self.bg_light_btn.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid #888;"
        )
        self.bg_light_label.setText(color.name())

    def _on_history_check_changed(self, state):
        self.history_spin.setEnabled(state == Qt.Checked)

    def _on_perf_mode_changed(self, idx):
        mode = self.perf_combo.currentData()
        if mode == "quality":
            self.aa_check.setChecked(True)
            self.smooth_check.setChecked(True)
        elif mode == "balanced":
            self.aa_check.setChecked(True)
            self.smooth_check.setChecked(True)
        elif mode == "performance":
            self.aa_check.setChecked(False)
            self.smooth_check.setChecked(False)

    def _collect_settings(self):
        """收集当前UI中的设置"""
        result = {}
        # 背景类型
        type_map = {0: "solid", 1: "grid", 2: "dots", 3: "image"}
        bg_type = type_map.get(self.bg_type_btns.checkedId(), "solid")
        result["background_type"] = bg_type
        
        # 颜色
        result["background_color"] = self.bg_color_label.text() or "#2b2b2b"
        result["background_color_light"] = self.bg_light_label.text() or "#3a3a3a"
        
        # 网格
        result["grid_size"] = self.grid_size_spin.value()
        result["grid_opacity"] = self.grid_opacity_slider.value() / 100.0
        
        # 图片
        result["background_image"] = self.bg_image_edit.text()
        scale_map = {0: "fit", 1: "stretch", 2: "tile"}
        result["background_image_scale"] = scale_map.get(self.bg_image_scale.currentIndex(), "fit")
        
        # 自动保存
        result["autosave_delay_ms"] = self.autosave_spin.value()
        
        # 历史数量
        if self.history_check.isChecked():
            result["max_history_items"] = self.history_spin.value()
        else:
            result["max_history_items"] = None
        
        # 性能
        result["performance_mode"] = self.perf_combo.currentData()
        result["antialiasing"] = self.aa_check.isChecked()
        result["smooth_pixmap"] = self.smooth_check.isChecked()
        return result

    def _on_apply(self):
        """应用设置"""
        new_settings = self._collect_settings()
        self._settings.update(new_settings)
        self._settings.save()
        # 清空背景缓存
        BackgroundCache().clear()
        # 通知主窗口应用新设置（背景、性能等）
        if self._main_window:
            self._main_window.apply_settings()

    def _on_ok(self):
        self._on_apply()
        self.accept()


# ==================== 项目信息元数据 ====================
class ProjectInfo:
    """项目信息元数据（集中管理所有项目相关信息）"""
    # ----- 基本信息 -----
    NAME = "Image Canvas Stitcher"
    DISPLAY_NAME = "图片自由拼接工具"
    VERSION = "3.8"
    BUILD_DATE = "2026-07-25"
    
    # ----- 作者信息 -----
    AUTHOR = "杜玛"
    COPYRIGHT = "© 永久 杜玛"
    LICENSE = "MIT"
    
    # ----- 联系方式 -----
    URL = "https://github.com/duma520/IntervalTracker"
    MAINTAINER_EMAIL = "不提供"
    
    # ----- 程序描述 -----
    DESCRIPTION = "图片自由拼接工具 - 支持拖拽、粘贴、缩放、透明度调整、差异比对、历史记录、工具栏自定义"
    
    # ----- 窗口标题格式 -----
    TITLE_FORMAT = "{display_name} v{version}"
    TITLE_FORMAT_WITH_USER = "{display_name} v{version} - 当前用户: {username}"
    
    @classmethod
    def get_full_name(cls) -> str:
        """获取完整的程序名称（带版本）"""
        return f"{cls.NAME} v{cls.VERSION}"
    
    @classmethod
    def get_display_full_name(cls) -> str:
        """获取显示用完整名称（中文名 + 版本）"""
        return f"{cls.DISPLAY_NAME} v{cls.VERSION}"
    
    @classmethod
    def get_window_title(cls, username: str = None) -> str:
        """获取窗口标题"""
        if username:
            return cls.TITLE_FORMAT_WITH_USER.format(
                display_name=cls.DISPLAY_NAME,
                version=cls.VERSION,
                username=username
            )
        return cls.TITLE_FORMAT.format(
            display_name=cls.DISPLAY_NAME,
            version=cls.VERSION
        )
    
    @classmethod
    def get_about_text(cls) -> str:
        """获取关于信息文本（HTML格式）"""
        return f"""
        <h2>{cls.DISPLAY_NAME}</h2>
        <p><b>英文名:</b> {cls.NAME}</p>
        <p><b>版本:</b> {cls.VERSION}</p>
        <p><b>构建日期:</b> {cls.BUILD_DATE}</p>
        <p><b>作者:</b> {cls.AUTHOR}</p>
        <p><b>版权:</b> {cls.COPYRIGHT}</p>
        <p><b>许可证:</b> {cls.LICENSE}</p>
        <p><b>项目主页:</b> <a href='{cls.URL}'>{cls.URL}</a></p>
        <p><b>维护者邮箱:</b> {cls.MAINTAINER_EMAIL}</p>
        <p><b>描述:</b> {cls.DESCRIPTION}</p>
        """
    
    @classmethod
    def get_status_tip(cls) -> str:
        """获取状态栏提示信息"""
        return (
            "提示：Ctrl+V粘贴 | 拖拽文件导入 | 左键拖动图片 | "
            "Ctrl+滚轮缩放视图 | 选中后滚轮缩放图片 | "
            "空格+左键/中键平移 | 右键菜单"
        )
    
    @classmethod
    def get_export_default_filename(cls) -> str:
        """获取导出默认文件名"""
        return f"stitched_image_{time.strftime('%Y%m%d_%H%M%S')}.png"


# ==================== 可移动图片图元 ====================
class MovableImageItem(QGraphicsPixmapItem):
    """可移动、可缩放、可调透明度的图片图元"""
    def __init__(self, pixmap, parent=None, item_id=None):
        super().__init__(pixmap, parent)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self._scale_factor = 1.0
        self._original_pixmap = pixmap
        self._base_size = pixmap.size()
        self._opacity = 1.0
        self._rotation = 0.0
        self._flipped_h = False  # 水平镜像状态
        self._flipped_v = False  # 垂直镜像状态
        self._item_id = item_id or str(uuid.uuid4())[:8]
        self.setAcceptHoverEvents(True)
        self.setOpacity(self._opacity)
        # 设置变换原点为图片中心，用于旋转
        self.setTransformOriginPoint(pixmap.width() / 2, pixmap.height() / 2)

    def item_id(self):
        return self._item_id

    def original_pixmap(self):
        return self._original_pixmap

    def original_size(self):
        return self._base_size

    def scale_factor(self):
        return self._scale_factor

    def opacity_value(self):
        return self._opacity

    def set_opacity_value(self, opacity):
        """设置单张图片透明度 0.0 ~ 1.0"""
        opacity = max(0.0, min(opacity, 1.0))
        self._opacity = opacity
        self.setOpacity(opacity)

    def rotation_value(self):
        """返回当前旋转角度（度数）"""
        return self._rotation

    def set_rotation_deg(self, degrees):
        """设置绝对旋转角度（以中心为锚点）"""
        self._rotation = degrees % 360
        self.setRotation(self._rotation)

    def rotate_by(self, degrees):
        """相对旋转指定度数（正数顺时针，负数逆时针）"""
        self.set_rotation_deg(self._rotation + degrees)

    def reset_rotation(self):
        """重置旋转角度为0"""
        self.set_rotation_deg(0.0)

    def is_flipped_horizontal(self):
        """返回是否水平镜像"""
        return self._flipped_h

    def is_flipped_vertical(self):
        """返回是否垂直镜像"""
        return self._flipped_v

    def flip_horizontal(self):
        """水平镜像翻转（左右翻转，可切换）"""
        self._flipped_h = not self._flipped_h
        self._apply_flip()

    def flip_vertical(self):
        """垂直镜像翻转（上下翻转，可切换）"""
        self._flipped_v = not self._flipped_v
        self._apply_flip()

    def reset_flip(self):
        """重置镜像状态"""
        if self._flipped_h or self._flipped_v:
            self._flipped_h = False
            self._flipped_v = False
            self._apply_flip()

    def _apply_flip(self):
        """应用镜像翻转到当前显示，保持中心位置不变"""
        center = self.sceneBoundingRect().center()
        # 创建变换矩阵进行镜像
        transform = QTransform()
        if self._flipped_h:
            transform.scale(-1, 1)
        if self._flipped_v:
            transform.scale(1, -1)
        # 应用变换到原始图片
        flipped = self._original_pixmap.transformed(transform, Qt.SmoothTransformation)
        # 重新应用当前缩放
        settings = SettingsManager()
        transform_mode = Qt.SmoothTransformation if settings.get("smooth_pixmap", True) else Qt.FastTransformation
        new_size = self._base_size * self._scale_factor
        scaled = flipped.scaled(
            int(new_size.width()), int(new_size.height()),
            Qt.KeepAspectRatio, transform_mode
        )
        self.setPixmap(scaled)
        # 更新变换原点
        self.setTransformOriginPoint(self.pixmap().width() / 2, self.pixmap().height() / 2)
        # 保持中心位置不变
        new_center = self.sceneBoundingRect().center()
        offset = center - new_center
        self.moveBy(offset.x(), offset.y())

    def set_scale_factor(self, factor):
        """设置缩放比例（以中心为锚点）"""
        factor = max(0.05, min(factor, 5.0))
        if factor == self._scale_factor:
            return
        center = self.sceneBoundingRect().center()
        self._scale_factor = factor
        new_size = self._base_size * factor
        settings = SettingsManager()
        transform_mode = Qt.SmoothTransformation if settings.get("smooth_pixmap", True) else Qt.FastTransformation
        scaled = self._original_pixmap.scaled(
            int(new_size.width()), int(new_size.height()),
            Qt.KeepAspectRatio, transform_mode
        )
        self.setPixmap(scaled)
        # 更新变换原点（缩放后尺寸变化）
        self.setTransformOriginPoint(self.pixmap().width() / 2, self.pixmap().height() / 2)
        new_center = self.sceneBoundingRect().center()
        offset = center - new_center
        self.moveBy(offset.x(), offset.y())

    def scale_at(self, factor, scene_pos):
        """以指定场景坐标为锚点缩放"""
        factor = max(0.05, min(self._scale_factor * factor, 5.0)) / self._scale_factor
        if factor == 1.0:
            return
        local_pos = self.mapFromScene(scene_pos)
        rel_x = local_pos.x() / self.pixmap().width() if self.pixmap().width() else 0
        rel_y = local_pos.y() / self.pixmap().height() if self.pixmap().height() else 0
        self._scale_factor *= factor
        new_size = self._base_size * self._scale_factor
        settings = SettingsManager()
        transform_mode = Qt.SmoothTransformation if settings.get("smooth_pixmap", True) else Qt.FastTransformation
        scaled = self._original_pixmap.scaled(
            int(new_size.width()), int(new_size.height()),
            Qt.KeepAspectRatio, transform_mode
        )
        self.setPixmap(scaled)
        # 更新变换原点（缩放后尺寸变化）
        self.setTransformOriginPoint(self.pixmap().width() / 2, self.pixmap().height() / 2)
        new_local_x = rel_x * self.pixmap().width()
        new_local_y = rel_y * self.pixmap().height()
        new_scene = self.mapToScene(QPointF(new_local_x, new_local_y))
        delta = scene_pos - new_scene
        self.moveBy(delta.x(), delta.y())

    def itemChange(self, change, value):
        """选中时更新边框"""
        if change == QGraphicsItem.ItemSelectedHasChanged:
            if self.isSelected():
                self.setZValue(1000)
            else:
                self.setZValue(self.data(0) if self.data(0) is not None else 0)
        return super().itemChange(change, value)

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        if self.isSelected():
            painter.setPen(QPen(QColor(0, 120, 212), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.boundingRect())

    def to_dict(self):
        """序列化状态"""
        return {
            "id": self._item_id,
            "pos": {"x": self.pos().x(), "y": self.pos().y()},
            "scale": self._scale_factor,
            "opacity": self._opacity,
            "rotation": self._rotation,
            "flipped_h": self._flipped_h,
            "flipped_v": self._flipped_v,
            "z": self.zValue(),
        }


# ==================== 差异标记图元 ====================
class DiffMarkerItem(QGraphicsRectItem):
    """差异区域红色半透明标记"""
    def __init__(self, rect, parent=None):
        super().__init__(rect, parent)
        self.setPen(QPen(QColor(255, 0, 0), 2))
        self.setBrush(QBrush(QColor(255, 0, 0, 80)))
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setZValue(9999)


# ==================== 画布视图 ====================
class ImageCanvasView(QGraphicsView):
    """自定义画布视图，处理各种交互"""
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self._settings = SettingsManager()
        self._apply_render_hints()
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self._bg_cache = BackgroundCache()
        self._update_background_brush()
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._panning = False
        self._pan_start = QPointF()
        self._space_pressed = False
        self._main_window = None
        self._min_zoom = 0.05
        self._max_zoom = 10.0
        # 右键菜单防抖：避免菜单关闭后立即触发场景变化导致卡顿
        self._right_menu_closed_at = 0
        self._right_menu_cooldown_ms = 150

    def _apply_render_hints(self):
        """根据性能设置应用渲染提示"""
        hints = QPainter.TextAntialiasing
        if self._settings.get("antialiasing", True):
            hints |= QPainter.Antialiasing
        if self._settings.get("smooth_pixmap", True):
            hints |= QPainter.SmoothPixmapTransform
        self.setRenderHints(hints)

    def _update_background_brush(self):
        """更新背景画刷（使用缓存背景）"""
        # 获取视口大小
        if self.viewport():
            size = self.viewport().size()
        else:
            size = QSize(800, 600)
        
        # 渲染背景
        bg_img = self._bg_cache.get_background(
            self._settings._settings, size.width(), size.height()
        )
        pixmap = QPixmap.fromImage(bg_img)
        self.setBackgroundBrush(QBrush(pixmap))

    def update_background(self):
        """更新背景（外部调用）"""
        self._bg_cache.clear()
        self._update_background_brush()
        self.viewport().update()

    def resizeEvent(self, event):
        """窗口大小变化时更新背景"""
        super().resizeEvent(event)
        self._update_background_brush()

    def apply_settings(self):
        """应用新的设置"""
        self._apply_render_hints()
        self._update_background_brush()
        self.viewport().update()

    def set_main_window(self, mw):
        self._main_window = mw

    def set_space_pressed(self, pressed):
        self._space_pressed = pressed
        if pressed:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.viewport().setCursor(Qt.OpenHandCursor)
        else:
            if not self._panning:
                self.setDragMode(QGraphicsView.NoDrag)
                self.viewport().setCursor(Qt.ArrowCursor)

    def view_scale(self):
        return self.transform().m11()

    def zoom_view(self, factor):
        current = self.view_scale()
        new_scale = current * factor
        if new_scale < self._min_zoom:
            factor = self._min_zoom / current
        elif new_scale > self._max_zoom:
            factor = self._max_zoom / current
        if factor != 1.0:
            self.scale(factor, factor)
        if self._main_window:
            self._main_window.update_view_zoom_status()

    def reset_view_zoom(self):
        self.resetTransform()
        if self._main_window:
            self._main_window.update_view_zoom_status()

    def fit_all_items(self):
        items = [i for i in self.scene().items() if isinstance(i, MovableImageItem)]
        if not items:
            return
        rect = QRectF()
        for item in items:
            rect = rect.united(item.sceneBoundingRect())
        margin = 60
        rect.adjust(-margin, -margin, margin, margin)
        self.fitInView(rect, Qt.KeepAspectRatio)
        if self._main_window:
            self._main_window.update_view_zoom_status()

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton or (
            event.button() == Qt.LeftButton and self._space_pressed
        ):
            self._panning = True
            self._pan_start = event.position()
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.viewport().setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.RightButton:
            item = self.itemAt(event.position().toPoint())
            if isinstance(item, MovableImageItem):
                if not item.isSelected():
                    self.scene().clearSelection()
                    item.setSelected(True)
                self._show_context_menu(event.globalPosition().toPoint(), item)
            else:
                self.scene().clearSelection()
                self._show_context_menu(event.globalPosition().toPoint(), None)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # 右键菜单关闭后的冷却期内，忽略移动事件触发的重绘，避免卡顿
        if self._right_menu_closed_at > 0:
            elapsed = (time.time() - self._right_menu_closed_at) * 1000
            if elapsed < self._right_menu_cooldown_ms:
                # 冷却期内只处理平移，不触发其他更新
                if self._panning:
                    delta = event.position() - self._pan_start
                    self._pan_start = event.position()
                    self.horizontalScrollBar().setValue(
                        self.horizontalScrollBar().value() - delta.x()
                    )
                    self.verticalScrollBar().setValue(
                        self.verticalScrollBar().value() - delta.y()
                    )
                event.accept()
                return
            else:
                self._right_menu_closed_at = 0

        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._panning and (
            event.button() == Qt.MiddleButton or event.button() == Qt.LeftButton
        ):
            self._panning = False
            if self._space_pressed:
                self.viewport().setCursor(Qt.OpenHandCursor)
            else:
                self.setDragMode(QGraphicsView.NoDrag)
                self.viewport().setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
            self.zoom_view(factor)
            event.accept()
            return
        scene_pos = self.mapToScene(event.position().toPoint())
        selected_items = self.scene().selectedItems()
        for item in selected_items:
            if isinstance(item, MovableImageItem):
                factor = 1.1 if event.angleDelta().y() > 0 else 0.9
                item.scale_at(factor, scene_pos)
                if self._main_window:
                    self._main_window.update_status(item)
                    self._main_window.schedule_autosave()
                event.accept()
                return
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.zoom_view(factor)
        event.accept()

    def _show_context_menu(self, global_pos, item):
        menu = QMenu(self)
        if item:
            delete_act = menu.addAction("删除")
            menu.addSeparator()
            zoom_in_act = menu.addAction("放大")
            zoom_out_act = menu.addAction("缩小")
            reset_act = menu.addAction("重置大小")
            menu.addSeparator()
            # 透明度子菜单
            opacity_menu = menu.addMenu("透明度")
            opa_100 = opacity_menu.addAction("100% (不透明)")
            opa_75 = opacity_menu.addAction("75%")
            opa_50 = opacity_menu.addAction("50% (半透明)")
            opa_25 = opacity_menu.addAction("25%")
            opa_10 = opacity_menu.addAction("10%")
            menu.addSeparator()
            # 旋转子菜单
            rotate_menu = menu.addMenu("旋转")
            rot_cw90 = rotate_menu.addAction("顺时针 90°")
            rot_ccw90 = rotate_menu.addAction("逆时针 90°")
            rot_180 = rotate_menu.addAction("旋转 180°")
            rot_cw45 = rotate_menu.addAction("顺时针 45°")
            rot_ccw45 = rotate_menu.addAction("逆时针 45°")
            rot_reset = rotate_menu.addAction("重置 0°")
            menu.addSeparator()
            # 镜像翻转子菜单
            flip_menu = menu.addMenu("镜像翻转")
            flip_h = flip_menu.addAction("水平翻转 (左右)")
            flip_v = flip_menu.addAction("垂直翻转 (上下)")
            flip_reset = flip_menu.addAction("重置翻转")
            menu.addSeparator()
            front_act = menu.addAction("置顶")
            back_act = menu.addAction("置底")
            menu.addSeparator()
        else:
            view_zoom_in_act = menu.addAction("视图放大")
            view_zoom_out_act = menu.addAction("视图缩小")
            view_reset_act = menu.addAction("视图重置 (100%)")
            view_fit_act = menu.addAction("适配全部")
            menu.addSeparator()
            clear_diff_act = menu.addAction("清除差异标记")
            menu.addSeparator()
            # 整体旋转子菜单
            all_rotate_menu = menu.addMenu("整体旋转")
            all_rot_cw90 = all_rotate_menu.addAction("全部顺时针 90°")
            all_rot_ccw90 = all_rotate_menu.addAction("全部逆时针 90°")
            all_rot_180 = all_rotate_menu.addAction("全部旋转 180°")
            all_rot_cw45 = all_rotate_menu.addAction("全部顺时针 45°")
            all_rot_ccw45 = all_rotate_menu.addAction("全部逆时针 45°")
            all_rot_reset = all_rotate_menu.addAction("全部重置 0°")
            menu.addSeparator()
            # 整体镜像翻转子菜单
            all_flip_menu = menu.addMenu("整体镜像翻转")
            all_flip_h = all_flip_menu.addAction("全部水平翻转")
            all_flip_v = all_flip_menu.addAction("全部垂直翻转")
            menu.addSeparator()
        paste_act = menu.addAction("粘贴图片")

        # 记录菜单关闭时间，用于防抖
        action = menu.exec(global_pos)
        self._right_menu_closed_at = time.time()

        if not action:
            return
        if item:
            if action == delete_act:
                self.scene().removeItem(item)
                if self._main_window:
                    self._main_window.update_status(None)
                    self._main_window.schedule_autosave()
            elif action == zoom_in_act:
                item.set_scale_factor(item.scale_factor() * 1.2)
                if self._main_window:
                    self._main_window.update_status(item)
                    self._main_window.schedule_autosave()
            elif action == zoom_out_act:
                item.set_scale_factor(item.scale_factor() * 0.8)
                if self._main_window:
                    self._main_window.update_status(item)
                    self._main_window.schedule_autosave()
            elif action == reset_act:
                item.set_scale_factor(1.0)
                if self._main_window:
                    self._main_window.update_status(item)
                    self._main_window.schedule_autosave()
            elif action == opa_100:
                item.set_opacity_value(1.0)
                if self._main_window:
                    self._main_window.schedule_autosave()
            elif action == opa_75:
                item.set_opacity_value(0.75)
                if self._main_window:
                    self._main_window.schedule_autosave()
            elif action == opa_50:
                item.set_opacity_value(0.5)
                if self._main_window:
                    self._main_window.schedule_autosave()
            elif action == opa_25:
                item.set_opacity_value(0.25)
                if self._main_window:
                    self._main_window.schedule_autosave()
            elif action == opa_10:
                item.set_opacity_value(0.1)
                if self._main_window:
                    self._main_window.schedule_autosave()
            elif action == rot_cw90:
                for it in self.scene().selectedItems():
                    if isinstance(it, MovableImageItem):
                        it.rotate_by(90)
                if self._main_window:
                    self._main_window.update_status(item)
                    self._main_window.schedule_autosave()
            elif action == rot_ccw90:
                for it in self.scene().selectedItems():
                    if isinstance(it, MovableImageItem):
                        it.rotate_by(-90)
                if self._main_window:
                    self._main_window.update_status(item)
                    self._main_window.schedule_autosave()
            elif action == rot_180:
                for it in self.scene().selectedItems():
                    if isinstance(it, MovableImageItem):
                        it.rotate_by(180)
                if self._main_window:
                    self._main_window.update_status(item)
                    self._main_window.schedule_autosave()
            elif action == rot_cw45:
                for it in self.scene().selectedItems():
                    if isinstance(it, MovableImageItem):
                        it.rotate_by(45)
                if self._main_window:
                    self._main_window.update_status(item)
                    self._main_window.schedule_autosave()
            elif action == rot_ccw45:
                for it in self.scene().selectedItems():
                    if isinstance(it, MovableImageItem):
                        it.rotate_by(-45)
                if self._main_window:
                    self._main_window.update_status(item)
                    self._main_window.schedule_autosave()
            elif action == rot_reset:
                for it in self.scene().selectedItems():
                    if isinstance(it, MovableImageItem):
                        it.reset_rotation()
                if self._main_window:
                    self._main_window.update_status(item)
                    self._main_window.schedule_autosave()
            elif action == flip_h:
                for it in self.scene().selectedItems():
                    if isinstance(it, MovableImageItem):
                        it.flip_horizontal()
                if self._main_window:
                    self._main_window.update_status(item)
                    self._main_window.schedule_autosave()
            elif action == flip_v:
                for it in self.scene().selectedItems():
                    if isinstance(it, MovableImageItem):
                        it.flip_vertical()
                if self._main_window:
                    self._main_window.update_status(item)
                    self._main_window.schedule_autosave()
            elif action == flip_reset:
                for it in self.scene().selectedItems():
                    if isinstance(it, MovableImageItem):
                        it.reset_flip()
                if self._main_window:
                    self._main_window.update_status(item)
                    self._main_window.schedule_autosave()
            elif action == front_act:
                max_z = 0
                for it in self.scene().items():
                    if isinstance(it, MovableImageItem) and it != item:
                        max_z = max(max_z, it.zValue())
                item.setZValue(max_z + 1)
                item.setData(0, max_z + 1)
                if self._main_window:
                    self._main_window.schedule_autosave()
            elif action == back_act:
                min_z = 0
                for it in self.scene().items():
                    if isinstance(it, MovableImageItem) and it != item:
                        min_z = min(min_z, it.zValue())
                item.setZValue(min_z - 1)
                item.setData(0, min_z - 1)
                if self._main_window:
                    self._main_window.schedule_autosave()
        else:
            if action == view_zoom_in_act:
                self.zoom_view(1.2)
            elif action == view_zoom_out_act:
                self.zoom_view(1 / 1.2)
            elif action == view_reset_act:
                self.reset_view_zoom()
            elif action == view_fit_act:
                self.fit_all_items()
            elif action == clear_diff_act and self._main_window:
                self._main_window.clear_diff_markers()
            elif action == all_rot_cw90:
                for it in self.scene().items():
                    if isinstance(it, MovableImageItem):
                        it.rotate_by(90)
                if self._main_window:
                    self._main_window.schedule_autosave()
            elif action == all_rot_ccw90:
                for it in self.scene().items():
                    if isinstance(it, MovableImageItem):
                        it.rotate_by(-90)
                if self._main_window:
                    self._main_window.schedule_autosave()
            elif action == all_rot_180:
                for it in self.scene().items():
                    if isinstance(it, MovableImageItem):
                        it.rotate_by(180)
                if self._main_window:
                    self._main_window.schedule_autosave()
            elif action == all_rot_cw45:
                for it in self.scene().items():
                    if isinstance(it, MovableImageItem):
                        it.rotate_by(45)
                if self._main_window:
                    self._main_window.schedule_autosave()
            elif action == all_rot_ccw45:
                for it in self.scene().items():
                    if isinstance(it, MovableImageItem):
                        it.rotate_by(-45)
                if self._main_window:
                    self._main_window.schedule_autosave()
            elif action == all_rot_reset:
                for it in self.scene().items():
                    if isinstance(it, MovableImageItem):
                        it.reset_rotation()
                if self._main_window:
                    self._main_window.schedule_autosave()
            elif action == all_flip_h:
                for it in self.scene().items():
                    if isinstance(it, MovableImageItem):
                        it.flip_horizontal()
                if self._main_window:
                    self._main_window.schedule_autosave()
            elif action == all_flip_v:
                for it in self.scene().items():
                    if isinstance(it, MovableImageItem):
                        it.flip_vertical()
                if self._main_window:
                    self._main_window.schedule_autosave()
        if action == paste_act and self._main_window:
            self._main_window.paste_from_clipboard()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasUrls() and self._main_window:
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path and os.path.isfile(path):
                    scene_pos = self.mapToScene(event.position().toPoint())
                    self._main_window.load_image(path, scene_pos.x(), scene_pos.y())
            event.acceptProposedAction()


# ==================== 历史记录对话框 ====================
class HistoryDialog(QDialog):
    """历史记录管理对话框"""
    def __init__(self, history_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("历史记录")
        self.resize(700, 500)
        self._history_manager = history_manager
        self._selected_id = None
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        # 左侧列表
        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self._on_select)
        splitter.addWidget(self.list_widget)
        # 右侧预览区
        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.preview_label = QLabel("选择一个历史项目查看预览")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(300, 300)
        self.preview_label.setStyleSheet(
            "border: 1px solid #555; background: #2b2b2b; color: #888;"
        )
        right_layout.addWidget(self.preview_label, 1)
        # 信息标签
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #aaa; padding: 5px;")
        right_layout.addWidget(self.info_label)
        # 按钮
        btn_layout = QHBoxLayout()
        self.btn_load = QPushButton("加载编辑")
        self.btn_load.clicked.connect(self._on_load)
        self.btn_load.setEnabled(False)
        self.btn_delete = QPushButton("删除")
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_delete.setEnabled(False)
        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_delete)
        right_layout.addLayout(btn_layout)
        splitter.addWidget(right)
        splitter.setSizes([250, 450])
        layout.addWidget(splitter)
        # 底部关闭按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _refresh_list(self):
        self.list_widget.clear()
        items = self._history_manager.list_history()
        for h in items:
            list_item = QListWidgetItem(h.get("title", "未命名"))
            list_item.setData(Qt.UserRole, h["id"])
            self.list_widget.addItem(list_item)

    def _on_select(self):
        items = self.list_widget.selectedItems()
        if not items:
            self._selected_id = None
            self.btn_load.setEnabled(False)
            self.btn_delete.setEnabled(False)
            self.preview_label.setText("选择一个历史项目查看预览")
            self.preview_label.setPixmap(QPixmap())
            self.info_label.setText("")
            return
        hid = items[0].data(Qt.UserRole)
        self._selected_id = hid
        self.btn_load.setEnabled(True)
        self.btn_delete.setEnabled(True)
        # 加载预览
        info = self._history_manager.get_history_info(hid)
        thumb_path = self._history_manager.get_thumbnail_path(hid)
        if thumb_path and os.path.exists(thumb_path):
            pm = QPixmap(thumb_path)
            self.preview_label.setPixmap(
                pm.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            self.preview_label.setText("无预览图")
            self.preview_label.setPixmap(QPixmap())
        if info:
            t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(info.get("timestamp", 0)))
            count = info.get("image_count", 0)
            self.info_label.setText(f"时间：{t}\n图片数量：{count} 张")

    def _on_load(self):
        if self._selected_id:
            self.accept()

    def _on_delete(self):
        if not self._selected_id:
            return
        reply = QMessageBox.question(
            self, "确认", "确定要删除这条历史记录吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._history_manager.delete_history(self._selected_id)
            self._refresh_list()
            self._selected_id = None
            self.btn_load.setEnabled(False)
            self.btn_delete.setEnabled(False)

    def selected_history_id(self):
        return self._selected_id


# ==================== 自动保存管理器 ====================
class AutoSaveManager:
    """自动保存与恢复"""
    def __init__(self):
        ensure_dirs()
        self.state_file = os.path.join(AUTOSAVE_DIR, "state.json")
        self.images_dir = os.path.join(AUTOSAVE_DIR, "images")

    def save_state(self, items):
        """保存画布状态"""
        state = {
            "version": 1,
            "timestamp": time.time(),
            "images": []
        }
        for item in items:
            if not isinstance(item, MovableImageItem):
                continue
            iid = item.item_id()
            # 保存图片缓存
            img_path = os.path.join(self.images_dir, f"{iid}.png")
            item.original_pixmap().save(img_path, "PNG")
            info = item.to_dict()
            info["image_file"] = f"{iid}.png"
            state["images"].append(info)
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def has_autosave(self):
        return os.path.exists(self.state_file)

    def load_state(self, scene, add_callback):
        """恢复画布状态，返回恢复的图片数量"""
        if not self.has_autosave():
            return 0
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            return 0
        count = 0
        for img_info in state.get("images", []):
            img_file = os.path.join(self.images_dir, img_info.get("image_file", ""))
            if not os.path.exists(img_file):
                continue
            pixmap = QPixmap(img_file)
            if pixmap.isNull():
                continue
            item = MovableImageItem(pixmap, item_id=img_info.get("id"))
            item.set_scale_factor(img_info.get("scale", 1.0))
            item.set_opacity_value(img_info.get("opacity", 1.0))
            z = img_info.get("z", 0)
            item.setZValue(z)
            item.setData(0, z)
            pos = img_info.get("pos", {})
            item.setPos(pos.get("x", 0), pos.get("y", 0))
            rotation = img_info.get("rotation", 0.0)
            item.set_rotation_deg(rotation)
            flipped_h = img_info.get("flipped_h", False)
            flipped_v = img_info.get("flipped_v", False)
            if flipped_h:
                item.flip_horizontal()
            if flipped_v:
                item.flip_vertical()
            scene.addItem(item)
            add_callback(item)
            count += 1
        return count


# ==================== 历史记录管理器 ====================
class HistoryManager:
    """历史记录管理"""
    def __init__(self):
        ensure_dirs()
        self.index_file = os.path.join(HISTORY_DIR, "index.json")
        self.images_dir = os.path.join(HISTORY_DIR, "images")
        self._load_index()

    def _load_index(self):
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    self._index = json.load(f)
            except Exception:
                self._index = []
        else:
            self._index = []

    def _save_index(self):
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self._index, f, ensure_ascii=False, indent=2)

    def save_history(self, items, title=None):
        """保存当前画布为一条历史记录"""
        ensure_dirs()
        settings = SettingsManager()
        max_items = settings.get_max_history()

        hid = str(uuid.uuid4())[:8]
        ts = time.time()
        title = title or time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))
        state_dir = os.path.join(HISTORY_DIR, hid)
        os.makedirs(state_dir, exist_ok=True)
        state = {"version": 1, "timestamp": ts, "images": []}
        # 计算缩略图边界
        all_rect = QRectF()
        movable_items = [i for i in items if isinstance(i, MovableImageItem)]
        for item in movable_items:
            all_rect = all_rect.united(item.sceneBoundingRect())
        for item in movable_items:
            iid = item.item_id()
            img_path = os.path.join(state_dir, f"{iid}.png")
            item.original_pixmap().save(img_path, "PNG")
            info = item.to_dict()
            info["image_file"] = f"{iid}.png"
            state["images"].append(info)
        state_path = os.path.join(state_dir, "state.json")
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        # 生成缩略图
        thumb_path = os.path.join(state_dir, "thumb.png")
        self._render_thumbnail(movable_items, all_rect, thumb_path)
        # 更新索引
        entry = {
            "id": hid,
            "title": title,
            "timestamp": ts,
            "image_count": len(movable_items),
        }
        self._index.insert(0, entry)
        # 限制数量（如果设置了上限）
        if max_items is not None and len(self._index) > max_items:
            old = self._index[max_items:]
            self._index = self._index[:max_items]
            for e in old:
                self._delete_history_dir(e["id"])
        self._save_index()
        return hid

    def _render_thumbnail(self, items, bounds, output_path, max_size=400):
        """渲染缩略图"""
        if not items or bounds.isEmpty():
            return
        margin = 20
        w = bounds.width() + margin * 2
        h = bounds.height() + margin * 2
        # 缩放
        scale = min(max_size / w, max_size / h, 1.0)
        tw = int(w * scale)
        th = int(h * scale)
        img = QImage(tw, th, QImage.Format_ARGB32)
        settings = SettingsManager()
        # 使用背景颜色填充
        bg_color = settings.get_background_color()
        img.fill(bg_color)
        painter = QPainter(img)
        if settings.get("antialiasing", True):
            painter.setRenderHint(QPainter.Antialiasing)
        if settings.get("smooth_pixmap", True):
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.scale(scale, scale)
        sorted_items = sorted(items, key=lambda x: x.zValue())
        for item in sorted_items:
            rect = item.sceneBoundingRect()
            cx = rect.center().x() - bounds.left() + margin
            cy = rect.center().y() - bounds.top() + margin
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(item.rotation_value())
            painter.setOpacity(item.opacity_value())
            pw = item.pixmap().width()
            ph = item.pixmap().height()
            painter.drawPixmap(QPointF(-pw/2, -ph/2), item.pixmap())
            painter.restore()
        painter.end()
        img.save(output_path, "PNG")

    def list_history(self):
        return list(self._index)

    def get_history_info(self, hid):
        for e in self._index:
            if e["id"] == hid:
                return e
        return None

    def get_thumbnail_path(self, hid):
        return os.path.join(HISTORY_DIR, hid, "thumb.png")

    def get_state_path(self, hid):
        return os.path.join(HISTORY_DIR, hid, "state.json")

    def get_state_dir(self, hid):
        return os.path.join(HISTORY_DIR, hid)

    def load_history(self, hid, scene, add_callback):
        """加载历史记录到画布，返回图片数量"""
        state_path = self.get_state_path(hid)
        state_dir = self.get_state_dir(hid)
        if not os.path.exists(state_path):
            return 0
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            return 0
        count = 0
        for img_info in state.get("images", []):
            img_file = os.path.join(state_dir, img_info.get("image_file", ""))
            if not os.path.exists(img_file):
                continue
            pixmap = QPixmap(img_file)
            if pixmap.isNull():
                continue
            item = MovableImageItem(pixmap, item_id=img_info.get("id"))
            item.set_scale_factor(img_info.get("scale", 1.0))
            item.set_opacity_value(img_info.get("opacity", 1.0))
            z = img_info.get("z", 0)
            item.setZValue(z)
            item.setData(0, z)
            pos = img_info.get("pos", {})
            item.setPos(pos.get("x", 0), pos.get("y", 0))
            rotation = img_info.get("rotation", 0.0)
            item.set_rotation_deg(rotation)
            flipped_h = img_info.get("flipped_h", False)
            flipped_v = img_info.get("flipped_v", False)
            if flipped_h:
                item.flip_horizontal()
            if flipped_v:
                item.flip_vertical()
            scene.addItem(item)
            add_callback(item)
            count += 1
        return count

    def _delete_history_dir(self, hid):
        import shutil
        d = os.path.join(HISTORY_DIR, hid)
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)

    def delete_history(self, hid):
        self._index = [e for e in self._index if e["id"] != hid]
        self._save_index()
        self._delete_history_dir(hid)


# ==================== 主窗口 ====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._settings = SettingsManager()
        # 使用 ProjectInfo 统一设置窗口标题
        self.setWindowTitle(ProjectInfo.get_window_title())
        self.resize(1200, 800)
        self._set_app_icon()
        # 管理器
        self._autosave_mgr = AutoSaveManager()
        self._history_mgr = HistoryManager()
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._do_autosave)
        # 差异标记列表
        self._diff_markers = []
        # 场景和视图
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(-5000, -5000, 10000, 10000)
        self.view = ImageCanvasView(self.scene, self)
        self.view.set_main_window(self)
        self.setCentralWidget(self.view)
        # 保存所有工具栏控件的引用
        self._toolbar_widgets = {}
        self._toolbar_actions = {}  # 存储 QAction 引用
        self._build_toolbar()
        self._build_statusbar()
        self._z_counter = 0
        self._global_opacity = 1.0
        # 使用 QTimer 延迟应用工具栏可见性，确保所有控件都已初始化
        QTimer.singleShot(50, self.apply_toolbar_visibility)
        # 尝试恢复自动保存
        self._try_restore_autosave()
        # 监听场景变化以触发自动保存
        self.scene.changed.connect(self._on_scene_changed)

    def _set_app_icon(self):
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            self.setWindowIcon(icon)
            QApplication.setWindowIcon(icon)
        else:
            for ext in [".png", ".jpg", ".jpeg", ".bmp"]:
                alt_path = os.path.join(os.path.dirname(__file__), f"icon{ext}")
                if os.path.exists(alt_path):
                    icon = QIcon(alt_path)
                    self.setWindowIcon(icon)
                    QApplication.setWindowIcon(icon)
                    break

    def _build_toolbar(self):
        """构建自适应工具栏 - 分组布局，适配各种分辨率"""
        self._toolbar = QToolBar("工具栏", self)
        self._toolbar.setMovable(False)
        self._toolbar.setAllowedAreas(Qt.TopToolBarArea)
        self._toolbar.setStyleSheet("""
            QToolBar { spacing: 2px; padding: 2px; }
            QPushButton { 
                padding: 4px 8px; 
                min-height: 24px;
                font-size: 12px;
            }
            QLabel { font-size: 12px; }
        """)
        self.addToolBar(self._toolbar)

        # 使用字典存储所有控件，方便按名称显示/隐藏
        widgets = {}
        actions = {}

        # === 第一组：文件操作 ===
        btn_import = QPushButton("导入")
        btn_import.setToolTip("导入图片文件")
        btn_import.clicked.connect(self.import_images)
        act_import = self._toolbar.addWidget(btn_import)
        actions["btn_import"] = act_import
        widgets["btn_import"] = btn_import

        btn_paste = QPushButton("粘贴")
        btn_paste.setToolTip("从剪贴板粘贴图片 (Ctrl+V)")
        btn_paste.clicked.connect(self.paste_from_clipboard)
        act_paste = self._toolbar.addWidget(btn_paste)
        actions["btn_paste"] = act_paste
        widgets["btn_paste"] = btn_paste

        btn_del = QPushButton("删除")
        btn_del.setToolTip("删除选中图片 (Del)")
        btn_del.clicked.connect(self.delete_selected)
        act_del = self._toolbar.addWidget(btn_del)
        actions["btn_del"] = act_del
        widgets["btn_del"] = btn_del

        sep1 = self._toolbar.addSeparator()
        actions["sep1"] = sep1

        # === 第二组：图片缩放 ===
        btn_zoom_in = QPushButton("放大+")
        btn_zoom_in.setToolTip("选中图片放大")
        btn_zoom_in.clicked.connect(lambda: self.scale_selected(1.2))
        act_zoom_in = self._toolbar.addWidget(btn_zoom_in)
        actions["btn_zoom_in"] = act_zoom_in
        widgets["btn_zoom_in"] = btn_zoom_in

        btn_zoom_out = QPushButton("缩小-")
        btn_zoom_out.setToolTip("选中图片缩小")
        btn_zoom_out.clicked.connect(lambda: self.scale_selected(0.8))
        act_zoom_out = self._toolbar.addWidget(btn_zoom_out)
        actions["btn_zoom_out"] = act_zoom_out
        widgets["btn_zoom_out"] = btn_zoom_out

        btn_reset = QPushButton("重置")
        btn_reset.setToolTip("重置选中图片大小")
        btn_reset.clicked.connect(self.reset_scale_selected)
        act_reset = self._toolbar.addWidget(btn_reset)
        actions["btn_reset"] = act_reset
        widgets["btn_reset"] = btn_reset

        sep2 = self._toolbar.addSeparator()
        actions["sep2"] = sep2

        # === 新增组：图片旋转 ===
        btn_rot_left = QPushButton("↺左旋")
        btn_rot_left.setToolTip("选中图片逆时针旋转90°")
        btn_rot_left.clicked.connect(lambda: self.rotate_selected(-90))
        act_rot_left = self._toolbar.addWidget(btn_rot_left)
        actions["btn_rot_left"] = act_rot_left
        widgets["btn_rot_left"] = btn_rot_left

        btn_rot_right = QPushButton("↻右旋")
        btn_rot_right.setToolTip("选中图片顺时针旋转90°")
        btn_rot_right.clicked.connect(lambda: self.rotate_selected(90))
        act_rot_right = self._toolbar.addWidget(btn_rot_right)
        actions["btn_rot_right"] = act_rot_right
        widgets["btn_rot_right"] = btn_rot_right

        sep3 = self._toolbar.addSeparator()
        actions["sep3"] = sep3

        # === 新增组：镜像翻转 ===
        btn_flip_h = QPushButton("⇆水平镜像")
        btn_flip_h.setToolTip("选中图片水平镜像翻转（左右翻转）")
        btn_flip_h.clicked.connect(lambda: self.flip_selected_horizontal())
        act_flip_h = self._toolbar.addWidget(btn_flip_h)
        actions["btn_flip_h"] = act_flip_h
        widgets["btn_flip_h"] = btn_flip_h

        btn_flip_v = QPushButton("⇅垂直镜像")
        btn_flip_v.setToolTip("选中图片垂直镜像翻转（上下翻转）")
        btn_flip_v.clicked.connect(lambda: self.flip_selected_vertical())
        act_flip_v = self._toolbar.addWidget(btn_flip_v)
        actions["btn_flip_v"] = act_flip_v
        widgets["btn_flip_v"] = btn_flip_v

        sep4 = self._toolbar.addSeparator()
        actions["sep4"] = sep4

        # === 第三组：视图缩放 ===
        btn_view_in = QPushButton("视图+")
        btn_view_in.setToolTip("放大视图")
        btn_view_in.clicked.connect(lambda: self.view.zoom_view(1.2))
        act_view_in = self._toolbar.addWidget(btn_view_in)
        actions["btn_view_in"] = act_view_in
        widgets["btn_view_in"] = btn_view_in

        btn_view_out = QPushButton("视图-")
        btn_view_out.setToolTip("缩小视图")
        btn_view_out.clicked.connect(lambda: self.view.zoom_view(1 / 1.2))
        act_view_out = self._toolbar.addWidget(btn_view_out)
        actions["btn_view_out"] = act_view_out
        widgets["btn_view_out"] = btn_view_out

        btn_view_fit = QPushButton("适配")
        btn_view_fit.setToolTip("适配全部图片")
        btn_view_fit.clicked.connect(self.view.fit_all_items)
        act_view_fit = self._toolbar.addWidget(btn_view_fit)
        actions["btn_view_fit"] = act_view_fit
        widgets["btn_view_fit"] = btn_view_fit

        sep5 = self._toolbar.addSeparator()
        actions["sep5"] = sep5

        # === 第四组：图层 ===
        btn_front = QPushButton("置顶")
        btn_front.setToolTip("将选中图片置顶")
        btn_front.clicked.connect(self.bring_to_front)
        act_front = self._toolbar.addWidget(btn_front)
        actions["btn_front"] = act_front
        widgets["btn_front"] = btn_front

        btn_back = QPushButton("置底")
        btn_back.setToolTip("将选中图片置底")
        btn_back.clicked.connect(self.send_to_back)
        act_back = self._toolbar.addWidget(btn_back)
        actions["btn_back"] = act_back
        widgets["btn_back"] = btn_back

        sep6 = self._toolbar.addSeparator()
        actions["sep6"] = sep6

        # === 第五组：透明度（紧凑布局） ===
        lbl_item = QLabel("单图:")
        act_lbl_item = self._toolbar.addWidget(lbl_item)
        actions["lbl_item"] = act_lbl_item
        widgets["lbl_item"] = lbl_item

        sld_item_opacity = QSlider(Qt.Horizontal)
        sld_item_opacity.setRange(0, 100)
        sld_item_opacity.setValue(100)
        sld_item_opacity.setFixedWidth(60)
        sld_item_opacity.setToolTip("选中图片的透明度")
        sld_item_opacity.valueChanged.connect(self._on_item_opacity_slider)
        act_sld_item = self._toolbar.addWidget(sld_item_opacity)
        actions["sld_item_opacity"] = act_sld_item
        widgets["sld_item_opacity"] = sld_item_opacity
        # 保存引用供其他地方使用
        self.sld_item_opacity = sld_item_opacity

        lbl_item_opacity = QLabel("100%")
        lbl_item_opacity.setFixedWidth(35)
        lbl_item_opacity.setStyleSheet("color: #888;")
        act_lbl_item_opacity = self._toolbar.addWidget(lbl_item_opacity)
        actions["lbl_item_opacity"] = act_lbl_item_opacity
        widgets["lbl_item_opacity"] = lbl_item_opacity
        self.lbl_item_opacity = lbl_item_opacity

        sep7 = self._toolbar.addSeparator()
        actions["sep7"] = sep7

        lbl_global = QLabel("整体:")
        act_lbl_global = self._toolbar.addWidget(lbl_global)
        actions["lbl_global"] = act_lbl_global
        widgets["lbl_global"] = lbl_global

        sld_global_opacity = QSlider(Qt.Horizontal)
        sld_global_opacity.setRange(0, 100)
        sld_global_opacity.setValue(100)
        sld_global_opacity.setFixedWidth(60)
        sld_global_opacity.setToolTip("所有图片整体透明度")
        sld_global_opacity.valueChanged.connect(self._on_global_opacity_slider)
        act_sld_global = self._toolbar.addWidget(sld_global_opacity)
        actions["sld_global_opacity"] = act_sld_global
        widgets["sld_global_opacity"] = sld_global_opacity
        self.sld_global_opacity = sld_global_opacity

        lbl_global_opacity = QLabel("100%")
        lbl_global_opacity.setFixedWidth(35)
        lbl_global_opacity.setStyleSheet("color: #888;")
        act_lbl_global_opacity = self._toolbar.addWidget(lbl_global_opacity)
        actions["lbl_global_opacity"] = act_lbl_global_opacity
        widgets["lbl_global_opacity"] = lbl_global_opacity
        self.lbl_global_opacity = lbl_global_opacity

        sep8 = self._toolbar.addSeparator()
        actions["sep8"] = sep8

        # === 第六组：差异比对 ===
        btn_diff = QPushButton("比对差异")
        btn_diff.setToolTip("选中两张高度相似的图片，比对并标记差异区域（红色）")
        btn_diff.clicked.connect(self.compare_diff)
        act_diff = self._toolbar.addWidget(btn_diff)
        actions["btn_diff"] = act_diff
        widgets["btn_diff"] = btn_diff

        btn_clear_diff = QPushButton("清标记")
        btn_clear_diff.setToolTip("清除所有差异红色标记")
        btn_clear_diff.clicked.connect(self.clear_diff_markers)
        act_clear_diff = self._toolbar.addWidget(btn_clear_diff)
        actions["btn_clear_diff"] = act_clear_diff
        widgets["btn_clear_diff"] = btn_clear_diff

        sep9 = self._toolbar.addSeparator()
        actions["sep9"] = sep9

        # === 第七组：历史记录 ===
        btn_save_hist = QPushButton("存历史")
        btn_save_hist.setToolTip("保存当前画面到历史记录")
        btn_save_hist.clicked.connect(self.save_to_history)
        act_save_hist = self._toolbar.addWidget(btn_save_hist)
        actions["btn_save_hist"] = act_save_hist
        widgets["btn_save_hist"] = btn_save_hist

        btn_history = QPushButton("历史")
        btn_history.setToolTip("打开历史记录管理器")
        btn_history.clicked.connect(self.show_history)
        act_history = self._toolbar.addWidget(btn_history)
        actions["btn_history"] = act_history
        widgets["btn_history"] = btn_history

        sep10 = self._toolbar.addSeparator()
        actions["sep10"] = sep10

        # === 第八组：导出和设置 ===
        btn_export = QPushButton("导出")
        btn_export.setToolTip("导出拼接后的大图")
        btn_export.clicked.connect(self.export_canvas)
        act_export = self._toolbar.addWidget(btn_export)
        actions["btn_export"] = act_export
        widgets["btn_export"] = btn_export

        btn_clear = QPushButton("清空")
        btn_clear.setToolTip("清空画布上所有图片")
        btn_clear.clicked.connect(self.clear_canvas)
        act_clear = self._toolbar.addWidget(btn_clear)
        actions["btn_clear"] = act_clear
        widgets["btn_clear"] = btn_clear

        sep11 = self._toolbar.addSeparator()
        actions["sep11"] = sep11

        btn_settings = QPushButton("设置")
        btn_settings.setToolTip("打开选项设置")
        btn_settings.clicked.connect(self.show_settings)
        act_settings = self._toolbar.addWidget(btn_settings)
        actions["btn_settings"] = act_settings
        widgets["btn_settings"] = btn_settings

        # 保存所有控件引用
        self._toolbar_widgets = widgets
        self._toolbar_actions = actions

    def apply_toolbar_visibility(self):
        """应用工具栏可见性设置 - 使用 QAction 的 setVisible"""
        visibility = self._settings.get_toolbar_visibility()
        
        # 定义每个控件名称对应的可见性键
        widget_keys = {
            "btn_import": "btn_import",
            "btn_paste": "btn_paste",
            "btn_del": "btn_del",
            "btn_zoom_in": "btn_zoom_in",
            "btn_zoom_out": "btn_zoom_out",
            "btn_reset": "btn_reset",
            "btn_rot_left": "btn_rot_left",
            "btn_rot_right": "btn_rot_right",
            "btn_flip_h": "btn_flip_h",
            "btn_flip_v": "btn_flip_v",
            "btn_view_in": "btn_view_in",
            "btn_view_out": "btn_view_out",
            "btn_view_fit": "btn_view_fit",
            "btn_front": "btn_front",
            "btn_back": "btn_back",
            "lbl_item": "item_opacity",
            "sld_item_opacity": "item_opacity",
            "lbl_item_opacity": "item_opacity",
            "lbl_global": "global_opacity",
            "sld_global_opacity": "global_opacity",
            "lbl_global_opacity": "global_opacity",
            "btn_diff": "btn_diff",
            "btn_clear_diff": "btn_clear_diff",
            "btn_save_hist": "btn_save_hist",
            "btn_history": "btn_history",
            "btn_export": "btn_export",
            "btn_clear": "btn_clear",
            "btn_settings": "btn_settings",
        }
        
        # 分隔符列表
        sep_keys = ["sep1", "sep2", "sep3", "sep4", "sep5", "sep6", "sep7", "sep8", "sep9", "sep10", "sep11"]
        
        # 第一步：通过 QAction 设置所有控件的可见性
        for action_name, action in self._toolbar_actions.items():
            if action_name in widget_keys:
                key = widget_keys[action_name]
                visible = visibility.get(key, True)
                action.setVisible(visible)
            elif action_name in sep_keys:
                # 分隔符默认可见，稍后根据上下文调整
                action.setVisible(True)
        
        # 第二步：收集所有控件的可见性状态
        items_info = []
        for name in self._toolbar_actions.keys():
            action = self._toolbar_actions[name]
            is_sep = name in sep_keys
            if is_sep:
                items_info.append({"name": name, "type": "separator", "action": action})
            else:
                if name in widget_keys:
                    key = widget_keys[name]
                    visible = visibility.get(key, True)
                else:
                    visible = action.isVisible()
                items_info.append({"name": name, "type": "widget", "action": action, "visible": visible})
        
        # 第三步：重新计算分隔符的可见性
        for i, info in enumerate(items_info):
            if info["type"] == "separator":
                # 查找前一个可见的控件
                prev_visible = False
                for j in range(i - 1, -1, -1):
                    if items_info[j]["type"] == "widget":
                        prev_visible = items_info[j]["visible"]
                        break
                
                # 查找后一个可见的控件
                next_visible = False
                for j in range(i + 1, len(items_info)):
                    if items_info[j]["type"] == "widget":
                        next_visible = items_info[j]["visible"]
                        break
                
                # 只有前后都有可见控件时，分隔符才可见
                sep_visible = prev_visible and next_visible
                info["action"].setVisible(sep_visible)
        
        # 强制更新工具栏 - 使用 QTimer 延迟确保 UI 刷新
        self._toolbar.update()
        self._toolbar.repaint()
        # 强制主窗口更新
        self.update()

    def _build_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel(ProjectInfo.get_status_tip())
        self.status_bar.addWidget(self.status_label, 1)
        self.view_zoom_label = QLabel("视图: 100%")
        self.view_zoom_label.setStyleSheet("padding: 0 10px; color: #888;")
        self.status_bar.addPermanentWidget(self.view_zoom_label)

    def update_view_zoom_status(self):
        zoom = self.view.view_scale()
        self.view_zoom_label.setText(f"视图: {zoom:.0%}")

    def update_status(self, item):
        if isinstance(item, MovableImageItem):
            pos = item.pos()
            size = item.original_size()
            self.status_label.setText(
                f"已选中 - 位置:({int(pos.x())},{int(pos.y())})  "
                f"缩放:{item.scale_factor():.0%}  "
                f"旋转:{item.rotation_value():.0f}°  "
                f"透明:{item.opacity_value():.0%}  "
                f"原始:{size.width()}x{size.height()}"
            )
            # 同步滑块
            self.sld_item_opacity.blockSignals(True)
            self.sld_item_opacity.setValue(int(item.opacity_value() * 100))
            self.sld_item_opacity.blockSignals(False)
            self.lbl_item_opacity.setText(f"{int(item.opacity_value() * 100)}%")
        else:
            self.status_label.setText(ProjectInfo.get_status_tip())

    # ==================== 设置相关 ====================
    def show_settings(self):
        """打开设置对话框"""
        dlg = SettingsDialog(self)
        dlg.exec()

    def apply_settings(self):
        """应用新的设置到界面"""
        # 更新自动保存定时器间隔
        self._autosave_timer.setInterval(self._settings.get_autosave_delay())
        # 更新视图（背景、渲染质量）
        self.view.apply_settings()

    # ==================== 透明度 ====================
    def _on_item_opacity_slider(self, value):
        self.lbl_item_opacity.setText(f"{value}%")
        opacity = value / 100.0
        for item in self.scene.selectedItems():
            if isinstance(item, MovableImageItem):
                item.set_opacity_value(opacity)
        self.schedule_autosave()

    def _on_global_opacity_slider(self, value):
        self.lbl_global_opacity.setText(f"{value}%")
        self._global_opacity = value / 100.0
        # 整体透明度 = 基础值 * 全局系数
        for item in self.scene.items():
            if isinstance(item, MovableImageItem):
                item.setOpacity(item._opacity * self._global_opacity)

    # ==================== 图片加载 ====================
    def load_image(self, filepath, x=None, y=None):
        pixmap = QPixmap(filepath)
        if pixmap.isNull():
            return None
        return self._add_pixmap(pixmap, x, y)

    def _add_pixmap(self, pixmap, x=None, y=None):
        item = MovableImageItem(pixmap)
        self._z_counter += 1
        item.setZValue(self._z_counter)
        item.setData(0, self._z_counter)
        if x is not None and y is not None:
            item.setPos(x, y)
        else:
            center = self.view.mapToScene(self.view.viewport().rect().center())
            item.setPos(
                center.x() - pixmap.width() / 2 + len(self.scene.items()) * 10,
                center.y() - pixmap.height() / 2 + len(self.scene.items()) * 10
            )
        # 应用全局透明度
        item.setOpacity(item._opacity * self._global_opacity)
        self.scene.addItem(item)
        self.scene.clearSelection()
        item.setSelected(True)
        self.update_status(item)
        self.schedule_autosave()
        return item

    def _on_item_added(self, item):
        """供管理器加载时回调"""
        if isinstance(item, MovableImageItem):
            z = item.zValue()
            if z > self._z_counter:
                self._z_counter = int(z)
            item.setData(0, z)

    def import_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff);;所有文件 (*.*)"
        )
        for f in files:
            self.load_image(f)

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()
        if mime.hasImage():
            image = clipboard.image()
            pixmap = QPixmap.fromImage(image)
            if not pixmap.isNull():
                self._add_pixmap(pixmap)
                return
        QMessageBox.information(self, "提示", "剪贴板中没有图片，请先截图或复制图片后再粘贴。")

    def delete_selected(self):
        for item in self.scene.selectedItems():
            if isinstance(item, MovableImageItem):
                self.scene.removeItem(item)
        self.update_status(None)
        self.schedule_autosave()

    def scale_selected(self, factor):
        for item in self.scene.selectedItems():
            if isinstance(item, MovableImageItem):
                item.set_scale_factor(item.scale_factor() * factor)
                self.update_status(item)
        self.schedule_autosave()

    def reset_scale_selected(self):
        for item in self.scene.selectedItems():
            if isinstance(item, MovableImageItem):
                item.set_scale_factor(1.0)
                self.update_status(item)
        self.schedule_autosave()

    def rotate_selected(self, degrees):
        """旋转选中的图片"""
        for item in self.scene.selectedItems():
            if isinstance(item, MovableImageItem):
                item.rotate_by(degrees)
                self.update_status(item)
        self.schedule_autosave()

    def rotate_all(self, degrees):
        """旋转所有图片（整体旋转）"""
        for item in self.scene.items():
            if isinstance(item, MovableImageItem):
                item.rotate_by(degrees)
        self.schedule_autosave()

    def flip_selected_horizontal(self):
        """选中图片水平镜像翻转"""
        for item in self.scene.selectedItems():
            if isinstance(item, MovableImageItem):
                item.flip_horizontal()
                self.update_status(item)
        self.schedule_autosave()

    def flip_selected_vertical(self):
        """选中图片垂直镜像翻转"""
        for item in self.scene.selectedItems():
            if isinstance(item, MovableImageItem):
                item.flip_vertical()
                self.update_status(item)
        self.schedule_autosave()

    def flip_all_horizontal(self):
        """所有图片水平镜像翻转"""
        for item in self.scene.items():
            if isinstance(item, MovableImageItem):
                item.flip_horizontal()
        self.schedule_autosave()

    def flip_all_vertical(self):
        """所有图片垂直镜像翻转"""
        for item in self.scene.items():
            if isinstance(item, MovableImageItem):
                item.flip_vertical()
        self.schedule_autosave()

    def bring_to_front(self):
        items = [i for i in self.scene.selectedItems() if isinstance(i, MovableImageItem)]
        if not items:
            return
        max_z = 0
        for it in self.scene.items():
            if isinstance(it, MovableImageItem):
                max_z = max(max_z, it.zValue())
        for i, item in enumerate(items):
            item.setZValue(max_z + 1 + i)
            item.setData(0, max_z + 1 + i)
        self.schedule_autosave()

    def send_to_back(self):
        items = [i for i in self.scene.selectedItems() if isinstance(i, MovableImageItem)]
        if not items:
            return
        min_z = 0
        for it in self.scene.items():
            if isinstance(it, MovableImageItem):
                min_z = min(min_z, it.zValue())
        for i, item in enumerate(reversed(items)):
            item.setZValue(min_z - 1 - i)
            item.setData(0, min_z - 1 - i)
        self.schedule_autosave()

    def clear_canvas(self):
        items = [i for i in self.scene.items() if isinstance(i, MovableImageItem)]
        if not items:
            return
        reply = QMessageBox.question(
            self, "确认", "确定要清空所有图片吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            for item in items:
                self.scene.removeItem(item)
            self.clear_diff_markers()
            self.update_status(None)
            self.schedule_autosave()

    # ==================== 差异比对 ====================
    def compare_diff(self):
        """比对选中的两张图片差异，用红色矩形标记"""
        selected = [i for i in self.scene.selectedItems() if isinstance(i, MovableImageItem)]
        if len(selected) < 2:
            QMessageBox.information(
                self, "提示",
                "请先选中两张（或多张）高度相似的图片，再点击比对差异。\n"
                "按住 Ctrl 点击可多选。"
            )
            return
        # 清除旧标记
        self.clear_diff_markers()
        base_item = selected[0]
        base_img = base_item.original_pixmap().toImage().convertToFormat(QImage.Format_RGB32)
        total_diff_regions = 0
        for other_item in selected[1:]:
            other_img = other_item.original_pixmap().toImage().convertToFormat(QImage.Format_RGB32)
            # 缩放到相同尺寸比较（以基准图尺寸为准）
            if base_img.size() != other_img.size():
                other_img = other_img.scaled(
                    base_img.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            # 逐像素比较，生成差异掩码
            w = min(base_img.width(), other_img.width())
            h = min(base_img.height(), other_img.height())
            threshold = 30  # 颜色差异阈值
            # 找出差异像素的边界框（分块检测，减少标记数量）
            block_size = 8
            diff_blocks = []
            for by in range(0, h, block_size):
                for bx in range(0, w, block_size):
                    has_diff = False
                    for py in range(by, min(by + block_size, h)):
                        if has_diff:
                            break
                        for px in range(bx, min(bx + block_size, w)):
                            c1 = base_img.pixelColor(px, py)
                            c2 = other_img.pixelColor(px, py)
                            dr = abs(c1.red() - c2.red())
                            dg = abs(c1.green() - c2.green())
                            db = abs(c1.blue() - c2.blue())
                            if dr + dg + db > threshold:
                                has_diff = True
                                break
                    if has_diff:
                        diff_blocks.append((bx, by))
            if not diff_blocks:
                continue
            # 合并邻近的差异块为大矩形（简单的聚类：按行合并）
            regions = self._merge_diff_blocks(diff_blocks, block_size, w, h)
            # 将差异区域映射到场景坐标（基于 other_item 的位置和缩放）
            scale = other_item.scale_factor()
            pos = other_item.pos()
            base_w = other_item.original_size().width()
            base_h = other_item.original_size().height()
            # 计算缩放系数
            sx = scale * other_item.pixmap().width() / base_w if base_w else 1
            sy = scale * other_item.pixmap().height() / base_h if base_h else 1
            for (rx, ry, rw, rh) in regions:
                scene_rect = QRectF(
                    pos.x() + rx * sx,
                    pos.y() + ry * sy,
                    rw * sx,
                    rh * sy
                )
                marker = DiffMarkerItem(scene_rect)
                self.scene.addItem(marker)
                self._diff_markers.append(marker)
                total_diff_regions += 1
        if total_diff_regions == 0:
            QMessageBox.information(self, "比对结果", "未检测到明显差异，两张图片几乎完全相同。")
        else:
            QMessageBox.information(
                self, "比对完成",
                f"检测到 {total_diff_regions} 处差异区域，已用红色半透明框标记。\n"
                f"可点击「清除标记」按钮移除标记。"
            )

    def _merge_diff_blocks(self, blocks, block_size, w, h):
        """将分散的差异块合并为较大的矩形区域（连通区域检测简化版）"""
        if not blocks:
            return []
        # 构建网格
        cols = (w + block_size - 1) // block_size
        rows = (h + block_size - 1) // block_size
        grid = [[False] * cols for _ in range(rows)]
        for bx, by in blocks:
            cx = bx // block_size
            cy = by // block_size
            if 0 <= cy < rows and 0 <= cx < cols:
                grid[cy][cx] = True
        visited = [[False] * cols for _ in range(rows)]
        regions = []
        for y in range(rows):
            for x in range(cols):
                if grid[y][x] and not visited[y][x]:
                    # BFS
                    stack = [(x, y)]
                    visited[y][x] = True
                    min_x = max_x = x
                    min_y = max_y = y
                    while stack:
                        cx, cy = stack.pop()
                        min_x = min(min_x, cx)
                        max_x = max(max_x, cx)
                        min_y = min(min_y, cy)
                        max_y = max(max_y, cy)
                        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nx, ny = cx + dx, cy + dy
                            if (0 <= nx < cols and 0 <= ny < rows
                                    and grid[ny][nx] and not visited[ny][nx]):
                                visited[ny][nx] = True
                                stack.append((nx, ny))
                    rx = min_x * block_size
                    ry = min_y * block_size
                    rw = (max_x - min_x + 1) * block_size
                    rh = (max_y - min_y + 1) * block_size
                    regions.append((rx, ry, rw, rh))
        return regions

    def clear_diff_markers(self):
        """清除所有差异标记"""
        for marker in self._diff_markers:
            self.scene.removeItem(marker)
        self._diff_markers = []

    # ==================== 自动保存 ====================
    def schedule_autosave(self):
        """调度自动保存（防抖）"""
        self._autosave_timer.start(self._settings.get_autosave_delay())

    def _on_scene_changed(self, rects):
        """场景变化时触发自动保存（主要捕获拖动）"""
        # 只在有图片被选中拖动时保存
        selected = self.scene.selectedItems()
        if any(isinstance(i, MovableImageItem) for i in selected):
            self.schedule_autosave()

    def _do_autosave(self):
        """执行自动保存"""
        items = [i for i in self.scene.items() if isinstance(i, MovableImageItem)]
        try:
            self._autosave_mgr.save_state(items)
        except Exception:
            pass

    def _try_restore_autosave(self):
        """启动时尝试恢复上次画面"""
        if not self._autosave_mgr.has_autosave():
            return
        count = self._autosave_mgr.load_state(self.scene, self._on_item_added)
        if count > 0:
            self.status_label.setText(f"已自动恢复上次画面，共 {count} 张图片")
            # 适配视图
            QTimer.singleShot(100, self.view.fit_all_items)

    # ==================== 历史记录 ====================
    def save_to_history(self):
        items = [i for i in self.scene.items() if isinstance(i, MovableImageItem)]
        if not items:
            QMessageBox.information(self, "提示", "画布上没有图片，无法保存到历史记录。")
            return
        hid = self._history_mgr.save_history(items)
        QMessageBox.information(self, "已保存", "当前画面已保存到历史记录。")

    def show_history(self):
        dlg = HistoryDialog(self._history_mgr, self)
        if dlg.exec() == QDialog.Accepted:
            hid = dlg.selected_history_id()
            if hid:
                self._load_history(hid)

    def _load_history(self, hid):
        """加载指定历史记录"""
        # 先清空
        for item in list(self.scene.items()):
            if isinstance(item, MovableImageItem) or isinstance(item, DiffMarkerItem):
                self.scene.removeItem(item)
        self._diff_markers = []
        count = self._history_mgr.load_history(hid, self.scene, self._on_item_added)
        self.clear_diff_markers()
        if count > 0:
            self.status_label.setText(f"已加载历史记录，共 {count} 张图片")
            self.view.fit_all_items()
            self.schedule_autosave()
        else:
            QMessageBox.warning(self, "失败", "加载历史记录失败。")

    # ==================== 导出 ====================
    def export_canvas(self):
        items = [i for i in self.scene.items() if isinstance(i, MovableImageItem)]
        if not items:
            QMessageBox.information(self, "提示", "画布上没有图片可导出。")
            return
        margin = 20
        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")
        for item in items:
            rect = item.sceneBoundingRect()
            min_x = min(min_x, rect.left())
            min_y = min(min_y, rect.top())
            max_x = max(max_x, rect.right())
            max_y = max(max_y, rect.bottom())
        total_w = int(max_x - min_x + margin * 2)
        total_h = int(max_y - min_y + margin * 2)
        if total_w > 20000 or total_h > 20000:
            reply = QMessageBox.question(
                self, "警告",
                f"导出尺寸较大 ({total_w}x{total_h})，确定继续吗？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        result = QImage(total_w, total_h, QImage.Format_ARGB32)
        result.fill(Qt.transparent)
        painter = QPainter(result)
        settings = SettingsManager()
        if settings.get("antialiasing", True):
            painter.setRenderHint(QPainter.Antialiasing)
        if settings.get("smooth_pixmap", True):
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
        sorted_items = sorted(items, key=lambda x: x.zValue())
        for item in sorted_items:
            rect = item.sceneBoundingRect()
            cx = rect.center().x() - min_x + margin
            cy = rect.center().y() - min_y + margin
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(item.rotation_value())
            painter.setOpacity(item.opacity_value() * self._global_opacity)
            pw = item.pixmap().width()
            ph = item.pixmap().height()
            painter.drawPixmap(-pw / 2, -ph / 2, item.pixmap())
            painter.restore()
        painter.end()
        save_path, _ = QFileDialog.getSaveFileName(
            self, "导出拼接大图", ProjectInfo.get_export_default_filename(),
            "PNG 图片 (支持透明) (*.png);;JPEG 图片 (*.jpg);;BMP 图片 (*.bmp)"
        )
        if not save_path:
            return
        ext = os.path.splitext(save_path)[1].lower()
        if ext in (".jpg", ".jpeg"):
            bg = QImage(result.size(), QImage.Format_RGB32)
            bg.fill(Qt.white)
            p = QPainter(bg)
            p.drawImage(0, 0, result)
            p.end()
            bg.save(save_path, quality=95)
        else:
            result.save(save_path)
        QMessageBox.information(
            self, "成功",
            f"已导出到:\n{save_path}\n尺寸: {total_w}x{total_h}"
        )

    # ==================== 键盘事件 ====================
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.view.set_space_pressed(True)
            event.accept()
            return
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            self.delete_selected()
            event.accept()
            return
        if event.matches(QKeySequence.Paste):
            self.paste_from_clipboard()
            event.accept()
            return
        if event.key() == Qt.Key_0 and event.modifiers() & Qt.ControlModifier:
            self.view.reset_view_zoom()
            event.accept()
            return
        if event.key() == Qt.Key_Equal and event.modifiers() & Qt.ControlModifier:
            self.view.zoom_view(1.2)
            event.accept()
            return
        if event.key() == Qt.Key_Minus and event.modifiers() & Qt.ControlModifier:
            self.view.zoom_view(1 / 1.2)
            event.accept()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.view.set_space_pressed(False)
            event.accept()
            return
        super().keyReleaseEvent(event)

    def closeEvent(self, event):
        """关闭前保存一次"""
        self._do_autosave()
        super().closeEvent(event)


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ensure_dirs()
    window = MainWindow()
    window.show()
    window.view.centerOn(0, 0)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()