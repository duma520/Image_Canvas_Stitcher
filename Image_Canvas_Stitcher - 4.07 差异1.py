# -*- coding: utf-8 -*-
"""
图片自由拼接工具 - Image Canvas Stitcher (PySide6 版本)
版本: 4.07
功能：
- 从剪贴板粘贴图片 (Ctrl+V)
- 拖拽文件导入图片
- 鼠标拖动自由摆放图片位置
- 滚轮缩放选中的图片（选中时）或缩放整个视图（未选中时 / Ctrl+滚轮）
- 大画布可平移（按住空格+鼠标拖动 / 中键拖动）
- 右键菜单：删除、置顶、置底、缩放重置、透明度调整、旋转
- 导出拼接后的完整大图
- 视图整体缩放，方便看全貌和细节
- 单张/整体透明度调整
- 图片差异比对与红色标记
- 自动保存，下次启动自动恢复上次画面
- 历史记录管理，可保存、预览、加载历史项目
- 选项设置：自定义背景、自动保存间隔、历史数量、性能模式
- 单张/多张/整体图片旋转功能，支持90°、45°等常用角度
- 图片水平/垂直镜像翻转功能（单张/整体）
- 背景方案：纯色、网格、点阵、自定义图片
- 40+种背景形状和图案
- 在图片上画画做标记，并保存下来供下次使用
- Emoji表情功能：Win+; 调出面板、右键/菜单添加、吸附锁定
- 【新增 v3.34】Emoji独立文件保存，永久保留，彻底解决重开/加载历史位置错乱问题
- 【新增 v4.04】设置新增「整体缩放时背景显示缩放效果」开关，可让背景图案随视图缩放
- 【新增 v4.05】新增「撤回上一步」功能（工具栏按钮 / Ctrl+Z / 右键菜单），支持图片、Emoji、标记、变换操作的撤销
- 【新增 v4.05】差异比对增强：支持两图/多图比对、差异标记吸附到图片（随移动/缩放/旋转跟随）、可调差异判定阈值
- 【新增 v4.05】新增「图内差异比对」：在一张图内框选两处相似区域，自动找出差异并吸附标记（工具栏「图内比对」/右键菜单）
- 【新增 v4.07】修复「图内比对/比对差异」找不到差异的bug：改用快速像素比对（大图不再卡顿）、自动小范围对齐修正框选误差，支持麻将牌这类两张相似图
- 【新增 v4.07】差异比对增强：新增「彩色RGB/灰度」两种比对方案、降采样提速、帧差式快而准的差异识别（类比对两帧差异）
- 【新增 v4.07】新增 4 种相似度比对方案：灰度直方图（整体亮度分布）、SSIM 结构相似度（人眼感知+差异热力图）、特征点匹配（ORB，需 OpenCV）、感知哈希 pHash（海量去重）
"""
import sys
import os
import json
import time
import uuid
import math
import shutil
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsItem, QToolBar, QPushButton,
    QLabel, QStatusBar, QMenu, QFileDialog, QMessageBox, QWidget,
    QHBoxLayout, QSlider, QVBoxLayout, QListWidget, QListWidgetItem,
    QDialog, QDialogButtonBox, QSplitter, QGraphicsRectItem,
    QGroupBox, QFormLayout, QSpinBox, QCheckBox, QColorDialog,
    QComboBox, QTabWidget, QScrollArea, QGridLayout, QFrame,
    QButtonGroup, QRadioButton, QLineEdit, QSizePolicy
)
from PySide6.QtGui import (
    QPixmap, QImage, QClipboard, QPainter, QAction, QCursor,
    QPen, QColor, QBrush, QIcon, QPixmap, QTransform, QPainterPath,
    QPolygonF, QKeySequence, QFont, QFontMetrics
)
from PySide6.QtCore import Qt, QPointF, QRectF, QSizeF, QTimer, QSize, QRect, QPoint

# ==================== 配置常量 ====================
PROGRAM_DIR = os.path.dirname(os.path.abspath(__file__))
AUTOSAVE_DIR = os.path.join(PROGRAM_DIR, "autosave")
HISTORY_DIR = os.path.join(PROGRAM_DIR, "history")
SETTINGS_FILE = os.path.join(PROGRAM_DIR, "settings.json")
BACKGROUNDS_DIR = os.path.join(PROGRAM_DIR, "backgrounds")
MARKERS_DIR = os.path.join(PROGRAM_DIR, "markers")
EMOJIS_DIR = os.path.join(PROGRAM_DIR, "emojis")  # ✅ 新增 Emoji 独立存储目录

# 背景形状类型 - 40+种
BACKGROUND_SHAPES = [
    "square", "rectangle", "triangle", "hexagon", "circle", 
    "diamond", "star", "cross", "pentagon", "octagon",
    "arrow_up", "arrow_down", "arrow_left", "arrow_right",
    "arrow_up_right", "arrow_up_left", "arrow_down_right", "arrow_down_left",
    "heart", "moon", "sun", "cloud", "lightning",
    "flower", "spiral", "gear", "shield", "infinity",
    "chevron_up", "chevron_down", "chevron_left", "chevron_right",
    "ring", "teardrop", "hourglass", "trapezoid", "parallelogram",
    "semicircle", "quarter_circle", "pin", "target",
]

BACKGROUND_PATTERNS = [
    "grid", "dots", "diagonal", "checkerboard", 
    "concentric", "crosshair", "wave", "hatch",
    "herringbone", "zigzag", "spiral_pattern",
    "triangle_tile", "hexagon_tile", "circle_tile", "diamond_tile",
    "sawtooth", "scale", "maze", "radar",
    "starburst", "target_pattern", "ripple", "mosaic",
]

# 常用Emoji列表（快速选择）- 从3.25合并
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
    "background_zoom": False,
    "diff_threshold": 30,
    "diff_mode": "rgb",
    "heatmap_opacity": 50,
    "heatmap_display_mode": "both",
    "recent_emojis": [],
    "toolbar_visibility": {
        "btn_import": True,
        "btn_paste": True,
        "btn_undo": True,
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
        "btn_internal_diff": True,
        "heatmap_opacity": True,
        "heatmap_display_mode": True,
        "btn_save_hist": True,
        "btn_history": True,
        "btn_export": True,
        "btn_clear": True,
        "btn_settings": True,
        "btn_marker": True,
        "btn_clear_markers": True,
        "btn_emoji": True,
        "btn_emoji_favorites": True,
    }
}


def ensure_dirs():
    for d in [AUTOSAVE_DIR, HISTORY_DIR, BACKGROUNDS_DIR, MARKERS_DIR, EMOJIS_DIR,
              os.path.join(AUTOSAVE_DIR, "images"),
              os.path.join(HISTORY_DIR, "images"),
              os.path.join(MARKERS_DIR, "images")]:
        os.makedirs(d, exist_ok=True)


# ==================== 背景形状生成器 ====================
class ShapeGenerator:
    """各种形状的路径生成器 - 40+种形状"""
    
    @staticmethod
    def get_shape_path(shape_type, size, center_x, center_y):
        half = size / 2
        path = QPainterPath()
        
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
        elif shape_type == "heart":
            path.moveTo(center_x, center_y + half * 0.4)
            path.cubicTo(
                center_x - half * 0.8, center_y - half * 0.8,
                center_x - half * 1.2, center_y + half * 0.1,
                center_x, center_y + half * 0.7
            )
            path.cubicTo(
                center_x + half * 1.2, center_y + half * 0.1,
                center_x + half * 0.8, center_y - half * 0.8,
                center_x, center_y + half * 0.4
            )
            return path
        elif shape_type == "moon":
            path.addEllipse(QRectF(center_x - half, center_y - half, size, size))
            sub_path = QPainterPath()
            sub_path.addEllipse(QRectF(center_x + half * 0.25, center_y - half * 0.6, size * 0.6, size * 0.9))
            return path.subtracted(sub_path)
        elif shape_type == "sun":
            path.addEllipse(QRectF(center_x - half * 0.4, center_y - half * 0.4, size * 0.8, size * 0.8))
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
            for i in range(6):
                angle = math.radians(60 * i)
                cx = center_x + half * 0.5 * math.cos(angle)
                cy = center_y + half * 0.5 * math.sin(angle)
                path.addEllipse(QRectF(cx - half * 0.3, cy - half * 0.3, size * 0.6, size * 0.6))
            path.addEllipse(QRectF(center_x - half * 0.2, center_y - half * 0.2, size * 0.4, size * 0.4))
            return path
        elif shape_type == "spiral":
            path.moveTo(center_x, center_y)
            for t in range(1, 100):
                angle = t * 0.2
                r = t * 0.02 * half
                x = center_x + r * math.cos(angle)
                y = center_y + r * math.sin(angle)
                path.lineTo(x, y)
            return path
        elif shape_type == "gear":
            teeth = 8
            for i in range(teeth):
                angle = math.radians(360 / teeth * i)
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
            path.addEllipse(QRectF(center_x - half * 0.25, center_y - half * 0.25, size * 0.5, size * 0.5))
            path.moveTo(center_x, center_y + half * 0.2)
            path.lineTo(center_x, center_y + half * 0.8)
            path.addEllipse(QRectF(center_x - half * 0.12, center_y + half * 0.7, size * 0.24, size * 0.24))
            return path
        elif shape_type == "target":
            for r in [0.2, 0.4, 0.6, 0.8, 1.0]:
                radius = half * r
                path.addEllipse(QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2))
            return path
        else:
            path.addRect(QRectF(center_x - half, center_y - half, size, size))
            return path


# ==================== 背景渲染器 ====================
class BackgroundRenderer:
    @staticmethod
    def render_background(settings, width, height, zoom=1.0):
        bg_type = settings.get("background_type", "solid")
        if zoom != 1.0:
            # 缩放效果模式：把图案尺寸/间距按 zoom 放大，
            # 使背景图案在屏幕上随整体缩放而缩放（且保持清晰）
            settings = dict(settings)
            settings["shape_size"] = settings.get("shape_size", 40) * zoom
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
        cols = int(width / spacing) + 2
        rows = int(height / spacing) + 2
        
        for row in range(rows):
            for col in range(cols):
                x = col * spacing + (spacing / 2 if row % 2 == 1 else 0)
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
        bg_color = QColor(settings.get("background_color", "#2b2b2b"))
        line_color = QColor(settings.get("background_color_light", "#4a4a4a"))
        line_color.setAlpha(int(255 * settings.get("shape_opacity", 0.3)))
        return bg_color, line_color
    
    @staticmethod
    def _render_grid(settings, width, height):
        bg_color, line_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(line_color, 1))
        x = 0
        while x <= width:
            painter.drawLine(x, 0, x, height)
            x += spacing
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
    def _render_herringbone(settings, width, height):
        bg_color, line_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(line_color, 1.5))
        painter.setRenderHint(QPainter.Antialiasing)
        h = spacing * 0.5
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
        bg_color, tri_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(tri_color, 1))
        painter.setBrush(QBrush(tri_color))
        painter.setRenderHint(QPainter.Antialiasing)
        h = spacing * math.sqrt(3) / 2
        for row in range(int(-2), int(height / h) + 3):
            for col in range(int(-2), int(width / spacing) + 3):
                x = col * spacing + (spacing / 2 if row % 2 == 1 else 0)
                y = row * h
                path1 = QPainterPath()
                path1.moveTo(x, y + h)
                path1.lineTo(x + spacing/2, y)
                path1.lineTo(x + spacing, y + h)
                path1.closeSubpath()
                painter.drawPath(path1)
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
        bg_color, hex_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(hex_color, 1))
        painter.setBrush(QBrush(hex_color))
        painter.setRenderHint(QPainter.Antialiasing)
        r = spacing / math.sqrt(3)
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
        bg_color, circ_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        radius = spacing * 0.35
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(circ_color, 1))
        painter.setBrush(QBrush(circ_color))
        painter.setRenderHint(QPainter.Antialiasing)
        for row in range(int(-2), int(height / spacing) + 3):
            for col in range(int(-2), int(width / spacing) + 3):
                x = col * spacing + (spacing / 2 if row % 2 == 1 else 0)
                y = row * spacing * 0.866
                painter.drawEllipse(QPointF(x, y), radius, radius)
        painter.end()
        return img
    
    @staticmethod
    def _render_diamond_tile(settings, width, height):
        bg_color, dia_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(dia_color, 1))
        painter.setBrush(QBrush(dia_color))
        painter.setRenderHint(QPainter.Antialiasing)
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
        bg_color, scale_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        radius = spacing * 0.5
        cols = int(width / radius) + 2
        rows = int(height / (radius * 0.8)) + 2
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing)
        total_cells = cols * rows
        max_cells = 3000
        if total_cells > max_cells:
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
        import random
        bg_color, line_color = BackgroundRenderer._get_pattern_colors(settings)
        spacing = settings.get("shape_size", 40)
        cols = max(3, int(width / spacing))
        rows = max(3, int(height / spacing))
        cell_w = width / cols
        cell_h = height / rows
        img = QImage(width, height, QImage.Format_RGB32)
        img.fill(bg_color)
        painter = QPainter(img)
        painter.setPen(QPen(line_color, 2))
        painter.setRenderHint(QPainter.Antialiasing)
        walls = [[[True, True] for _ in range(cols)] for _ in range(rows)]
        visited = [[False] * cols for _ in range(rows)]
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
        walls[0][0][1] = False
        walls[rows-1][cols-1][1] = False
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
        painter.setPen(QPen(line_color, wall_thickness * 2))
        painter.drawRect(0, 0, width, height)
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
    
    def get_background(self, settings, width, height, zoom=1.0):
        key = self._make_key(settings, width, height, zoom)
        if key in self._cache:
            return self._cache[key]
        img = BackgroundRenderer.render_background(settings, width, height, zoom)
        self._cache[key] = img
        if len(self._cache) > 10:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        return img
    
    def _make_key(self, settings, width, height, zoom=1.0):
        bg_type = settings.get("background_type", "solid")
        parts = [bg_type, str(width), str(height), str(round(zoom, 4))]
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
        self._scale_factor = 1.0  # 缩放因子
        
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        
        # 如果有父图片，建立绑定
        if parent_item:
            self.set_parent_image(parent_item, True)
        
        self.setZValue(100)  # Emoji在图片之上
    
    @staticmethod
    def _render_emoji(emoji_char, font_size):
        """将Emoji字符渲染为QPixmap"""
        font = QFont()
        font.setPixelSize(font_size)
        if sys.platform == "win32":
            font.setFamily("Segoe UI Emoji")
        elif sys.platform == "darwin":
            font.setFamily("Apple Color Emoji")
        else:
            font.setFamily("Noto Color Emoji")
        
        fm = QFontMetrics(font)
        rect = fm.boundingRect(emoji_char)
        
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
        return self._item_id
    
    def set_parent_image(self, parent_item, auto_calc_offset=True):
        """
        设置吸附的父图片
        auto_calc_offset=True: 新建时自动计算相对于父图片中心的位置
        auto_calc_offset=False: 从保存状态恢复，直接使用已存储的 pos()
        """
        if parent_item:
            # 如果之前有父图片，先解除关系
            if self._parent_image:
                self._parent_image.remove_attached_emoji(self)
            
            self._parent_image = parent_item
            
            if auto_calc_offset:
                # ✅ 新建时：计算相对于父图片中心的位置
                parent_center = parent_item.boundingRect().center()
                # 获取当前场景坐标
                if self.scene() and parent_item.scene():
                    scene_pos = self.scenePos()
                    parent_scene_pos = parent_item.scenePos()
                else:
                    scene_pos = self.pos()
                    parent_scene_pos = parent_item.pos()
                
                # 计算相对于父图片的位置
                rel_pos = scene_pos - parent_scene_pos
                self.setPos(rel_pos)
            
            # ✅ 设置为父图片的子项（坐标自动变为相对父图片）
            self.setParentItem(parent_item)
            self.setFlag(QGraphicsItem.ItemIsMovable, True)

    def restore_parent(self, parent_item):
        """从保存状态恢复父项（不重新计算位置）"""
        if parent_item:
            if self._parent_image:
                self._parent_image.remove_attached_emoji(self)
            self._parent_image = parent_item
            # ✅ 直接设置父项，pos() 已经是相对父图片的坐标
            self.setParentItem(parent_item)
            self.setFlag(QGraphicsItem.ItemIsMovable, True)

    def get_parent_image(self):
        return self._parent_image
    
    def detach_from_parent(self):
        """从父图片分离"""
        if self._parent_image:
            self._parent_image.remove_attached_emoji(self)
            # ✅ 获取当前场景坐标
            scene_pos = self.scenePos()
            self.setParentItem(None)
            # ✅ 设置为场景中的绝对坐标
            self.setPos(scene_pos)
            self._parent_image = None
            self.setFlag(QGraphicsItem.ItemIsMovable, True)
    
    def set_scale_factor(self, factor):
        factor = max(0.2, min(factor, 5.0))
        if factor == self._scale_factor:
            return
        self._scale_factor = factor
        new_size = int(self._font_size * factor)
        new_size = max(8, new_size)
        new_pixmap = EmojiItem._render_emoji(self._emoji_char, new_size)
        self.setPixmap(new_pixmap)
        self.setTransformOriginPoint(self.pixmap().width() / 2, self.pixmap().height() / 2)
    
    def scale_at(self, factor, scene_pos):
        """在指定场景位置缩放"""
        new_factor = self._scale_factor * factor
        new_factor = max(0.2, min(new_factor, 5.0))
        if new_factor == self._scale_factor:
            return
        old_center = self.sceneBoundingRect().center()
        self.set_scale_factor(new_factor)
        new_center = self.sceneBoundingRect().center()
        offset = old_center - new_center
        self.moveBy(offset.x(), offset.y())
    
    def get_scale_factor(self):
        return self._scale_factor
    
    def itemChange(self, change, value):
        # ✅ 不需要额外处理位置变化，Qt 父项系统自动处理
        if change == QGraphicsItem.ItemSelectedHasChanged:
            if self.isSelected():
                self.setZValue(200)
            else:
                self.setZValue(100)
        return super().itemChange(change, value)
    
    def to_dict(self):
        """
        序列化为字典
        ✅ 只保存 pos()，不保存 _offset
        pos() 在 parentItem 存在时是相对父图片的坐标
        pos() 在 parentItem 为 None 时是场景绝对坐标
        """
        data = {
            "id": self.item_id(),
            "emoji": self._emoji_char,
            "font_size": self._font_size,
            "scale": self._scale_factor,
            "z": self.zValue(),
            "parent_id": self._parent_image.item_id() if self._parent_image else None,
            "pos": {"x": self.pos().x(), "y": self.pos().y()},
        }
        return data


