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
- 【新增】背景方案：纯色、网格、点阵、自定义图片
- 【新增】40+种背景形状和图案
- 【新增】Emoji表情功能：Win+; 调出面板、右键/菜单添加、吸附锁定
- 【新增】Emoji大小调整：右键菜单/滚轮缩放
"""
import sys
import os
import json
import time
import uuid
import math
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
    QPen, QColor, QBrush, QIcon, QTransform, QPainterPath,
    QPolygonF, QKeySequence, QFont, QFontDatabase, QFontMetrics
)
from PySide6.QtCore import Qt, QPointF, QRectF, QSizeF, QTimer, QSize, QRect, QPoint

# ==================== 配置常量 ====================
PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
AUTOSAVE_DIR = os.path.join(PROGRAM_DIR, "autosave")
HISTORY_DIR = os.path.join(PROGRAM_DIR, "history")
SETTINGS_FILE = os.path.join(PROGRAM_DIR, "settings.json")
BACKGROUNDS_DIR = os.path.join(PROGRAM_DIR, "backgrounds")

# 背景形状类型 - 40+种
BACKGROUND_SHAPES = [
    # 基础几何
    "square", "rectangle", "triangle", "hexagon", "circle", 
    "diamond", "star", "cross", "pentagon", "octagon",
    # 箭头类
    "arrow_up", "arrow_down", "arrow_left", "arrow_right",
    "arrow_up_right", "arrow_up_left", "arrow_down_right", "arrow_down_left",
    # 特殊形状
    "heart", "moon", "sun", "cloud", "lightning",
    "flower", "spiral", "gear", "shield", "infinity",
    # 更多几何
    "chevron_up", "chevron_down", "chevron_left", "chevron_right",
    "ring", "teardrop", "hourglass", "trapezoid", "parallelogram",
    "semicircle", "quarter_circle", "pin", "target",
]

# 背景图案类型 - 20+种
BACKGROUND_PATTERNS = [
    # 经典图案
    "grid", "dots", "diagonal", "checkerboard", 
    "concentric", "crosshair", "wave", "hatch",
    # 纹理图案
    "herringbone", "zigzag", "spiral_pattern",
    "triangle_tile", "hexagon_tile", "circle_tile", "diamond_tile",
    # 特殊图案
    "sawtooth", "scale", "maze", "radar",
    "starburst", "target_pattern", "ripple", "mosaic",
]

# 常用Emoji列表（快速选择）
COMMON_EMOJIS = [
    "😀", "😁", "😂", "🤣", "😃", "😄", "😅", "😆", "😉", "😊",
    "😋", "😎", "😍", "🥰", "😘", "😗", "😙", "😚", "🙂", "🤗",
    "🤩", "🤔", "🤨", "😐", "😑", "😶", "🙄", "😏", "😣", "😥",
    "😮", "🤐", "😯", "😪", "😫", "😴", "😌", "😛", "😜", "😝",
    "🤤", "😒", "😓", "😔", "😕", "🙃", "🤑", "😲", "☹️", "🙁",
    "😖", "😞", "😟", "😤", "😢", "😭", "😦", "😧", "😨", "😩",
    "🤯", "😬", "😰", "😱", "🥵", "🥶", "😳", "🤪", "😵", "😡",
    "😠", "🤬", "😷", "🤒", "🤕", "🤢", "🤮", "🥴", "😇", "🤠",
    "🤡", "🥳", "🥺", "🤥", "🤫", "🤭", "🧐", "🤓", "😈", "👿",
    "👹", "👺", "💀", "☠️", "👻", "👽", "👾", "🤖", "💩", "😺",
    "😸", "😹", "😻", "😼", "😽", "🙀", "😿", "😾", "🖐️", "✋",
    "👋", "🤚", "🖖", "👌", "🤌", "🤏", "✌️", "🤞", "🤟", "🤘",
    "👈", "👉", "👆", "👇", "☝️", "👍", "👎", "✊", "👊", "🤛",
    "🤜", "👏", "🙌", "👐", "🤲", "🤝", "🙏", "✍️", "💅", "🤳",
    "💪", "🦾", "🦿", "🦵", "🦶", "👂", "🦻", "👃", "🧠", "🫀",
    "🫁", "🦷", "🦴", "👀", "👁️", "👅", "👄", "🫦", "❤️", "🧡",
    "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔", "❤️‍🔥", "❤️‍🩹",
    "💕", "💞", "💓", "💗", "💖", "💘", "💝", "💟", "☮️", "✝️",
    "☪️", "🕉️", "☸️", "✡️", "🔯", "🕎", "☯️", "☦️", "🛐", "⛎",
    "♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑",
    "♒", "♓", "🆔", "⚛️", "🉑", "☢️", "☣️", "📴", "📳", "🈶",
    "🈚", "🈸", "🈺", "🈷️", "✴️", "🆚", "💮", "🉐", "㊙️", "㊗️",
    "🈴", "🈵", "🈹", "🈲", "🅰️", "🅱️", "🆎", "🆑", "🅾️", "🆘",
    "❌", "⭕", "🛑", "⛔", "📛", "🚫", "💯", "💢", "♨️", "🚷",
    "🚯", "🚳", "🚱", "🔞", "📵", "🚭", "❗", "❕", "❓", "❔",
    "‼️", "⁉️", "🔅", "🔆", "〽️", "⚠️", "🚸", "🔱", "⚜️", "🔰",
    "♻️", "✅", "🈯", "💹", "❇️", "✳️", "❎", "🌐", "💠", "Ⓜ️",
    "🌀", "💤", "💨", "💦", "💫", "🕳️", "💣", "💥", "🔥", "🌟",
    "✨", "⭐", "🌙", "☀️", "⛅", "☁️", "🌧️", "⛈️", "🌤️", "🌥️",
    "🌦️", "🌨️", "🌩️", "🌪️", "🌫️", "🌬️", "🌈", "☂️", "☔", "⛱️",
    "❄️", "☃️", "⛄", "☄️", "💧", "🌊", "🍇", "🍈", "🍉", "🍊",
    "🍋", "🍌", "🍍", "🥭", "🍎", "🍏", "🍐", "🍑", "🍒", "🍓",
    "🫐", "🥝", "🍅", "🫒", "🥥", "🥑", "🍆", "🥔", "🥕", "🌽",
    "🌶️", "🫑", "🥒", "🥬", "🥦", "🧄", "🧅", "🍄", "🥜", "🫘",
    "🌰", "🍞", "🥐", "🥖", "🫓", "🥨", "🥯", "🥞", "🧇", "🧀",
    "🍖", "🍗", "🥩", "🥓", "🍔", "🍟", "🍕", "🌭", "🥪", "🌮",
    "🌯", "🫔", "🥙", "🧆", "🥚", "🍳", "🥘", "🍲", "🫕", "🥣",
    "🥗", "🍿", "🧈", "🧂", "🥫", "🍱", "🍘", "🍙", "🍚", "🍛",
    "🍜", "🍝", "🍠", "🍢", "🍣", "🍤", "🍥", "🥮", "🍡", "🥟",
    "🥠", "🥡", "🦪", "🍦", "🍧", "🍨", "🍩", "🍪", "🎂", "🍰",
    "🧁", "🥧", "🍫", "🍬", "🍭", "🍮", "🍯", "🍼", "🥛", "☕",
    "🫖", "🍵", "🍶", "🍾", "🍷", "🍸", "🍹", "🍺", "🍻", "🥂",
    "🥃", "🥤", "🧃", "🧉", "🧊", "🥢", "🍽️", "🍴", "🥄", "🔪",
    "🏺", "🌍", "🌎", "🌏", "🌐", "🗺️", "🧭", "🏔️", "⛰️", "🌋",
    "🗻", "🏕️", "🏖️", "🏜️", "🏝️", "🏞️", "🏟️", "🏛️", "🏗️", "🧱",
    "🪨", "🪵", "🪹", "🪺", "🏘️", "🏚️", "🏠", "🏡", "🏢", "🏣",
    "🏤", "🏥", "🏦", "🏨", "🏩", "🏪", "🏫", "🏬", "🏭", "🏯",
    "🏰", "💒", "🗼", "🗽", "⛪", "🕌", "🛕", "🕍", "⛩️", "🕋",
    "⛲", "⛺", "🌁", "🌃", "🏙️", "🌄", "🌅", "🌆", "🌇", "🌉",
    "♠️", "♥️", "♦️", "♣️", "🃏", "🀄", "🎴", "🎭", "🖼️", "🎨",
    "🧵", "🧶", "🪡", "🪢", "👓", "🕶️", "🥽", "🥼", "🦺", "👔",
    "👕", "👖", "🧣", "🧤", "🧥", "🧦", "👗", "👘", "🥻", "🩱",
    "🩲", "🩳", "👙", "👚", "👛", "👜", "👝", "🎒", "🩴", "👞",
    "👟", "🥾", "🥿", "👠", "👡", "👢", "👑", "👒", "🎩", "🎓",
    "🧢", "🪖", "⛑️", "📿", "💄", "💍", "💎", "🔇", "🔈", "🔉",
    "🔊", "📢", "📣", "📯", "🔔", "🔕", "🎼", "🎵", "🎶", "🎙️",
    "🎚️", "🎛️", "🎤", "🎧", "📻", "🎷", "🪗", "🎸", "🎹", "🎺",
    "🎻", "🪕", "🥁", "🪘", "📱", "📲", "☎️", "📞", "📟", "📠",
    "🔋", "🪫", "🔌", "💻", "🖥️", "🖨️", "⌨️", "🖱️", "🖲️", "💽",
    "💾", "💿", "📀", "🧮", "🎥", "🎞️", "📽️", "🎬", "📺", "📷",
    "📸", "📹", "📼", "🔍", "🔎", "🕯️", "💡", "🔦", "🏮", "🪔",
    "📔", "📕", "📖", "📗", "📘", "📙", "📚", "📓", "📒", "📃",
    "📜", "📄", "📰", "🗞️", "📑", "🔖", "🏷️", "💰", "🪙", "💴",
    "💵", "💶", "💷", "💸", "💳", "🧾", "💹", "✉️", "📧", "📨",
    "📩", "📤", "📥", "📦", "📫", "📪", "📬", "📭", "📮", "🗳️",
    "✏️", "✒️", "🖋️", "🖊️", "🖌️", "🖍️", "📝", "💼", "📁", "📂",
    "🗂️", "📅", "📆", "🗒️", "🗓️", "📇", "📈", "📉", "📊", "📋",
    "📌", "📍", "📎", "🖇️", "📏", "📐", "✂️", "🗃️", "🗄️", "🗑️",
    "🔒", "🔓", "🔏", "🔐", "🔑", "🗝️", "🔨", "🪓", "⛏️", "⚒️",
    "🛠️", "🗡️", "⚔️", "🔫", "🪃", "🏹", "🛡️", "🪚", "🔧", "🪛",
    "🔩", "⚙️", "🗜️", "⚖️", "🪝", "🔗", "⛓️", "🪣", "🧰", "🧲",
    "🪜", "⚗️", "🧪", "🧫", "🧬", "🔬", "🔭", "📡", "💉", "🩸",
    "💊", "🩹", "🩺", "🚪", "🛗", "🪞", "🪟", "🛏️", "🛋️", "🪑",
    "🚽", "🪠", "🚿", "🛁", "🪥", "🧴", "🧷", "🧹", "🧺", "🧻",
    "🪣", "🧼", "🪥", "🧽", "🧯", "🛒", "🚬", "⚰️", "🪦", "⚱️",
    "🗿", "🪧", "🪪", "🏧", "🚮", "🚰", "♿", "🚹", "🚺", "🚻",
    "🚼", "🚾", "🛂", "🛃", "🛄", "🛅", "⚠️", "🚸", "⛔", "🚫",
    "🚳", "🚭", "🚯", "🚱", "🚷", "📵", "🔞", "☢️", "☣️", "⬆️",
    "↗️", "➡️", "↘️", "⬇️", "↙️", "⬅️", "↖️", "↕️", "↔️", "↩️",
    "↪️", "⤴️", "⤵️", "🔃", "🔄", "🔙", "🔚", "🔛", "🔜", "🔝",
    "🛐", "⚛️", "🕉️", "✡️", "🔯", "🕎", "☯️", "☦️", "🛐", "⛎",
    "♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑",
    "♒", "♓", "🆔", "⚛️", "🉑", "☢️", "☣️", "📴", "📳", "🈶",
]

DEFAULT_SETTINGS = {
    "background_type": "solid",
    "background_shape": "square",
    "background_pattern": "grid",
    "background_color": "#2b2b2b",
    "background_color_light": "#4a4a4a",
    "background_color_accent": "#5a5a5a",
    "background_image": "",
    "background_image_scale": "fit",
    "shape_size": 40,
    "shape_opacity": 0.3,
    "autosave_delay_ms": 1500,
    "max_history_items": None,
    "performance_mode": "balanced",
    "antialiasing": True,
    "smooth_pixmap": True,
    "toolbar_visibility": {
        "btn_import": True,
        "btn_paste": True,
        "btn_del": True,
        "btn_zoom_in": True,
        "btn_zoom_out": True,
        "btn_reset": True,
        "btn_rot_left": True,
        "btn_rot_right": True,
        "btn_flip_h": True,
        "btn_flip_v": True,
        "btn_view_in": True,
        "btn_view_out": True,
        "btn_view_fit": True,
        "btn_front": True,
        "btn_back": True,
        "item_opacity": True,
        "global_opacity": True,
        "btn_diff": True,
        "btn_clear_diff": True,
        "btn_save_hist": True,
        "btn_history": True,
        "btn_export": True,
        "btn_clear": True,
        "btn_settings": True,
        "btn_emoji": True,
        "btn_emoji_favorites": True,
    }
}


def ensure_dirs():
    for d in [AUTOSAVE_DIR, HISTORY_DIR, BACKGROUNDS_DIR,
              os.path.join(AUTOSAVE_DIR, "images"),
              os.path.join(HISTORY_DIR, "images")]:
        os.makedirs(d, exist_ok=True)


# ==================== 背景形状生成器 ====================
class ShapeGenerator:
    """各种形状的路径生成器 - 40+种形状"""
    
    @staticmethod
    def get_shape_path(shape_type, size, center_x, center_y):
        """获取形状的QPainterPath"""
        half = size / 2
        path = QPainterPath()
        
        # ==================== 基础几何 ====================
        if shape_type == "square":
            path.addRect(QRectF(center_x - half, center_y - half, size, size))
            return path
        
        elif shape_type == "rectangle":
            w = size * 1.2
            h = size * 0.7
            path.addRect(QRectF(center_x - w/2, center_y - h/2, w, h))
            return path
        
        elif shape_type == "triangle":
            path.moveTo(center_x, center_y - half)
            path.lineTo(center_x - half * 0.866, center_y + half * 0.5)
            path.lineTo(center_x + half * 0.866, center_y + half * 0.5)
            path.closeSubpath()
            return path
        
        elif shape_type == "hexagon":
            points = []
            for i in range(6):
                angle = math.radians(60 * i - 30)
                px = center_x + half * math.cos(angle)
                py = center_y + half * math.sin(angle)
                points.append(QPointF(px, py))
            path.moveTo(points[0])
            for p in points[1:]:
                path.lineTo(p)
            path.closeSubpath()
            return path
        
        elif shape_type == "circle":
            path.addEllipse(QRectF(center_x - half, center_y - half, size, size))
            return path
        
        elif shape_type == "diamond":
            path.moveTo(center_x, center_y - half)
            path.lineTo(center_x + half, center_y)
            path.lineTo(center_x, center_y + half)
            path.lineTo(center_x - half, center_y)
            path.closeSubpath()
            return path
        
        elif shape_type == "star":
            outer = half
            inner = half * 0.4
            points = []
            for i in range(10):
                angle = math.radians(36 * i - 90)
                r = outer if i % 2 == 0 else inner
                px = center_x + r * math.cos(angle)
                py = center_y + r * math.sin(angle)
                points.append(QPointF(px, py))
            path.moveTo(points[0])
            for p in points[1:]:
                path.lineTo(p)
            path.closeSubpath()
            return path
        
        elif shape_type == "cross":
            bar_width = size * 0.25
            bar_length = size
            path.addRect(QRectF(center_x - bar_length/2, center_y - bar_width/2, bar_length, bar_width))
            path.addRect(QRectF(center_x - bar_width/2, center_y - bar_length/2, bar_width, bar_length))
            return path
        
        elif shape_type == "pentagon":
            points = []
            for i in range(5):
                angle = math.radians(72 * i - 90)
                px = center_x + half * math.cos(angle)
                py = center_y + half * math.sin(angle)
                points.append(QPointF(px, py))
            path.moveTo(points[0])
            for p in points[1:]:
                path.lineTo(p)
            path.closeSubpath()
            return path
        
        elif shape_type == "octagon":
            points = []
            for i in range(8):
                angle = math.radians(45 * i - 22.5)
                px = center_x + half * math.cos(angle)
                py = center_y + half * math.sin(angle)
                points.append(QPointF(px, py))
            path.moveTo(points[0])
            for p in points[1:]:
                path.lineTo(p)
            path.closeSubpath()
            return path
        
        # ==================== 箭头类 ====================
        elif shape_type == "arrow_up":
            shaft_w = size * 0.2
            shaft_h = size * 0.5
            head_w = size * 0.6
            head_h = size * 0.5
            path.moveTo(center_x, center_y - half)
            path.lineTo(center_x + head_w/2, center_y - half + head_h)
            path.lineTo(center_x + shaft_w/2, center_y - half + head_h)
            path.lineTo(center_x + shaft_w/2, center_y + half)
            path.lineTo(center_x - shaft_w/2, center_y + half)
            path.lineTo(center_x - shaft_w/2, center_y - half + head_h)
            path.lineTo(center_x - head_w/2, center_y - half + head_h)
            path.closeSubpath()
            return path
        
        elif shape_type == "arrow_down":
            shaft_w = size * 0.2
            shaft_h = size * 0.5
            head_w = size * 0.6
            head_h = size * 0.5
            path.moveTo(center_x, center_y + half)
            path.lineTo(center_x + head_w/2, center_y + half - head_h)
            path.lineTo(center_x + shaft_w/2, center_y + half - head_h)
            path.lineTo(center_x + shaft_w/2, center_y - half)
            path.lineTo(center_x - shaft_w/2, center_y - half)
            path.lineTo(center_x - shaft_w/2, center_y + half - head_h)
            path.lineTo(center_x - head_w/2, center_y + half - head_h)
            path.closeSubpath()
            return path
        
        elif shape_type == "arrow_left":
            shaft_w = size * 0.5
            shaft_h = size * 0.2
            head_w = size * 0.5
            head_h = size * 0.6
            path.moveTo(center_x - half, center_y)
            path.lineTo(center_x - half + head_w, center_y - head_h/2)
            path.lineTo(center_x - half + head_w, center_y - shaft_h/2)
            path.lineTo(center_x + half, center_y - shaft_h/2)
            path.lineTo(center_x + half, center_y + shaft_h/2)
            path.lineTo(center_x - half + head_w, center_y + shaft_h/2)
            path.lineTo(center_x - half + head_w, center_y + head_h/2)
            path.closeSubpath()
            return path
        
        elif shape_type == "arrow_right":
            shaft_w = size * 0.5
            shaft_h = size * 0.2
            head_w = size * 0.5
            head_h = size * 0.6
            path.moveTo(center_x + half, center_y)
            path.lineTo(center_x + half - head_w, center_y - head_h/2)
            path.lineTo(center_x + half - head_w, center_y - shaft_h/2)
            path.lineTo(center_x - half, center_y - shaft_h/2)
            path.lineTo(center_x - half, center_y + shaft_h/2)
            path.lineTo(center_x + half - head_w, center_y + shaft_h/2)
            path.lineTo(center_x + half - head_w, center_y + head_h/2)
            path.closeSubpath()
            return path
        
        elif shape_type == "arrow_up_right":
            path.moveTo(center_x + half, center_y - half)
            path.lineTo(center_x - half, center_y + half)
            path.lineTo(center_x - half, center_y - half)
            path.closeSubpath()
            return path
        
        elif shape_type == "arrow_up_left":
            path.moveTo(center_x - half, center_y - half)
            path.lineTo(center_x + half, center_y + half)
            path.lineTo(center_x + half, center_y - half)
            path.closeSubpath()
            return path
        
        elif shape_type == "arrow_down_right":
            path.moveTo(center_x + half, center_y + half)
            path.lineTo(center_x - half, center_y - half)
            path.lineTo(center_x - half, center_y + half)
            path.closeSubpath()
            return path
        
        elif shape_type == "arrow_down_left":
            path.moveTo(center_x - half, center_y + half)
            path.lineTo(center_x + half, center_y - half)
            path.lineTo(center_x + half, center_y + half)
            path.closeSubpath()
            return path
        
        # ==================== 特殊形状 ====================
        elif shape_type == "heart":
            # 心形使用贝塞尔曲线
            path.moveTo(center_x, center_y + half * 0.4)
            # 左半心
            path.cubicTo(
                center_x - half * 0.8, center_y - half * 0.8,
                center_x - half * 1.2, center_y + half * 0.1,
                center_x, center_y + half * 0.7
            )
            # 右半心
            path.cubicTo(
                center_x + half * 1.2, center_y + half * 0.1,
                center_x + half * 0.8, center_y - half * 0.8,
                center_x, center_y + half * 0.4
            )
            return path
        
        elif shape_type == "moon":
            path.addEllipse(QRectF(center_x - half, center_y - half, size, size))
            # 减去一个圆形成月牙
            sub_path = QPainterPath()
            sub_path.addEllipse(QRectF(center_x + half * 0.25, center_y - half * 0.6, size * 0.6, size * 0.9))
            return path.subtracted(sub_path)
        
        elif shape_type == "sun":
            # 中心圆
            path.addEllipse(QRectF(center_x - half * 0.4, center_y - half * 0.4, size * 0.8, size * 0.8))
            # 光芒
            for i in range(8):
                angle = math.radians(45 * i)
                r1 = half * 0.5
                r2 = half * 0.8
                x1 = center_x + r1 * math.cos(angle)
                y1 = center_y + r1 * math.sin(angle)
                x2 = center_x + r2 * math.cos(angle)
                y2 = center_y + r2 * math.sin(angle)
                path.moveTo(x1, y1)
                path.lineTo(x2, y2)
            return path
        
        elif shape_type == "cloud":
            # 用多个圆拼成云朵
            path.addEllipse(QRectF(center_x - half * 0.6, center_y - half * 0.2, size * 0.5, size * 0.4))
            path.addEllipse(QRectF(center_x - half * 0.2, center_y - half * 0.5, size * 0.5, size * 0.5))
            path.addEllipse(QRectF(center_x + half * 0.1, center_y - half * 0.35, size * 0.4, size * 0.4))
            path.addEllipse(QRectF(center_x - half * 0.5, center_y + half * 0.1, size * 0.6, size * 0.3))
            return path
        
        elif shape_type == "lightning":
            path.moveTo(center_x + half * 0.3, center_y - half)
            path.lineTo(center_x - half * 0.1, center_y - half * 0.1)
            path.lineTo(center_x + half * 0.1, center_y - half * 0.1)
            path.lineTo(center_x - half * 0.3, center_y + half)
            path.lineTo(center_x + half * 0.1, center_y + half * 0.1)
            path.lineTo(center_x - half * 0.1, center_y + half * 0.1)
            path.closeSubpath()
            return path
        
        elif shape_type == "flower":
            # 花瓣
            for i in range(6):
                angle = math.radians(60 * i)
                cx = center_x + half * 0.5 * math.cos(angle)
                cy = center_y + half * 0.5 * math.sin(angle)
                path.addEllipse(QRectF(cx - half * 0.3, cy - half * 0.3, size * 0.6, size * 0.6))
            # 花蕊
            path.addEllipse(QRectF(center_x - half * 0.2, center_y - half * 0.2, size * 0.4, size * 0.4))
            return path
        
        elif shape_type == "spiral":
            # 螺旋线（绘制路径）
            path.moveTo(center_x, center_y)
            for t in range(1, 100):
                angle = t * 0.2
                r = t * 0.02 * half
                x = center_x + r * math.cos(angle)
                y = center_y + r * math.sin(angle)
                path.lineTo(x, y)
            return path
        
        elif shape_type == "gear":
            # 齿轮
            teeth = 8
            for i in range(teeth):
                angle = math.radians(360 / teeth * i)
                # 齿
                a1 = angle
                a2 = angle + math.radians(360 / teeth * 0.5)
                r1 = half * 0.7
                r2 = half * 0.9
                x1 = center_x + r1 * math.cos(a1)
                y1 = center_y + r1 * math.sin(a1)
                x2 = center_x + r2 * math.cos(a1)
                y2 = center_y + r2 * math.sin(a1)
                x3 = center_x + r2 * math.cos(a2)
                y3 = center_y + r2 * math.sin(a2)
                x4 = center_x + r1 * math.cos(a2)
                y4 = center_y + r1 * math.sin(a2)
                if i == 0:
                    path.moveTo(x1, y1)
                path.lineTo(x2, y2)
                path.lineTo(x3, y3)
                path.lineTo(x4, y4)
            path.closeSubpath()
            # 中心孔
            sub_path = QPainterPath()
            sub_path.addEllipse(QRectF(center_x - half * 0.2, center_y - half * 0.2, size * 0.4, size * 0.4))
            return path.subtracted(sub_path)
        
        elif shape_type == "shield":
            path.moveTo(center_x - half, center_y - half * 0.6)
            path.lineTo(center_x + half, center_y - half * 0.6)
            path.lineTo(center_x + half, center_y + half * 0.2)
            path.quadTo(center_x, center_y + half, center_x - half, center_y + half * 0.2)
            path.closeSubpath()
            return path
        
        elif shape_type == "infinity":
            path.moveTo(center_x - half * 0.8, center_y)
            path.cubicTo(
                center_x - half * 1.2, center_y - half * 0.6,
                center_x - half * 0.2, center_y - half * 0.6,
                center_x, center_y
            )
            path.cubicTo(
                center_x + half * 0.2, center_y + half * 0.6,
                center_x + half * 1.2, center_y + half * 0.6,
                center_x + half * 0.8, center_y
            )
            path.cubicTo(
                center_x + half * 0.2, center_y - half * 0.6,
                center_x - half * 0.2, center_y - half * 0.6,
                center_x - half * 0.8, center_y
            )
            return path
        
        # ==================== 更多几何 ====================
        elif shape_type == "chevron_up":
            path.moveTo(center_x - half, center_y + half * 0.3)
            path.lineTo(center_x, center_y - half * 0.3)
            path.lineTo(center_x + half, center_y + half * 0.3)
            return path
        
        elif shape_type == "chevron_down":
            path.moveTo(center_x - half, center_y - half * 0.3)
            path.lineTo(center_x, center_y + half * 0.3)
            path.lineTo(center_x + half, center_y - half * 0.3)
            return path
        
        elif shape_type == "chevron_left":
            path.moveTo(center_x + half * 0.3, center_y - half)
            path.lineTo(center_x - half * 0.3, center_y)
            path.lineTo(center_x + half * 0.3, center_y + half)
            return path
        
        elif shape_type == "chevron_right":
            path.moveTo(center_x - half * 0.3, center_y - half)
            path.lineTo(center_x + half * 0.3, center_y)
            path.lineTo(center_x - half * 0.3, center_y + half)
            return path
        
        elif shape_type == "ring":
            path.addEllipse(QRectF(center_x - half, center_y - half, size, size))
            sub_path = QPainterPath()
            sub_path.addEllipse(QRectF(center_x - half * 0.5, center_y - half * 0.5, size * 0.5, size * 0.5))
            return path.subtracted(sub_path)
        
        elif shape_type == "teardrop":
            path.moveTo(center_x, center_y - half)
            path.cubicTo(
                center_x + half, center_y - half * 0.3,
                center_x + half, center_y + half * 0.3,
                center_x, center_y + half * 0.6
            )
            path.cubicTo(
                center_x - half, center_y + half * 0.3,
                center_x - half, center_y - half * 0.3,
                center_x, center_y - half
            )
            return path
        
        elif shape_type == "hourglass":
            path.moveTo(center_x - half * 0.6, center_y - half)
            path.lineTo(center_x + half * 0.6, center_y - half)
            path.lineTo(center_x + half * 0.2, center_y)
            path.lineTo(center_x + half * 0.6, center_y + half)
            path.lineTo(center_x - half * 0.6, center_y + half)
            path.lineTo(center_x - half * 0.2, center_y)
            path.closeSubpath()
            return path
        
        elif shape_type == "trapezoid":
            path.moveTo(center_x - half * 0.6, center_y - half)
            path.lineTo(center_x + half * 0.6, center_y - half)
            path.lineTo(center_x + half, center_y + half)
            path.lineTo(center_x - half, center_y + half)
            path.closeSubpath()
            return path
        
        elif shape_type == "parallelogram":
            path.moveTo(center_x - half * 0.6, center_y - half)
            path.lineTo(center_x + half * 0.4, center_y - half)
            path.lineTo(center_x + half * 0.6, center_y + half)
            path.lineTo(center_x - half * 0.4, center_y + half)
            path.closeSubpath()
            return path
        
        elif shape_type == "semicircle":
            path.moveTo(center_x - half, center_y)
            path.arcTo(center_x - half, center_y - half, size, size, 180, -180)
            path.closeSubpath()
            return path
        
        elif shape_type == "quarter_circle":
            path.moveTo(center_x, center_y)
            path.arcTo(center_x - half, center_y - half, size, size, 0, -90)
            path.closeSubpath()
            return path
        
        elif shape_type == "pin":
            # 图钉形状
            path.addEllipse(QRectF(center_x - half * 0.25, center_y - half * 0.25, size * 0.5, size * 0.5))
            path.moveTo(center_x, center_y + half * 0.2)
            path.lineTo(center_x, center_y + half * 0.8)
            # 圆头
            path.addEllipse(QRectF(center_x - half * 0.12, center_y + half * 0.7, size * 0.24, size * 0.24))
            return path
        
        elif shape_type == "target":
            # 靶心
            for r in [0.2, 0.4, 0.6, 0.8, 1.0]:
                radius = half * r
                path.addEllipse(QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2))
            return path
        
        else:
            path.addRect(QRectF(center_x - half, center_y - half, size, size))
            return path


# ==================== 背景渲染器 ====================
class BackgroundRenderer:
    """背景渲染器 - 支持多种背景方案"""
    
    @staticmethod
    def render_background(settings, width, height):
        bg_type = settings.get("background_type", "solid")
        
        if bg_type == "solid":
            return BackgroundRenderer._render_solid(settings, width, height)
        elif bg_type == "shape":
            return BackgroundRenderer._render_shape(settings, width, height)
        elif bg_type == "pattern":
            return BackgroundRenderer._render_pattern(settings, width, height)
        elif bg_type == "image":
            return BackgroundRenderer._render_image(settings, width, height)
        else:
            return BackgroundRenderer._render_solid(settings, width, height)
    
    @staticmethod
    def _render_solid(settings, width, height):
        img = QImage(width, height, QImage.Format_RGB32)
        color = QColor(settings.get("background_color", "#2b2b2b"))
        img.fill(color)
        return img
    
    @staticmethod
    def _render_shape(settings, width, height):
        """形状背景 - 从(0,0)开始连续平铺"""
        img = QImage(width, height, QImage.Format_RGB32)
        bg_color = QColor(settings.get("background_color", "#2b2b2b"))
        shape_color = QColor(settings.get("background_color_light", "#4a4a4a"))
        shape_color.setAlpha(int(255 * settings.get("shape_opacity", 0.3)))
        shape_type = settings.get("background_shape", "square")
        shape_size = settings.get("shape_size", 40)
        accent_color = QColor(settings.get("background_color_accent", "#5a5a5a"))
        accent_color.setAlpha(int(255 * settings.get("shape_opacity", 0.3)))
        
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing)
        
        spacing = shape_size * 1.5
        
        # 计算需要绘制的行列数，从0开始
        cols = int(width / spacing) + 2
        rows = int(height / spacing) + 2
        
        for row in range(rows):
            for col in range(cols):
                # x 坐标：奇数行偏移 spacing/2（交错排列），偶数行从0开始
                x = col * spacing + (spacing / 2 if row % 2 == 1 else 0)
                # y 坐标：从0开始，每行增加 spacing
                y = row * spacing
                use_accent = (row + col) % 2 == 1
                color = accent_color if use_accent else shape_color
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(color, 1))
                path = ShapeGenerator.get_shape_path(shape_type, shape_size, x, y)
                painter.drawPath(path)
        
        painter.end()
        return img
    
    @staticmethod
    def _render_pattern(settings, width, height):
        """图案背景 - 支持20+种图案"""
        pattern_type = settings.get("background_pattern", "grid")
        
        pattern_handlers = {
            "grid": BackgroundRenderer._render_grid,
            "dots": BackgroundRenderer._render_dots,
            "diagonal": BackgroundRenderer._render_diagonal,
            "checkerboard": BackgroundRenderer._render_checkerboard,
            "concentric": BackgroundRenderer._render_concentric,
            "crosshair": BackgroundRenderer._render_crosshair,
            "wave": BackgroundRenderer._render_wave,
            "hatch": BackgroundRenderer._render_hatch,
            "herringbone": BackgroundRenderer._render_herringbone,
            "zigzag": BackgroundRenderer._render_zigzag,
            "spiral_pattern": BackgroundRenderer._render_spiral_pattern,
            "triangle_tile": BackgroundRenderer._render_triangle_tile,
            "hexagon_tile": BackgroundRenderer._render_hexagon_tile,
            "circle_tile": BackgroundRenderer._render_circle_tile,
            "diamond_tile": BackgroundRenderer._render_diamond_tile,
            "sawtooth": BackgroundRenderer._render_sawtooth,
            "scale": BackgroundRenderer._render_scale,
            "maze": BackgroundRenderer._render_maze,
            "radar": BackgroundRenderer._render_radar,
            "starburst": BackgroundRenderer._render_starburst,
            "target_pattern": BackgroundRenderer._render_target_pattern,
            "ripple": BackgroundRenderer._render_ripple,
            "mosaic": BackgroundRenderer._render_mosaic,
        }
        
        handler = pattern_handlers.get(pattern_type, BackgroundRenderer._render_grid)
        return handler(settings, width, height)
    
    @staticmethod
    def _get_pattern_colors(settings):
        """获取图案颜色"""
        bg_color = QColor(settings.get("background_color", "#2b2b2b"))
        line_color = QColor(settings.get("background_color_light", "#4a4a4a"))
        line_color.setAlpha(int(255 * settings.get("shape_opacity", 0.3)))
        return bg_color, line_color
    
    @staticmethod
    def _render_grid(settings, width, height):
        """网格图案 - 从(0,0)开始连续平铺"""
        bg_color, line_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(line_color, 1))
        
        # 垂直线：从0开始，到width结束
        x = 0
        while x <= width:
            painter.drawLine(x, 0, x, height)
            x += spacing
        
        # 水平线：从0开始，到height结束
        y = 0
        while y <= height:
            painter.drawLine(0, y, width, y)
            y += spacing
        
        painter.end()
        return img
    
    @staticmethod
    def _render_dots(settings, width, height):
        bg_color, dot_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        dot_radius = spacing * 0.08
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(dot_color, 1))
        painter.setBrush(QBrush(dot_color))
        painter.setRenderHint(QPainter.Antialiasing)
        # 从0开始，确保覆盖整个画布
        x = 0
        while x <= width:
            y = 0
            while y <= height:
                painter.drawEllipse(QPointF(x, y), dot_radius, dot_radius)
                y += spacing
            x += spacing
        painter.end()
        return img
    
    @staticmethod
    def _render_diagonal(settings, width, height):
        bg_color, line_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(line_color, 1))
        # 从0开始，确保覆盖整个画布
        offset = 0
        while offset <= width + height:
            painter.drawLine(offset, height, offset + height, 0)
            offset += spacing
        painter.end()
        return img
    
    @staticmethod
    def _render_checkerboard(settings, width, height):
        bg_color, light_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        # 从0开始，确保覆盖整个画布
        for y in range(0, height + spacing, spacing):
            for x in range(0, width + spacing, spacing):
                if ((x // spacing) + (y // spacing)) % 2 == 1:
                    painter.fillRect(x, y, spacing, spacing, light_color)
        painter.end()
        return img
    
    @staticmethod
    def _render_concentric(settings, width, height):
        bg_color, circle_color = BackgroundRenderer._get_pattern_colors(settings)
        circle_color.setAlpha(int(255 * settings.get("shape_opacity", 0.25)))
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(circle_color, 1))
        
        # 从(0,0)开始均匀分布多个中心点
        grid_spacing = spacing * 3
        for cx in range(0, width + grid_spacing, grid_spacing):
            for cy in range(0, height + grid_spacing, grid_spacing):
                max_r = min(grid_spacing * 0.6, cx + grid_spacing, cy + grid_spacing, width - cx + grid_spacing, height - cy + grid_spacing)
                max_r = max(0, max_r)
                r = spacing * 0.3
                while r < max_r:
                    painter.drawEllipse(QPointF(cx, cy), r, r)
                    r += spacing * 0.5
        painter.end()
        return img
    
    @staticmethod
    def _render_crosshair(settings, width, height):
        bg_color, line_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        cross_size = spacing * 0.3
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(line_color, 1))
        painter.setRenderHint(QPainter.Antialiasing)
        # 从0开始，确保覆盖整个画布
        x = 0
        while x <= width:
            y = 0
            while y <= height:
                painter.drawLine(x - cross_size, y, x + cross_size, y)
                painter.drawLine(x, y - cross_size, x, y + cross_size)
                y += spacing
            x += spacing
        painter.end()
        return img
    
    @staticmethod
    def _render_wave(settings, width, height):
        bg_color, wave_color = BackgroundRenderer._get_pattern_colors(settings)
        wave_color.setAlpha(int(255 * settings.get("shape_opacity", 0.25)))
        spacing = settings.get("shape_size", 40)
        amplitude = spacing * 0.3
        wavelength = spacing * 1.5
        
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(wave_color, 1.5))
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 从0开始，确保覆盖整个画布
        y_start = 0
        while y_start <= height:
            path = QPainterPath()
            x = 0
            path.moveTo(x, y_start + amplitude * math.sin(2 * math.pi * x / wavelength))
            while x <= width:
                x += 1
                path.lineTo(x, y_start + amplitude * math.sin(2 * math.pi * x / wavelength))
            painter.drawPath(path)
            y_start += spacing
        painter.end()
        return img
    
    @staticmethod
    def _render_hatch(settings, width, height):
        bg_color, line_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(line_color, 1))
        # 从0开始，确保覆盖整个画布
        offset = 0
        while offset <= width + height:
            painter.drawLine(offset, height, offset + height, 0)
            offset += spacing
        offset = 0
        while offset <= width + height:
            painter.drawLine(offset, 0, offset + height, height)
            offset += spacing
        painter.end()
        return img
    
    @staticmethod
    def _render_brick(settings, width, height):
        """砖墙图案"""
        bg_color, brick_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(brick_color, 1))
        brick_w = spacing
        brick_h = spacing * 0.5
        for y in range(0, height + brick_h, brick_h):
            offset = (brick_w / 2) if (y // brick_h) % 2 == 1 else 0
            for x in range(-brick_w, width + brick_w, brick_w):
                painter.drawRect(x + offset, y, brick_w, brick_h)
        painter.end()
        return img
        
    @staticmethod
    def _render_herringbone(settings, width, height):
        bg_color, line_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(line_color, 1.5))
        painter.setRenderHint(QPainter.Antialiasing)
        
        h = spacing * 0.5
        # 从0开始，确保覆盖整个画布
        for y in range(0, height + spacing, spacing):
            for x in range(0, width + spacing, spacing):
                offset = (spacing / 2) if (y // spacing) % 2 == 1 else 0
                cx = x + offset
                painter.drawLine(cx - h, y + spacing, cx, y)
                painter.drawLine(cx, y, cx + h, y + spacing)
        painter.end()
        return img
    
    @staticmethod
    def _render_zigzag(settings, width, height):
        bg_color, line_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(line_color, 1.5))
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 从0开始，确保覆盖整个画布
        for y in range(0, height + spacing, spacing):
            path = QPainterPath()
            x = 0
            path.moveTo(x, y)
            direction = 1
            while x <= width:
                x += spacing * 0.5
                y2 = y + direction * spacing * 0.4
                path.lineTo(x, y2)
                direction = -direction
            painter.drawPath(path)
        painter.end()
        return img
    
    @staticmethod
    def _render_spiral_pattern(settings, width, height):
        bg_color, line_color = BackgroundRenderer._get_pattern_colors(settings)
        line_color.setAlpha(int(255 * settings.get("shape_opacity", 0.2)))
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(line_color, 1))
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 从0开始，均匀分布螺旋中心
        step = spacing * 2
        for cx in range(0, width + step, step):
            for cy in range(0, height + step, step):
                path = QPainterPath()
                path.moveTo(cx, cy)
                max_t = int(spacing * 1.2)
                for t in range(1, max_t):
                    angle = t * 0.2
                    r = t * 0.02 * spacing
                    x = cx + r * math.cos(angle)
                    y = cy + r * math.sin(angle)
                    path.lineTo(x, y)
                painter.drawPath(path)
        painter.end()
        return img
    
    @staticmethod
    def _render_triangle_tile(settings, width, height):
        """三角形平铺 - 修复为连续平铺"""
        bg_color, tri_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(tri_color, 1))
        painter.setBrush(QBrush(tri_color))
        painter.setRenderHint(QPainter.Antialiasing)
        
        h = spacing * math.sqrt(3) / 2
        # 从负值开始，确保覆盖整个画布
        for row in range(int(-2), int(height / h) + 3):
            for col in range(int(-2), int(width / spacing) + 3):
                x = col * spacing + (spacing / 2 if row % 2 == 1 else 0)
                y = row * h
                # 正三角形
                path1 = QPainterPath()
                path1.moveTo(x, y + h)
                path1.lineTo(x + spacing/2, y)
                path1.lineTo(x + spacing, y + h)
                path1.closeSubpath()
                painter.drawPath(path1)
                # 倒三角形
                path2 = QPainterPath()
                path2.moveTo(x + spacing/2, y + h)
                path2.lineTo(x, y + 2*h)
                path2.lineTo(x + spacing, y + 2*h)
                path2.closeSubpath()
                painter.drawPath(path2)
        painter.end()
        return img
    
    @staticmethod
    def _render_hexagon_tile(settings, width, height):
        """六边形平铺 - 修复为连续平铺"""
        bg_color, hex_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(hex_color, 1))
        painter.setBrush(QBrush(hex_color))
        painter.setRenderHint(QPainter.Antialiasing)
        
        r = spacing / math.sqrt(3)
        # 从负值开始，确保覆盖整个画布
        for row in range(int(-2), int(height / (r * 1.5)) + 3):
            for col in range(int(-2), int(width / (r * 2)) + 3):
                x = col * r * 2 + (r if row % 2 == 1 else 0)
                y = row * r * 1.5
                path = QPainterPath()
                for i in range(6):
                    angle = math.radians(60 * i + 30)
                    px = x + r * math.cos(angle)
                    py = y + r * math.sin(angle)
                    if i == 0:
                        path.moveTo(px, py)
                    else:
                        path.lineTo(px, py)
                path.closeSubpath()
                painter.drawPath(path)
        painter.end()
        return img
    
    @staticmethod
    def _render_circle_tile(settings, width, height):
        """圆形平铺（交错排列）- 修复为连续平铺"""
        bg_color, circ_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        radius = spacing * 0.35
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(circ_color, 1))
        painter.setBrush(QBrush(circ_color))
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 从负值开始，确保覆盖整个画布
        for row in range(int(-2), int(height / spacing) + 3):
            for col in range(int(-2), int(width / spacing) + 3):
                x = col * spacing + (spacing / 2 if row % 2 == 1 else 0)
                y = row * spacing * 0.866
                painter.drawEllipse(QPointF(x, y), radius, radius)
        painter.end()
        return img
    
    @staticmethod
    def _render_diamond_tile(settings, width, height):
        """菱形平铺 - 修复为连续平铺"""
        bg_color, dia_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(dia_color, 1))
        painter.setBrush(QBrush(dia_color))
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 从负值开始，确保覆盖整个画布
        for row in range(int(-2), int(height / spacing) + 3):
            for col in range(int(-2), int(width / spacing) + 3):
                x = col * spacing + (spacing / 2 if row % 2 == 1 else 0)
                y = row * spacing * 0.5
                path = QPainterPath()
                path.moveTo(x, y)
                path.lineTo(x + spacing/2, y + spacing/2)
                path.lineTo(x, y + spacing)
                path.lineTo(x - spacing/2, y + spacing/2)
                path.closeSubpath()
                painter.drawPath(path)
        painter.end()
        return img
    
    @staticmethod
    def _render_sawtooth(settings, width, height):
        bg_color, line_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(line_color, 1.5))
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 从0开始，确保覆盖整个画布
        for y in range(0, height + spacing, spacing):
            path = QPainterPath()
            x = 0
            path.moveTo(x, y)
            while x <= width:
                x += spacing * 0.5
                path.lineTo(x, y + spacing * 0.3)
                x += spacing * 0.5
                path.lineTo(x, y - spacing * 0.1)
            painter.drawPath(path)
        painter.end()
        return img
    
    @staticmethod
    def _render_scale(settings, width, height):
        """鳞片/鱼鳞图案 - 从(0,0)开始连续，优化性能"""
        bg_color, scale_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        radius = spacing * 0.5
        
        # 计算需要绘制的行和列，从0开始
        cols = int(width / radius) + 2
        rows = int(height / (radius * 0.8)) + 2
        
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 限制最大数量避免卡顿
        total_cells = cols * rows
        max_cells = 3000
        
        if total_cells > max_cells:
            # 简化渲染：使用椭圆
            painter.setPen(QPen(scale_color, 1))
            painter.setBrush(QBrush(scale_color))
            step = max(1, int(total_cells / max_cells))
            for row in range(0, rows, step):
                for col in range(0, cols, step):
                    x = col * radius + (radius / 2 if row % 2 == 1 else 0)
                    y = row * radius * 0.8
                    if x > width + radius or y > height + radius:
                        continue
                    painter.drawEllipse(QPointF(x, y), radius * 0.5, radius * 0.35)
        else:
            # 完整渲染：使用半圆路径
            painter.setPen(QPen(scale_color, 1))
            painter.setBrush(QBrush(scale_color))
            for row in range(rows):
                for col in range(cols):
                    x = col * radius + (radius / 2 if row % 2 == 1 else 0)
                    y = row * radius * 0.8
                    if x > width + radius or y > height + radius:
                        continue
                    path = QPainterPath()
                    path.arcTo(QRectF(x - radius, y - radius, radius * 2, radius * 2), 0, -180)
                    path.closeSubpath()
                    painter.drawPath(path)
        
        painter.end()
        return img
    
    @staticmethod
    def _render_maze(settings, width, height):
        """迷宫图案 - 使用DFS生成真正的迷宫，边界连续"""
        import random
        
        bg_color, line_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        
        # 确保迷宫尺寸合理
        cols = max(3, int(width / spacing))
        rows = max(3, int(height / spacing))
        
        # 调整间距以适配窗口
        cell_w = width / cols
        cell_h = height / rows
        
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(line_color, 2))
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 生成迷宫网格
        walls = [[[True, True] for _ in range(cols)] for _ in range(rows)]
        visited = [[False] * cols for _ in range(rows)]
        
        # 使用DFS生成迷宫
        stack = []
        start_r, start_c = 0, 0
        visited[start_r][start_c] = True
        stack.append((start_r, start_c))
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        
        while stack:
            r, c = stack[-1]
            neighbors = []
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and not visited[nr][nc]:
                    neighbors.append((nr, nc, dr, dc))
            
            if neighbors:
                nr, nc, dr, dc = random.choice(neighbors)
                visited[nr][nc] = True
                if dr == 0 and dc == 1:
                    walls[r][c][0] = False
                elif dr == 1 and dc == 0:
                    walls[r][c][1] = False
                elif dr == 0 and dc == -1:
                    walls[nr][nc][0] = False
                elif dr == -1 and dc == 0:
                    walls[nr][nc][1] = False
                stack.append((nr, nc))
            else:
                stack.pop()
        
        # 确保入口和出口
        walls[0][0][1] = False
        walls[rows-1][cols-1][1] = False
        
        # 绘制迷宫墙壁 - 确保从边界开始
        wall_thickness = max(2, min(4, spacing * 0.08))
        painter.setPen(QPen(line_color, wall_thickness))
        
        for r in range(rows):
            for c in range(cols):
                x = c * cell_w
                y = r * cell_h
                if walls[r][c][0]:
                    painter.drawLine(x + cell_w, y + 1, x + cell_w, y + cell_h - 1)
                if walls[r][c][1]:
                    painter.drawLine(x + 1, y + cell_h, x + cell_w - 1, y + cell_h)
        
        # 绘制外边框
        painter.setPen(QPen(line_color, wall_thickness * 2))
        painter.drawRect(0, 0, width, height)
        
        # 入口/出口标记
        painter.setPen(QPen(QColor(0, 200, 0), spacing * 0.15))
        painter.setBrush(QBrush(QColor(0, 200, 0, 150)))
        painter.drawEllipse(QPointF(cell_w/2, cell_h/2), spacing * 0.12, spacing * 0.12)
        painter.setPen(QPen(QColor(255, 100, 0), spacing * 0.15))
        painter.setBrush(QBrush(QColor(255, 100, 0, 150)))
        painter.drawEllipse(QPointF(width - cell_w/2, height - cell_h/2), spacing * 0.12, spacing * 0.12)
        
        painter.end()
        return img
    
    @staticmethod
    def _render_radar(settings, width, height):
        bg_color, line_color = BackgroundRenderer._get_pattern_colors(settings)
        line_color.setAlpha(int(255 * settings.get("shape_opacity", 0.2)))
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(line_color, 1))
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 从0开始均匀分布雷达中心
        grid_step = spacing * 2
        for cx in range(0, width + grid_step, grid_step):
            for cy in range(0, height + grid_step, grid_step):
                max_r = min(spacing * 0.8, grid_step * 0.5)
                max_r = max(spacing * 0.2, max_r)
                r = spacing * 0.2
                while r < max_r:
                    painter.drawEllipse(QPointF(cx, cy), r, r)
                    r += spacing * 0.15
                painter.drawLine(cx - max_r, cy, cx + max_r, cy)
                painter.drawLine(cx, cy - max_r, cx, cy + max_r)
        painter.end()
        return img
    
    @staticmethod
    def _render_starburst(settings, width, height):
        bg_color, line_color = BackgroundRenderer._get_pattern_colors(settings)
        line_color.setAlpha(int(255 * settings.get("shape_opacity", 0.2)))
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(line_color, 1))
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 从0开始均匀分布星爆中心
        grid_step = spacing * 2
        for cx in range(0, width + grid_step, grid_step):
            for cy in range(0, height + grid_step, grid_step):
                max_r = min(spacing * 0.8, grid_step * 0.5)
                max_r = max(spacing * 0.2, max_r)
                for i in range(12):
                    angle = math.radians(30 * i)
                    x = cx + max_r * math.cos(angle)
                    y = cy + max_r * math.sin(angle)
                    painter.drawLine(cx, cy, x, y)
        painter.end()
        return img
    
    @staticmethod
    def _render_target_pattern(settings, width, height):
        bg_color, line_color = BackgroundRenderer._get_pattern_colors(settings)
        line_color.setAlpha(int(255 * settings.get("shape_opacity", 0.2)))
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(line_color, 1))
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 从0开始均匀分布靶心中心
        grid_step = spacing * 2
        for cx in range(0, width + grid_step, grid_step):
            for cy in range(0, height + grid_step, grid_step):
                max_r = min(spacing * 0.8, grid_step * 0.5)
                max_r = max(spacing * 0.2, max_r)
                rings = 4
                for i in range(rings, 0, -1):
                    r = max_r * i / rings
                    painter.drawEllipse(QPointF(cx, cy), r, r)
        painter.end()
        return img
    
    @staticmethod
    def _render_ripple(settings, width, height):
        bg_color, line_color = BackgroundRenderer._get_pattern_colors(settings)
        line_color.setAlpha(int(255 * settings.get("shape_opacity", 0.2)))
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(line_color, 1))
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 从0开始均匀分布涟漪中心
        grid_step = spacing * 3
        for cx in range(0, width + grid_step, grid_step):
            for cy in range(0, height + grid_step, grid_step):
                max_r = min(grid_step * 0.6, cx + grid_step, cy + grid_step, width - cx + grid_step, height - cy + grid_step)
                max_r = max(spacing * 0.3, max_r)
                r = spacing * 0.2
                while r < max_r:
                    painter.drawEllipse(QPointF(cx, cy), r, r)
                    r += spacing * 0.3
        painter.end()
        return img
    
    @staticmethod
    def _render_mosaic(settings, width, height):
        bg_color, block_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(block_color, 1))
        painter.setBrush(QBrush(block_color))
        block_size = spacing * 0.3
        block_size = max(1, int(block_size))
        
        # 从0开始，确保覆盖整个画布
        for y in range(0, height + spacing, spacing):
            for x in range(0, width + spacing, spacing):
                offset_x = (spacing * 0.5) if ((y // spacing) % 2 == 1) else 0
                for bx in range(0, spacing, block_size):
                    for by in range(0, spacing, block_size):
                        if (bx + by) % 2 == 0:
                            painter.fillRect(
                                x + offset_x + bx, 
                                y + by, 
                                block_size, 
                                block_size, 
                                block_color
                            )
        painter.end()
        return img
    
    @staticmethod
    def _render_image(settings, width, height):
        img_path = settings.get("background_image", "")
        if not img_path or not os.path.exists(img_path):
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
                scaled = pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                x = (width - scaled.width()) // 2
                y = (height - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
            elif scale_mode == "stretch":
                scaled = pixmap.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                painter.drawPixmap(0, 0, scaled)
            elif scale_mode == "tile":
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
    _instance = None
    _cache = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_background(self, settings, width, height):
        key = self._make_key(settings, width, height)
        if key in self._cache:
            return self._cache[key]
        img = BackgroundRenderer.render_background(settings, width, height)
        self._cache[key] = img
        if len(self._cache) > 10:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        return img
    
    def _make_key(self, settings, width, height):
        bg_type = settings.get("background_type", "solid")
        # 宽高始终作为第一部分
        parts = [bg_type, str(width), str(height)]
        
        if bg_type == "solid":
            parts.append(settings.get("background_color", "#2b2b2b"))
        elif bg_type == "shape":
            parts.extend([
                settings.get("background_shape", "square"),
                settings.get("background_color", "#2b2b2b"),
                settings.get("background_color_light", "#4a4a4a"),
                settings.get("background_color_accent", "#5a5a5a"),
                str(settings.get("shape_size", 40)),
                str(settings.get("shape_opacity", 0.3))
            ])
        elif bg_type == "pattern":
            parts.extend([
                settings.get("background_pattern", "grid"),
                settings.get("background_color", "#2b2b2b"),
                settings.get("background_color_light", "#4a4a4a"),
                str(settings.get("shape_size", 40)),
                str(settings.get("shape_opacity", 0.3))
            ])
            # 注意：宽高已经在 parts 开头了，不需要再添加
        elif bg_type == "image":
            parts.extend([
                settings.get("background_image", ""),
                settings.get("background_image_scale", "fit")
            ])
        return "_".join(parts)
    
    def clear(self):
        self._cache.clear()


# ==================== 设置管理器 ====================
class SettingsManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        self._settings = dict(DEFAULT_SETTINGS)
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    for key, value in DEFAULT_SETTINGS.items():
                        if key not in saved:
                            saved[key] = value
                    self._settings.update(saved)
            except Exception:
                pass
        self._save_defaults()

    def _save_defaults(self):
        if not os.path.exists(SETTINGS_FILE):
            self.save()

    def save(self):
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

    def get_autosave_delay(self):
        return int(self._settings.get("autosave_delay_ms", 1500))

    def get_max_history(self):
        return self._settings.get("max_history_items", None)

    def get_performance_mode(self):
        return self._settings.get("performance_mode", "balanced")

    def get_toolbar_visibility(self):
        return self._settings.get("toolbar_visibility", dict(DEFAULT_SETTINGS["toolbar_visibility"]))

    def set_toolbar_visibility(self, visibility_dict):
        self._settings["toolbar_visibility"] = visibility_dict


# ==================== 工具栏自定义对话框 ====================
class ToolbarCustomizeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("自定义工具栏")
        self.resize(550, 500)
        self._settings = SettingsManager()
        self._visibility = self._settings.get_toolbar_visibility().copy()
        self._main_window = None
        self._find_main_window(parent)
        self._build_ui()
        self._load_values()

    def _find_main_window(self, widget):
        while widget is not None:
            if isinstance(widget, MainWindow):
                self._main_window = widget
                break
            widget = widget.parent()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        info_label = QLabel("勾选要在工具栏中显示的按钮和组件：")
        info_label.setStyleSheet("font-weight: bold; padding: 5px 0;")
        layout.addWidget(info_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        main_layout.setSpacing(12)

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
            ("😀 Emoji表情", [
                ("btn_emoji", "添加表情"),
                ("btn_emoji_favorites", "常用表情"),
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
            group_box = QGroupBox(group_name)
            group_layout = QGridLayout(group_box)
            group_layout.setSpacing(6)
            cols = 2
            for idx, (key, label) in enumerate(items):
                row = idx // cols
                col = idx % cols
                cb = QCheckBox(label)
                cb.setObjectName(key)
                self.checkboxes[key] = cb
                group_layout.addWidget(cb, row, col, Qt.AlignLeft)
            main_layout.addWidget(group_box)

        main_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

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
        if self._main_window:
            self._main_window.apply_toolbar_visibility()

    def _on_ok(self):
        self._on_apply()
        self.accept()


# ==================== 设置对话框 ====================
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选项设置")
        self.resize(580, 680)
        self._settings = SettingsManager()
        self._main_window = None
        self._find_main_window(parent)
        self._build_ui()
        self._load_values()

    def _find_main_window(self, widget):
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

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Apply).clicked.connect(self._on_apply)
        layout.addWidget(buttons)

    def _build_background_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 背景类型选择
        type_group = QGroupBox("背景类型")
        type_layout = QHBoxLayout()
        self.bg_type_btns = QButtonGroup(self)
        
        self.bg_solid = QRadioButton("纯色")
        self.bg_shape = QRadioButton("形状")
        self.bg_pattern = QRadioButton("图案")
        self.bg_image = QRadioButton("自定义图片")
        
        self.bg_type_btns.addButton(self.bg_solid, 0)
        self.bg_type_btns.addButton(self.bg_shape, 1)
        self.bg_type_btns.addButton(self.bg_pattern, 2)
        self.bg_type_btns.addButton(self.bg_image, 3)
        
        type_layout.addWidget(self.bg_solid)
        type_layout.addWidget(self.bg_shape)
        type_layout.addWidget(self.bg_pattern)
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
        
        # 形状设置
        self.shape_frame = QFrame()
        shape_layout = QFormLayout(self.shape_frame)
        
        self.shape_combo = QComboBox()
        shape_names = {
            # 基础几何
            "square": "■ 正方形", "rectangle": "▬ 长方形",
            "triangle": "▲ 三角形", "hexagon": "⬡ 六边形",
            "circle": "● 圆形", "diamond": "◆ 菱形",
            "star": "★ 星形", "cross": "✚ 十字形",
            "pentagon": "⬠ 五边形", "octagon": "⯃ 八边形",
            # 箭头
            "arrow_up": "↑ 上箭头", "arrow_down": "↓ 下箭头",
            "arrow_left": "← 左箭头", "arrow_right": "→ 右箭头",
            "arrow_up_right": "↗ 右上箭头", "arrow_up_left": "↖ 左上箭头",
            "arrow_down_right": "↘ 右下箭头", "arrow_down_left": "↙ 左下箭头",
            # 特殊
            "heart": "♥ 心形", "moon": "☽ 月亮", "sun": "☀ 太阳",
            "cloud": "☁ 云朵", "lightning": "⚡ 闪电",
            "flower": "❀ 花朵", "spiral": "🌀 螺旋",
            "gear": "⚙ 齿轮", "shield": "🛡 盾牌",
            "infinity": "∞ 无限",
            # 更多几何
            "chevron_up": "⌃ 上V", "chevron_down": "⌄ 下V",
            "chevron_left": "⌈ 左V", "chevron_right": "⌉ 右V",
            "ring": "◎ 圆环", "teardrop": "💧 水滴",
            "hourglass": "⌛ 沙漏", "trapezoid": "⏢ 梯形",
            "parallelogram": "▱ 平行四边形",
            "semicircle": "◗ 半圆", "quarter_circle": "◘ 四分之一圆",
            "pin": "📍 图钉", "target": "🎯 靶心",
        }
        for key, name in shape_names.items():
            self.shape_combo.addItem(name, key)
        shape_layout.addRow("形状:", self.shape_combo)
        
        shape_color_layout = QHBoxLayout()
        self.shape_color_btn = QPushButton()
        self.shape_color_btn.setFixedSize(60, 28)
        self.shape_color_btn.clicked.connect(self._choose_shape_color)
        self.shape_color_label = QLabel("")
        shape_color_layout.addWidget(self.shape_color_btn)
        shape_color_layout.addWidget(self.shape_color_label)
        shape_color_layout.addStretch()
        shape_layout.addRow("形状颜色:", shape_color_layout)
        
        accent_layout = QHBoxLayout()
        self.accent_color_btn = QPushButton()
        self.accent_color_btn.setFixedSize(60, 28)
        self.accent_color_btn.clicked.connect(self._choose_accent_color)
        self.accent_color_label = QLabel("")
        accent_layout.addWidget(self.accent_color_btn)
        accent_layout.addWidget(self.accent_color_label)
        accent_layout.addStretch()
        shape_layout.addRow("交替颜色:", accent_layout)
        
        self.shape_size_spin = QSpinBox()
        self.shape_size_spin.setRange(10, 200)
        self.shape_size_spin.setSuffix(" px")
        shape_layout.addRow("大小:", self.shape_size_spin)
        
        self.shape_opacity_slider = QSlider(Qt.Horizontal)
        self.shape_opacity_slider.setRange(5, 100)
        self.shape_opacity_slider.setValue(30)
        self.shape_opacity_label = QLabel("30%")
        shape_opacity_layout = QHBoxLayout()
        shape_opacity_layout.addWidget(self.shape_opacity_slider)
        shape_opacity_layout.addWidget(self.shape_opacity_label)
        shape_layout.addRow("透明度:", shape_opacity_layout)
        
        layout.addWidget(self.shape_frame)
        
        # 图案设置
        self.pattern_frame = QFrame()
        pattern_layout = QFormLayout(self.pattern_frame)
        
        self.pattern_combo = QComboBox()
        pattern_names = {
            "grid": "⊞ 网格", "dots": "• 点阵",
            "diagonal": "╱ 斜线", "checkerboard": "▦ 棋盘格",
            "concentric": "◎ 同心圆", "crosshair": "✚ 十字线",
            "wave": "〰 波浪", "hatch": "╳ 交叉斜线",
            "herringbone": "🐟 人字形",
            "zigzag": "⚡ 锯齿", "spiral_pattern": "🌀 螺旋纹",
            "triangle_tile": "△ 三角砖", "hexagon_tile": "⬡ 六角砖",
            "circle_tile": "● 圆砖", "diamond_tile": "◇ 菱形砖",
            "sawtooth": "锯齿轮廓", "scale": "🐉 鳞片",
            "maze": "🧩 迷宫（DFS生成）", "radar": "📡 雷达",
            "starburst": "✨ 星爆", "target_pattern": "🎯 靶心纹",
            "ripple": "🌊 涟漪", "mosaic": "🎨 马赛克",
        }
        for key, name in pattern_names.items():
            self.pattern_combo.addItem(name, key)
        pattern_layout.addRow("图案:", self.pattern_combo)
        
        pattern_color_layout = QHBoxLayout()
        self.pattern_color_btn = QPushButton()
        self.pattern_color_btn.setFixedSize(60, 28)
        self.pattern_color_btn.clicked.connect(self._choose_pattern_color)
        self.pattern_color_label = QLabel("")
        pattern_color_layout.addWidget(self.pattern_color_btn)
        pattern_color_layout.addWidget(self.pattern_color_label)
        pattern_color_layout.addStretch()
        pattern_layout.addRow("图案颜色:", pattern_color_layout)
        
        self.pattern_size_spin = QSpinBox()
        self.pattern_size_spin.setRange(10, 200)
        self.pattern_size_spin.setSuffix(" px")
        pattern_layout.addRow("大小/间距:", self.pattern_size_spin)
        
        self.pattern_opacity_slider = QSlider(Qt.Horizontal)
        self.pattern_opacity_slider.setRange(5, 100)
        self.pattern_opacity_slider.setValue(30)
        self.pattern_opacity_label = QLabel("30%")
        pattern_opacity_layout = QHBoxLayout()
        pattern_opacity_layout.addWidget(self.pattern_opacity_slider)
        pattern_opacity_layout.addWidget(self.pattern_opacity_label)
        pattern_layout.addRow("透明度:", pattern_opacity_layout)
        
        layout.addWidget(self.pattern_frame)
        
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
        
        preview_btn = QPushButton("预览背景")
        preview_btn.clicked.connect(self._preview_background)
        image_layout.addRow("", preview_btn)
        
        layout.addWidget(self.image_frame)
        
        self.bg_type_btns.idClicked.connect(self._on_bg_type_changed)
        layout.addStretch()
        return widget

    def _build_general_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        
        self.autosave_spin = QSpinBox()
        self.autosave_spin.setRange(100, 30000)
        self.autosave_spin.setSingleStep(100)
        self.autosave_spin.setSuffix(" 毫秒")
        self.autosave_spin.setToolTip("操作停止后多久自动保存一次（防抖延迟）")
        layout.addRow("自动保存延迟:", self.autosave_spin)
        
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
        
        self.perf_combo = QComboBox()
        self.perf_combo.addItem("🌟 高质量（渲染精细，稍慢）", "quality")
        self.perf_combo.addItem("⚖️ 平衡（推荐）", "balanced")
        self.perf_combo.addItem("⚡ 高性能（流畅优先）", "performance")
        self.perf_combo.currentIndexChanged.connect(self._on_perf_mode_changed)
        layout.addRow("性能模式:", self.perf_combo)
        
        self.aa_check = QCheckBox("启用抗锯齿（边缘更平滑）")
        layout.addRow("", self.aa_check)
        
        self.smooth_check = QCheckBox("平滑图片缩放（缩放更细腻）")
        layout.addRow("", self.smooth_check)
        
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
        type_map = {"solid": 0, "shape": 1, "pattern": 2, "image": 3}
        self.bg_type_btns.button(type_map.get(bg_type, 0)).setChecked(True)
        self._on_bg_type_changed(type_map.get(bg_type, 0))
        
        color = QColor(s.get("background_color", "#2b2b2b"))
        self._update_bg_color_button(color)
        
        shape = s.get("background_shape", "square")
        idx = self.shape_combo.findData(shape)
        if idx >= 0:
            self.shape_combo.setCurrentIndex(idx)
        light = QColor(s.get("background_color_light", "#4a4a4a"))
        self._update_shape_color_button(light)
        accent = QColor(s.get("background_color_accent", "#5a5a5a"))
        self._update_accent_color_button(accent)
        self.shape_size_spin.setValue(s.get("shape_size", 40))
        opacity = s.get("shape_opacity", 0.3)
        self.shape_opacity_slider.setValue(int(opacity * 100))
        self.shape_opacity_label.setText(f"{int(opacity * 100)}%")
        
        pattern = s.get("background_pattern", "grid")
        idx = self.pattern_combo.findData(pattern)
        if idx >= 0:
            self.pattern_combo.setCurrentIndex(idx)
        self._update_pattern_color_button(light)
        self.pattern_size_spin.setValue(s.get("shape_size", 40))
        self.pattern_opacity_slider.setValue(int(opacity * 100))
        self.pattern_opacity_label.setText(f"{int(opacity * 100)}%")
        
        self.bg_image_edit.setText(s.get("background_image", ""))
        scale_map = {"fit": 0, "stretch": 1, "tile": 2}
        self.bg_image_scale.setCurrentIndex(scale_map.get(s.get("background_image_scale", "fit"), 0))
        
        self.autosave_spin.setValue(s.get_autosave_delay())
        
        max_hist = s.get_max_history()
        if max_hist is not None:
            self.history_check.setChecked(True)
            self.history_spin.setValue(max_hist)
            self.history_spin.setEnabled(True)
        else:
            self.history_check.setChecked(False)
            self.history_spin.setEnabled(False)
        
        mode = s.get_performance_mode()
        idx = self.perf_combo.findData(mode)
        if idx >= 0:
            self.perf_combo.setCurrentIndex(idx)
        self.aa_check.setChecked(s.get("antialiasing", True))
        self.smooth_check.setChecked(s.get("smooth_pixmap", True))

    def _on_bg_type_changed(self, type_id):
        self.solid_frame.setVisible(type_id == 0)
        self.shape_frame.setVisible(type_id == 1)
        self.pattern_frame.setVisible(type_id == 2)
        self.image_frame.setVisible(type_id == 3)

    def _choose_bg_color(self):
        current = self._settings.get_background_color()
        color = QColorDialog.getColor(current, self, "选择背景颜色")
        if color.isValid():
            self._update_bg_color_button(color)

    def _choose_shape_color(self):
        current = QColor(self._settings.get("background_color_light", "#4a4a4a"))
        color = QColorDialog.getColor(current, self, "选择形状颜色")
        if color.isValid():
            self._update_shape_color_button(color)

    def _choose_accent_color(self):
        current = QColor(self._settings.get("background_color_accent", "#5a5a5a"))
        color = QColorDialog.getColor(current, self, "选择交替颜色")
        if color.isValid():
            self._update_accent_color_button(color)

    def _choose_pattern_color(self):
        current = QColor(self._settings.get("background_color_light", "#4a4a4a"))
        color = QColorDialog.getColor(current, self, "选择图案颜色")
        if color.isValid():
            self._update_pattern_color_button(color)

    def _choose_bg_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff);;所有文件 (*.*)"
        )
        if file_path:
            self.bg_image_edit.setText(file_path)

    def _preview_background(self):
        if self._main_window:
            self._on_apply()
            self._main_window.view.update_background()

    def _update_bg_color_button(self, color):
        self.bg_color_btn.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid #888;"
        )
        self.bg_color_label.setText(color.name())

    def _update_shape_color_button(self, color):
        self.shape_color_btn.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid #888;"
        )
        self.shape_color_label.setText(color.name())

    def _update_accent_color_button(self, color):
        self.accent_color_btn.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid #888;"
        )
        self.accent_color_label.setText(color.name())

    def _update_pattern_color_button(self, color):
        self.pattern_color_btn.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid #888;"
        )
        self.pattern_color_label.setText(color.name())

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
        result = {}
        type_map = {0: "solid", 1: "shape", 2: "pattern", 3: "image"}
        bg_type = type_map.get(self.bg_type_btns.checkedId(), "solid")
        result["background_type"] = bg_type
        
        result["background_color"] = self.bg_color_label.text() or "#2b2b2b"
        
        if bg_type == "shape":
            result["background_shape"] = self.shape_combo.currentData()
            result["background_color_light"] = self.shape_color_label.text() or "#4a4a4a"
            result["background_color_accent"] = self.accent_color_label.text() or "#5a5a5a"
            result["shape_size"] = self.shape_size_spin.value()
            result["shape_opacity"] = self.shape_opacity_slider.value() / 100.0
        elif bg_type == "pattern":
            result["background_pattern"] = self.pattern_combo.currentData()
            result["background_color_light"] = self.pattern_color_label.text() or "#4a4a4a"
            result["shape_size"] = self.pattern_size_spin.value()
            result["shape_opacity"] = self.pattern_opacity_slider.value() / 100.0
        elif bg_type == "image":
            result["background_image"] = self.bg_image_edit.text()
            scale_map = {0: "fit", 1: "stretch", 2: "tile"}
            result["background_image_scale"] = scale_map.get(self.bg_image_scale.currentIndex(), "fit")
        
        result["autosave_delay_ms"] = self.autosave_spin.value()
        
        if self.history_check.isChecked():
            result["max_history_items"] = self.history_spin.value()
        else:
            result["max_history_items"] = None
        
        result["performance_mode"] = self.perf_combo.currentData()
        result["antialiasing"] = self.aa_check.isChecked()
        result["smooth_pixmap"] = self.smooth_check.isChecked()
        return result

    def _on_apply(self):
        new_settings = self._collect_settings()
        self._settings.update(new_settings)
        self._settings.save()
        BackgroundCache().clear()
        if self._main_window:
            self._main_window.apply_settings()

    def _on_ok(self):
        self._on_apply()
        self.accept()


# ==================== 项目信息元数据 ====================
class ProjectInfo:
    NAME = "Image Canvas Stitcher"
    DISPLAY_NAME = "图片自由拼接工具"
    VERSION = "3.21"
    BUILD_DATE = "2026-07-28"
    AUTHOR = "杜玛"
    COPYRIGHT = "© 永久 杜玛"
    LICENSE = "MIT"
    URL = "https://github.com/duma520/IntervalTracker"
    MAINTAINER_EMAIL = "不提供"
    DESCRIPTION = "图片自由拼接工具 - 支持拖拽、粘贴、缩放、透明度调整、差异比对、历史记录、工具栏自定义、Emoji表情"
    TITLE_FORMAT = "{display_name} v{version}"
    TITLE_FORMAT_WITH_USER = "{display_name} v{version} - 当前用户: {username}"
    
    @classmethod
    def get_full_name(cls):
        return f"{cls.NAME} v{cls.VERSION}"
    
    @classmethod
    def get_display_full_name(cls):
        return f"{cls.DISPLAY_NAME} v{cls.VERSION}"
    
    @classmethod
    def get_window_title(cls, username=None):
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
    def get_about_text(cls):
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
    def get_status_tip(cls):
        return (
            "提示：Ctrl+V粘贴 | 拖拽文件导入 | 左键拖动图片 | "
            "Ctrl+滚轮缩放视图 | 选中后滚轮缩放图片/Emoji | "
            "空格+左键/中键平移 | 右键菜单 | "
            "Win+; 添加表情 | 表情可吸附到图片上同步移动"
        )
    
    @classmethod
    def get_export_default_filename(cls):
        return f"stitched_image_{time.strftime('%Y%m%d_%H%M%S')}.png"


# ==================== Emoji表情图元 ====================
class EmojiItem(QGraphicsPixmapItem):
    """Emoji表情图元 - 可吸附到图片上同步移动"""
    
    def __init__(self, emoji_char, parent_item=None, font_size=48, item_id=None):
        # 创建Emoji图片
        self._font_size = font_size
        self._emoji_char = emoji_char
        pixmap = EmojiItem._render_emoji(emoji_char, font_size)
        super().__init__(pixmap)
        
        self._parent_image = None
        self._item_id = item_id or str(uuid.uuid4())[:8]
        self._offset = QPointF(0, 0)  # 相对于父图片的偏移量
        self._scale_factor = 1.0  # 缩放因子
        
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        
        # 如果有父图片，建立绑定
        if parent_item:
            self.set_parent_image(parent_item, True)  # 自动计算偏移
        
        self.setZValue(100)  # Emoji在图片之上
    
    @staticmethod
    def _render_emoji(emoji_char, font_size):
        """将Emoji字符渲染为QPixmap"""
        # 获取系统Emoji字体
        font = QFont()
        font.setPixelSize(font_size)
        # 尝试使用系统Emoji字体
        if sys.platform == "win32":
            font.setFamily("Segoe UI Emoji")
        elif sys.platform == "darwin":
            font.setFamily("Apple Color Emoji")
        else:
            font.setFamily("Noto Color Emoji")
        
        # 测量文本大小
        fm = QFontMetrics(font)
        rect = fm.boundingRect(emoji_char)
        
        # 创建真正的图片
        padding = 4
        w = max(rect.width() + padding * 2, font_size)
        h = max(rect.height() + padding * 2, font_size)
        img = QImage(w, h, QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        
        painter = QPainter(img)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(
            QRectF(padding, padding, w - padding * 2, h - padding * 2),
            Qt.AlignCenter,
            emoji_char
        )
        painter.end()
        
        return QPixmap.fromImage(img)
    
    def item_id(self):
        """获取Emoji的ID"""  # ✅ 添加这个方法
        return self._item_id
    
    def set_parent_image(self, parent_item, auto_calc_offset=True):
        if parent_item:
            if self._parent_image:
                self._parent_image.remove_attached_emoji(self)
            self._parent_image = parent_item
            if auto_calc_offset:
                # 计算相对于父项的偏移量
                parent_pos = parent_item.scenePos() if parent_item.scene() else parent_item.pos()
                self._offset = self.scenePos() - parent_pos
            self.setParentItem(parent_item)
            self.setPos(self._offset)
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
    
    def get_parent_image(self):
        """获取父图片"""
        return self._parent_image
    
    def detach_from_parent(self):
        """从父图片分离"""
        if self._parent_image:
            self._parent_image.remove_attached_emoji(self)
            scene_pos = self.scenePos()
            self.setParentItem(None)
            self.setPos(scene_pos)
            self._parent_image = None
            self._offset = QPointF(0, 0)
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
    
    def update_position_from_parent(self):
        # 作为子项，位置相对于父项自动跟随，无需额外操作
        # 仅当父项变换（旋转/缩放）时才需更新，但 Qt 会自动处理子项变换
        pass
    
    def set_scale_factor(self, factor):
        """设置Emoji缩放"""
        factor = max(0.2, min(factor, 5.0))
        if factor == self._scale_factor:
            return
        self._scale_factor = factor
        # 重新渲染Emoji
        new_size = int(self._font_size * factor)
        new_size = max(8, new_size)
        new_pixmap = EmojiItem._render_emoji(self._emoji_char, new_size)
        self.setPixmap(new_pixmap)
        # 保持位置不变
        self.setTransformOriginPoint(self.pixmap().width() / 2, self.pixmap().height() / 2)
    
    def scale_at(self, factor, scene_pos):
        """在指定位置缩放"""
        new_factor = self._scale_factor * factor
        new_factor = max(0.2, min(new_factor, 5.0))
        if new_factor == self._scale_factor:
            return
        # 计算缩放前后的中心偏移
        old_center = self.sceneBoundingRect().center()
        self.set_scale_factor(new_factor)
        new_center = self.sceneBoundingRect().center()
        offset = old_center - new_center
        self.moveBy(offset.x(), offset.y())
    
    def get_scale_factor(self):
        """获取缩放因子"""
        return self._scale_factor
    
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            # 当Emoji被拖动时，更新偏移量（保持与父图片的相对位置）
            if self._parent_image:
                parent_pos = self._parent_image.scenePos()
                self._offset = value - parent_pos
        elif change == QGraphicsItem.ItemSelectedHasChanged:
            if self.isSelected():
                self.setZValue(200)
            else:
                self.setZValue(100)
        return super().itemChange(change, value)
    
    def to_dict(self):
        return {
            "id": self.item_id(),
            "emoji": self._emoji_char,
            "font_size": self._font_size,
            "scale": self._scale_factor,
            "pos": {"x": self.pos().x(), "y": self.pos().y()},
            "z": self.zValue(),
            "parent_id": self._parent_image.item_id() if self._parent_image else None,
            "offset": {"x": self._offset.x(), "y": self._offset.y()},
        }


# ==================== Emoji选择对话框 ====================
class EmojiPickerDialog(QDialog):
    """Emoji选择对话框 - 带分类标签页"""
    
    # Emoji分类数据 - 完整版
    EMOJI_CATEGORIES = {
        "🕐 最近使用": [],  # 动态填充
        "😊 表情与情感": [
            "😀", "😁", "😂", "🤣", "😃", "😄", "😅", "😆", "😉", "😊",
            "😋", "😎", "😍", "🥰", "😘", "😗", "😙", "😚", "🙂", "🤗",
            "🤩", "🤔", "🤨", "😐", "😑", "😶", "🙄", "😏", "😣", "😥",
            "😮", "🤐", "😯", "😪", "😫", "😴", "😌", "😛", "😜", "😝",
            "🤤", "😒", "😓", "😔", "😕", "🙃", "🤑", "😲", "☹️", "🙁",
            "😖", "😞", "😟", "😤", "😢", "😭", "😦", "😧", "😨", "😩",
            "🤯", "😬", "😰", "😱", "🥵", "🥶", "😳", "🤪", "😵", "😡",
            "😠", "🤬", "😷", "🤒", "🤕", "🤢", "🤮", "🥴", "😇", "🤠",
            "🤡", "🥳", "🥺", "🤥", "🤫", "🤭", "🧐", "🤓", "😈", "👿",
            "👹", "👺", "💀", "☠️", "👻", "👽", "👾", "🤖", "💩", "😺",
            "😸", "😹", "😻", "😼", "😽", "🙀", "😿", "😾"
        ],
        "👋 手势与身体": [
            "🖐️", "✋", "👋", "🤚", "🖖", "👌", "🤌", "🤏", "✌️", "🤞",
            "🤟", "🤘", "👈", "👉", "👆", "👇", "☝️", "👍", "👎", "✊",
            "👊", "🤛", "🤜", "👏", "🙌", "👐", "🤲", "🤝", "🙏", "✍️",
            "💅", "🤳", "💪", "🦾", "🦿", "🦵", "🦶", "👂", "🦻", "👃",
            "🧠", "🫀", "🫁", "🦷", "🦴", "👀", "👁️", "👅", "👄", "🫦"
        ],
        "❤️ 爱心与符号": [
            "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔",
            "❤️‍🔥", "❤️‍🩹", "💕", "💞", "💓", "💗", "💖", "💘", "💝", "💟",
            "☮️", "✝️", "☪️", "🕉️", "☸️", "✡️", "🔯", "🕎", "☯️", "☦️",
            "🛐", "⛎", "♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏",
            "♐", "♑", "♒", "♓", "🆔", "⚛️", "🉑", "☢️", "☣️", "📴",
            "📳", "🈶", "🈚", "🈸", "🈺", "🈷️", "✴️", "🆚", "💮", "🉐",
            "㊙️", "㊗️", "🈴", "🈵", "🈹", "🈲", "🅰️", "🅱️", "🆎", "🆑",
            "🅾️", "🆘", "❌", "⭕", "🛑", "⛔", "📛", "🚫", "💯", "💢",
            "♨️", "🚷", "🚯", "🚳", "🚱", "🔞", "📵", "🚭", "❗", "❕",
            "❓", "❔", "‼️", "⁉️", "🔅", "🔆", "〽️", "⚠️", "🚸", "🔱",
            "⚜️", "🔰", "♻️", "✅", "🈯", "💹", "❇️", "✳️", "❎"
        ],
        "🌍 自然与天气": [
            "🌐", "💠", "Ⓜ️", "🌀", "💤", "💨", "💦", "💫", "🕳️", "💣",
            "💥", "🔥", "🌟", "✨", "⭐", "🌙", "☀️", "⛅", "☁️", "🌧️",
            "⛈️", "🌤️", "🌥️", "🌦️", "🌨️", "🌩️", "🌪️", "🌫️", "🌬️", "🌈",
            "☂️", "☔", "⛱️", "❄️", "☃️", "⛄", "☄️", "💧", "🌊", "🌍",
            "🌎", "🌏", "🗺️", "🧭", "🏔️", "⛰️", "🌋", "🗻", "🏕️", "🏖️",
            "🏜️", "🏝️", "🏞️"
        ],
        "🍔 食物与饮料": [
            "🍇", "🍈", "🍉", "🍊", "🍋", "🍌", "🍍", "🥭", "🍎", "🍏",
            "🍐", "🍑", "🍒", "🍓", "🫐", "🥝", "🍅", "🫒", "🥥", "🥑",
            "🍆", "🥔", "🥕", "🌽", "🌶️", "🫑", "🥒", "🥬", "🥦", "🧄",
            "🧅", "🍄", "🥜", "🫘", "🌰", "🍞", "🥐", "🥖", "🫓", "🥨",
            "🥯", "🥞", "🧇", "🧀", "🍖", "🍗", "🥩", "🥓", "🍔", "🍟",
            "🍕", "🌭", "🥪", "🌮", "🌯", "🫔", "🥙", "🧆", "🥚", "🍳",
            "🥘", "🍲", "🫕", "🥣", "🥗", "🍿", "🧈", "🧂", "🥫", "🍱",
            "🍘", "🍙", "🍚", "🍛", "🍜", "🍝", "🍠", "🍢", "🍣", "🍤",
            "🍥", "🥮", "🍡", "🥟", "🥠", "🥡", "🦪", "🍦", "🍧", "🍨",
            "🍩", "🍪", "🎂", "🍰", "🧁", "🥧", "🍫", "🍬", "🍭", "🍮",
            "🍯", "🍼", "🥛", "☕", "🫖", "🍵", "🍶", "🍾", "🍷", "🍸",
            "🍹", "🍺", "🍻", "🥂", "🥃", "🥤", "🧃", "🧉", "🧊", "🥢",
            "🍽️", "🍴", "🥄", "🔪", "🏺"
        ],
        "🏠 建筑与地点": [
            "🏠", "🏡", "🏢", "🏣", "🏤", "🏥", "🏦", "🏨", "🏩", "🏪",
            "🏫", "🏬", "🏭", "🏯", "🏰", "💒", "🗼", "🗽", "⛪", "🕌",
            "🛕", "🕍", "⛩️", "🕋", "⛲", "⛺", "🌁", "🌃", "🏙️", "🌄",
            "🌅", "🌆", "🌇", "🌉", "🏘️", "🏚️", "🏗️", "🧱", "🪨", "🪵",
            "🪹", "🪺"
        ],
        "🎨 艺术与娱乐": [
            "♠️", "♥️", "♦️", "♣️", "🃏", "🀄", "🎴", "🎭", "🖼️", "🎨",
            "🧵", "🧶", "🪡", "🪢", "👓", "🕶️", "🥽", "🥼", "🦺", "👔",
            "👕", "👖", "🧣", "🧤", "🧥", "🧦", "👗", "👘", "🥻", "🩱",
            "🩲", "🩳", "👙", "👚", "👛", "👜", "👝", "🎒", "🩴", "👞",
            "👟", "🥾", "🥿", "👠", "👡", "👢", "👑", "👒", "🎩", "🎓",
            "🧢", "🪖", "⛑️", "📿", "💄", "💍", "💎"
        ],
        "🎵 音乐与媒体": [
            "🔇", "🔈", "🔉", "🔊", "📢", "📣", "📯", "🔔", "🔕", "🎼",
            "🎵", "🎶", "🎙️", "🎚️", "🎛️", "🎤", "🎧", "📻", "🎷", "🪗",
            "🎸", "🎹", "🎺", "🎻", "🪕", "🥁", "🪘", "📱", "📲", "☎️",
            "📞", "📟", "📠", "🔋", "🪫", "🔌", "💻", "🖥️", "🖨️", "⌨️",
            "🖱️", "🖲️", "💽", "💾", "💿", "📀", "🧮", "🎥", "🎞️", "📽️",
            "🎬", "📺", "📷", "📸", "📹", "📼", "🔍", "🔎"
        ],
        "🛠️ 工具与物品": [
            "🕯️", "💡", "🔦", "🏮", "🪔", "📔", "📕", "📖", "📗", "📘",
            "📙", "📚", "📓", "📒", "📃", "📜", "📄", "📰", "🗞️", "📑",
            "🔖", "🏷️", "💰", "🪙", "💴", "💵", "💶", "💷", "💸", "💳",
            "🧾", "✉️", "📧", "📨", "📩", "📤", "📥", "📦", "📫", "📪",
            "📬", "📭", "📮", "🗳️", "✏️", "✒️", "🖋️", "🖊️", "🖌️", "🖍️",
            "📝", "💼", "📁", "📂", "🗂️", "📅", "📆", "🗒️", "🗓️", "📇",
            "📈", "📉", "📊", "📋", "📌", "📍", "📎", "🖇️", "📏", "📐",
            "✂️", "🗃️", "🗄️", "🗑️", "🔒", "🔓", "🔏", "🔐", "🔑", "🗝️",
            "🔨", "🪓", "⛏️", "⚒️", "🛠️", "🗡️", "⚔️", "🔫", "🪃", "🏹",
            "🛡️", "🪚", "🔧", "🪛", "🔩", "⚙️", "🗜️", "⚖️", "🪝", "🔗",
            "⛓️", "🪣", "🧰", "🧲", "🪜", "⚗️", "🧪", "🧫", "🧬", "🔬",
            "🔭", "📡", "💉", "🩸", "💊", "🩹", "🩺"
        ],
        "🚗 交通与出行": [
            "🚪", "🛗", "🪞", "🪟", "🛏️", "🛋️", "🪑", "🚽", "🪠", "🚿",
            "🛁", "🪥", "🧴", "🧷", "🧹", "🧺", "🧻", "🪣", "🧼", "🪥",
            "🧽", "🧯", "🛒", "🚬", "⚰️", "🪦", "⚱️", "🗿", "🪧", "🪪",
            "🏧", "🚮", "🚰", "♿", "🚹", "🚺", "🚻", "🚼", "🚾", "🛂",
            "🛃", "🛄", "🛅"
        ],
        "🔢 数字与几何": [
            "⬆️", "↗️", "➡️", "↘️", "⬇️", "↙️", "⬅️", "↖️", "↕️", "↔️",
            "↩️", "↪️", "⤴️", "⤵️", "🔃", "🔄", "🔙", "🔚", "🔛", "🔜",
            "🔝"
        ],
        "⚽ 运动与活动": [
            "⚽", "🏀", "🏈", "⚾", "🥎", "🎾", "🏐", "🏉", "🥏", "🎱",
            "🪀", "🏓", "🏸", "🏒", "🏑", "🥍", "🏏", "⛳", "🏹", "🎣",
            "🥊", "🥋", "🎽", "🛹", "🛼", "⛸️", "🥌", "🎿", "⛷️", "🏂",
            "🪂", "🏋️", "🤼", "🤸", "⛹️", "🤾", "🏌️", "🏇", "🧘", "🏄",
            "🏊", "🤽", "🚣", "🧗", "🚵", "🚴"
        ],
        "🎮 游戏与娱乐": [
            "🎮", "🕹️", "🎲", "🧩", "🧸", "🪅", "🪩", "🎪", "🃏", "🎴",
            "🎯", "🎱", "🎳", "🎰", "🎲", "🧩", "🎭", "🎨", "🎬", "🎤",
            "🎧", "🎼", "🎹", "🥁", "🎷", "🎺", "🎸", "🎻"
        ],
        "📚 学习与办公": [
            "📚", "📖", "📕", "📗", "📘", "📙", "📔", "📓", "📒", "📃",
            "📜", "📄", "📰", "🗞️", "📑", "🔖", "🏷️", "📝", "✏️", "✒️",
            "🖋️", "🖊️", "🖌️", "🖍️", "📌", "📍", "📎", "🖇️", "📏", "📐",
            "✂️", "📁", "📂", "🗂️", "📇", "📊", "📈", "📉", "📋", "📅",
            "📆", "🗒️", "🗓️", "⏰", "⏱️", "⏲️", "🕰️"
        ],
        "💻 科技与电子": [
            "💻", "🖥️", "🖨️", "⌨️", "🖱️", "🖲️", "💽", "💾", "💿", "📀",
            "🧮", "📱", "📲", "☎️", "📞", "📟", "📠", "🔋", "🪫", "🔌",
            "📡", "🔭", "🔬", "🧪", "🧫", "🧬", "💉", "💊", "🩺", "🩹",
            "🩸"
        ]
    }
    
    def __init__(self, parent=None, parent_image=None):
        super().__init__(parent)
        self.setWindowTitle("选择Emoji表情")
        self.resize(780, 600)  # 增大默认窗口
        self._parent_image = parent_image
        self._selected_emoji = None
        self._main_window = None
        self._recent_emojis = []  # 最近使用的Emoji
        self._load_recent_emojis()
        self._find_main_window(parent)
        self._build_ui()
        
        # 设置窗口属性为工具窗口
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowCloseButtonHint |
            Qt.WindowStaysOnTopHint
        )
    
    def _load_recent_emojis(self):
        """加载最近使用的Emoji"""
        settings = SettingsManager()
        recent = settings.get("recent_emojis", [])
        if isinstance(recent, list):
            self._recent_emojis = recent[:30]
    
    def _save_recent_emojis(self):
        """保存最近使用的Emoji"""
        settings = SettingsManager()
        settings.set("recent_emojis", self._recent_emojis[:30])
        settings.save()
    
    def _add_recent_emoji(self, emoji_char):
        """添加Emoji到最近使用列表"""
        if emoji_char in self._recent_emojis:
            self._recent_emojis.remove(emoji_char)
        self._recent_emojis.insert(0, emoji_char)
        if len(self._recent_emojis) > 30:
            self._recent_emojis = self._recent_emojis[:30]
        self._save_recent_emojis()
        self._update_recent_tab()
    
    def _update_recent_tab(self):
        """更新最近使用标签页"""
        # 找到最近使用标签页
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == "🕐 最近使用":
                container = self.category_widgets.get("🕐 最近使用")
                if not container:
                    continue
                
                # 清除所有子控件
                for child in container.findChildren(QPushButton):
                    child.deleteLater()
                for child in container.findChildren(QLabel):
                    child.deleteLater()
                
                grid_layout = container.layout()
                # 清除布局中的所有项
                while grid_layout.count():
                    item = grid_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                
                buttons = []
                if self._recent_emojis:
                    # 动态计算列数
                    cols = self._calc_columns()
                    for idx, emoji in enumerate(self._recent_emojis):
                        btn = QPushButton(emoji)
                        btn.setFixedSize(50, 50)
                        btn.setFont(QFont("Segoe UI Emoji", 18))
                        btn.clicked.connect(lambda checked, e=emoji: self._select_emoji(e))
                        btn.setToolTip(emoji)
                        buttons.append(btn)
                        row = idx // cols
                        col = idx % cols
                        grid_layout.addWidget(btn, row, col)
                    
                    if buttons:
                        last_row = len(buttons) // cols
                        grid_layout.setRowStretch(last_row + 1, 1)
                else:
                    label = QLabel("还没有使用过Emoji，点击选择吧！")
                    label.setAlignment(Qt.AlignCenter)
                    label.setStyleSheet("color: #888; font-size: 14px; padding: 20px;")
                    grid_layout.addWidget(label, 0, 0)
                    grid_layout.setRowStretch(1, 1)
                
                self.emoji_buttons["🕐 最近使用"] = buttons
                break
    
    def _calc_columns(self):
        """计算每行显示的列数"""
        # 根据容器宽度计算
        container_width = self.width() - 40  # 减去边距
        btn_width = 54  # 按钮宽度 + 间距
        cols = max(4, container_width // btn_width)
        return min(cols, 20)  # 最多20列
    
    def _find_main_window(self, widget):
        while widget is not None:
            if isinstance(widget, MainWindow):
                self._main_window = widget
                break
            widget = widget.parent()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # 搜索框
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 搜索:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词搜索Emoji...")
        self.search_input.textChanged.connect(self._filter_emojis)
        self.search_input.setFixedHeight(30)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # 分类标签页 - 使用默认风格
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        
        # 创建所有分类标签页
        self.category_widgets = {}
        self.emoji_buttons = {}
        
        for category_name, emojis in self.EMOJI_CATEGORIES.items():
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            
            container = QWidget()
            grid_layout = QGridLayout(container)
            grid_layout.setSpacing(6)
            grid_layout.setContentsMargins(8, 8, 8, 8)
            
            buttons = []
            if emojis:
                cols = self._calc_columns()
                for idx, emoji in enumerate(emojis):
                    btn = QPushButton(emoji)
                    btn.setFixedSize(50, 50)
                    btn.setFont(QFont("Segoe UI Emoji", 18))
                    btn.clicked.connect(lambda checked, e=emoji: self._select_emoji(e))
                    btn.setToolTip(emoji)
                    buttons.append(btn)
                    row = idx // cols
                    col = idx % cols
                    grid_layout.addWidget(btn, row, col)
                
                if buttons:
                    last_row = len(buttons) // cols
                    grid_layout.setRowStretch(last_row + 1, 1)
            else:
                # 最近使用标签页，先占位，稍后更新
                label = QLabel("加载中...")
                label.setAlignment(Qt.AlignCenter)
                label.setStyleSheet("color: #888; font-size: 14px; padding: 20px;")
                grid_layout.addWidget(label, 0, 0)
                grid_layout.setRowStretch(1, 1)
            
            scroll.setWidget(container)
            self.tab_widget.addTab(scroll, category_name)
            self.category_widgets[category_name] = container
            self.emoji_buttons[category_name] = buttons
        
        layout.addWidget(self.tab_widget, 1)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_add_to_image = QPushButton("📌 添加到选中的图片")
        self.btn_add_to_image.clicked.connect(self._add_to_selected_image)
        self.btn_add_to_image.setEnabled(False)
        btn_layout.addWidget(self.btn_add_to_image)
        
        self.btn_add_to_canvas = QPushButton("➕ 添加到画布")
        self.btn_add_to_canvas.clicked.connect(self._add_to_canvas)
        btn_layout.addWidget(self.btn_add_to_canvas)
        
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(btn_layout)
        
        self._update_selection_status()
        self.resizeEvent = self._on_resize
        
        # 在UI完全构建后更新最近使用标签页
        QTimer.singleShot(50, self._update_recent_tab)
    
    def _on_resize(self, event):
        """窗口大小变化时重新布局"""
        super().resizeEvent(event)
        # 重新计算所有分类的列数
        self._reflow_all_categories()
    
    def _reflow_all_categories(self):
        """重新排列所有分类的Emoji"""
        cols = self._calc_columns()
        for category_name, buttons in self.emoji_buttons.items():
            if not buttons:
                continue
            container = self.category_widgets.get(category_name)
            if not container:
                continue
            grid_layout = container.layout()
            if not grid_layout:
                continue
            
            # 重新排列按钮
            for idx, btn in enumerate(buttons):
                row = idx // cols
                col = idx % cols
                grid_layout.addWidget(btn, row, col)
            
            # 添加弹性空间
            if buttons:
                last_row = len(buttons) // cols
                grid_layout.setRowStretch(last_row + 1, 1)
    
    def _filter_emojis(self, text):
        """根据搜索文本过滤所有分类中的Emoji"""
        text = text.strip().lower()
        
        if not text:
            for i in range(self.tab_widget.count()):
                self.tab_widget.setTabVisible(i, True)
            for category, buttons in self.emoji_buttons.items():
                for btn in buttons:
                    if btn:
                        btn.setVisible(True)
            return
        
        for category, buttons in self.emoji_buttons.items():
            has_match = False
            for btn in buttons:
                if not btn:
                    continue
                emoji = btn.text()
                visible = text in emoji or any(
                    text in c for c in emoji if ord(c) > 127
                )
                btn.setVisible(visible)
                if visible:
                    has_match = True
            
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == category:
                    self.tab_widget.setTabVisible(i, has_match)
                    if has_match:
                        self.tab_widget.setCurrentIndex(i)
                    break
    def _select_emoji(self, emoji_char):
        """选择Emoji"""
        self._selected_emoji = emoji_char
        self._add_recent_emoji(emoji_char)
        self._update_selection_status()
        
        # 简单高亮选中的按钮（使用默认风格）
        for category, buttons in self.emoji_buttons.items():
            for btn in buttons:
                if btn and btn.text() == emoji_char:
                    btn.setStyleSheet("background-color: #e0e0e0; border: 2px solid #4a8ec5;")
                elif btn:
                    btn.setStyleSheet("")  # 恢复默认
    
    def _update_selection_status(self):
        has_selection = self._selected_emoji is not None
        self.btn_add_to_image.setEnabled(has_selection)
        self.btn_add_to_canvas.setEnabled(has_selection)
        
        if has_selection:
            self.setWindowTitle(f"选择Emoji表情 - 已选: {self._selected_emoji}")
    
    def _add_to_selected_image(self):
        if not self._selected_emoji or not self._main_window:
            return
        
        selected = [i for i in self._main_window.scene.selectedItems() 
                   if isinstance(i, MovableImageItem)]
        
        if not selected:
            QMessageBox.information(
                self, "提示", 
                "请先在画布上选中一张图片，然后点击此按钮添加Emoji。\n"
                "Emoji会自动吸附到该图片上，随图片一起移动。"
            )
            return
        
        parent_img = selected[0]
        self._main_window.add_emoji_to_image(self._selected_emoji, parent_img)
        self.accept()
    
    def _add_to_canvas(self):
        if not self._selected_emoji or not self._main_window:
            return
        
        self._main_window.add_emoji_to_canvas(self._selected_emoji)
        self.accept()

# ==================== 可移动图片图元 ====================
class MovableImageItem(QGraphicsPixmapItem):
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
        self._flipped_h = False
        self._flipped_v = False
        self._item_id = item_id or str(uuid.uuid4())[:8]
        self._attached_emojis = []  # 吸附的Emoji列表
        self.setAcceptHoverEvents(True)
        self.setOpacity(self._opacity)
        self.setTransformOriginPoint(pixmap.width() / 2, pixmap.height() / 2)

    def item_id(self):
        """获取Emoji的ID"""
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
        opacity = max(0.0, min(opacity, 1.0))
        self._opacity = opacity
        self.setOpacity(opacity)

    def rotation_value(self):
        return self._rotation

    def set_rotation_deg(self, degrees):
        self._rotation = degrees % 360
        self.setRotation(self._rotation)

    def rotate_by(self, degrees):
        self.set_rotation_deg(self._rotation + degrees)

    def reset_rotation(self):
        self.set_rotation_deg(0.0)

    def is_flipped_horizontal(self):
        return self._flipped_h

    def is_flipped_vertical(self):
        return self._flipped_v

    def flip_horizontal(self):
        self._flipped_h = not self._flipped_h
        self._apply_flip()

    def flip_vertical(self):
        self._flipped_v = not self._flipped_v
        self._apply_flip()

    def reset_flip(self):
        if self._flipped_h or self._flipped_v:
            self._flipped_h = False
            self._flipped_v = False
            self._apply_flip()

    def _apply_flip(self):
        center = self.sceneBoundingRect().center()
        transform = QTransform()
        if self._flipped_h:
            transform.scale(-1, 1)
        if self._flipped_v:
            transform.scale(1, -1)
        flipped = self._original_pixmap.transformed(transform, Qt.SmoothTransformation)
        settings = SettingsManager()
        transform_mode = Qt.SmoothTransformation if settings.get("smooth_pixmap", True) else Qt.FastTransformation
        new_size = self._base_size * self._scale_factor
        scaled = flipped.scaled(
            int(new_size.width()), int(new_size.height()),
            Qt.KeepAspectRatio, transform_mode
        )
        self.setPixmap(scaled)
        self.setTransformOriginPoint(self.pixmap().width() / 2, self.pixmap().height() / 2)
        new_center = self.sceneBoundingRect().center()
        offset = center - new_center
        self.moveBy(offset.x(), offset.y())

    def set_scale_factor(self, factor):
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
        self.setTransformOriginPoint(self.pixmap().width() / 2, self.pixmap().height() / 2)
        new_center = self.sceneBoundingRect().center()
        offset = center - new_center
        self.moveBy(offset.x(), offset.y())

    def scale_at(self, factor, scene_pos):
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
        self.setTransformOriginPoint(self.pixmap().width() / 2, self.pixmap().height() / 2)
        new_local_x = rel_x * self.pixmap().width()
        new_local_y = rel_y * self.pixmap().height()
        new_scene = self.mapToScene(QPointF(new_local_x, new_local_y))
        delta = scene_pos - new_scene
        self.moveBy(delta.x(), delta.y())

    def add_attached_emoji(self, emoji_item):
        if emoji_item not in self._attached_emojis:
            self._attached_emojis.append(emoji_item)
            emoji_item.set_parent_image(self, True)  # 自动计算偏移

    def remove_attached_emoji(self, emoji_item):
        """移除吸附的Emoji"""
        if emoji_item in self._attached_emojis:
            self._attached_emojis.remove(emoji_item)

    def get_attached_emojis(self):
        """获取所有吸附的Emoji"""
        return list(self._attached_emojis)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            # 当图片移动时，更新吸附的Emoji位置
            for emoji in self._attached_emojis:
                if emoji and emoji.scene():
                    emoji.update_position_from_parent()
        elif change == QGraphicsItem.ItemSelectedHasChanged:
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
        return {
            "id": self._item_id,
            "pos": {"x": self.pos().x(), "y": self.pos().y()},
            "scale": self._scale_factor,
            "opacity": self._opacity,
            "rotation": self._rotation,
            "flipped_h": self._flipped_h,
            "flipped_v": self._flipped_v,
            "z": self.zValue(),
            "attached_emojis": [
                {
                    "id": e.item_id(),
                    "emoji": e._emoji_char,
                    "font_size": e._font_size,
                    "scale": e.get_scale_factor(),
                    "offset": {"x": e._offset.x(), "y": e._offset.y()},
                    "z": e.zValue(),
                }
                for e in self._attached_emojis
            ]
        }


# ==================== 差异标记图元 ====================
class DiffMarkerItem(QGraphicsRectItem):
    def __init__(self, rect, parent=None):
        super().__init__(rect, parent)
        self.setPen(QPen(QColor(255, 0, 0), 2))
        self.setBrush(QBrush(QColor(255, 0, 0, 80)))
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setZValue(9999)


# ==================== 画布视图 ====================
class ImageCanvasView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self._settings = SettingsManager()
        self._apply_render_hints()
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self._bg_cache = BackgroundCache()
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._panning = False
        self._pan_start = QPointF()
        self._space_pressed = False
        self._main_window = None
        self._min_zoom = 0.05
        self._max_zoom = 10.0
        self._right_menu_closed_at = 0
        self._right_menu_cooldown_ms = 150
        # 缓存背景图像
        self._cached_bg_pixmap = None
        self._cached_bg_size = None
        self._bg_dirty = True  # 新增：标记背景是否需要重新生成

    def _apply_render_hints(self):
        hints = QPainter.TextAntialiasing
        if self._settings.get("antialiasing", True):
            hints |= QPainter.Antialiasing
        if self._settings.get("smooth_pixmap", True):
            hints |= QPainter.SmoothPixmapTransform
        self.setRenderHints(hints)

    def drawBackground(self, painter, rect):
        """重写背景绘制，实现拉伸填充，彻底解决平铺问题"""
        if self.viewport():
            size = self.viewport().size()
        else:
            size = QSize(800, 600)
        
        # 如果缓存尺寸变化、背景脏或缓存为空，重新生成背景
        if (self._cached_bg_pixmap is None or 
            self._cached_bg_size != size or
            self._bg_dirty):
            # 清除缓存确保获取最新背景
            self._bg_cache.clear()
            bg_img = self._bg_cache.get_background(
                self._settings._settings, size.width(), size.height()
            )
            self._cached_bg_pixmap = QPixmap.fromImage(bg_img)
            self._cached_bg_size = size
            self._bg_dirty = False
        
        # 直接绘制背景，拉伸到整个视口
        if self._cached_bg_pixmap and not self._cached_bg_pixmap.isNull():
            painter.drawPixmap(rect, self._cached_bg_pixmap, 
                              QRectF(0, 0, self._cached_bg_pixmap.width(), 
                                    self._cached_bg_pixmap.height()))

    def mark_background_dirty(self):
        """标记背景需要重新生成（当场景发生变化时调用）"""
        self._bg_dirty = True
        self.viewport().update()

    def update_background(self):
        """手动更新背景"""
        self._bg_cache.clear()
        self._cached_bg_pixmap = None
        self._cached_bg_size = None
        self._bg_dirty = True
        self.viewport().update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 窗口大小变化时，标记背景需要重新生成
        self._bg_dirty = True
        self.viewport().update()

    def apply_settings(self):
        self._apply_render_hints()
        self.update_background()

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
            elif isinstance(item, EmojiItem):
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
        if self._right_menu_closed_at > 0:
            elapsed = (time.time() - self._right_menu_closed_at) * 1000
            if elapsed < self._right_menu_cooldown_ms:
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
            elif isinstance(item, EmojiItem):
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
        
        # 通用操作
        paste_act = menu.addAction("📋 粘贴图片")
        menu.addSeparator()
        
        # Emoji相关操作
        emoji_menu = menu.addMenu("😀 添加Emoji")
        add_emoji_act = emoji_menu.addAction("➕ 从选择器添加...")
        add_to_image_act = emoji_menu.addAction("📌 添加到选中图片")
        menu.addSeparator()
        
        # 初始化所有可能用到的变量
        add_emoji_canvas_act = None
        
        # 根据选中对象显示不同菜单
        if isinstance(item, MovableImageItem):
            # 图片菜单
            delete_act = menu.addAction("🗑️ 删除")
            menu.addSeparator()
            zoom_in_act = menu.addAction("🔍 放大")
            zoom_out_act = menu.addAction("🔍 缩小")
            reset_act = menu.addAction("↩️ 重置大小")
            menu.addSeparator()
            opacity_menu = menu.addMenu("🎨 透明度")
            opa_100 = opacity_menu.addAction("100% (不透明)")
            opa_75 = opacity_menu.addAction("75%")
            opa_50 = opacity_menu.addAction("50% (半透明)")
            opa_25 = opacity_menu.addAction("25%")
            opa_10 = opacity_menu.addAction("10%")
            menu.addSeparator()
            rotate_menu = menu.addMenu("🔄 旋转")
            rot_cw90 = rotate_menu.addAction("顺时针 90°")
            rot_ccw90 = rotate_menu.addAction("逆时针 90°")
            rot_180 = rotate_menu.addAction("旋转 180°")
            rot_cw45 = rotate_menu.addAction("顺时针 45°")
            rot_ccw45 = rotate_menu.addAction("逆时针 45°")
            rot_reset = rotate_menu.addAction("重置 0°")
            menu.addSeparator()
            flip_menu = menu.addMenu("🪞 镜像翻转")
            flip_h = flip_menu.addAction("水平翻转 (左右)")
            flip_v = flip_menu.addAction("垂直翻转 (上下)")
            flip_reset = flip_menu.addAction("重置翻转")
            menu.addSeparator()
            front_act = menu.addAction("⬆️ 置顶")
            back_act = menu.addAction("⬇️ 置底")
            menu.addSeparator()
            # Emoji管理
            emoji_mgmt = menu.addMenu("😊 管理Emoji")
            detach_all_act = emoji_mgmt.addAction("分离所有Emoji")
            menu.addSeparator()
            
        elif isinstance(item, EmojiItem):
            # Emoji菜单
            delete_emoji_act = menu.addAction("🗑️ 删除Emoji")
            menu.addSeparator()
            emoji_zoom_in_act = menu.addAction("🔍 放大Emoji")
            emoji_zoom_out_act = menu.addAction("🔍 缩小Emoji")
            emoji_reset_act = menu.addAction("↩️ 重置Emoji大小")
            menu.addSeparator()
            detach_emoji_act = menu.addAction("↗️ 从图片分离")
            attach_emoji_act = menu.addAction("📌 吸附到选中图片")
            menu.addSeparator()
        else:
            # 空白处菜单
            view_zoom_in_act = menu.addAction("🔍 视图放大")
            view_zoom_out_act = menu.addAction("🔍 视图缩小")
            view_reset_act = menu.addAction("↩️ 视图重置 (100%)")
            view_fit_act = menu.addAction("📐 适配全部")
            menu.addSeparator()
            clear_diff_act = menu.addAction("🧹 清除差异标记")
            menu.addSeparator()
            all_rotate_menu = menu.addMenu("🔄 整体旋转")
            all_rot_cw90 = all_rotate_menu.addAction("全部顺时针 90°")
            all_rot_ccw90 = all_rotate_menu.addAction("全部逆时针 90°")
            all_rot_180 = all_rotate_menu.addAction("全部旋转 180°")
            all_rot_cw45 = all_rotate_menu.addAction("全部顺时针 45°")
            all_rot_ccw45 = all_rotate_menu.addAction("全部逆时针 45°")
            all_rot_reset = all_rotate_menu.addAction("全部重置 0°")
            menu.addSeparator()
            all_flip_menu = menu.addMenu("🪞 整体镜像翻转")
            all_flip_h = all_flip_menu.addAction("全部水平翻转")
            all_flip_v = all_flip_menu.addAction("全部垂直翻转")
            menu.addSeparator()
            # 添加Emoji到画布
            add_emoji_canvas_act = menu.addAction("😀 添加Emoji到画布")

        action = menu.exec(global_pos)
        self._right_menu_closed_at = time.time()

        if not action:
            return
        
        # ====== 通用操作 ======
        if action == paste_act and self._main_window:
            self._main_window.paste_from_clipboard()
            return
        
        # ====== Emoji选择器 ======
        if action == add_emoji_act and self._main_window:
            # 获取选中的图片作为父对象
            selected = [i for i in self.scene().selectedItems() 
                       if isinstance(i, MovableImageItem)]
            parent_img = selected[0] if selected else None
            self._main_window.show_emoji_picker(parent_img)
            return
        
        if action == add_to_image_act and self._main_window:
            selected = [i for i in self.scene().selectedItems() 
                       if isinstance(i, MovableImageItem)]
            if selected:
                self._main_window.show_emoji_picker(selected[0])
            else:
                QMessageBox.information(
                    self._main_window, "提示", 
                    "请先在画布上选中一张图片，然后点击此操作添加Emoji。"
                )
            return
        
        if add_emoji_canvas_act and action == add_emoji_canvas_act and self._main_window:
            self._main_window.show_emoji_picker(None)
            return
        
        # ====== 图片操作 ======
        if isinstance(item, MovableImageItem):
            if action == delete_act:
                # 删除图片时，同时删除吸附的Emoji
                for emoji in item.get_attached_emojis():
                    self.scene().removeItem(emoji)
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
            elif action == detach_all_act:
                for emoji in item.get_attached_emojis():
                    emoji.detach_from_parent()
                if self._main_window:
                    self._main_window.schedule_autosave()
        
        # ====== Emoji操作 ======
        elif isinstance(item, EmojiItem):
            if action == delete_emoji_act:
                if item.get_parent_image():
                    item.get_parent_image().remove_attached_emoji(item)
                self.scene().removeItem(item)
                if self._main_window:
                    self._main_window.schedule_autosave()
            elif action == emoji_zoom_in_act:
                item.scale_at(1.3, item.scenePos())
                if self._main_window:
                    self._main_window.update_status(item)
                    self._main_window.schedule_autosave()
            elif action == emoji_zoom_out_act:
                item.scale_at(1 / 1.3, item.scenePos())
                if self._main_window:
                    self._main_window.update_status(item)
                    self._main_window.schedule_autosave()
            elif action == emoji_reset_act:
                item.set_scale_factor(1.0)
                if self._main_window:
                    self._main_window.update_status(item)
                    self._main_window.schedule_autosave()
            elif action == detach_emoji_act:
                item.detach_from_parent()
                if self._main_window:
                    self._main_window.schedule_autosave()
            elif action == attach_emoji_act:
                selected = [i for i in self.scene().selectedItems() 
                           if isinstance(i, MovableImageItem) and i != item]
                if selected:
                    parent_img = selected[0]
                    item.detach_from_parent()
                    parent_img.add_attached_emoji(item)
                    item.update_position_from_parent()
                    if self._main_window:
                        self._main_window.schedule_autosave()
                else:
                    QMessageBox.information(
                        self._main_window, "提示", 
                        "请先选中一张图片作为吸附目标。"
                    )
        
        # ====== 空白处操作 ======
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
        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self._on_select)
        splitter.addWidget(self.list_widget)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.preview_label = QLabel("选择一个历史项目查看预览")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(300, 300)
        self.preview_label.setStyleSheet(
            "border: 1px solid #555; background: #2b2b2b; color: #888;"
        )
        right_layout.addWidget(self.preview_label, 1)
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #aaa; padding: 5px;")
        right_layout.addWidget(self.info_label)
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
    def __init__(self):
        ensure_dirs()
        self.state_file = os.path.join(AUTOSAVE_DIR, "state.json")
        self.images_dir = os.path.join(AUTOSAVE_DIR, "images")

    def save_state(self, items):
        state = {"version": 1, "timestamp": time.time(), "images": [], "emojis": []}
        
        # 保存图片（包含吸附的Emoji信息）
        for item in items:
            if isinstance(item, MovableImageItem):
                iid = item.item_id()
                img_path = os.path.join(self.images_dir, f"{iid}.png")
                item.original_pixmap().save(img_path, "PNG")
                info = item.to_dict()
                info["image_file"] = f"{iid}.png"
                state["images"].append(info)
            elif isinstance(item, EmojiItem) and not item.get_parent_image():
                # 只保存独立Emoji（吸附的在图片的to_dict中已包含）
                state["emojis"].append(item.to_dict())
        
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def has_autosave(self):
        return os.path.exists(self.state_file)

    def load_state(self, scene, add_callback):
        if not self.has_autosave():
            return 0
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            return 0
        count = 0
        image_items = {}  # 用于建立ID到图片的映射
        
        # 加载图片
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
            image_items[item.item_id()] = item
            count += 1
        
        # 加载吸附的Emoji（从图片的attached_emojis中恢复）
        for img_info in state.get("images", []):
            parent_id = img_info.get("id")
            parent_img = image_items.get(parent_id)
            if not parent_img:
                continue
            for emoji_info in img_info.get("attached_emojis", []):
                emoji_char = emoji_info.get("emoji", "😀")
                font_size = emoji_info.get("font_size", 48)
                scale = emoji_info.get("scale", 1.0)
                offset = emoji_info.get("offset", {"x": 0, "y": 0})
                
                # 创建Emoji，不自动吸附
                emoji = EmojiItem(emoji_char, parent_item=None, font_size=font_size, item_id=emoji_info.get("id"))
                emoji.set_scale_factor(scale)
                emoji._offset = QPointF(offset.get("x", 0), offset.get("y", 0))
                # 使用 auto_calc_offset=False 保持偏移量不变
                emoji.set_parent_image(parent_img, False)  # 关键修改
                emoji.setZValue(emoji_info.get("z", 100))
                emoji._parent_image = parent_img
                parent_img._attached_emojis.append(emoji)
                count += 1
        
        # 加载独立Emoji
        for emoji_info in state.get("emojis", []):
            emoji_char = emoji_info.get("emoji", "😀")
            font_size = emoji_info.get("font_size", 48)
            emoji = EmojiItem(emoji_char, font_size=font_size, item_id=emoji_info.get("id"))
            scale = emoji_info.get("scale", 1.0)
            emoji.set_scale_factor(scale)
            pos = emoji_info.get("pos", {})
            emoji.setPos(pos.get("x", 0), pos.get("y", 0))
            emoji.setZValue(emoji_info.get("z", 100))
            scene.addItem(emoji)
            count += 1
        
        return count


# ==================== 历史记录管理器 ====================
class HistoryManager:
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
        ensure_dirs()
        settings = SettingsManager()
        max_items = settings.get_max_history()

        hid = str(uuid.uuid4())[:8]
        ts = time.time()
        title = title or time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))
        state_dir = os.path.join(HISTORY_DIR, hid)
        os.makedirs(state_dir, exist_ok=True)
        state = {"version": 1, "timestamp": ts, "images": [], "emojis": []}
        all_rect = QRectF()
        movable_items = [i for i in items if isinstance(i, MovableImageItem)]
        
        for item in movable_items:
            all_rect = all_rect.united(item.sceneBoundingRect())
        
        # 保存图片（包含吸附的Emoji信息）
        for item in movable_items:
            iid = item.item_id()
            img_path = os.path.join(state_dir, f"{iid}.png")
            item.original_pixmap().save(img_path, "PNG")
            info = item.to_dict()
            info["image_file"] = f"{iid}.png"
            state["images"].append(info)
        
        # 保存独立Emoji
        for item in items:
            if isinstance(item, EmojiItem) and not item.get_parent_image():
                state["emojis"].append(item.to_dict())
        
        state_path = os.path.join(state_dir, "state.json")
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        thumb_path = os.path.join(state_dir, "thumb.png")
        self._render_thumbnail(movable_items, all_rect, thumb_path)
        entry = {
            "id": hid,
            "title": title,
            "timestamp": ts,
            "image_count": len(movable_items),
        }
        self._index.insert(0, entry)
        if max_items is not None and len(self._index) > max_items:
            old = self._index[max_items:]
            self._index = self._index[:max_items]
            for e in old:
                self._delete_history_dir(e["id"])
        self._save_index()
        return hid

    def _render_thumbnail(self, items, bounds, output_path, max_size=400):
        if not items or bounds.isEmpty():
            return
        margin = 20
        w = bounds.width() + margin * 2
        h = bounds.height() + margin * 2
        scale = min(max_size / w, max_size / h, 1.0)
        tw = int(w * scale)
        th = int(h * scale)
        img = QImage(tw, th, QImage.Format_ARGB32)
        settings = SettingsManager()
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
        image_items = {}
        
        # 加载图片
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
            image_items[item.item_id()] = item
            count += 1
        
        # 加载吸附的Emoji（从图片的attached_emojis中恢复）
        for img_info in state.get("images", []):
            parent_id = img_info.get("id")
            parent_img = image_items.get(parent_id)
            if not parent_img:
                continue
            for emoji_info in img_info.get("attached_emojis", []):
                emoji_char = emoji_info.get("emoji", "😀")
                font_size = emoji_info.get("font_size", 48)
                scale = emoji_info.get("scale", 1.0)
                offset = emoji_info.get("offset", {"x": 0, "y": 0})
                
                # 创建Emoji，不自动吸附
                emoji = EmojiItem(emoji_char, parent_item=None, font_size=font_size, item_id=emoji_info.get("id"))
                emoji.set_scale_factor(scale)
                emoji._offset = QPointF(offset.get("x", 0), offset.get("y", 0))
                # 使用 auto_calc_offset=False 保持偏移量不变
                emoji.set_parent_image(parent_img, False)  # 关键修改
                emoji.setZValue(emoji_info.get("z", 100))
                emoji._parent_image = parent_img
                parent_img._attached_emojis.append(emoji)
                count += 1
        
        # 加载独立Emoji
        for emoji_info in state.get("emojis", []):
            emoji_char = emoji_info.get("emoji", "😀")
            font_size = emoji_info.get("font_size", 48)
            emoji = EmojiItem(emoji_char, font_size=font_size, item_id=emoji_info.get("id"))
            scale = emoji_info.get("scale", 1.0)
            emoji.set_scale_factor(scale)
            pos = emoji_info.get("pos", {})
            emoji.setPos(pos.get("x", 0), pos.get("y", 0))
            emoji.setZValue(emoji_info.get("z", 100))
            scene.addItem(emoji)
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
        self.setWindowTitle(ProjectInfo.get_window_title())
        self.resize(1200, 800)
        self._set_app_icon()
        self._autosave_mgr = AutoSaveManager()
        self._history_mgr = HistoryManager()
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._do_autosave)
        self._diff_markers = []
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(-5000, -5000, 10000, 10000)
        self.view = ImageCanvasView(self.scene, self)
        self.view.set_main_window(self)
        self.setCentralWidget(self.view)
        self._toolbar_widgets = {}
        self._toolbar_actions = {}
        self._build_toolbar()
        self._build_statusbar()
        self._z_counter = 0
        self._global_opacity = 1.0
        QTimer.singleShot(50, self.apply_toolbar_visibility)
        self._try_restore_autosave()
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
        self._toolbar = QToolBar("工具栏", self)
        self._toolbar.setMovable(False)
        self._toolbar.setAllowedAreas(Qt.TopToolBarArea)
        self._toolbar.setStyleSheet("""
            QToolBar { spacing: 2px; padding: 2px; }
            QPushButton { padding: 4px 8px; min-height: 24px; font-size: 12px; }
            QLabel { font-size: 12px; }
        """)
        self.addToolBar(self._toolbar)

        widgets = {}
        actions = {}

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

        # Emoji按钮
        btn_emoji = QPushButton("😀 添加表情")
        btn_emoji.setToolTip("打开Emoji选择器添加表情 (Win+;)")
        btn_emoji.clicked.connect(lambda: self.show_emoji_picker(None))
        act_emoji = self._toolbar.addWidget(btn_emoji)
        actions["btn_emoji"] = act_emoji
        widgets["btn_emoji"] = btn_emoji

        btn_emoji_favorites = QPushButton("⭐ 常用")
        btn_emoji_favorites.setToolTip("快速添加常用Emoji到画布")
        btn_emoji_favorites.clicked.connect(self.show_favorite_emojis)
        act_emoji_fav = self._toolbar.addWidget(btn_emoji_favorites)
        actions["btn_emoji_favorites"] = act_emoji_fav
        widgets["btn_emoji_favorites"] = btn_emoji_favorites

        sep10 = self._toolbar.addSeparator()
        actions["sep10"] = sep10

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

        sep11 = self._toolbar.addSeparator()
        actions["sep11"] = sep11

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

        sep12 = self._toolbar.addSeparator()
        actions["sep12"] = sep12

        btn_settings = QPushButton("设置")
        btn_settings.setToolTip("打开选项设置")
        btn_settings.clicked.connect(self.show_settings)
        act_settings = self._toolbar.addWidget(btn_settings)
        actions["btn_settings"] = act_settings
        widgets["btn_settings"] = btn_settings

        self._toolbar_widgets = widgets
        self._toolbar_actions = actions

    def apply_toolbar_visibility(self):
        visibility = self._settings.get_toolbar_visibility()
        widget_keys = {
            "btn_import": "btn_import", "btn_paste": "btn_paste", "btn_del": "btn_del",
            "btn_zoom_in": "btn_zoom_in", "btn_zoom_out": "btn_zoom_out", "btn_reset": "btn_reset",
            "btn_rot_left": "btn_rot_left", "btn_rot_right": "btn_rot_right",
            "btn_flip_h": "btn_flip_h", "btn_flip_v": "btn_flip_v",
            "btn_view_in": "btn_view_in", "btn_view_out": "btn_view_out", "btn_view_fit": "btn_view_fit",
            "btn_front": "btn_front", "btn_back": "btn_back",
            "lbl_item": "item_opacity", "sld_item_opacity": "item_opacity", "lbl_item_opacity": "item_opacity",
            "lbl_global": "global_opacity", "sld_global_opacity": "global_opacity", "lbl_global_opacity": "global_opacity",
            "btn_diff": "btn_diff", "btn_clear_diff": "btn_clear_diff",
            "btn_save_hist": "btn_save_hist", "btn_history": "btn_history",
            "btn_export": "btn_export", "btn_clear": "btn_clear", "btn_settings": "btn_settings",
            "btn_emoji": "btn_emoji", "btn_emoji_favorites": "btn_emoji_favorites",
        }
        sep_keys = ["sep1", "sep2", "sep3", "sep4", "sep5", "sep6", "sep7", "sep8", "sep9", "sep10", "sep11", "sep12"]
        
        for action_name, action in self._toolbar_actions.items():
            if action_name in widget_keys:
                key = widget_keys[action_name]
                visible = visibility.get(key, True)
                action.setVisible(visible)
            elif action_name in sep_keys:
                action.setVisible(True)
        
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
        
        for i, info in enumerate(items_info):
            if info["type"] == "separator":
                prev_visible = False
                for j in range(i - 1, -1, -1):
                    if items_info[j]["type"] == "widget":
                        prev_visible = items_info[j]["visible"]
                        break
                next_visible = False
                for j in range(i + 1, len(items_info)):
                    if items_info[j]["type"] == "widget":
                        next_visible = items_info[j]["visible"]
                        break
                sep_visible = prev_visible and next_visible
                info["action"].setVisible(sep_visible)
        
        self._toolbar.update()
        self._toolbar.repaint()
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
            emoji_count = len(item.get_attached_emojis())
            self.status_label.setText(
                f"已选中图片 - 位置:({int(pos.x())},{int(pos.y())})  "
                f"缩放:{item.scale_factor():.0%}  "
                f"旋转:{item.rotation_value():.0f}°  "
                f"透明:{item.opacity_value():.0%}  "
                f"原始:{size.width()}x{size.height()}  "
                f"吸附Emoji:{emoji_count}个"
            )
            self.sld_item_opacity.blockSignals(True)
            self.sld_item_opacity.setValue(int(item.opacity_value() * 100))
            self.sld_item_opacity.blockSignals(False)
            self.lbl_item_opacity.setText(f"{int(item.opacity_value() * 100)}%")
        elif isinstance(item, EmojiItem):
            parent = item.get_parent_image()
            parent_info = f"吸附于: {parent.item_id()[:6]}" if parent else "独立"
            self.status_label.setText(
                f"Emoji: {item._emoji_char}  "
                f"位置:({int(item.pos().x())},{int(item.pos().y())})  "
                f"大小:{item.get_scale_factor():.0%}  "
                f"{parent_info}"
            )
        else:
            self.status_label.setText(ProjectInfo.get_status_tip())

    def show_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    def apply_settings(self):
        self._autosave_timer.setInterval(self._settings.get_autosave_delay())
        self.view.apply_settings()

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
        for item in self.scene.items():
            if isinstance(item, MovableImageItem):
                item.setOpacity(item._opacity * self._global_opacity)

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
        item.setOpacity(item._opacity * self._global_opacity)
        self.scene.addItem(item)
        self.scene.clearSelection()
        item.setSelected(True)
        self.update_status(item)
        self.schedule_autosave()
        self.view.mark_background_dirty()
        return item

    def _on_item_added(self, item):
        if isinstance(item, MovableImageItem):
            z = item.zValue()
            if z > self._z_counter:
                self._z_counter = int(z)
            item.setData(0, z)
            self.view.mark_background_dirty()

    # ==================== Emoji相关方法 ====================
    
    def show_emoji_picker(self, parent_image=None):
        """显示Emoji选择器"""
        dlg = EmojiPickerDialog(self, parent_image)
        dlg.exec()

    def show_favorite_emojis(self):
        """显示常用Emoji快速选择菜单"""
        menu = QMenu(self)
        
        # 显示前20个常用Emoji
        for emoji in COMMON_EMOJIS[:24]:
            act = menu.addAction(emoji)
            act.setFont(QFont("Segoe UI Emoji", 14))
            act.triggered.connect(lambda checked, e=emoji: self._add_emoji_to_selected_or_canvas(e))
        
        menu.addSeparator()
        open_picker = menu.addAction("📂 打开完整选择器...")
        open_picker.triggered.connect(lambda: self.show_emoji_picker(None))
        
        # 在鼠标位置显示
        menu.exec(QCursor.pos())

    def _add_emoji_to_selected_or_canvas(self, emoji_char):
        """将Emoji添加到选中的图片或画布"""
        # 检查是否有选中的图片
        selected = [i for i in self.scene.selectedItems() if isinstance(i, MovableImageItem)]
        if selected:
            self.add_emoji_to_image(emoji_char, selected[0])
        else:
            self.add_emoji_to_canvas(emoji_char)

    def add_emoji_to_image(self, emoji_char, parent_image):
        """将Emoji添加到指定图片并吸附"""
        if not parent_image or not isinstance(parent_image, MovableImageItem):
            return
        
        center = parent_image.boundingRect().center()
        emoji = EmojiItem(emoji_char, font_size=48)
        
        # 先添加到场景（作为独立项）
        self.scene.addItem(emoji)
        # 设置场景位置为父图片中心
        emoji.setPos(parent_image.scenePos() + center)
        
        # 计算相对于父图片的偏移
        parent_pos = parent_image.scenePos()
        emoji._offset = emoji.scenePos() - parent_pos
        
        # 设置为父项的子项
        emoji.setParentItem(parent_image)
        emoji.setPos(emoji._offset)  # 使用偏移量作为本地坐标
        emoji._parent_image = parent_image
        
        # 添加到父图片的吸附列表
        parent_image._attached_emojis.append(emoji)
        
        emoji.setZValue(100)
        self.scene.clearSelection()
        emoji.setSelected(True)
        self.update_status(emoji)
        self.schedule_autosave()
        self.view.mark_background_dirty()

    def add_emoji_to_canvas(self, emoji_char):
        """将Emoji独立添加到画布"""
        center = self.view.mapToScene(self.view.viewport().rect().center())
        emoji = EmojiItem(emoji_char, font_size=48)
        emoji.setPos(center)
        emoji.setZValue(100)
        
        self.scene.addItem(emoji)
        self.scene.clearSelection()
        emoji.setSelected(True)
        self.update_status(emoji)
        self.schedule_autosave()
        self.view.mark_background_dirty()

    def keyPressEvent(self, event):
        # Win+; 打开Emoji选择器
        if event.key() == Qt.Key_Semicolon and event.modifiers() == Qt.MetaModifier:
            self.show_emoji_picker(None)
            event.accept()
            return
        
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.view.set_space_pressed(True)
            event.accept()
            return
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            # 检查是否选中了Emoji或图片
            selected = self.scene.selectedItems()
            if selected:
                for item in selected:
                    if isinstance(item, EmojiItem):
                        if item.get_parent_image():
                            item.get_parent_image().remove_attached_emoji(item)
                        self.scene.removeItem(item)
                    elif isinstance(item, MovableImageItem):
                        # 删除图片时同时删除吸附的Emoji
                        for emoji in item.get_attached_emojis():
                            self.scene.removeItem(emoji)
                        self.scene.removeItem(item)
                self.update_status(None)
                self.schedule_autosave()
                self.view.mark_background_dirty()
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
                # 删除吸附的Emoji
                for emoji in item.get_attached_emojis():
                    self.scene.removeItem(emoji)
                self.scene.removeItem(item)
            elif isinstance(item, EmojiItem):
                if item.get_parent_image():
                    item.get_parent_image().remove_attached_emoji(item)
                self.scene.removeItem(item)
        self.update_status(None)
        self.schedule_autosave()
        self.view.mark_background_dirty()

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
        for item in self.scene.selectedItems():
            if isinstance(item, MovableImageItem):
                item.rotate_by(degrees)
                self.update_status(item)
        self.schedule_autosave()

    def flip_selected_horizontal(self):
        for item in self.scene.selectedItems():
            if isinstance(item, MovableImageItem):
                item.flip_horizontal()
                self.update_status(item)
        self.schedule_autosave()

    def flip_selected_vertical(self):
        for item in self.scene.selectedItems():
            if isinstance(item, MovableImageItem):
                item.flip_vertical()
                self.update_status(item)
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
        items = [i for i in self.scene.items() if isinstance(i, MovableImageItem) or isinstance(i, EmojiItem)]
        if not items:
            return
        reply = QMessageBox.question(
            self, "确认", "确定要清空所有图片和Emoji吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            for item in items:
                self.scene.removeItem(item)
            self.clear_diff_markers()
            self.update_status(None)
            self.schedule_autosave()
            self.view.mark_background_dirty()

    def compare_diff(self):
        selected = [i for i in self.scene.selectedItems() if isinstance(i, MovableImageItem)]
        if len(selected) < 2:
            QMessageBox.information(
                self, "提示",
                "请先选中两张（或多张）高度相似的图片，再点击比对差异。\n"
                "按住 Ctrl 点击可多选。"
            )
            return
        self.clear_diff_markers()
        base_item = selected[0]
        base_img = base_item.original_pixmap().toImage().convertToFormat(QImage.Format_RGB32)
        total_diff_regions = 0
        for other_item in selected[1:]:
            other_img = other_item.original_pixmap().toImage().convertToFormat(QImage.Format_RGB32)
            if base_img.size() != other_img.size():
                other_img = other_img.scaled(
                    base_img.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            w = min(base_img.width(), other_img.width())
            h = min(base_img.height(), other_img.height())
            threshold = 30
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
            regions = self._merge_diff_blocks(diff_blocks, block_size, w, h)
            scale = other_item.scale_factor()
            pos = other_item.pos()
            base_w = other_item.original_size().width()
            base_h = other_item.original_size().height()
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
        if not blocks:
            return []
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
        for marker in self._diff_markers:
            self.scene.removeItem(marker)
        self._diff_markers = []

    def schedule_autosave(self):
        self._autosave_timer.start(self._settings.get_autosave_delay())

    def _on_scene_changed(self, rects):
        self.view.mark_background_dirty()
        selected = self.scene.selectedItems()
        if any(isinstance(i, MovableImageItem) for i in selected):
            self.schedule_autosave()

    def _do_autosave(self):
        items = [i for i in self.scene.items() if isinstance(i, MovableImageItem) or isinstance(i, EmojiItem)]
        try:
            self._autosave_mgr.save_state(items)
        except Exception:
            pass

    def _try_restore_autosave(self):
        if not self._autosave_mgr.has_autosave():
            return
        count = self._autosave_mgr.load_state(self.scene, self._on_item_added)
        if count > 0:
            self.status_label.setText(f"已自动恢复上次画面，共 {count} 个元素")
            QTimer.singleShot(100, self.view.fit_all_items)

    def save_to_history(self):
        items = [i for i in self.scene.items() if isinstance(i, MovableImageItem) or isinstance(i, EmojiItem)]
        if not items:
            QMessageBox.information(self, "提示", "画布上没有内容，无法保存到历史记录。")
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
        for item in list(self.scene.items()):
            if isinstance(item, MovableImageItem) or isinstance(item, EmojiItem) or isinstance(item, DiffMarkerItem):
                self.scene.removeItem(item)
        self._diff_markers = []
        count = self._history_mgr.load_history(hid, self.scene, self._on_item_added)
        self.clear_diff_markers()
        if count > 0:
            self.status_label.setText(f"已加载历史记录，共 {count} 个元素")
            self.view.fit_all_items()
            self.schedule_autosave()
        else:
            QMessageBox.warning(self, "失败", "加载历史记录失败。")

    def export_canvas(self):
        items = [i for i in self.scene.items() if isinstance(i, MovableImageItem) or isinstance(i, EmojiItem)]
        if not items:
            QMessageBox.information(self, "提示", "画布上没有内容可导出。")
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
        
        # 先绘制图片，再绘制Emoji
        sorted_items = sorted(items, key=lambda x: x.zValue())
        for item in sorted_items:
            if isinstance(item, MovableImageItem):
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
            elif isinstance(item, EmojiItem):
                rect = item.sceneBoundingRect()
                cx = rect.center().x() - min_x + margin
                cy = rect.center().y() - min_y + margin
                painter.save()
                painter.translate(cx, cy)
                painter.drawPixmap(
                    -item.pixmap().width() / 2,
                    -item.pixmap().height() / 2,
                    item.pixmap()
                )
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

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.view.set_space_pressed(False)
            event.accept()
            return
        super().keyReleaseEvent(event)

    def closeEvent(self, event):
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