# ==================== Emoji选择对话框 ====================
class EmojiPickerDialog(QDialog):
    """Emoji选择对话框 - 带分类标签页"""
    
    EMOJI_CATEGORIES = {
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
        self.resize(780, 600)
        self._parent_image = parent_image
        self._selected_emoji = None
        self._main_window = None
        self._find_main_window(parent)
        self._build_ui()
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowCloseButtonHint |
            Qt.WindowStaysOnTopHint
        )
    
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
        
        # 分类标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        
        self.category_widgets = {}
        self.emoji_buttons = {}
        
        # 最近使用标签页（放在最前面，方便快速再次添加）
        self._build_recent_tab()
        
        for category_name, emojis in self.EMOJI_CATEGORIES.items():
            self._build_category_tab(category_name, emojis)
        
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
    
    def _get_recent_emojis(self):
        """获取最近使用的Emoji列表（从设置读取）"""
        if self._main_window:
            return list(self._main_window._settings.get("recent_emojis", []) or [])
        return []
    
    def _build_recent_tab(self):
        """构建「最近使用」标签页（放在最前面）"""
        recent_list = self._get_recent_emojis()
        if recent_list:
            self._build_category_tab("🕘 最近使用", recent_list)
            return
        # 空列表时显示占位提示
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        placeholder = QLabel("暂无最近使用的Emoji\n（通过选择器添加过的表情会显示在这里）")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #888; font-size: 13px;")
        placeholder.setWordWrap(True)
        scroll.setWidget(placeholder)
        self.tab_widget.addTab(scroll, "🕘 最近使用")
        self.category_widgets["🕘 最近使用"] = placeholder
        self.emoji_buttons["🕘 最近使用"] = []
    
    def _build_category_tab(self, category_name, emojis):
        """构建一个分类标签页"""
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
        
        scroll.setWidget(container)
        self.tab_widget.addTab(scroll, category_name)
        self.category_widgets[category_name] = container
        self.emoji_buttons[category_name] = buttons
        return scroll
    
    def _on_resize(self, event):
        super().resizeEvent(event)
        self._reflow_all_categories()
    
    def _calc_columns(self):
        container_width = self.width() - 40
        btn_width = 54
        cols = max(4, container_width // btn_width)
        return min(cols, 20)
    
    def _reflow_all_categories(self):
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
            for idx, btn in enumerate(buttons):
                row = idx // cols
                col = idx % cols
                grid_layout.addWidget(btn, row, col)
            if buttons:
                last_row = len(buttons) // cols
                grid_layout.setRowStretch(last_row + 1, 1)
    
    def _filter_emojis(self, text):
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
        self._selected_emoji = emoji_char
        self._update_selection_status()
        for category, buttons in self.emoji_buttons.items():
            for btn in buttons:
                if btn and btn.text() == emoji_char:
                    btn.setStyleSheet("background-color: #e0e0e0; border: 2px solid #4a8ec5;")
                elif btn:
                    btn.setStyleSheet("")
    
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
        self._attached_emojis = []
        self.setAcceptHoverEvents(True)
        self.setOpacity(self._opacity)
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
        old_pixmap_size = self.pixmap().size()  # ✅ 缩放前记录旧 pixmap 尺寸（用于同步子项）
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
        # ✅ 同步吸附的 Emoji 与标记覆盖层：保持相对位置并随图片一起缩放
        self._sync_child_items(old_pixmap_size, self.pixmap().size())

    def scale_at(self, factor, scene_pos):
        factor = max(0.05, min(self._scale_factor * factor, 5.0)) / self._scale_factor
        if factor == 1.0:
            return
        local_pos = self.mapFromScene(scene_pos)
        rel_x = local_pos.x() / self.pixmap().width() if self.pixmap().width() else 0
        rel_y = local_pos.y() / self.pixmap().height() if self.pixmap().height() else 0
        old_pixmap_size = self.pixmap().size()  # ✅ 缩放前记录旧 pixmap 尺寸（用于同步子项）
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
        # ✅ 同步吸附的 Emoji 与标记覆盖层：保持相对位置并随图片一起缩放
        self._sync_child_items(old_pixmap_size, self.pixmap().size())

    def _sync_child_items(self, old_size, new_size):
        """
        图片缩放（替换 pixmap）后，同步吸附的 Emoji 与标记覆盖层：
        - Emoji：保持相对图片中心的比例位置，并随图片一起缩放
        - 标记覆盖层：以图片左上角为原点随图片一起缩放
        """
        if old_size == new_size:
            return
        old_w = old_size.width()
        old_h = old_size.height()
        if old_w == 0 or old_h == 0:
            return
        new_w = new_size.width()
        new_h = new_size.height()
        ratio_x = new_w / old_w
        ratio_y = new_h / old_h
        old_center = QPointF(old_w / 2, old_h / 2)
        new_center = QPointF(new_w / 2, new_h / 2)

        for child in self.childItems():
            if isinstance(child, EmojiItem):
                # 记录 Emoji 中心相对图片中心的偏移（Emoji 坐标是相对图片左上角）
                pos = child.pos()
                emoji_size = child.pixmap().size()
                emoji_center = QPointF(
                    pos.x() + emoji_size.width() / 2,
                    pos.y() + emoji_size.height() / 2
                )
                rel = emoji_center - old_center
                # Emoji 自身随图片一起缩放
                child.set_scale_factor(child.get_scale_factor() * ratio_x)
                # 用缩放后的实际 pixmap 尺寸重算 pos，保持相对位置不变
                new_emoji_size = child.pixmap().size()
                new_abs_center = QPointF(
                    new_center.x() + rel.x() * ratio_x,
                    new_center.y() + rel.y() * ratio_y
                )
                child.setPos(
                    new_abs_center.x() - new_emoji_size.width() / 2,
                    new_abs_center.y() - new_emoji_size.height() / 2
                )
            elif isinstance(child, MarkerOverlay):
                # 标记覆盖层以图片左上角 (0,0) 为原点随图片缩放
                child.setScale(child.scale() * ratio_x)
            elif isinstance(child, DiffOverlay):
                # 差异标记覆盖层以图片左上角 (0,0) 为原点随图片缩放
                child.setScale(child.scale() * ratio_x)
            elif isinstance(child, HeatmapOverlay):
                # 热力图覆盖层以图片左上角 (0,0) 为原点随图片缩放
                child.setScale(child.scale() * ratio_x)

    # ====== Emoji 相关方法 ======
    def add_attached_emoji(self, emoji_item):
        """添加吸附的Emoji"""
        if emoji_item not in self._attached_emojis:
            self._attached_emojis.append(emoji_item)
            emoji_item.set_parent_image(self, True)

    def remove_attached_emoji(self, emoji_item):
        """移除吸附的Emoji"""
        if emoji_item in self._attached_emojis:
            self._attached_emojis.remove(emoji_item)

    def get_attached_emojis(self):
        """获取所有吸附的Emoji"""
        return list(self._attached_emojis)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            for emoji in self._attached_emojis:
                if emoji and emoji.scene():
                    pass
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
                    "pos": {"x": e.pos().x(), "y": e.pos().y()},  # ✅ 改为 pos
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


class DiffOverlay(QGraphicsItem):
    """差异标记覆盖层 - 作为图片的子项吸附到图片上，
    随图片移动/旋转/缩放/翻转而自动跟随，标记不会与图片错位"""
    def __init__(self, parent_item):
        super().__init__(parent_item)
        self._parent_item = parent_item
        self._rects = []
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setZValue(parent_item.zValue() + 0.1)

    def set_diff_rects(self, rects):
        """rects: 图片本地坐标系下的差异矩形列表"""
        self._rects = list(rects)
        self.update()

    def rect_count(self):
        return len(self._rects)

    def boundingRect(self):
        if self._parent_item:
            return self._parent_item.boundingRect()
        return QRectF()

    def paint(self, painter, option, widget):
        if not self._parent_item or not self._rects:
            return
        painter.save()
        painter.setBrush(QBrush(QColor(255, 0, 0, 80)))
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        for rect in self._rects:
            painter.drawRect(rect)
        painter.restore()


class HeatmapOverlay(QGraphicsPixmapItem):
    """SSIM 差异热力图覆盖层 - 吸附到图片（随图片移动/缩放/旋转），可调透明度"""
    def __init__(self, parent_item, heatmap_image, target_rect=None):
        super().__init__(parent_item)
        self._parent_item = parent_item
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setAcceptedMouseButtons(Qt.NoButton)  # 不拦截鼠标，点击可穿透到图片
        if target_rect is None or target_rect.isEmpty():
            target_rect = QRectF(0, 0,
                                 parent_item.pixmap().width(),
                                 parent_item.pixmap().height())
        pm = QPixmap.fromImage(heatmap_image).scaled(
            max(1, int(target_rect.width())), max(1, int(target_rect.height())),
            Qt.IgnoreAspectRatio, Qt.SmoothTransformation
        )
        self.setPixmap(pm)
        self.setPos(target_rect.x(), target_rect.y())
        self.setOpacity(0.5)
        self.setZValue(parent_item.zValue() + 0.05)


class DiffSettingsDialog(QDialog):
    """差异比对参数设置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("差异比对设置")
        self.resize(460, 230)
        self._settings = SettingsManager()
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("设置差异判定阈值（多大的差异才算差异）：")
        title.setStyleSheet("font-weight: bold;")
        layout.addWidget(title)
        row = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 255)
        self.slider.setPageStep(5)
        self.value_label = QLabel("30")
        self.value_label.setMinimumWidth(60)
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        row.addWidget(self.slider, 1)
        row.addWidget(self.value_label)
        layout.addLayout(row)
        # 比对方案选择
        mode_row = QHBoxLayout()
        mode_label = QLabel("比对方案:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("彩色 RGB（标记差异区域，推荐）", "rgb")
        self.mode_combo.addItem("灰度（标记差异区域，更快）", "gray")
        self.mode_combo.addItem("灰度+直方图（相似度）", "hist")
        self.mode_combo.addItem("SSIM 结构相似度（+热力图）", "ssim")
        self.mode_combo.addItem("特征点匹配（相似度）", "feat")
        self.mode_combo.addItem("感知哈希 pHash（相似度）", "phash")
        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.mode_combo, 1)
        layout.addLayout(mode_row)
        tip = QLabel(
            "阈值（仅 RGB/灰度标记方案有效）越小越敏感：\n"
            "0   = 任何细微差异都算差异（最敏感）\n"
            "30 = 默认值\n"
            "255 = 只有强烈差异才算差异（最宽松）\n"
            "灰度：忽略颜色只看明暗，更快；适合纯黑白/相似色调图。\n"
            "直方图：比较整体亮度分布是否相似。\n"
            "SSIM：按人眼感知给出 0~1 相似度 + 差异热力图。\n"
            "特征点：适合不同尺寸/角度的图（需安装 OpenCV）。\n"
            "pHash：感知哈希，适合批量去重，越接近越相似。"
        )
        tip.setStyleSheet("color: #888; font-size: 11px; padding: 6px 2px;")
        tip.setWordWrap(True)
        layout.addWidget(tip)
        self.slider.valueChanged.connect(lambda v: self.value_label.setText(str(v)))
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load(self):
        val = int(self._settings.get("diff_threshold", 30))
        self.slider.setValue(val)
        self.value_label.setText(str(val))
        mode = self._settings.get("diff_mode", "rgb")
        idx = self.mode_combo.findData(mode)
        if idx >= 0:
            self.mode_combo.setCurrentIndex(idx)

    def _on_ok(self):
        self._settings.set("diff_threshold", self.slider.value())
        self._settings.set("diff_mode", self.mode_combo.currentData())
        self._settings.save()
        self.accept()

    def get_threshold(self):
        return self.slider.value()

    def get_mode(self):
        return self.mode_combo.currentData()


class SimilarityResultDialog(QDialog):
    """相似度比对结果对话框：显示文字结论 + 可选热力图"""
    def __init__(self, text, heat=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("差异比对结果")
        self.resize(540, 600)
        layout = QVBoxLayout(self)
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 13px; padding: 8px;")
        layout.addWidget(label)
        if heat is not None and not heat.isNull():
            pix = QPixmap.fromImage(heat).scaled(
                480, 420, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            img_label = QLabel()
            img_label.setPixmap(pix)
            img_label.setAlignment(Qt.AlignCenter)
            img_label.setStyleSheet("border: 1px solid #555; background: #1e1e1e;")
            layout.addWidget(img_label, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


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
        # 全视口更新：避免 Qt 默认的 bitblt 滚动优化把旧背景像素拷贝到新位置，
        # 导致与 drawBackground 绘制的屏幕固定背景错位，出现花屏
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self._panning = False
        self._pan_start = QPointF()
        self._space_pressed = False
        self._main_window = None
        self._min_zoom = 0.05
        self._max_zoom = 10.0
        self._right_menu_closed_at = 0
        self._right_menu_cooldown_ms = 150
        self._cached_bg_pixmap = None
        self._cached_bg_size = None
        self._cached_bg_zoom = 1.0
        self._bg_dirty = True
        self._marker_click_handled = False

    def _apply_render_hints(self):
        hints = QPainter.TextAntialiasing
        if self._settings.get("antialiasing", True):
            hints |= QPainter.Antialiasing
        if self._settings.get("smooth_pixmap", True):
            hints |= QPainter.SmoothPixmapTransform
        self.setRenderHints(hints)

    def drawBackground(self, painter, rect):
        if self.viewport():
            size = self.viewport().size()
        else:
            size = QSize(800, 600)
        zoom_mode = bool(self._settings.get("background_zoom", False))
        zoom = self.view_scale() if zoom_mode else 1.0
        if (self._cached_bg_pixmap is None or 
            self._cached_bg_size != size or
            self._cached_bg_zoom != zoom or
            self._bg_dirty):
            self._bg_cache.clear()
            bg_img = self._bg_cache.get_background(
                self._settings._settings, size.width(), size.height(), zoom
            )
            self._cached_bg_pixmap = QPixmap.fromImage(bg_img)
            self._cached_bg_size = size
            self._cached_bg_zoom = zoom
            self._bg_dirty = False
        if self._cached_bg_pixmap and not self._cached_bg_pixmap.isNull():
            if zoom_mode:
                # 缩放效果模式：在场景坐标中绘制到当前可见区域，
                # 背景图案随整体缩放而缩放（按 zoom 重新渲染，保持清晰）
                visible = self.mapToScene(self.viewport().rect()).boundingRect()
                painter.drawPixmap(
                    QRectF(visible.x(), visible.y(), visible.width(), visible.height()),
                    self._cached_bg_pixmap,
                    QRectF(0, 0, self._cached_bg_pixmap.width(),
                           self._cached_bg_pixmap.height())
                )
            else:
                # 背景按视口（屏幕）坐标绘制，保持 1:1 铺满视口，
                # 避免随场景平移/缩放导致背景被拉伸错位而花屏
                painter.save()
                painter.resetTransform()
                painter.drawPixmap(0, 0, self._cached_bg_pixmap)
                painter.restore()

    def mark_background_dirty(self):
        self._bg_dirty = True
        self.viewport().update()

    def update_background(self):
        self._bg_cache.clear()
        self._cached_bg_pixmap = None
        self._cached_bg_size = None
        self._cached_bg_zoom = 1.0
        self._bg_dirty = True
        self.viewport().update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
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
        self._marker_click_handled = False
        
        # 图内差异比对：框选两个区域
        if (self._main_window and self._main_window._internal_diff_mode):
            if event.button() == Qt.RightButton:
                self._main_window.exit_internal_diff()
                event.accept()
                return
            if event.button() == Qt.LeftButton and not self._space_pressed:
                self._main_window._on_internal_diff_press(event)
                event.accept()
                return
        
        if event.button() == Qt.MiddleButton or (
            event.button() == Qt.LeftButton and self._space_pressed
        ):
            self._panning = True
            self._pan_start = event.position()
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.viewport().setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        
        if (self._main_window and 
            self._main_window._marker_tool.mode != MarkerTool.MODE_OFF and
            event.button() == Qt.LeftButton):
            
            if self._main_window._marker_tool.is_drawing:
                self._main_window._end_marker_draw()
            
            scene_pos = self.mapToScene(event.position().toPoint())
            item_at_pos = self.scene().itemAt(scene_pos, self.transform())
            target_item = None
            
            if isinstance(item_at_pos, MovableImageItem):
                target_item = item_at_pos
            elif isinstance(item_at_pos, MarkerOverlay):
                target_item = item_at_pos._parent_item
            else:
                for it in self.scene().items(scene_pos):
                    if isinstance(it, MovableImageItem):
                        target_item = it
                        break
                    elif isinstance(it, MarkerOverlay):
                        target_item = it._parent_item
                        break
            
            if target_item is not None and isinstance(target_item, MovableImageItem):
                self._main_window._start_marker_draw(target_item, event.position())
                self._marker_click_handled = True
                event.accept()
                return
            else:
                if self._main_window._marker_tool.is_drawing:
                    self._main_window._marker_tool.is_drawing = False
                self._main_window._current_draw_item = None
                self._main_window._draw_start_pos = None
                self._main_window._draw_path = None
                event.ignore()
                return
        
        if event.button() == Qt.RightButton:
            item = self.itemAt(event.position().toPoint())
            # 点击差异标记/热力图时穿透到其所在图片
            if isinstance(item, (DiffOverlay, MarkerOverlay, HeatmapOverlay)) and getattr(item, "_parent_item", None):
                item = item._parent_item
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
        
        # 左键按下可移动图元时保存快照，支持拖动移动/缩放后的撤回
        if (event.button() == Qt.LeftButton and not self._space_pressed and self._main_window):
            hit = self.itemAt(event.position().toPoint())
            if isinstance(hit, (MovableImageItem, EmojiItem)):
                self._main_window.push_undo()
        
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # 图内差异比对：拖动框选区域
        if (self._main_window and self._main_window._internal_diff_mode and 
                self._main_window._internal_diff_dragging):
            self._main_window._on_internal_diff_move(event)
            event.accept()
            return
        
        if (self._main_window and 
            self._main_window._marker_tool.mode != MarkerTool.MODE_OFF and
            self._main_window._marker_tool.is_drawing):
            self._main_window._continue_marker_draw(event.position())
            event.accept()
            return
        
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
        # 图内差异比对：完成一个区域的框选
        if (self._main_window and self._main_window._internal_diff_mode and 
                event.button() == Qt.LeftButton):
            self._main_window._on_internal_diff_release(event)
            event.accept()
            return
        
        if (self._main_window and 
            self._main_window._marker_tool.mode != MarkerTool.MODE_OFF and
            self._main_window._marker_tool.is_drawing and
            event.button() == Qt.LeftButton):
            
            self._main_window._end_marker_draw()
            self._marker_click_handled = True
            event.accept()
            return
        
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
        undo_act = menu.addAction("↩️ 撤回上一步 (Ctrl+Z)")
        menu.addSeparator()
        
        # Emoji相关操作
        emoji_menu = menu.addMenu("😀 添加Emoji")
        add_emoji_act = emoji_menu.addAction("➕ 从选择器添加...")
        add_to_image_act = emoji_menu.addAction("📌 添加到选中图片")
        menu.addSeparator()
        
        add_emoji_canvas_act = None
        
        if isinstance(item, MovableImageItem):
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
            emoji_mgmt = menu.addMenu("😊 管理Emoji")
            detach_all_act = emoji_mgmt.addAction("分离所有Emoji")
            menu.addSeparator()
            
        elif isinstance(item, EmojiItem):
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
            view_zoom_in_act = menu.addAction("🔍 视图放大")
            view_zoom_out_act = menu.addAction("🔍 视图缩小")
            view_reset_act = menu.addAction("↩️ 视图重置 (100%)")
            view_fit_act = menu.addAction("📐 适配全部")
            menu.addSeparator()
            clear_diff_act = menu.addAction("🧹 清除差异标记")
            internal_diff_act = menu.addAction("🖼️ 图内差异比对（框选两处区域）")
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
            add_emoji_canvas_act = menu.addAction("😀 添加Emoji到画布")

        action = menu.exec(global_pos)
        self._right_menu_closed_at = time.time()

        if not action:
            return
        
        # ====== 通用操作 ======
        if action == paste_act and self._main_window:
            self._main_window.paste_from_clipboard()
            return
        if action == undo_act and self._main_window:
            self._main_window.undo_last()
            return
        
        # ====== Emoji选择器 ======
        if action == add_emoji_act and self._main_window:
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
        
        # 保存操作前快照（用于撤回），跳过视图类与选择器类操作
        if self._main_window:
            self._main_window.push_undo()
        
        # ====== 图片操作 ======
        if isinstance(item, MovableImageItem):
            if action == delete_act:
                # 删除图片的同时删除 Emoji 文件
                self._main_window._delete_emoji_file(item.item_id())
                for emoji in item.get_attached_emojis():
                    self.scene().removeItem(emoji)
                self._main_window._marker_manager.save_markers_for_item(item)
                self._main_window._marker_manager.remove_overlay(item)
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
                else:
                    # 删除独立 Emoji 文件中的记录
                    self._main_window._remove_orphan_emoji(item)
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
                # 分离后保存到 orphans
                self._main_window._save_orphan_emoji(item)
                if self._main_window:
                    self._main_window.schedule_autosave()
            elif action == attach_emoji_act:
                selected = [i for i in self.scene().selectedItems() 
                           if isinstance(i, MovableImageItem) and i != item]
                if selected:
                    parent_img = selected[0]
                    # 从 orphans 中移除
                    self._main_window._remove_orphan_emoji(item)
                    item.detach_from_parent()
                    parent_img.add_attached_emoji(item)
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
            elif action == internal_diff_act and self._main_window:
                self._main_window.start_internal_diff()
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


# ==================== 自动保存管理器 ====================
class AutoSaveManager:
    def __init__(self):
        ensure_dirs()
        self.state_file = os.path.join(AUTOSAVE_DIR, "state.json")
        self.images_dir = os.path.join(AUTOSAVE_DIR, "images")

    def save_state(self, items):
        state = {"version": 1, "timestamp": time.time(), "images": [], "emojis": []}
        
        for item in items:
            if isinstance(item, MovableImageItem):
                iid = item.item_id()
                img_path = os.path.join(self.images_dir, f"{iid}.png")
                item.original_pixmap().save(img_path, "PNG")
                info = item.to_dict()
                info["image_file"] = f"{iid}.png"
                state["images"].append(info)
                # ✅ 同时保存该图片的 Emoji 到独立文件
                self._save_emojis_for_item(item)
            elif isinstance(item, EmojiItem):
                # ✅ 独立 Emoji 保存到 orphans
                self._save_orphan_emoji(item)
                # 同时保留在状态中作为备份
                state["emojis"].append(item.to_dict())
        
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def _save_emojis_for_item(self, item):
        """保存某个图片的所有吸附 Emoji 到独立文件"""
        if not isinstance(item, MovableImageItem):
            return
        emojis = item.get_attached_emojis()
        if not emojis:
            emoji_file = os.path.join(EMOJIS_DIR, f"{item.item_id()}.json")
            if os.path.exists(emoji_file):
                try:
                    os.remove(emoji_file)
                except:
                    pass
            return
        
        data = []
        for emoji in emojis:
            data.append({
                "id": emoji.item_id(),
                "emoji": emoji._emoji_char,
                "font_size": emoji._font_size,
                "scale": emoji.get_scale_factor(),
                "pos": {"x": emoji.pos().x(), "y": emoji.pos().y()},  # ✅ 保存 pos
                "z": emoji.zValue(),
            })
        
        emoji_file = os.path.join(EMOJIS_DIR, f"{item.item_id()}.json")
        with open(emoji_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_orphan_emoji(self, emoji):
        """保存独立的 Emoji（没有父图片）"""
        if emoji.get_parent_image():
            return  # 有父图片的由上面的方法保存
        orphans_file = os.path.join(EMOJIS_DIR, "orphans.json")
        orphans = []
        if os.path.exists(orphans_file):
            try:
                with open(orphans_file, "r", encoding="utf-8") as f:
                    orphans = json.load(f)
            except:
                pass
        
        # 更新或添加
        found = False
        for i, o in enumerate(orphans):
            if o.get("id") == emoji.item_id():
                orphans[i] = emoji.to_dict()
                found = True
                break
        if not found:
            orphans.append(emoji.to_dict())
        
        with open(orphans_file, "w", encoding="utf-8") as f:
            json.dump(orphans, f, ensure_ascii=False, indent=2)

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
        image_items = {}
        
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
        
        # ✅ 第二步：为每个图片恢复其 Emoji
        for item_id, item in image_items.items():
            self._load_emojis_for_item(item)
            count += len(item.get_attached_emojis())
        
        # ✅ 第三步：恢复独立 Emoji（孤儿）
        count += self._load_orphan_emojis(scene)
        
        return count

    def _load_emojis_for_item(self, item):
        """为指定图片加载其吸附的 Emoji"""
        emoji_file = os.path.join(EMOJIS_DIR, f"{item.item_id()}.json")
        if not os.path.exists(emoji_file):
            return
        
        try:
            with open(emoji_file, "r", encoding="utf-8") as f:
                emojis_data = json.load(f)
            
            for data in emojis_data:
                emoji = EmojiItem(
                    data.get("emoji", "😀"),
                    font_size=data.get("font_size", 48),
                    item_id=data.get("id")
                )
                emoji.set_scale_factor(data.get("scale", 1.0))
                
                # ✅ 直接使用 pos
                pos = data.get("pos", {})
                emoji._parent_image = item
                emoji.setParentItem(item)  # 先设置父项
                emoji.setPos(pos.get("x", 0), pos.get("y", 0))  # 再设置相对位置
                emoji.setZValue(data.get("z", 100))
                
                item._attached_emojis.append(emoji)
                    
        except Exception as e:
            print(f"加载 Emoji 失败 ({item.item_id()}): {e}")

    def _load_orphan_emojis(self, scene):
        """恢复独立的 Emoji（没有父图片）"""
        orphans_file = os.path.join(EMOJIS_DIR, "orphans.json")
        if not os.path.exists(orphans_file):
            return 0
        
        try:
            with open(orphans_file, "r", encoding="utf-8") as f:
                orphans = json.load(f)
            
            count = 0
            for data in orphans:
                emoji = EmojiItem(
                    data.get("emoji", "😀"),
                    font_size=data.get("font_size", 48),
                    item_id=data.get("id")
                )
                emoji.set_scale_factor(data.get("scale", 1.0))
                pos = data.get("pos", {})
                emoji.setPos(pos.get("x", 0), pos.get("y", 0))
                emoji.setZValue(data.get("z", 100))
                scene.addItem(emoji)
                count += 1
            return count
        except Exception as e:
            print(f"加载独立 Emoji 失败: {e}")
            return 0


# ==================== 历史记录管理器 ====================
class HistoryManager:
    def __init__(self):
        ensure_dirs()
        self.index_file = os.path.join(HISTORY_DIR, "index.json")
        self.images_dir = os.path.join(HISTORY_DIR, "images")
        self._load_index()
        self._main_window = None

    def set_main_window(self, main_window):
        self._main_window = main_window

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
        
        for item in movable_items:
            iid = item.item_id()
            img_path = os.path.join(state_dir, f"{iid}.png")
            item.original_pixmap().save(img_path, "PNG")
            info = item.to_dict()
            info["image_file"] = f"{iid}.png"
            # 保存标记数据到历史记录目录
            marker_file = os.path.join(MARKERS_DIR, f"{iid}.json")
            if os.path.exists(marker_file):
                try:
                    dest_marker = os.path.join(state_dir, f"marker_{iid}.json")
                    shutil.copy2(marker_file, dest_marker)
                    info["has_marker"] = True
                    info["marker_file"] = f"marker_{iid}.json"
                except Exception as e:
                    print(f"复制标记文件失败: {e}")
                    info["has_marker"] = False
            else:
                info["has_marker"] = False
            
            # ✅ 保存 Emoji 到历史目录
            emoji_file_src = os.path.join(EMOJIS_DIR, f"{iid}.json")
            if os.path.exists(emoji_file_src):
                try:
                    dest_emoji = os.path.join(state_dir, f"emoji_{iid}.json")
                    shutil.copy2(emoji_file_src, dest_emoji)
                    info["has_emojis"] = True
                    info["emoji_file"] = f"emoji_{iid}.json"
                except Exception as e:
                    print(f"复制 Emoji 文件失败: {e}")
                    info["has_emojis"] = False
            else:
                info["has_emojis"] = False
            
            state["images"].append(info)
        
        # 保存独立 Emoji
        for item in items:
            if isinstance(item, EmojiItem) and not item.get_parent_image():
                state["emojis"].append(item.to_dict())
        
        # 保存独立 Emoji 到历史目录
        orphans_file = os.path.join(EMOJIS_DIR, "orphans.json")
        if os.path.exists(orphans_file):
            try:
                shutil.copy2(orphans_file, os.path.join(state_dir, "orphans.json"))
            except:
                pass
        
        state_path = os.path.join(state_dir, "state.json")
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        
        thumb_path = os.path.join(state_dir, "thumb.png")
        self._render_thumbnail_screenshot(thumb_path)
        
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

    def _render_thumbnail_screenshot(self, output_path, max_size=400):
        if self._main_window is None:
            img = QImage(max_size, max_size, QImage.Format_RGB32)
            img.fill(QColor(40, 40, 40))
            img.save(output_path, "PNG")
            return
        
        view = self._main_window.view
        if view is None or view.viewport() is None:
            img = QImage(max_size, max_size, QImage.Format_RGB32)
            img.fill(QColor(40, 40, 40))
            img.save(output_path, "PNG")
            return
        
        try:
            viewport_rect = view.viewport().rect()
            screenshot = view.grab(viewport_rect)
            if screenshot.isNull():
                img = QImage(max_size, max_size, QImage.Format_RGB32)
                img.fill(QColor(40, 40, 40))
                img.save(output_path, "PNG")
                return
            scaled = screenshot.scaled(
                max_size, max_size, 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            scaled.save(output_path, "PNG")
        except Exception as e:
            print(f"截图生成缩略图失败: {e}")
            img = QImage(max_size, max_size, QImage.Format_RGB32)
            img.fill(QColor(40, 40, 40))
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
            
            if img_info.get("has_marker", False):
                marker_file = img_info.get("marker_file", "")
                if marker_file:
                    src_marker = os.path.join(state_dir, marker_file)
                    if os.path.exists(src_marker):
                        try:
                            dest_marker = os.path.join(MARKERS_DIR, f"{img_info.get('id')}.json")
                            if os.path.exists(dest_marker):
                                try:
                                    backup = dest_marker + ".old"
                                    shutil.move(dest_marker, backup)
                                except Exception:
                                    pass
                            shutil.copy2(src_marker, dest_marker)
                            marker_index_file = os.path.join(MARKERS_DIR, "index.json")
                            marker_index = {}
                            if os.path.exists(marker_index_file):
                                try:
                                    with open(marker_index_file, "r", encoding="utf-8") as f:
                                        marker_index = json.load(f)
                                except Exception:
                                    pass
                            marker_index[img_info.get("id")] = {
                                "image_file": f"{img_info.get('id')}.png",
                                "marker_file": f"{img_info.get('id')}.json",
                                "timestamp": time.time()
                            }
                            with open(marker_index_file, "w", encoding="utf-8") as f:
                                json.dump(marker_index, f, ensure_ascii=False, indent=2)
                        except Exception as e:
                            print(f"恢复历史标记失败: {e}")
            
            # ✅ 恢复 Emoji
            if img_info.get("has_emojis", False):
                emoji_file = img_info.get("emoji_file", "")
                if emoji_file:
                    src_emoji = os.path.join(state_dir, emoji_file)
                    if os.path.exists(src_emoji):
                        try:
                            dest_emoji = os.path.join(EMOJIS_DIR, f"{img_info.get('id')}.json")
                            shutil.copy2(src_emoji, dest_emoji)
                        except Exception as e:
                            print(f"恢复历史 Emoji 失败: {e}")
            
            count += 1
        

        # 加载 Emoji
        for item_id, item in image_items.items():
            emoji_file = os.path.join(EMOJIS_DIR, f"{item_id}.json")
            if os.path.exists(emoji_file):
                try:
                    with open(emoji_file, "r", encoding="utf-8") as f:
                        emojis_data = json.load(f)
                    for data in emojis_data:
                        emoji = EmojiItem(
                            data.get("emoji", "😀"),
                            font_size=data.get("font_size", 48),
                            item_id=data.get("id")
                        )
                        emoji.set_scale_factor(data.get("scale", 1.0))
                        # ✅ 直接使用 pos
                        pos = data.get("pos", {})
                        emoji._parent_image = item
                        emoji.setParentItem(item)  # 先设置父项
                        emoji.setPos(pos.get("x", 0), pos.get("y", 0))  # 再设置相对位置
                        emoji.setZValue(data.get("z", 100))
                        
                        item._attached_emojis.append(emoji)
                        count += 1
                except Exception as e:
                    print(f"从历史恢复 Emoji 失败: {e}")
        
        # 恢复独立 Emoji
        orphans_file = os.path.join(state_dir, "orphans.json")
        if os.path.exists(orphans_file):
            try:
                dest_orphans = os.path.join(EMOJIS_DIR, "orphans.json")
                shutil.copy2(orphans_file, dest_orphans)
            except Exception as e:
                print(f"恢复独立 Emoji 失败: {e}")
            
            try:
                with open(orphans_file, "r", encoding="utf-8") as f:
                    orphans = json.load(f)
                for data in orphans:
                    emoji = EmojiItem(
                        data.get("emoji", "😀"),
                        font_size=data.get("font_size", 48),
                        item_id=data.get("id")
                    )
                    emoji.set_scale_factor(data.get("scale", 1.0))
                    pos = data.get("pos", {})
                    emoji.setPos(pos.get("x", 0), pos.get("y", 0))
                    emoji.setZValue(data.get("z", 100))
                    scene.addItem(emoji)
                    count += 1
            except Exception as e:
                print(f"加载独立 Emoji 失败: {e}")
        
        for emoji_info in state.get("emojis", []):
            # 避免重复加载
            pass
        
        return count

    def _delete_history_dir(self, hid):
        d = os.path.join(HISTORY_DIR, hid)
        if os.path.isdir(d):
            shutil.rmtree(d, ignore_errors=True)

    def delete_history(self, hid):
        self._index = [e for e in self._index if e["id"] != hid]
        self._save_index()
        self._delete_history_dir(hid)


# ==================== 项目信息元数据 ====================
class ProjectInfo:
    NAME = "Image Canvas Stitcher"
    DISPLAY_NAME = "图片自由拼接工具"
    VERSION = "4.07"
    BUILD_DATE = "2026-08-04"
    AUTHOR = "杜玛"
    COPYRIGHT = "© 永久 杜玛"
    LICENSE = "MIT"
    URL = "https://github.com/duma520/IntervalTracker"
    MAINTAINER_EMAIL = "不提供"
    DESCRIPTION = "图片自由拼接工具 - 支持拖拽、粘贴、缩放、透明度调整、差异比对、历史记录、工具栏自定义、图片标记、Emoji表情（永久保留）"
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
            "Win+; 添加表情 | 表情可吸附到图片上同步移动 | "
            "Emoji永久保留，重开/加载历史位置不变"
        )
    
    @classmethod
    def get_export_default_filename(cls):
        return f"stitched_image_{time.strftime('%Y%m%d_%H%M%S')}.png"


# ==================== 标记绘制工具 ====================
class MarkerTool:
    MODE_OFF = 0
    MODE_PEN = 1
    MODE_LINE = 2
    MODE_RECT = 3
    MODE_ELLIPSE = 4
    MODE_ARROW = 5
    MODE_TEXT = 6
    
    def __init__(self):
        self.mode = self.MODE_OFF
        self.color = QColor(255, 0, 0)
        self.pen_width = 3
        self.font_size = 16
        self.current_item = None
        self.start_pos = None
        self.is_drawing = False
        self.text = ""
        
    def set_mode(self, mode):
        self.mode = mode
        self.is_drawing = False
        self.current_item = None
        self.start_pos = None


class MarkerOverlay(QGraphicsItem):
    def __init__(self, parent_item, marker_id=None):
        super().__init__(parent_item)
        self._parent_item = parent_item
        self._marker_id = marker_id or str(uuid.uuid4())[:8]
        self._paths = []
        self._lines = []
        self._rects = []
        self._ellipses = []
        self._arrows = []
        self._texts = []
        self._pen_color = QColor(255, 0, 0)
        self._pen_width = 3
        self.setZValue(parent_item.zValue() + 0.1)
        self._dirty = True
        self._overlay_id = str(uuid.uuid4())[:8]
        
    def boundingRect(self):
        if self._parent_item:
            return self._parent_item.boundingRect()
        return QRectF()
    
    def paint(self, painter, option, widget):
        if not self._parent_item:
            return
        painter.save()
        pen = QPen(self._pen_color, self._pen_width)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        for path in self._paths:
            painter.drawPath(path)
        for line in self._lines:
            painter.drawLine(line[0], line[1])
        for rect in self._rects:
            painter.drawRect(rect)
        for ellipse in self._ellipses:
            painter.drawEllipse(ellipse)
        for arrow in self._arrows:
            self._draw_arrow(painter, arrow[0], arrow[1])
        if self._texts:
            painter.setFont(QFont("Arial", self._pen_width + 8))
            for text_data in self._texts:
                painter.drawText(text_data[0], text_data[1])
        painter.restore()
    
    def _draw_arrow(self, painter, start, end):
        painter.drawLine(start, end)
        angle = math.atan2(end.y() - start.y(), end.x() - start.x())
        arrow_size = 12
        p1 = QPointF(
            end.x() - arrow_size * math.cos(angle - math.pi/6),
            end.y() - arrow_size * math.sin(angle - math.pi/6)
        )
        p2 = QPointF(
            end.x() - arrow_size * math.cos(angle + math.pi/6),
            end.y() - arrow_size * math.sin(angle + math.pi/6)
        )
        painter.drawLine(end, p1)
        painter.drawLine(end, p2)
    
    def add_path(self, path):
        self._paths.append(path)
        self._dirty = True
        self.update()
    
    def add_line(self, start, end):
        self._lines.append((start, end))
        self._dirty = True
        self.update()
    
    def add_rect(self, rect):
        self._rects.append(rect)
        self._dirty = True
        self.update()
    
    def add_ellipse(self, rect):
        self._ellipses.append(rect)
        self._dirty = True
        self.update()
    
    def add_arrow(self, start, end):
        self._arrows.append((start, end))
        self._dirty = True
        self.update()
    
    def add_text(self, pos, text):
        self._texts.append((pos, text))
        self._dirty = True
        self.update()
    
    def set_pen_color(self, color):
        self._pen_color = color        
        self._dirty = True
        self.update()
    
    def set_pen_width(self, width):
        self._pen_width = width
        self._dirty = True
        self.update()
    
    def marker_id(self):
        return self._marker_id
    
    def to_dict(self):
        data = {
            "id": self._marker_id,
            "color": self._pen_color.name(),
            "pen_width": self._pen_width,
            "paths": [],
            "lines": [],
            "rects": [],
            "ellipses": [],
            "arrows": [],
            "texts": []
        }
        for path in self._paths:
            points = []
            for i in range(path.elementCount()):
                elem = path.elementAt(i)
                try:
                    elem_type = int(elem.type)
                except (TypeError, ValueError):
                    elem_type = 1
                points.append({"x": elem.x, "y": elem.y, "type": elem_type})
            data["paths"].append(points)
        for line in self._lines:
            data["lines"].append([
                {"x": line[0].x(), "y": line[0].y()},
                {"x": line[1].x(), "y": line[1].y()}
            ])
        for rect in self._rects:
            data["rects"].append({
                "x": rect.x(), "y": rect.y(),
                "w": rect.width(), "h": rect.height()
            })
        for ellipse in self._ellipses:
            data["ellipses"].append({
                "x": ellipse.x(), "y": ellipse.y(),
                "w": ellipse.width(), "h": ellipse.height()
            })
        for arrow in self._arrows:
            data["arrows"].append([
                {"x": arrow[0].x(), "y": arrow[0].y()},
                {"x": arrow[1].x(), "y": arrow[1].y()}
            ])
        for text_data in self._texts:
            data["texts"].append({
                "x": text_data[0].x(), "y": text_data[0].y(),
                "text": text_data[1]
            })
        return data
    
    def from_dict(self, data):
        self._marker_id = data.get("id", str(uuid.uuid4())[:8])
        self._pen_color = QColor(data.get("color", "#ff0000"))
        self._pen_width = data.get("pen_width", 3)
        
        for path_data in data.get("paths", []):
            path = QPainterPath()
            started = False
            for point in path_data:
                x = point.get("x", 0)
                y = point.get("y", 0)
                elem_type = point.get("type", 0)
                if not started or elem_type == 0:
                    path.moveTo(x, y)
                    started = True
                elif elem_type == 1:
                    path.lineTo(x, y)
                else:
                    path.lineTo(x, y)
            if path.elementCount() > 0:
                self._paths.append(path)
        
        for line_data in data.get("lines", []):
            if len(line_data) >= 2:
                start = QPointF(line_data[0].get("x", 0), line_data[0].get("y", 0))
                end = QPointF(line_data[1].get("x", 0), line_data[1].get("y", 0))
                self._lines.append((start, end))
        
        for rect_data in data.get("rects", []):
            x = rect_data.get("x", 0)
            y = rect_data.get("y", 0)
            w = rect_data.get("w", 0)
            h = rect_data.get("h", 0)
            if w > 0 and h > 0:
                self._rects.append(QRectF(x, y, w, h))
        
        for ellipse_data in data.get("ellipses", []):
            x = ellipse_data.get("x", 0)
            y = ellipse_data.get("y", 0)
            w = ellipse_data.get("w", 0)
            h = ellipse_data.get("h", 0)
            if w > 0 and h > 0:
                self._ellipses.append(QRectF(x, y, w, h))
        
        for arrow_data in data.get("arrows", []):
            if len(arrow_data) >= 2:
                start = QPointF(arrow_data[0].get("x", 0), arrow_data[0].get("y", 0))
                end = QPointF(arrow_data[1].get("x", 0), arrow_data[1].get("y", 0))
                self._arrows.append((start, end))
        
        for text_data in data.get("texts", []):
            pos = QPointF(text_data.get("x", 0), text_data.get("y", 0))
            text = text_data.get("text", "")
            if text:
                self._texts.append((pos, text))
        
        self._dirty = True
        self.update()
    
    def has_markers(self):
        return (len(self._paths) > 0 or len(self._lines) > 0 or 
                len(self._rects) > 0 or len(self._ellipses) > 0 or
                len(self._arrows) > 0 or len(self._texts) > 0)
    
    def clear(self):
        self._paths.clear()
        self._lines.clear()
        self._rects.clear()
        self._ellipses.clear()
        self._arrows.clear()
        self._texts.clear()
        self._dirty = True
        self.update()


# ==================== 标记管理器 ====================
class MarkerManager:
    def __init__(self):
        ensure_dirs()
        self._overlays = {}
        self._marker_index_file = os.path.join(MARKERS_DIR, "index.json")
        self._load_index()
    
    def _load_index(self):
        if os.path.exists(self._marker_index_file):
            try:
                with open(self._marker_index_file, "r", encoding="utf-8") as f:
                    self._index = json.load(f)
            except Exception:
                self._index = {}
        else:
            self._index = {}
    
    def _save_index(self):
        try:
            with open(self._marker_index_file, "w", encoding="utf-8") as f:
                json.dump(self._index, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def get_overlay(self, item, create=True):
        if not isinstance(item, MovableImageItem):
            return None
        item_id = item.item_id()
        if item_id in self._overlays:
            overlay = self._overlays[item_id]
            if overlay.scene() is None and item.scene() is not None:
                item.scene().addItem(overlay)
            return overlay
        if create:
            overlay = MarkerOverlay(item)
            overlay.set_pen_color(QColor(255, 0, 0))
            overlay.set_pen_width(3)
            self._overlays[item_id] = overlay
            return overlay
        return None
    
    def remove_overlay(self, item):
        if not isinstance(item, MovableImageItem):
            return
        item_id = item.item_id()
        if item_id in self._overlays:
            overlay = self._overlays[item_id]
            if overlay.scene():
                overlay.scene().removeItem(overlay)
            del self._overlays[item_id]
    
    def save_markers_for_item(self, item):
        if not isinstance(item, MovableImageItem):
            return
        item_id = item.item_id()
        overlay = self._overlays.get(item_id)
        if overlay and overlay.has_markers():
            marker_file = os.path.join(MARKERS_DIR, f"{item_id}.json")
            data = overlay.to_dict()
            try:
                temp_file = marker_file + ".tmp"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                with open(temp_file, "r", encoding="utf-8") as f:
                    json.load(f)
                if os.path.exists(marker_file):
                    os.remove(marker_file)
                os.rename(temp_file, marker_file)
                self._index[item_id] = {
                    "image_file": f"{item_id}.png",
                    "marker_file": f"{item_id}.json",
                    "timestamp": time.time()
                }
                self._save_index()
            except Exception as e:
                print(f"保存标记失败: {e}")
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except OSError:
                    pass
        else:
            marker_file = os.path.join(MARKERS_DIR, f"{item_id}.json")
            try:
                if os.path.exists(marker_file):
                    os.remove(marker_file)
            except OSError:
                pass
            if item_id in self._index:
                del self._index[item_id]
                self._save_index()
    
    def load_markers_for_item(self, item):
        if not isinstance(item, MovableImageItem):
            return
        item_id = item.item_id()
        marker_file = os.path.join(MARKERS_DIR, f"{item_id}.json")
        
        if not os.path.exists(marker_file):
            return
        
        try:
            file_size = os.path.getsize(marker_file)
            if file_size == 0:
                if os.path.exists(marker_file):
                    os.remove(marker_file)
                return
        except OSError:
            return
        
        try:
            with open(marker_file, "r", encoding="utf-8") as f:
                raw_content = f.read()
            
            if not raw_content or not raw_content.strip():
                os.remove(marker_file)
                return
            
            try:
                data = json.loads(raw_content)
            except json.JSONDecodeError as je:
                print(f"加载标记失败 (JSON格式错误): {je}")
                backup_file = marker_file + ".bak"
                try:
                    if os.path.exists(backup_file):
                        os.remove(backup_file)
                    os.rename(marker_file, backup_file)
                except OSError:
                    try:
                        os.remove(marker_file)
                    except OSError:
                        pass
                return
            
            if not isinstance(data, dict):
                print(f"加载标记失败: 数据格式不正确")
                backup_file = marker_file + ".bak"
                try:
                    os.rename(marker_file, backup_file)
                except OSError:
                    try:
                        os.remove(marker_file)
                    except OSError:
                        pass
                return
            
            has_data = False
            for key in ['paths', 'lines', 'rects', 'ellipses', 'arrows', 'texts']:
                value = data.get(key)
                if value and isinstance(value, list) and len(value) > 0:
                    has_data = True
                    break
            
            if not has_data:
                try:
                    os.remove(marker_file)
                except OSError:
                    pass
                return
            
            if item.scene() is None:
                return
            
            if item_id in self._overlays:
                overlay = self._overlays[item_id]
                if overlay.scene() is None:
                    item.scene().addItem(overlay)
                overlay.from_dict(data)
            else:
                overlay = MarkerOverlay(item)
                overlay.from_dict(data)
                self._overlays[item_id] = overlay
            
            overlay.update()
            
        except json.JSONDecodeError as e:
            print(f"加载标记失败 (JSON解析错误): {e}")
            backup_file = marker_file + ".bak"
            try:
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                os.rename(marker_file, backup_file)
            except OSError:
                try:
                    os.remove(marker_file)
                except OSError:
                    pass
        except PermissionError as e:
            print(f"加载标记失败 (权限错误): {e}")
        except Exception as e:
            print(f"加载标记失败 (未知错误): {e}")
    
    def save_all_markers(self, items):
        for item in items:
            if isinstance(item, MovableImageItem):
                self.save_markers_for_item(item)
    
    def clear_all_markers(self):
        for overlay in self._overlays.values():
            if overlay.scene():
                overlay.scene().removeItem(overlay)
        self._overlays.clear()
    
    def has_markers(self, item):
        if not isinstance(item, MovableImageItem):
            return False
        item_id = item.item_id()
        return item_id in self._index


# ==================== 工具栏自定义对话框 ====================
class ToolbarCustomizeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("自定义工具栏")
        self.resize(550, 550)
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
            ("✏️ 标记工具", [
                ("btn_marker", "标记工具"),
                ("btn_clear_markers", "清除标记"),
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


# ==================== 标记工具对话框 ====================
class MarkerToolDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("标记工具")
        self.setModal(False)
        self.resize(350, 400)
        self._main_window = None
        self._find_main_window(parent)
        self._marker_tool = None
        if self._main_window:
            self._marker_tool = self._main_window._marker_tool
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
        mode_group = QGroupBox("绘制工具")
        mode_layout = QGridLayout(mode_group)
        self.mode_btns = QButtonGroup(self)
        self.btn_off = QPushButton("🔴 关闭")
        self.btn_off.setCheckable(True)
        self.btn_pen = QPushButton("✏️ 画笔")
        self.btn_pen.setCheckable(True)
        self.btn_line = QPushButton("📏 直线")
        self.btn_line.setCheckable(True)
        self.btn_rect = QPushButton("▭ 矩形")
        self.btn_rect.setCheckable(True)
        self.btn_ellipse = QPushButton("◯ 椭圆")
        self.btn_ellipse.setCheckable(True)
        self.btn_arrow = QPushButton("➡️ 箭头")
        self.btn_arrow.setCheckable(True)
        self.btn_text = QPushButton("📝 文字")
        self.btn_text.setCheckable(True)
        self.mode_btns.addButton(self.btn_off, MarkerTool.MODE_OFF)
        self.mode_btns.addButton(self.btn_pen, MarkerTool.MODE_PEN)
        self.mode_btns.addButton(self.btn_line, MarkerTool.MODE_LINE)
        self.mode_btns.addButton(self.btn_rect, MarkerTool.MODE_RECT)
        self.mode_btns.addButton(self.btn_ellipse, MarkerTool.MODE_ELLIPSE)
        self.mode_btns.addButton(self.btn_arrow, MarkerTool.MODE_ARROW)
        self.mode_btns.addButton(self.btn_text, MarkerTool.MODE_TEXT)
        buttons = [
            (self.btn_off, 0, 0), (self.btn_pen, 0, 1),
            (self.btn_line, 1, 0), (self.btn_rect, 1, 1),
            (self.btn_ellipse, 2, 0), (self.btn_arrow, 2, 1),
            (self.btn_text, 3, 0)
        ]
        for btn, row, col in buttons:
            mode_layout.addWidget(btn, row, col)
        layout.addWidget(mode_group)
        color_group = QGroupBox("颜色")
        color_layout = QHBoxLayout(color_group)
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(60, 30)
        self.color_btn.clicked.connect(self._choose_color)
        self.color_label = QLabel("#ff0000")
        color_layout.addWidget(self.color_btn)
        color_layout.addWidget(self.color_label)
        color_layout.addStretch()
        layout.addWidget(color_group)
        size_group = QGroupBox("画笔大小")
        size_layout = QHBoxLayout(size_group)
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(1, 20)
        self.size_slider.setValue(3)
        self.size_label = QLabel("3 px")
        size_layout.addWidget(self.size_slider)
        size_layout.addWidget(self.size_label)
        layout.addWidget(size_group)
        text_group = QGroupBox("文字输入")
        text_layout = QHBoxLayout(text_group)
        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText("输入要写的文字...")
        self.text_edit.returnPressed.connect(self._apply_text)
        self.text_apply_btn = QPushButton("应用")
        self.text_apply_btn.clicked.connect(self._apply_text)
        text_layout.addWidget(self.text_edit)
        text_layout.addWidget(self.text_apply_btn)
        layout.addWidget(text_group)
        btn_layout = QHBoxLayout()
        self.btn_clear_current = QPushButton("清除当前标记")
        self.btn_clear_current.clicked.connect(self._clear_current_markers)
        self.btn_clear_all = QPushButton("清除所有标记")
        self.btn_clear_all.clicked.connect(self._clear_all_markers)
        btn_layout.addWidget(self.btn_clear_current)
        btn_layout.addWidget(self.btn_clear_all)
        layout.addLayout(btn_layout)
        tip_label = QLabel(
            "提示：\n"
            "• 在图片上按住左键拖动绘制\n"
            "• 松开左键完成绘制\n"
            "• 标记会随图片一起保存\n"
            "• 选择「关闭」退出绘制模式"
        )
        tip_label.setStyleSheet("color: #888; font-size: 11px; padding: 8px;")
        tip_label.setWordWrap(True)
        layout.addWidget(tip_label)
        self.mode_btns.idClicked.connect(self._on_mode_changed)
        self.size_slider.valueChanged.connect(self._on_size_changed)
    
    def _load_values(self):
        if self._marker_tool:
            color = self._marker_tool.color
            self.color_btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #888;")
            self.color_label.setText(color.name())
            self.size_slider.setValue(self._marker_tool.pen_width)
            self.size_label.setText(f"{self._marker_tool.pen_width} px")
            self.mode_btns.button(self._marker_tool.mode).setChecked(True)
    
    def _choose_color(self):
        if not self._marker_tool:
            return
        color = QColorDialog.getColor(self._marker_tool.color, self, "选择标记颜色")
        if color.isValid():
            self._marker_tool.color = color
            self.color_btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #888;")
            self.color_label.setText(color.name())
    
    def _on_mode_changed(self, mode_id):
        if self._marker_tool:
            self._marker_tool.set_mode(mode_id)
            if mode_id == MarkerTool.MODE_OFF:
                self.setWindowTitle("标记工具 - 已关闭")
            else:
                mode_names = {
                    MarkerTool.MODE_PEN: "画笔",
                    MarkerTool.MODE_LINE: "直线",
                    MarkerTool.MODE_RECT: "矩形",
                    MarkerTool.MODE_ELLIPSE: "椭圆",
                    MarkerTool.MODE_ARROW: "箭头",
                    MarkerTool.MODE_TEXT: "文字"
                }
                self.setWindowTitle(f"标记工具 - {mode_names.get(mode_id, '未知')}")
    
    def _on_size_changed(self, value):
        if self._marker_tool:
            self._marker_tool.pen_width = value
            self.size_label.setText(f"{value} px")
    
    def _apply_text(self):
        if self._marker_tool and self._marker_tool.mode == MarkerTool.MODE_TEXT:
            text = self.text_edit.text().strip()
            if text:
                self._marker_tool.text = text
                self.text_edit.clear()
    
    def _clear_current_markers(self):
        if self._main_window:
            self._main_window.clear_markers_for_selected()
    
    def _clear_all_markers(self):
        if self._main_window:
            self._main_window.clear_all_markers()
    
    def closeEvent(self, event):
        if self._marker_tool:
            self._marker_tool.set_mode(MarkerTool.MODE_OFF)
        super().closeEvent(event)


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
        self.shape_frame = QFrame()
        shape_layout = QFormLayout(self.shape_frame)
        self.shape_combo = QComboBox()
        shape_names = {
            "square": "■ 正方形", "rectangle": "▬ 长方形",
            "triangle": "▲ 三角形", "hexagon": "⬡ 六边形",
            "circle": "● 圆形", "diamond": "◆ 菱形",
            "star": "★ 星形", "cross": "✚ 十字形",
            "pentagon": "⬠ 五边形", "octagon": "⯃ 八边形",
            "arrow_up": "↑ 上箭头", "arrow_down": "↓ 下箭头",
            "arrow_left": "← 左箭头", "arrow_right": "→ 右箭头",
            "arrow_up_right": "↗ 右上箭头", "arrow_up_left": "↖ 左上箭头",
            "arrow_down_right": "↘ 右下箭头", "arrow_down_left": "↙ 左下箭头",
            "heart": "♥ 心形", "moon": "☽ 月亮", "sun": "☀ 太阳",
            "cloud": "☁ 云朵", "lightning": "⚡ 闪电",
            "flower": "❀ 花朵", "spiral": "🌀 螺旋",
            "gear": "⚙ 齿轮", "shield": "🛡 盾牌",
            "infinity": "∞ 无限",
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
        self.zoom_effect_check = QCheckBox("整体缩放时，背景显示缩放效果")
        self.zoom_effect_check.setToolTip(
            "启用后，Ctrl+滚轮整体缩放时，背景图案会随视图一起缩放\n"
            "（网格/形状会随缩放变大变小）；关闭则背景固定不动"
        )
        layout.addWidget(self.zoom_effect_check)
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
        self.zoom_effect_check.setChecked(s.get("background_zoom", False))

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
        result["background_zoom"] = self.zoom_effect_check.isChecked()
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


# ==================== 撤销管理器 ====================
class UndoManager:
    """基于场景快照的撤销管理器（撤回上一步操作）"""
    def __init__(self, main_window, max_steps=30):
        self._main_window = main_window
        self._stack = []
        self._max_steps = max_steps
    
    def can_undo(self):
        return len(self._stack) > 0
    
    def clear(self):
        self._stack.clear()
    
    def push(self):
        """在用户操作前保存一份当前场景快照"""
        snapshot = self._capture_snapshot()
        self._stack.append(snapshot)
        if len(self._stack) > self._max_steps:
            self._stack.pop(0)
    
    def undo(self):
        """恢复上一步操作前的场景"""
        if not self._stack:
            return False
        snapshot = self._stack.pop()
        self._restore_snapshot(snapshot)
        return True
    
    def _capture_snapshot(self):
        mw = self._main_window
        scene = mw.scene
        images = []
        emojis = []
        markers = {}
        for item in scene.items():
            if isinstance(item, MovableImageItem):
                info = {
                    "id": item.item_id(),
                    "pixmap": item.original_pixmap(),
                    "scale": item.scale_factor(),
                    "opacity": item.opacity_value(),
                    "z": item.zValue(),
                    "pos": [item.pos().x(), item.pos().y()],
                    "rotation": item.rotation_value(),
                    "flipped_h": item.is_flipped_horizontal(),
                    "flipped_v": item.is_flipped_vertical(),
                    "attached_emojis": [],
                }
                for e in item.get_attached_emojis():
                    info["attached_emojis"].append({
                        "id": e.item_id(),
                        "emoji": e._emoji_char,
                        "font_size": e._font_size,
                        "scale": e.get_scale_factor(),
                        "pos": [e.pos().x(), e.pos().y()],
                        "z": e.zValue(),
                    })
                images.append(info)
                overlay = mw._marker_manager.get_overlay(item, create=False)
                if overlay is not None:
                    markers[item.item_id()] = overlay.to_dict()
            elif isinstance(item, EmojiItem) and item.get_parent_image() is None:
                emojis.append({
                    "id": item.item_id(),
                    "emoji": item._emoji_char,
                    "font_size": item._font_size,
                    "scale": item.get_scale_factor(),
                    "pos": [item.pos().x(), item.pos().y()],
                    "z": item.zValue(),
                })
        return {"images": images, "emojis": emojis, "markers": markers}
    
    def _restore_snapshot(self, snapshot):
        mw = self._main_window
        scene = mw.scene
        # 清除当前场景全部内容
        for item in list(scene.items()):
            scene.removeItem(item)
        mw._marker_manager.clear_all_markers()
        
        # 重建图片
        for info in snapshot.get("images", []):
            item = MovableImageItem(info["pixmap"], item_id=info["id"])
            item.set_scale_factor(info["scale"])
            item.set_opacity_value(info["opacity"])
            # 叠加整体透明度
            item.setOpacity(item.opacity_value() * mw._global_opacity)
            item.setZValue(info["z"])
            item.setData(0, info["z"])
            item.setPos(info["pos"][0], info["pos"][1])
            item.set_rotation_deg(info["rotation"])
            if info["flipped_h"]:
                item.flip_horizontal()
            if info["flipped_v"]:
                item.flip_vertical()
            scene.addItem(item)
            mw._on_item_added(item)
            
            # 重建吸附的Emoji
            for ed in info.get("attached_emojis", []):
                emoji = EmojiItem(ed["emoji"], parent_item=None,
                                  font_size=ed["font_size"], item_id=ed["id"])
                emoji.set_scale_factor(ed["scale"])
                emoji._parent_image = item
                emoji.setParentItem(item)
                emoji.setPos(ed["pos"][0], ed["pos"][1])
                emoji.setZValue(ed["z"])
                item._attached_emojis.append(emoji)
            
            # 重建标记
            marker_data = snapshot.get("markers", {}).get(info["id"])
            if marker_data:
                overlay = mw._marker_manager.get_overlay(item, create=True)
                overlay.from_dict(marker_data)
                overlay.update()
        
        # 重建独立Emoji
        for ed in snapshot.get("emojis", []):
            emoji = EmojiItem(ed["emoji"], parent_item=None,
                              font_size=ed["font_size"], item_id=ed["id"])
            emoji.set_scale_factor(ed["scale"])
            emoji.setPos(ed["pos"][0], ed["pos"][1])
            emoji.setZValue(ed["z"])
            scene.addItem(emoji)
        
        scene.clearSelection()
        mw.update_status(None)
        mw.view.mark_background_dirty()
        mw.schedule_autosave()


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
        self._history_mgr.set_main_window(self)
        self._marker_manager = MarkerManager()
        self._marker_tool = MarkerTool()
        self._marker_dialog = None
        self._current_draw_item = None
        self._draw_start_pos = None
        self._draw_path = None
        self._undo = UndoManager(self)
        # 图内差异比对（一张图里框选两处相似区域找差异）
        self._internal_diff_mode = False
        self._internal_diff_dragging = False
        self._diff_regions = []
        self._diff_sel_rects = []
        self._current_sel_rect = None
        self._current_sel_image = None
        self._current_sel_start = None
        
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._do_autosave)
        self._diff_markers = []
        self._heatmap_overlays = []
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

        btn_undo = QPushButton("撤回")
        btn_undo.setToolTip("撤回上一步操作 (Ctrl+Z)")
        btn_undo.clicked.connect(self.undo_last)
        act_undo = self._toolbar.addWidget(btn_undo)
        actions["btn_undo"] = act_undo
        widgets["btn_undo"] = btn_undo

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
        sld_item_opacity.sliderPressed.connect(self.push_undo)
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
        sld_global_opacity.sliderPressed.connect(self.push_undo)
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
        btn_diff.setToolTip("选中两张或多张图片，比对并标记差异区域（红色，吸附到图片）\n点击后可设置差异判定阈值")
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

        btn_internal_diff = QPushButton("图内比对")
        btn_internal_diff.setToolTip(
            "在一张图片内框选两处相似区域，找出并标记差异（吸附到图片）\n"
            "点击后可设置差异判定阈值；框选两处区域后自动比对"
        )
        btn_internal_diff.clicked.connect(self.start_internal_diff)
        act_internal_diff = self._toolbar.addWidget(btn_internal_diff)
        actions["btn_internal_diff"] = act_internal_diff
        widgets["btn_internal_diff"] = btn_internal_diff

        # 热力图透明度滑块（叠加在图片上的 SSIM 热力图透明度）
        lbl_heat = QLabel("热力:")
        act_lbl_heat = self._toolbar.addWidget(lbl_heat)
        actions["lbl_heatmap"] = act_lbl_heat
        widgets["lbl_heatmap"] = lbl_heat

        sld_heatmap = QSlider(Qt.Horizontal)
        sld_heatmap.setRange(0, 100)
        sld_heatmap.setValue(int(self._settings.get("heatmap_opacity", 50)))
        sld_heatmap.setFixedWidth(60)
        sld_heatmap.setToolTip("SSIM 热力图叠加在图片上的透明度（0=隐藏，100=不透明）")
        sld_heatmap.valueChanged.connect(self._set_heatmap_opacity)
        sld_heatmap.sliderReleased.connect(self._save_heatmap_opacity)
        act_sld_heat = self._toolbar.addWidget(sld_heatmap)
        actions["sld_heatmap_opacity"] = act_sld_heat
        widgets["sld_heatmap_opacity"] = sld_heatmap
        self.sld_heatmap_opacity = sld_heatmap

        # 显示模式下拉框：标记+热力图 / 仅热力图 / 仅标记
        lbl_heat_mode = QLabel("显示:")
        act_lbl_heat_mode = self._toolbar.addWidget(lbl_heat_mode)
        actions["lbl_heatmap_mode"] = act_lbl_heat_mode
        widgets["lbl_heatmap_mode"] = lbl_heat_mode

        combo_heatmap_mode = QComboBox()
        combo_heatmap_mode.addItem("标记+热力图", "both")
        combo_heatmap_mode.addItem("仅热力图", "heat_only")
        combo_heatmap_mode.addItem("仅标记", "marker_only")
        mode = self._settings.get("heatmap_display_mode", "both")
        idx = combo_heatmap_mode.findData(mode)
        combo_heatmap_mode.setCurrentIndex(idx if idx >= 0 else 0)
        combo_heatmap_mode.setToolTip("差异结果显示方式：\n"
                                      "标记+热力图：红色差异框 + SSIM 热力图都显示\n"
                                      "仅热力图：只显示热力图，不显示红色标记框\n"
                                      "仅标记：只显示红色标记框，不显示热力图")
        combo_heatmap_mode.currentIndexChanged.connect(self._on_heatmap_mode_changed)
        act_combo_heat_mode = self._toolbar.addWidget(combo_heatmap_mode)
        actions["combo_heatmap_mode"] = act_combo_heat_mode
        widgets["combo_heatmap_mode"] = combo_heatmap_mode
        self.combo_heatmap_mode = combo_heatmap_mode

        sep9 = self._toolbar.addSeparator()
        actions["sep9"] = sep9

        # ====== Emoji按钮 ======
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

        btn_marker = QPushButton("✏️ 标记")
        btn_marker.setToolTip("打开标记工具，在图片上画画做标记")
        btn_marker.clicked.connect(self.show_marker_tool)
        act_marker = self._toolbar.addWidget(btn_marker)
        actions["btn_marker"] = act_marker
        widgets["btn_marker"] = btn_marker

        btn_clear_markers = QPushButton("🗑️ 清标记")
        btn_clear_markers.setToolTip("清除所有图片上的标记")
        btn_clear_markers.clicked.connect(self.clear_all_markers)
        act_clear_markers = self._toolbar.addWidget(btn_clear_markers)
        actions["btn_clear_markers"] = act_clear_markers
        widgets["btn_clear_markers"] = btn_clear_markers

        sep11 = self._toolbar.addSeparator()
        actions["sep11"] = sep11

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

        sep12 = self._toolbar.addSeparator()
        actions["sep12"] = sep12

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

        sep13 = self._toolbar.addSeparator()
        actions["sep13"] = sep13

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
            "btn_import": "btn_import", "btn_paste": "btn_paste", "btn_undo": "btn_undo", "btn_del": "btn_del",
            "btn_zoom_in": "btn_zoom_in", "btn_zoom_out": "btn_zoom_out", "btn_reset": "btn_reset",
            "btn_rot_left": "btn_rot_left", "btn_rot_right": "btn_rot_right",
            "btn_flip_h": "btn_flip_h", "btn_flip_v": "btn_flip_v",
            "btn_view_in": "btn_view_in", "btn_view_out": "btn_view_out", "btn_view_fit": "btn_view_fit",
            "btn_front": "btn_front", "btn_back": "btn_back",
            "lbl_item": "item_opacity", "sld_item_opacity": "item_opacity", "lbl_item_opacity": "item_opacity",
            "lbl_global": "global_opacity", "sld_global_opacity": "global_opacity", "lbl_global_opacity": "global_opacity",
            "btn_diff": "btn_diff", "btn_clear_diff": "btn_clear_diff", "btn_internal_diff": "btn_internal_diff",
            "lbl_heatmap": "heatmap_opacity", "sld_heatmap_opacity": "heatmap_opacity",
            "lbl_heatmap_mode": "heatmap_display_mode", "combo_heatmap_mode": "heatmap_display_mode",
            "btn_emoji": "btn_emoji", "btn_emoji_favorites": "btn_emoji_favorites",
            "btn_marker": "btn_marker", "btn_clear_markers": "btn_clear_markers",
            "btn_save_hist": "btn_save_hist", "btn_history": "btn_history",
            "btn_export": "btn_export", "btn_clear": "btn_clear", "btn_settings": "btn_settings",
        }
        sep_keys = ["sep1", "sep2", "sep3", "sep4", "sep5", "sep6", "sep7", "sep8", "sep9", "sep10", "sep11", "sep12", "sep13"]
        
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
        self.marker_status_label = QLabel("标记: 关闭")
        self.marker_status_label.setStyleSheet("padding: 0 10px; color: #888;")
        self.status_bar.addPermanentWidget(self.marker_status_label)

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

    def update_marker_status(self):
        if self._marker_tool.mode == MarkerTool.MODE_OFF:
            self.marker_status_label.setText("标记: 关闭")
            self.marker_status_label.setStyleSheet("padding: 0 10px; color: #888;")
        else:
            mode_names = {
                MarkerTool.MODE_PEN: "画笔",
                MarkerTool.MODE_LINE: "直线",
                MarkerTool.MODE_RECT: "矩形",
                MarkerTool.MODE_ELLIPSE: "椭圆",
                MarkerTool.MODE_ARROW: "箭头",
                MarkerTool.MODE_TEXT: "文字"
            }
            self.marker_status_label.setText(f"标记: {mode_names.get(self._marker_tool.mode, '未知')}")
            self.marker_status_label.setStyleSheet("padding: 0 10px; color: #ff6b6b; font-weight: bold;")

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
        item = self._add_pixmap(pixmap, x, y)
        if item:
            self._marker_manager.load_markers_for_item(item)
            # ✅ 加载 Emoji
            self._autosave_mgr._load_emojis_for_item(item)
        return item

    def _add_pixmap(self, pixmap, x=None, y=None):
        self.push_undo()
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
                item = self._add_pixmap(pixmap)
                if item:
                    self._marker_manager.load_markers_for_item(item)
                    self._autosave_mgr._load_emojis_for_item(item)
                return
        QMessageBox.information(self, "提示", "剪贴板中没有图片，请先截图或复制图片后再粘贴。")

    def push_undo(self):
        """保存一份当前场景快照（用于撤回）"""
        if hasattr(self, "_undo"):
            self._undo.push()

    def undo_last(self):
        """撤回上一步操作"""
        if self._undo.undo():
            self.status_label.setText("已撤回上一步操作")
        else:
            self.status_label.setText("没有可撤回的操作")

    def delete_selected(self):
        self.push_undo()
        for item in self.scene.selectedItems():
            if isinstance(item, MovableImageItem):
                # ✅ 删除该图片的 Emoji 文件
                self._delete_emoji_file(item.item_id())
                for emoji in item.get_attached_emojis():
                    self.scene.removeItem(emoji)
                self._marker_manager.save_markers_for_item(item)
                self._marker_manager.remove_overlay(item)
                self.scene.removeItem(item)
            elif isinstance(item, EmojiItem):
                if item.get_parent_image():
                    item.get_parent_image().remove_attached_emoji(item)
                else:
                    # ✅ 删除独立 Emoji 文件中的记录
                    self._remove_orphan_emoji(item)
                self.scene.removeItem(item)
        self.update_status(None)
        self.schedule_autosave()
        self.view.mark_background_dirty()

    def _delete_emoji_file(self, item_id):
        """删除图片对应的 Emoji 文件"""
        emoji_file = os.path.join(EMOJIS_DIR, f"{item_id}.json")
        if os.path.exists(emoji_file):
            try:
                os.remove(emoji_file)
            except:
                pass

    def _remove_orphan_emoji(self, emoji):
        """从 orphans.json 中移除独立 Emoji"""
        orphans_file = os.path.join(EMOJIS_DIR, "orphans.json")
        if not os.path.exists(orphans_file):
            return
        try:
            with open(orphans_file, "r", encoding="utf-8") as f:
                orphans = json.load(f)
            orphans = [o for o in orphans if o.get("id") != emoji.item_id()]
            with open(orphans_file, "w", encoding="utf-8") as f:
                json.dump(orphans, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _save_orphan_emoji(self, emoji):
        """保存独立 Emoji 到 orphans.json"""
        if emoji.get_parent_image():
            return
        orphans_file = os.path.join(EMOJIS_DIR, "orphans.json")
        orphans = []
        if os.path.exists(orphans_file):
            try:
                with open(orphans_file, "r", encoding="utf-8") as f:
                    orphans = json.load(f)
            except:
                pass
        
        found = False
        for i, o in enumerate(orphans):
            if o.get("id") == emoji.item_id():
                orphans[i] = emoji.to_dict()
                found = True
                break
        if not found:
            orphans.append(emoji.to_dict())
        
        with open(orphans_file, "w", encoding="utf-8") as f:
            json.dump(orphans, f, ensure_ascii=False, indent=2)

    def scale_selected(self, factor):
        self.push_undo()
        for item in self.scene.selectedItems():
            if isinstance(item, MovableImageItem):
                item.set_scale_factor(item.scale_factor() * factor)
                self.update_status(item)
        self.schedule_autosave()

    def reset_scale_selected(self):
        self.push_undo()
        for item in self.scene.selectedItems():
            if isinstance(item, MovableImageItem):
                item.set_scale_factor(1.0)
                self.update_status(item)
        self.schedule_autosave()

    def rotate_selected(self, degrees):
        self.push_undo()
        for item in self.scene.selectedItems():
            if isinstance(item, MovableImageItem):
                item.rotate_by(degrees)
                self.update_status(item)
        self.schedule_autosave()

    def flip_selected_horizontal(self):
        self.push_undo()
        for item in self.scene.selectedItems():
            if isinstance(item, MovableImageItem):
                item.flip_horizontal()
                self.update_status(item)
        self.schedule_autosave()

    def flip_selected_vertical(self):
        self.push_undo()
        for item in self.scene.selectedItems():
            if isinstance(item, MovableImageItem):
                item.flip_vertical()
                self.update_status(item)
        self.schedule_autosave()

    def bring_to_front(self):
        self.push_undo()
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
            overlay = self._marker_manager.get_overlay(item, create=False)
            if overlay:
                overlay.setZValue(item.zValue() + 0.1)
        self.schedule_autosave()

    def send_to_back(self):
        self.push_undo()
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
            overlay = self._marker_manager.get_overlay(item, create=False)
            if overlay:
                overlay.setZValue(item.zValue() + 0.1)
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
            self.push_undo()
            for item in items:
                if isinstance(item, MovableImageItem):
                    self._marker_manager.save_markers_for_item(item)
                    self._marker_manager.remove_overlay(item)
                    self._delete_emoji_file(item.item_id())
                self.scene.removeItem(item)
            # 清空 orphans
            orphans_file = os.path.join(EMOJIS_DIR, "orphans.json")
            if os.path.exists(orphans_file):
                try:
                    os.remove(orphans_file)
                except:
                    pass
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
        # 弹窗设置差异判定阈值/方案
        dlg = DiffSettingsDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        threshold = dlg.get_threshold()
        mode = dlg.get_mode()
        self.clear_diff_markers()
        base_item = selected[0]
        base_img = base_item.original_pixmap().toImage().convertToFormat(QImage.Format_RGB32)
        # ====== 相似度类方案（直方图/SSIM/特征点/pHash） ======
        if mode in ("hist", "ssim", "feat", "phash"):
            results = []
            last_heat = None
            for idx, other_item in enumerate(selected[1:], 1):
                other_img = other_item.original_pixmap().toImage().convertToFormat(QImage.Format_RGB32)
                if base_img.size() != other_img.size():
                    other_img = other_img.scaled(
                        base_img.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                msg, regions, heat, ok = self._run_similarity(base_img, other_img, mode)
                last_heat = heat
                fallback_rgb = (mode == "feat" and not ok)
                if fallback_rgb:
                    regions = self._diff_regions_between(base_img, other_img, threshold,
                                                         mode="rgb", block_size=4, max_shift=4)
                    msg += "\n（未安装 OpenCV，已自动改用 RGB 差异标记）"
                display_mode = self._heatmap_display_mode()
                show_markers = display_mode in ("both", "marker_only") or fallback_rgb
                show_heatmap = display_mode in ("both", "heat_only")
                if regions and (mode == "ssim" or fallback_rgb) and show_markers:
                    overlay = DiffOverlay(other_item)
                    overlay.set_diff_rects(self._diff_local_rects(other_item, regions))
                    self._diff_markers.append(overlay)
                if mode == "ssim" and heat is not None and not heat.isNull() and show_heatmap:
                    hv = HeatmapOverlay(other_item, heat)
                    hv.setOpacity(self._settings.get("heatmap_opacity", 50) / 100.0)
                    self._heatmap_overlays.append(hv)
                results.append(f"第{idx}张:\n{msg}")
            self._show_similarity_result("\n\n".join(results), last_heat)
            return
        # ====== 区域标记方案（RGB/灰度） ======
        total_diff_regions = 0
        for other_item in selected[1:]:
            other_img = other_item.original_pixmap().toImage().convertToFormat(QImage.Format_RGB32)
            if base_img.size() != other_img.size():
                other_img = other_img.scaled(
                    base_img.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
            regions = self._diff_regions_between(
                base_img, other_img, threshold,
                mode=mode,
                block_size=4, max_shift=4)
            if not regions:
                continue
            overlay = DiffOverlay(other_item)
            overlay.set_diff_rects(self._diff_local_rects(other_item, regions))
            self._diff_markers.append(overlay)
            total_diff_regions += len(regions)
        if total_diff_regions == 0:
            QMessageBox.information(self, "比对结果", "未检测到明显差异，两张图片几乎完全相同。")
        else:
            QMessageBox.information(
                self, "比对完成",
                f"检测到 {total_diff_regions} 处差异区域，已用红色半透明框标记。\n"
                f"差异标记已吸附到图片，随图片移动/缩放/旋转而跟随。\n"
                f"可点击「清除标记」按钮移除标记。"
            )

    def _luma_bytes(self, img):
        """转为灰度（每像素1字节），返回 (字节数组, bytesPerLine)"""
        g = img.convertToFormat(QImage.Format_Grayscale8)
        return g.constBits().tobytes(), g.bytesPerLine()

    def _best_shift(self, a_bytes, a_bpl, b_bytes, b_bpl, w, h, max_shift=8,
                    step=4, align_threshold=12):
        """在 ±max_shift 内寻找使差异像素最少（diff>align_threshold）的偏移 (dx, dy)。
        step=4 为 RGB（每像素4字节，取最大通道差），step=1 为灰度。
        用「差异像素个数」而非「平均差异」评分，避免白色背景稀释导致错位被误判为对齐"""
        step2 = max(2, min(w, h) // 80)
        best_dx = best_dy = 0
        best_score = None
        # 偶步粗搜（±1 的精确对齐交给 _refine_shift），大幅减少候选数
        for dy in range(-max_shift, max_shift + 1, 2):
            for dx in range(-max_shift, max_shift + 1, 2):
                count = 0
                for y in range(max_shift, h - max_shift, step2):
                    ao = y * a_bpl
                    bo = (y + dy) * b_bpl
                    for x in range(max_shift, w - max_shift, step2):
                        o1 = ao + x * step
                        o2 = bo + (x + dx) * step
                        if o1 + step - 1 >= len(a_bytes) or o2 + step - 1 >= len(b_bytes):
                            continue
                        if step == 1:
                            d = abs(a_bytes[o1] - b_bytes[o2])
                        else:
                            d = max(abs(a_bytes[o1] - b_bytes[o2]),
                                    abs(a_bytes[o1 + 1] - b_bytes[o2 + 1]),
                                    abs(a_bytes[o1 + 2] - b_bytes[o2 + 2]))
                        if d > align_threshold:
                            count += 1
                if best_score is None or count < best_score:
                    best_score = count
                    best_dx = dx
                    best_dy = dy
        return best_dx, best_dy

    def _refine_shift(self, a_bytes, a_bpl, b_bytes, b_bpl, w, h, cx, cy,
                      block_size=4, threshold=12, max_shift=8, step=4):
        """在粗搜结果 ±1 邻域内，用「差异块数」精确对齐。
        白色背景会稀释粗搜评分（dx=1 与 dx=2 得分几乎相同），
        而正确对齐时差异块数远少于错位时，可精确区分。"""
        def count_blocks(dx, dy):
            cnt = 0
            # 只扫描中央区域带（约 1/4 面积），对齐判定无需全图，大幅提速
            y0 = max(max_shift, h * 3 // 8)
            y1 = min(h - max_shift, 5 * h // 8)
            x0 = max(max_shift, w * 3 // 8)
            x1 = min(w - max_shift, 5 * w // 8)
            # 块内全像素扫描（与最终判定一致），确保 1px 错位细条也被计入
            for by in range(y0, y1, block_size):
                for bx in range(x0, x1, block_size):
                    hit = False
                    for py in range(by, min(by + block_size, y1)):
                        ao = py * a_bpl
                        bo = (py + dy) * b_bpl
                        for px in range(bx, min(bx + block_size, x1)):
                            o1 = ao + px * step
                            o2 = bo + (px + dx) * step
                            if step == 1:
                                d = abs(a_bytes[o1] - b_bytes[o2])
                            else:
                                d = max(abs(a_bytes[o1] - b_bytes[o2]),
                                        abs(a_bytes[o1 + 1] - b_bytes[o2 + 1]),
                                        abs(a_bytes[o1 + 2] - b_bytes[o2 + 2]))
                            if d > threshold:
                                hit = True
                                break
                        if hit:
                            break
                    if hit:
                        cnt += 1
            return cnt

        best = (cx, cy)
        best_n = None
        # 十字候选（5个）：中心 + 上下左右，足够修正粗搜误差，比 3x3 快近一半
        for (dx, dy) in [(cx, cy), (cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)]:
            if not (-max_shift <= dx <= max_shift and -max_shift <= dy <= max_shift):
                continue
            n = count_blocks(dx, dy)
            if best_n is None or n < best_n:
                best_n = n
                best = (dx, dy)
        return best

    def _diff_regions_between(self, img_a, img_b, threshold, mode="rgb",
                              block_size=4, max_shift=4, max_dim=400):
        """帧差式差异比对引擎（快而准）：
        1) 统一尺寸、必要时降采样（提速，同时等效扩大对齐范围）
        2) RGB(最大通道差) 或 灰度 两种方案
        3) 自动小范围对齐（修正框选/截图错位）
        4) 块级差异判定 + 区域合并
        返回全分辨率下的差异区域列表 [(rx,ry,rw,rh)]。"""
        img_a = img_a.convertToFormat(QImage.Format_RGB32)
        img_b = img_b.convertToFormat(QImage.Format_RGB32)
        w = min(img_a.width(), img_b.width())
        h = min(img_a.height(), img_b.height())
        if w < block_size or h < block_size:
            return []
        img_a = img_a.copy(0, 0, w, h)
        img_b = img_b.copy(0, 0, w, h)
        # 降采样：提速，且让对齐在更小图像上进行（等效全分辨率对齐范围更大）
        scale = 1.0
        maxd = max(w, h)
        if maxd > max_dim:
            scale = max_dim / maxd
            wa = img_a.scaled(max(1, int(round(w * scale))),
                              max(1, int(round(h * scale))),
                              Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            wb = img_b.scaled(max(1, int(round(w * scale))),
                              max(1, int(round(h * scale))),
                              Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        else:
            wa, wb = img_a, img_b
        ww = wa.width()
        wh = wa.height()
        use_gray = (mode == "gray")
        if use_gray:
            a_bytes, a_bpl = self._luma_bytes(wa)
            b_bytes, b_bpl = self._luma_bytes(wb)
            step = 1
        else:
            a_bytes = wa.constBits().tobytes()
            b_bytes = wb.constBits().tobytes()
            a_bpl = wa.bytesPerLine()
            b_bpl = wb.bytesPerLine()
            step = 4
        # 自动对齐（修正框选/截图造成的错位）；已对齐(0,0)时跳过精搜以提速
        dx, dy = 0, 0
        if max_shift > 0:
            dx, dy = self._best_shift(a_bytes, a_bpl, b_bytes, b_bpl,
                                      ww, wh, max_shift, step, 12)
            if dx != 0 or dy != 0:
                dx, dy = self._refine_shift(a_bytes, a_bpl, b_bytes, b_bpl,
                                            ww, wh, dx, dy,
                                            block_size, 12, max_shift, step)
        x0 = max_shift
        y0 = max_shift
        x1 = ww - max_shift
        y1 = wh - max_shift
        if x1 <= x0 or y1 <= y0:
            return []
        diff_blocks = []
        for by in range(y0, y1, block_size):
            for bx in range(x0, x1, block_size):
                has_diff = False
                for py in range(by, min(by + block_size, y1)):
                    ao = py * a_bpl
                    bo = (py + dy) * b_bpl
                    for px in range(bx, min(bx + block_size, x1)):
                        o1 = ao + px * step
                        o2 = bo + (px + dx) * step
                        if step == 1:
                            d = abs(a_bytes[o1] - b_bytes[o2])
                        else:
                            d = max(abs(a_bytes[o1] - b_bytes[o2]),
                                    abs(a_bytes[o1 + 1] - b_bytes[o2 + 1]),
                                    abs(a_bytes[o1 + 2] - b_bytes[o2 + 2]))
                        if d > threshold:
                            has_diff = True
                            break
                    if has_diff:
                        break
                if has_diff:
                    diff_blocks.append((bx - x0, by - y0))
        regions = self._merge_diff_blocks(diff_blocks, block_size, x1 - x0, y1 - y0)
        # 映射回全分辨率坐标
        inv = 1.0 / scale
        return [(int(round((rx + x0) * inv)), int(round((ry + y0) * inv)),
                 int(round(rw * inv)), int(round(rh * inv)))
                for (rx, ry, rw, rh) in regions]

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

    # ==================== 相似度比对方案 ====================

    def _prep_grayscale(self, img, max_dim=256):
        """转灰度并降采样，返回 (字节数组, bytesPerLine, 宽, 高)"""
        w = img.width()
        h = img.height()
        scale = min(1.0, max_dim / max(w, h))
        if scale < 1.0:
            img = img.scaled(max(1, int(w * scale)), max(1, int(h * scale)),
                             Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        g = img.convertToFormat(QImage.Format_Grayscale8)
        return g.constBits().tobytes(), g.bytesPerLine(), g.width(), g.height()

    def _hist_similarity(self, img_a, img_b):
        """方案1：灰度直方图比对（0~1，越接近1越相似），比较整体亮度/对比度分布"""
        a_bytes, a_bpl, aw, ah = self._prep_grayscale(img_a, 256)
        b_bytes, b_bpl, bw, bh = self._prep_grayscale(img_b, 256)
        w = min(aw, bw)
        h = min(ah, bh)
        ha = [0] * 256
        hb = [0] * 256
        for y in range(h):
            ao = y * a_bpl
            bo = y * b_bpl
            for x in range(w):
                ha[a_bytes[ao + x]] += 1
                hb[b_bytes[bo + x]] += 1
        sa = sum(ha) or 1
        sb = sum(hb) or 1
        inter = 0.0
        for i in range(256):
            inter += min(ha[i] / sa, hb[i] / sb)
        return inter

    def _ssim_similarity(self, img_a, img_b, window=8, k1=0.01, k2=0.03):
        """方案2：结构相似性 SSIM（0~1）。返回 (平均SSIM, 低相似区域, 热力图QImage)"""
        a_bytes, a_bpl, aw, ah = self._prep_grayscale(img_a, 200)
        b_bytes, b_bpl, bw, bh = self._prep_grayscale(img_b, 200)
        w = min(aw, bw)
        h = min(ah, bh)
        ws = window
        L = 255.0
        c1 = (k1 * L) ** 2
        c2 = (k2 * L) ** 2
        nw = w // ws
        nh = h // ws
        total = 0.0
        count = 0
        low_regions = []
        ssim_map = []
        for wy in range(0, nh * ws, ws):
            row_scores = []
            for wx in range(0, nw * ws, ws):
                s1 = s2 = 0.0
                for yy in range(wy, wy + ws):
                    ao = yy * a_bpl
                    bo = yy * b_bpl
                    for xx in range(wx, wx + ws):
                        s1 += a_bytes[ao + xx]
                        s2 += b_bytes[bo + xx]
                n = ws * ws
                m1 = s1 / n
                m2 = s2 / n
                v1 = v2 = cov = 0.0
                for yy in range(wy, wy + ws):
                    ao = yy * a_bpl
                    bo = yy * b_bpl
                    for xx in range(wx, wx + ws):
                        d1 = a_bytes[ao + xx] - m1
                        d2 = b_bytes[bo + xx] - m2
                        v1 += d1 * d1
                        v2 += d2 * d2
                        cov += d1 * d2
                v1 /= n
                v2 /= n
                cov /= n
                ssim = ((2 * m1 * m2 + c1) * (2 * cov + c2)) / \
                       ((m1 * m1 + m2 * m2 + c1) * (v1 + v2 + c2))
                row_scores.append(ssim)
                total += ssim
                count += 1
                if ssim < 0.85:
                    low_regions.append((wx, wy, ws, ws))
            ssim_map.append(row_scores)
        mean_ssim = total / count if count else 1.0
        heat = self._ssim_heatmap(ssim_map, ws, w, h)
        # 把低相似区域映射回 img_a 全分辨率坐标
        sx = img_a.width() / w if w else 1
        sy = img_a.height() / h if h else 1
        regions = [(int(rx * sx), int(ry * sy), int(rw * sx), int(rh * sy))
                   for (rx, ry, rw, rh) in low_regions]
        return mean_ssim, regions, heat

    def _ssim_heatmap(self, ssim_map, ws, w, h):
        """把 SSIM 分数映射为彩色热力图：红=差异大，绿=相似"""
        img = QImage(w, h, QImage.Format_RGB32)
        rows = len(ssim_map)
        for ry in range(rows):
            row = ssim_map[ry]
            for rx in range(len(row)):
                s = row[rx]
                if s >= 0.95:
                    col = QColor(0, 220, 40)
                elif s >= 0.85:
                    col = QColor(0, 180, 255)
                else:
                    t = max(0.0, min(1.0, (0.85 - s) / 0.85))
                    col = QColor(int(255 * t), 60, int(140 * (1 - t)))
                px = rx * ws
                py = ry * ws
                for yy in range(py, min(py + ws, h)):
                    for xx in range(px, min(px + ws, w)):
                        img.setPixel(xx, yy, col.rgb())
        return img

    def _feature_match(self, img_a, img_b):
        """方案3：特征点匹配（需 OpenCV）。返回 (结果文本, 是否成功)"""
        try:
            import cv2
            import numpy as np
        except ImportError:
            return "特征点匹配需要安装 OpenCV：\npip install opencv-python numpy", False

        def to_gray(img):
            g = img.convertToFormat(QImage.Format_Grayscale8)
            gw = g.width()
            gh = g.height()
            b = g.constBits().tobytes()
            arr = np.frombuffer(b, dtype=np.uint8).reshape((gh, g.bytesPerLine()))[:, :gw]
            return np.ascontiguousarray(arr)

        try:
            ga = to_gray(img_a)
            gb = to_gray(img_b)
            orb = cv2.ORB_create(nfeatures=1000)
            kp1, des1 = orb.detectAndCompute(ga, None)
            kp2, des2 = orb.detectAndCompute(gb, None)
            if des1 is None or des2 is None or len(kp1) < 5 or len(kp2) < 5:
                return "特征点过少，无法有效匹配（图片可能过于简单或差异过大）", False
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(des1, des2)
            matches = sorted(matches, key=lambda x: x.distance)
            good = [m for m in matches if m.distance < 50]
            ratio = len(good) / max(len(matches), 1)
            return (f"特征点匹配：图1 {len(kp1)} 个点，图2 {len(kp2)} 个点，"
                    f"匹配 {len(matches)} 对，优质 {len(good)} 对\n"
                    f"相似度约 {ratio * 100:.0f}%（匹配越密越相似）"), True
        except Exception as e:
            return f"特征点匹配出错：{e}", False

    def _phash(self, img):
        """感知哈希：缩放到 32x32 灰度 → DCT → 取 8x8 低频 → 按中位数生成 64 位哈希"""
        g = img.convertToFormat(QImage.Format_Grayscale8).scaled(
            32, 32, Qt.IgnoreAspectRatio, Qt.SmoothTransformation
        )
        b = g.constBits().tobytes()
        n = 32
        temp = [[0.0] * n for _ in range(n)]
        dct = [[0.0] * n for _ in range(n)]
        for u in range(n):
            for v in range(n):
                s = 0.0
                for x in range(n):
                    s += b[u * n + x] * math.cos(math.pi * (2 * x + 1) * v / (2 * n))
                temp[u][v] = s
        for u in range(n):
            for v in range(n):
                s = 0.0
                for y in range(n):
                    s += temp[y][v] * math.cos(math.pi * (2 * y + 1) * u / (2 * n))
                dct[u][v] = s
        coeffs = [int(round(dct[u][v])) for u in range(8) for v in range(8)]
        med = sorted(coeffs)[len(coeffs) // 2]
        h = 0
        for i, c in enumerate(coeffs):
            if c > med:
                h |= (1 << i)
        return h

    def _phash_distance(self, img_a, img_b):
        """方案4：感知哈希。返回 (汉明距离0~64, 相似度0~1)"""
        h1 = self._phash(img_a)
        h2 = self._phash(img_b)
        d = bin(h1 ^ h2).count("1")
        return d, 1.0 - d / 64.0

    def _run_similarity(self, img_a, img_b, mode):
        """运行相似度类方案，返回 (结果文本, 待标记区域, 热力图QImage或None, 是否成功)"""
        if mode == "hist":
            score = self._hist_similarity(img_a, img_b)
            return (f"灰度直方图相似度：{score * 100:.1f}%\n"
                    f"（1=亮度分布完全一致；越高越相似）", [], None, True)
        if mode == "ssim":
            mean, regions, heat = self._ssim_similarity(img_a, img_b)
            return (f"SSIM 结构相似度：{mean * 100:.1f}%\n"
                    f"（1=人眼感知完全一致；<85% 的区域已标红）", regions, heat, True)
        if mode == "feat":
            text, ok = self._feature_match(img_a, img_b)
            return (text, [], None, ok)
        if mode == "phash":
            dist, sim = self._phash_distance(img_a, img_b)
            return (f"感知哈希（pHash）：汉明距离 {dist}/64\n"
                    f"相似度 {sim * 100:.1f}%（距离越近越相似，0=完全一致）", [], None, True)
        return ("", [], None, True)

    def _show_similarity_result(self, msg, heat=None):
        if heat is not None and not heat.isNull():
            dlg = SimilarityResultDialog(msg, heat, self)
            dlg.exec()
        else:
            QMessageBox.information(self, "比对结果", msg)

    def _diff_local_rects(self, other_item, regions):
        """把原图坐标的差异区域映射到图片当前显示（本地）坐标"""
        pw = other_item.pixmap().width()
        ph = other_item.pixmap().height()
        base_w = other_item.original_size().width()
        base_h = other_item.original_size().height()
        sx = pw / base_w if base_w else 1
        sy = ph / base_h if base_h else 1
        local_rects = []
        for (rx, ry, rw, rh) in regions:
            lx = rx * sx
            ly = ry * sy
            lw = rw * sx
            lh = rh * sy
            if other_item.is_flipped_horizontal():
                lx = pw - (rx + rw) * sx
            if other_item.is_flipped_vertical():
                ly = ph - (ry + rh) * sy
            local_rects.append(QRectF(lx, ly, lw, lh))
        return local_rects

    def clear_diff_markers(self):
        for marker in self._diff_markers:
            if marker and marker.scene():
                self.scene.removeItem(marker)
        self._diff_markers = []
        # 同时清除叠加在图片上的热力图
        for ov in self._heatmap_overlays:
            if ov and ov.scene():
                self.scene.removeItem(ov)
        self._heatmap_overlays = []

    def _set_heatmap_opacity(self, value):
        """实时调整所有热力图覆盖层的透明度"""
        opacity = value / 100.0
        for ov in self._heatmap_overlays:
            if ov:
                ov.setOpacity(opacity)

    def _save_heatmap_opacity(self):
        self._settings.set("heatmap_opacity", self.sld_heatmap_opacity.value())
        self._settings.save()

    def _heatmap_display_mode(self):
        """当前差异显示模式：both=标记+热力图, heat_only=仅热力图, marker_only=仅标记"""
        return self._settings.get("heatmap_display_mode", "both")

    def _on_heatmap_mode_changed(self, index):
        mode = self.combo_heatmap_mode.itemData(index)
        self._settings.set("heatmap_display_mode", mode)
        self._settings.save()
        self._apply_heatmap_display_mode()

    def _apply_heatmap_display_mode(self):
        """根据当前显示模式，实时显示/隐藏所有差异标记与热力图覆盖层"""
        mode = self._heatmap_display_mode()
        show_markers = mode in ("both", "marker_only")
        show_heatmap = mode in ("both", "heat_only")
        for marker in self._diff_markers:
            if marker:
                marker.setVisible(show_markers)
        for ov in self._heatmap_overlays:
            if ov:
                ov.setVisible(show_heatmap)

    # ==================== 图内差异比对 ====================
    
    def start_internal_diff(self):
        """进入「图内比对」模式：在一张图内框选两处相似区域找差异"""
        if self._internal_diff_mode:
            self.exit_internal_diff()
            return
        dlg = DiffSettingsDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        self._internal_diff_mode = True
        self._internal_diff_dragging = False
        self._diff_regions = []
        self._diff_sel_rects = []
        self._current_sel_rect = None
        self._current_sel_image = None
        self._current_sel_start = None
        self.view.viewport().setCursor(Qt.CrossCursor)
        self.status_label.setText("图内比对：请在图片上框选第一处区域（右键取消）...")
        self.view.viewport().update()

    def exit_internal_diff(self):
        """退出图内比对模式"""
        self._internal_diff_mode = False
        self._internal_diff_dragging = False
        self._remove_diff_sel_rects()
        self._diff_regions = []
        self._current_sel_image = None
        self._current_sel_start = None
        self.view.viewport().setCursor(Qt.ArrowCursor)
        self.update_status(None)
        self.view.viewport().update()

    def _remove_diff_sel_rects(self):
        if self._current_sel_rect and self._current_sel_rect.scene():
            self.scene.removeItem(self._current_sel_rect)
        self._current_sel_rect = None
        for r in self._diff_sel_rects:
            if r and r.scene():
                self.scene.removeItem(r)
        self._diff_sel_rects = []

    def _find_image_at(self, event):
        """返回鼠标位置所在（或覆盖的）可移动图片"""
        scene_pos = self.view.mapToScene(event.position().toPoint())
        item = self.scene.itemAt(scene_pos, self.view.transform())
        if isinstance(item, MovableImageItem):
            return item
        if isinstance(item, (DiffOverlay, MarkerOverlay, HeatmapOverlay)) and getattr(item, "_parent_item", None):
            return item._parent_item
        for it in self.scene.items(scene_pos):
            if isinstance(it, MovableImageItem):
                return it
        return None

    def _on_internal_diff_press(self, event):
        target = self._find_image_at(event)
        if target is None:
            self.status_label.setText("图内比对：请先点击一张图片，再框选区域...")
            return
        local = target.mapFromScene(self.view.mapToScene(event.position().toPoint()))
        self._current_sel_image = target
        self._current_sel_start = local
        self._internal_diff_dragging = True
        # 创建当前框选矩形（吸附到图片本地坐标）
        self._current_sel_rect = QGraphicsRectItem()
        self._current_sel_rect.setPen(QPen(QColor(0, 160, 255), 2, Qt.DashLine))
        self._current_sel_rect.setBrush(QBrush(QColor(0, 160, 255, 40)))
        self._current_sel_rect.setZValue(10000)
        self._current_sel_rect.setParentItem(target)
        self._current_sel_rect.setRect(QRectF(local, local))
        self.view.viewport().update()

    def _on_internal_diff_move(self, event):
        if not self._internal_diff_dragging or not self._current_sel_image:
            return
        local = self._current_sel_image.mapFromScene(
            self.view.mapToScene(event.position().toPoint())
        )
        if self._current_sel_rect:
            self._current_sel_rect.setRect(
                QRectF(self._current_sel_start, local).normalized()
            )
            self.view.viewport().update()

    def _on_internal_diff_release(self, event):
        if not self._internal_diff_dragging or not self._current_sel_image:
            return
        local = self._current_sel_image.mapFromScene(
            self.view.mapToScene(event.position().toPoint())
        )
        rect = QRectF(self._current_sel_start, local).normalized()
        pw = self._current_sel_image.pixmap().width()
        ph = self._current_sel_image.pixmap().height()
        rect = rect.intersected(QRectF(0, 0, pw, ph))
        self._internal_diff_dragging = False
        if rect.width() < 5 or rect.height() < 5:
            if self._current_sel_rect and self._current_sel_rect.scene():
                self.scene.removeItem(self._current_sel_rect)
            self._current_sel_rect = None
            self.status_label.setText("区域太小，请重新框选当前区域...")
            return
        self._diff_regions.append((self._current_sel_image, QRectF(rect)))
        if len(self._diff_regions) == 1:
            # 第一处区域确定，把当前矩形保留为已选区域指示
            if self._current_sel_rect:
                self._diff_sel_rects.append(self._current_sel_rect)
            self._current_sel_rect = None
            self.status_label.setText("图内比对：已选第一处区域，请框选第二处区域（右键取消）...")
        else:
            self._run_internal_diff()

    def _run_internal_diff(self):
        if len(self._diff_regions) < 2:
            return
        (img1, r1), (img2, r2) = self._diff_regions
        self._remove_diff_sel_rects()
        self._diff_regions = []
        # 从当前显示（本地）坐标裁剪两个区域
        img_a = img1.pixmap().copy(r1.toRect()).toImage().convertToFormat(QImage.Format_RGB32)
        img_b = img2.pixmap().copy(r2.toRect()).toImage().convertToFormat(QImage.Format_RGB32)
        if img_a.isNull() or img_b.isNull() or img_a.width() < 1 or img_b.width() < 1:
            QMessageBox.information(self, "提示", "无法读取所选区域，请重新框选。")
            self.exit_internal_diff()
            return
        mode = self._settings.get("diff_mode", "rgb")
        if mode in ("hist", "ssim", "feat", "phash"):
            # 相似度类方案：输出相似度分数（SSIM 附差异热力图与标记）
            msg, regions, heat, ok = self._run_similarity(img_a, img_b, mode)
            fallback_rgb = (mode == "feat" and not ok)
            if fallback_rgb:
                # 未安装 OpenCV 时回退为 RGB 差异标记，保证有可见效果
                thr = int(self._settings.get("diff_threshold", 30))
                regions = self._diff_regions_between(img_a, img_b, thr, mode="rgb",
                                                     block_size=4, max_shift=4)
                msg += "\n（未安装 OpenCV，已自动改用 RGB 差异标记）"
            display_mode = self._heatmap_display_mode()
            show_markers = display_mode in ("both", "marker_only") or fallback_rgb
            show_heatmap = display_mode in ("both", "heat_only")
            if regions and show_markers:
                targets = ([(img2, r2)] if (mode == "ssim" and not fallback_rgb)
                           else [(img1, r1), (img2, r2)])
                for (img_item, region_rect) in targets:
                    rects = [QRectF(region_rect.x() + rx, region_rect.y() + ry, rw, rh)
                             for (rx, ry, rw, rh) in regions]
                    overlay = DiffOverlay(img_item)
                    overlay.set_diff_rects(rects)
                    self._diff_markers.append(overlay)
            if mode == "ssim" and heat is not None and not heat.isNull() and show_heatmap:
                # 把 SSIM 热力图叠加到第二处框选区域上（吸附图片，透明度可调）
                hv = HeatmapOverlay(img2, heat, r2)
                hv.setOpacity(self._settings.get("heatmap_opacity", 50) / 100.0)
                self._heatmap_overlays.append(hv)
            self.exit_internal_diff()
            self._show_similarity_result(msg, heat)
            return
        threshold = int(self._settings.get("diff_threshold", 30))
        # 快速比对 + 自动对齐（修正两处区域框选时的轻微错位）
        regions = self._diff_regions_between(
            img_a, img_b, threshold,
            mode=mode,
            block_size=4, max_shift=4)
        total = 0
        if regions:
            # 在两处区域都标记差异（吸附到图片）
            for (img_item, region_rect) in ((img1, r1), (img2, r2)):
                rects = [
                    QRectF(region_rect.x() + rx, region_rect.y() + ry, rw, rh)
                    for (rx, ry, rw, rh) in regions
                ]
                overlay = DiffOverlay(img_item)
                overlay.set_diff_rects(rects)
                self._diff_markers.append(overlay)
                total += len(rects)
        self.exit_internal_diff()
        if total == 0:
            QMessageBox.information(self, "比对结果", "未检测到明显差异，两处区域几乎完全相同。")
        else:
            QMessageBox.information(
                self, "比对完成",
                f"检测到 {total // 2} 处差异区域，已在两处区域同时用红色框标记（吸附到图片）。\n"
                f"可点击「清除标记」按钮移除标记。"
            )

    # ==================== 标记工具方法 ====================
    
    def show_marker_tool(self):
        if self._marker_dialog is None:
            self._marker_dialog = MarkerToolDialog(self)
        self._marker_dialog.show()
        self._marker_dialog.raise_()
        self._marker_dialog.activateWindow()
        self.update_marker_status()

    def _start_marker_draw(self, item, pos):
        if self._marker_tool.mode == MarkerTool.MODE_OFF:
            return
        self.push_undo()
        
        if self._marker_tool.is_drawing:
            self._end_marker_draw()
        
        self._current_draw_item = item
        scene_pos = self.view.mapToScene(pos.toPoint())
        local_pos = item.mapFromScene(scene_pos)
        self._draw_start_pos = local_pos
        
        overlay = self._marker_manager.get_overlay(item, create=True)
        if not overlay:
            return
        
        overlay.set_pen_color(self._marker_tool.color)
        overlay.set_pen_width(self._marker_tool.pen_width)
        self._marker_tool.is_drawing = True
        
        if self._marker_tool.mode == MarkerTool.MODE_PEN:
            self._draw_path = QPainterPath()
            self._draw_path.moveTo(local_pos)
            self._preview_path_index = len(overlay._paths)
            overlay._paths.append(QPainterPath())
        elif self._marker_tool.mode == MarkerTool.MODE_LINE:
            self._preview_line_index = len(overlay._lines)
            overlay._lines.append((local_pos, local_pos))
        elif self._marker_tool.mode == MarkerTool.MODE_RECT:
            self._preview_rect_index = len(overlay._rects)
            overlay._rects.append(QRectF(local_pos, local_pos))
        elif self._marker_tool.mode == MarkerTool.MODE_ELLIPSE:
            self._preview_ellipse_index = len(overlay._ellipses)
            overlay._ellipses.append(QRectF(local_pos, local_pos))
        elif self._marker_tool.mode == MarkerTool.MODE_ARROW:
            self._preview_arrow_index = len(overlay._arrows)
            overlay._arrows.append((local_pos, local_pos))
        elif self._marker_tool.mode == MarkerTool.MODE_TEXT:
            text = self._marker_tool.text or "标记"
            overlay.add_text(local_pos, text)
            self._marker_tool.is_drawing = False
            self._current_draw_item = None
            self._draw_start_pos = None
            self._marker_manager.save_markers_for_item(item)
            self.schedule_autosave()

    def _continue_marker_draw(self, pos):
        if not self._marker_tool.is_drawing or not self._current_draw_item:
            return
        
        item = self._current_draw_item
        scene_pos = self.view.mapToScene(pos.toPoint())
        local_pos = item.mapFromScene(scene_pos)
        
        overlay = self._marker_manager.get_overlay(item, create=False)
        if not overlay:
            return
        
        if self._marker_tool.mode == MarkerTool.MODE_PEN:
            if self._draw_path is None:
                self._draw_path = QPainterPath()
                self._draw_path.moveTo(self._draw_start_pos or local_pos)
            self._draw_path.lineTo(local_pos)
            if hasattr(self, '_preview_path_index') and self._preview_path_index < len(overlay._paths):
                overlay._paths[self._preview_path_index] = QPainterPath(self._draw_path)
            else:
                self._preview_path_index = len(overlay._paths)
                overlay._paths.append(QPainterPath(self._draw_path))
            overlay._dirty = True
            overlay.update()
        
        elif self._marker_tool.mode == MarkerTool.MODE_LINE:
            if hasattr(self, '_preview_line_index') and self._preview_line_index < len(overlay._lines):
                overlay._lines[self._preview_line_index] = (self._draw_start_pos, local_pos)
            else:
                self._preview_line_index = len(overlay._lines)
                overlay._lines.append((self._draw_start_pos, local_pos))
            overlay._dirty = True
            overlay.update()
        
        elif self._marker_tool.mode == MarkerTool.MODE_RECT:
            rect = QRectF(self._draw_start_pos, local_pos).normalized()
            if hasattr(self, '_preview_rect_index') and self._preview_rect_index < len(overlay._rects):
                overlay._rects[self._preview_rect_index] = rect
            else:
                self._preview_rect_index = len(overlay._rects)
                overlay._rects.append(rect)
            overlay._dirty = True
            overlay.update()
        
        elif self._marker_tool.mode == MarkerTool.MODE_ELLIPSE:
            rect = QRectF(self._draw_start_pos, local_pos).normalized()
            if hasattr(self, '_preview_ellipse_index') and self._preview_ellipse_index < len(overlay._ellipses):
                overlay._ellipses[self._preview_ellipse_index] = rect
            else:
                self._preview_ellipse_index = len(overlay._ellipses)
                overlay._ellipses.append(rect)
            overlay._dirty = True
            overlay.update()
        
        elif self._marker_tool.mode == MarkerTool.MODE_ARROW:
            if hasattr(self, '_preview_arrow_index') and self._preview_arrow_index < len(overlay._arrows):
                overlay._arrows[self._preview_arrow_index] = (self._draw_start_pos, local_pos)
            else:
                self._preview_arrow_index = len(overlay._arrows)
                overlay._arrows.append((self._draw_start_pos, local_pos))
            overlay._dirty = True
            overlay.update()

    def _end_marker_draw(self):
        if not self._marker_tool.is_drawing:
            return
        
        item = self._current_draw_item
        overlay = self._marker_manager.get_overlay(item, create=False)
        
        if overlay and item and self._draw_start_pos is not None:
            cursor_pos = self.view.mapFromGlobal(QCursor.pos())
            scene_pos = self.view.mapToScene(cursor_pos)
            end_pos = item.mapFromScene(scene_pos)
            
            if self._marker_tool.mode == MarkerTool.MODE_PEN:
                if self._draw_path is not None and self._draw_path.elementCount() <= 1:
                    if hasattr(self, '_preview_path_index') and self._preview_path_index < len(overlay._paths):
                        dot_path = QPainterPath()
                        r = max(0.5, self._marker_tool.pen_width / 2)
                        dot_path.addEllipse(QPointF(self._draw_start_pos), r, r)
                        overlay._paths[self._preview_path_index] = dot_path
                
            elif self._marker_tool.mode == MarkerTool.MODE_LINE:
                if hasattr(self, '_preview_line_index') and self._preview_line_index < len(overlay._lines):
                    line = overlay._lines[self._preview_line_index]
                    dx = line[1].x() - line[0].x()
                    dy = line[1].y() - line[0].y()
                    if abs(dx) < 1 and abs(dy) < 1:
                        overlay._lines[self._preview_line_index] = (self._draw_start_pos, 
                            QPointF(self._draw_start_pos.x() + 1, self._draw_start_pos.y()))
                
            elif self._marker_tool.mode == MarkerTool.MODE_RECT:
                if hasattr(self, '_preview_rect_index') and self._preview_rect_index < len(overlay._rects):
                    rect = overlay._rects[self._preview_rect_index]
                    if rect.width() < 1 and rect.height() < 1:
                        overlay._rects.pop(self._preview_rect_index)
                    elif rect.width() < 1 or rect.height() < 1:
                        overlay._rects[self._preview_rect_index] = rect.normalized()
                        
            elif self._marker_tool.mode == MarkerTool.MODE_ELLIPSE:
                if hasattr(self, '_preview_ellipse_index') and self._preview_ellipse_index < len(overlay._ellipses):
                    rect = overlay._ellipses[self._preview_ellipse_index]
                    if rect.width() < 1 and rect.height() < 1:
                        overlay._ellipses.pop(self._preview_ellipse_index)
                        
            elif self._marker_tool.mode == MarkerTool.MODE_ARROW:
                pass
            
            if overlay and item:
                self._marker_manager.save_markers_for_item(item)
                items = [i for i in self.scene.items() if isinstance(i, MovableImageItem)]
                self._autosave_mgr.save_state(items)
            self.schedule_autosave()

        self._marker_tool.is_drawing = False
        self._current_draw_item = None
        self._draw_start_pos = None
        self._draw_path = None
        
        for attr in ['_preview_path_index', '_preview_line_index', '_preview_rect_index', 
                    '_preview_ellipse_index', '_preview_arrow_index']:
            if hasattr(self, attr):
                delattr(self, attr)
        
        self.view.viewport().update()

    def clear_markers_for_item(self, item):
        if not isinstance(item, MovableImageItem):
            return
        overlay = self._marker_manager.get_overlay(item, create=False)
        if overlay:
            overlay.clear()
            self._marker_manager.save_markers_for_item(item)
        self.view.update()

    def clear_markers_for_selected(self):
        for item in self.scene.selectedItems():
            if isinstance(item, MovableImageItem):
                self.clear_markers_for_item(item)

    def clear_all_markers(self):
        reply = QMessageBox.question(
            self, "确认", "确定要清除所有图片上的标记吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            for item in self.scene.items():
                if isinstance(item, MovableImageItem):
                    overlay = self._marker_manager.get_overlay(item, create=False)
                    if overlay:
                        overlay.clear()
                        self._marker_manager.save_markers_for_item(item)
            self.view.update()
            self.status_label.setText("已清除所有标记")

    # ==================== Emoji相关方法 ====================
    
    def show_emoji_picker(self, parent_image=None):
        """显示Emoji选择器"""
        dlg = EmojiPickerDialog(self, parent_image)
        dlg.exec()

    def show_favorite_emojis(self):
        """显示常用Emoji快速选择菜单"""
        menu = QMenu(self)
        for emoji in COMMON_EMOJIS[:24]:
            act = menu.addAction(emoji)
            act.setFont(QFont("Segoe UI Emoji", 14))
            act.triggered.connect(lambda checked, e=emoji: self._add_emoji_to_selected_or_canvas(e))
        menu.addSeparator()
        open_picker = menu.addAction("📂 打开完整选择器...")
        open_picker.triggered.connect(lambda: self.show_emoji_picker(None))
        menu.exec(QCursor.pos())

    def _add_emoji_to_selected_or_canvas(self, emoji_char):
        """将Emoji添加到选中的图片或画布"""
        selected = [i for i in self.scene.selectedItems() if isinstance(i, MovableImageItem)]
        if selected:
            self.add_emoji_to_image(emoji_char, selected[0])
        else:
            self.add_emoji_to_canvas(emoji_char)

    def _record_recent_emoji(self, emoji_char):
        """记录最近使用的Emoji，便于下次在选择器中快速添加"""
        recent = list(self._settings.get("recent_emojis", []) or [])
        if emoji_char in recent:
            recent.remove(emoji_char)
        recent.insert(0, emoji_char)
        self._settings.set("recent_emojis", recent[:40])
        self._settings.save()

    def add_emoji_to_image(self, emoji_char, parent_image):
        """将Emoji添加到指定图片并吸附"""
        if not parent_image or not isinstance(parent_image, MovableImageItem):
            return
        self.push_undo()
        self._record_recent_emoji(emoji_char)
        
        center = parent_image.boundingRect().center()
        emoji = EmojiItem(emoji_char, font_size=48)
        self.scene.addItem(emoji)
        emoji.setPos(parent_image.scenePos() + center)
        parent_image.add_attached_emoji(emoji)
        emoji.setZValue(100)
        self.scene.clearSelection()
        emoji.setSelected(True)
        self.update_status(emoji)
        self.schedule_autosave()
        self.view.mark_background_dirty()

    def add_emoji_to_canvas(self, emoji_char):
        """将Emoji独立添加到画布"""
        self.push_undo()
        self._record_recent_emoji(emoji_char)
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

    # ==================== 自动保存相关 ====================

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
            self._marker_manager.save_all_markers(
                [i for i in items if isinstance(i, MovableImageItem)]
            )
            self._autosave_mgr.save_state(items)
        except Exception as e:
            print(f"自动保存失败: {e}")

    def _try_restore_autosave(self):
        if not self._autosave_mgr.has_autosave():
            return
        count = self._autosave_mgr.load_state(self.scene, self._on_item_added)
        if count > 0:
            QTimer.singleShot(200, self._restore_all_markers)
            self.status_label.setText(f"已自动恢复上次画面，共 {count} 个元素")
            QTimer.singleShot(100, self.view.fit_all_items)

    def _restore_all_markers(self):
        restored_count = 0
        failed_count = 0
        total_items = 0
        
        for item in self.scene.items():
            if isinstance(item, MovableImageItem):
                total_items += 1
                item_id = item.item_id()
                marker_file = os.path.join(MARKERS_DIR, f"{item_id}.json")
                
                if os.path.exists(marker_file):
                    try:
                        if item.scene() is not None:
                            self._marker_manager.load_markers_for_item(item)
                            overlay = self._marker_manager.get_overlay(item, create=False)
                            if overlay and overlay.has_markers():
                                restored_count += 1
                            else:
                                failed_count += 1
                    except Exception as e:
                        failed_count += 1
                        print(f"恢复标记失败 ({item_id}): {e}")
        
        if total_items > 0:
            msg = f"已自动恢复上次画面，共 {total_items} 个元素"
            if restored_count > 0:
                msg += f"，{restored_count} 个有标记"
            if failed_count > 0:
                msg += f"，{failed_count} 个标记加载失败"
            self.status_label.setText(msg)
            if restored_count > 0:
                self.view.viewport().update()

    # ==================== 历史记录相关 ====================

    def save_to_history(self):
        items = [i for i in self.scene.items() if isinstance(i, MovableImageItem) or isinstance(i, EmojiItem)]
        if not items:
            QMessageBox.information(self, "提示", "画布上没有内容，无法保存到历史记录。")
            return
        self._marker_manager.save_all_markers(
            [i for i in items if isinstance(i, MovableImageItem)]
        )
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
            if isinstance(item, MovableImageItem) or isinstance(item, DiffMarkerItem) or isinstance(item, MarkerOverlay) or isinstance(item, EmojiItem):
                self.scene.removeItem(item)
        self._diff_markers = []
        self._marker_manager.clear_all_markers()
        count = self._history_mgr.load_history(hid, self.scene, self._on_item_added)
        self.clear_diff_markers()
        if count > 0:
            for item in self.scene.items():
                if isinstance(item, MovableImageItem):
                    self._marker_manager.load_markers_for_item(item)
            self.status_label.setText(f"已加载历史记录，共 {count} 个元素")
            self.view.fit_all_items()
            self.schedule_autosave()
        else:
            QMessageBox.warning(self, "失败", "加载历史记录失败。")

    # ==================== 导出相关 ====================

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
        
        draw_items = []
        for item in self.scene.items():
            if isinstance(item, MovableImageItem):
                draw_items.append(item)
            elif isinstance(item, MarkerOverlay):
                draw_items.append(item)
            elif isinstance(item, EmojiItem):
                draw_items.append(item)
        
        sorted_items = sorted(draw_items, key=lambda x: x.zValue())
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
            elif isinstance(item, MarkerOverlay):
                parent_item = item._parent_item
                if parent_item and parent_item.scene():
                    rect = parent_item.sceneBoundingRect()
                    cx = rect.center().x() - min_x + margin
                    cy = rect.center().y() - min_y + margin
                    painter.save()
                    painter.translate(cx, cy)
                    painter.rotate(parent_item.rotation_value())
                    painter.setOpacity(parent_item.opacity_value() * self._global_opacity)
                    item.paint(painter, None, None)
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

    # ==================== 键盘事件 ====================

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Semicolon and event.modifiers() == Qt.MetaModifier:
            self.show_emoji_picker(None)
            event.accept()
            return

        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.view.set_space_pressed(True)
            event.accept()
            return
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            selected = self.scene.selectedItems()
            if selected:
                for item in selected:
                    if isinstance(item, EmojiItem):
                        if item.get_parent_image():
                            item.get_parent_image().remove_attached_emoji(item)
                        else:
                            self._remove_orphan_emoji(item)
                        self.scene.removeItem(item)
                    elif isinstance(item, MovableImageItem):
                        self._delete_emoji_file(item.item_id())
                        for emoji in item.get_attached_emojis():
                            self.scene.removeItem(emoji)
                        self._marker_manager.save_markers_for_item(item)
                        self._marker_manager.remove_overlay(item)
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
        if event.key() == Qt.Key_Z and event.modifiers() & Qt.ControlModifier:
            self.undo_last()
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
        if event.key() == Qt.Key_Escape:
            if self._marker_tool.mode != MarkerTool.MODE_OFF:
                self._marker_tool.set_mode(MarkerTool.MODE_OFF)
                self.update_marker_status()
                if self._marker_dialog:
                    self._marker_dialog.mode_btns.button(MarkerTool.MODE_OFF).setChecked(True)
                    self._marker_dialog.setWindowTitle("标记工具 - 已关闭")
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
        items = [i for i in self.scene.items() if isinstance(i, MovableImageItem) or isinstance(i, EmojiItem)]
        self._marker_manager.save_all_markers(
            [i for i in items if isinstance(i, MovableImageItem)]
        )
        # ✅ 保存前先保存所有 Emoji 到独立文件
        for item in self.scene.items():
            if isinstance(item, MovableImageItem):
                self._autosave_mgr._save_emojis_for_item(item)
            elif isinstance(item, EmojiItem) and not item.get_parent_image():
                self._save_orphan_emoji(item)
        self._do_autosave()
        if self._marker_dialog:
            self._marker_dialog.close()
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