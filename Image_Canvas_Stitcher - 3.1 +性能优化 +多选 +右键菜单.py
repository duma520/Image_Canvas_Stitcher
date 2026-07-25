# -*- coding: utf-8 -*-
"""
图片自由拼接工具 - Image Canvas Stitcher (PySide6 版本)
功能：
- 从剪贴板粘贴图片 (Ctrl+V)
- 拖拽文件导入图片
- 鼠标拖动自由摆放图片位置
- 滚轮缩放选中的图片（选中时）或缩放整个视图（未选中时 / Ctrl+滚轮）
- 大画布可平移（按住空格+鼠标拖动 / 中键拖动）
- 框选多图：空白处按住左键拖拽可框选多张，多选后可一起移动/删除/缩放
- 右键菜单：删除、缩放、透明度、图层、比对差异、导入导出等常用操作
- 导出拼接后的完整大图
- 视图整体缩放，方便看全貌和细节
- 单张/整体透明度调整
- 图片差异比对与红色标记
- 自动保存，下次启动自动恢复上次画面
- 历史记录管理，可保存、预览、加载历史项目
- 【优化】大量图片时的渲染性能（BSP索引、图元缓存、最小化视口更新）
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
    QDialog, QDialogButtonBox, QSplitter, QGraphicsRectItem
)
from PySide6.QtGui import (
    QPixmap, QImage, QClipboard, QPainter, QAction, QCursor,
    QPen, QColor, QBrush, QIcon
)
from PySide6.QtCore import Qt, QPointF, QRectF, QSizeF, QTimer, QSize
from PySide6.QtGui import QKeySequence

# ==================== 配置常量 ====================
APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".image_stitcher")
AUTOSAVE_DIR = os.path.join(APP_DATA_DIR, "autosave")
HISTORY_DIR = os.path.join(APP_DATA_DIR, "history")
AUTOSAVE_DELAY_MS = 3000  # 自动保存防抖延迟（加长减少频繁IO）
MAX_HISTORY_ITEMS = 50


def ensure_dirs():
    for d in [APP_DATA_DIR, AUTOSAVE_DIR, HISTORY_DIR,
              os.path.join(AUTOSAVE_DIR, "images"),
              os.path.join(HISTORY_DIR, "images")]:
        os.makedirs(d, exist_ok=True)


# ==================== 可移动图片图元 ====================
class MovableImageItem(QGraphicsPixmapItem):
    """可移动、可缩放、可调透明度的图片图元（带渲染缓存优化）"""

    def __init__(self, pixmap, parent=None, item_id=None):
        super().__init__(pixmap, parent)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        # 渲染缓存：设备坐标缓存，大幅减少重复绘制开销
        self.setCacheMode(QGraphicsItem.DeviceCoordinateCache)
        self._scale_factor = 1.0
        self._original_pixmap = pixmap
        self._base_size = pixmap.size()
        self._opacity = 1.0
        self._item_id = item_id or str(uuid.uuid4())[:8]
        self.setAcceptHoverEvents(True)
        self.setOpacity(self._opacity)

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

    def set_scale_factor(self, factor):
        factor = max(0.05, min(factor, 5.0))
        if factor == self._scale_factor:
            return
        center = self.sceneBoundingRect().center()
        self._scale_factor = factor
        new_size = self._base_size * factor
        scaled = self._original_pixmap.scaled(
            int(new_size.width()), int(new_size.height()),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.setPixmap(scaled)
        # 缩放后缓存失效，需要重新生成
        self.update()
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
        scaled = self._original_pixmap.scaled(
            int(new_size.width()), int(new_size.height()),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.setPixmap(scaled)
        new_local_x = rel_x * self.pixmap().width()
        new_local_y = rel_y * self.pixmap().height()
        new_scene = self.mapToScene(QPointF(new_local_x, new_local_y))
        delta = scene_pos - new_scene
        self.moveBy(delta.x(), delta.y())

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            if self.isSelected():
                self.setZValue(1000)
            else:
                self.setZValue(self.data(0) if self.data(0) is not None else 0)
            self.update()  # 选中状态变化只重绘自身
        return super().itemChange(change, value)

    def paint(self, painter, option, widget=None):
        # 关闭默认的抗锯齿开销，图片缩放已用平滑变换
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
            "z": self.zValue(),
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
    """自定义画布视图：支持框选、平移、右键菜单等"""

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        # 性能优化：平滑变换保留，抗锯齿在图多时关闭可进一步提速
        self.setRenderHints(QPainter.SmoothPixmapTransform)
        # 最小化视口更新：只重绘变化区域，大幅提升大量图元时的帧率
        self.setViewportUpdateMode(QGraphicsView.MinimalViewportUpdate)
        # 默认拖拽模式：橡皮筋框选（空白处拖选多图）
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(QColor(43, 43, 43)))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # 橡皮筋选择框样式
        self.setRubberBandSelectionMode(Qt.IntersectsItemShape)

        self._panning = False
        self._pan_start = QPointF()
        self._space_pressed = False
        self._main_window = None
        self._min_zoom = 0.05
        self._max_zoom = 10.0
        self._drag_started_on_item = False  # 记录按下时是否点在图元上

    def set_main_window(self, mw):
        self._main_window = mw

    def set_space_pressed(self, pressed):
        self._space_pressed = pressed
        if pressed:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.viewport().setCursor(Qt.OpenHandCursor)
        else:
            if not self._panning:
                # 恢复默认框选模式
                self.setDragMode(QGraphicsView.RubberBandDrag)
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
        # 中键 或 空格+左键：平移
        if event.button() == Qt.MiddleButton or (
            event.button() == Qt.LeftButton and self._space_pressed
        ):
            self._panning = True
            self._pan_start = event.position()
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.viewport().setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        # 右键：弹出菜单
        if event.button() == Qt.RightButton:
            item = self.itemAt(event.position().toPoint())
            if isinstance(item, MovableImageItem):
                if not item.isSelected():
                    # 没按住Ctrl时，点击切换选中为当前这张
                    if not (event.modifiers() & Qt.ControlModifier):
                        self.scene().clearSelection()
                    item.setSelected(True)
            else:
                # 空白处右键不清除选择，方便多选后右键操作
                pass
            self._show_context_menu(event.globalPosition().toPoint(), item)
            event.accept()
            return

        # 左键：判断点在图元上还是空白处
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.position().toPoint())
            self._drag_started_on_item = isinstance(item, MovableImageItem)
            if self._drag_started_on_item:
                # 点在图元上：切换为可移动模式（让QGraphicsView处理item拖动）
                # 注意：RubberBandDrag模式下点中图元也能拖动，Qt内部已处理
                pass
            else:
                # 点在空白处：如果没按Ctrl/Shift，先清空选择
                if not (event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier)):
                    self.scene().clearSelection()
                    if self._main_window:
                        self._main_window.update_status(None)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
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
                self.setDragMode(QGraphicsView.RubberBandDrag)
                self.viewport().setCursor(Qt.ArrowCursor)
            event.accept()
            return

        # 松开左键时：如果有选中的图片，触发自动保存 + 更新状态栏
        if event.button() == Qt.LeftButton:
            selected = self.scene().selectedItems()
            movable_selected = [i for i in selected if isinstance(i, MovableImageItem)]
            if movable_selected:
                if self._main_window:
                    self._main_window.update_status(movable_selected[0])
                    self._main_window.schedule_autosave()
            self._drag_started_on_item = False

        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        # Ctrl + 滚轮：缩放整个视图
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
            self.zoom_view(factor)
            event.accept()
            return

        scene_pos = self.mapToScene(event.position().toPoint())
        selected_items = self.scene().selectedItems()
        movable_selected = [i for i in selected_items if isinstance(i, MovableImageItem)]
        if movable_selected:
            # 有选中图片：缩放所有选中的图片
            factor = 1.1 if event.angleDelta().y() > 0 else 0.9
            for item in movable_selected:
                item.scale_at(factor, scene_pos)
            if self._main_window:
                self._main_window.update_status(movable_selected[0])
                self._main_window.schedule_autosave()
            event.accept()
            return

        # 没有选中：缩放视图
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.zoom_view(factor)
        event.accept()

    def _show_context_menu(self, global_pos, item):
        """丰富右键菜单：选中图片菜单 + 空白处菜单"""
        menu = QMenu(self)
        selected = [i for i in self.scene().selectedItems() if isinstance(i, MovableImageItem)]
        has_selection = len(selected) > 0

        if has_selection:
            # ========== 有选中图片时的菜单 ==========
            count = len(selected)
            title = menu.addAction(f"已选中 {count} 张图片")
            title.setEnabled(False)
            menu.addSeparator()

            delete_act = menu.addAction("删除选中 (Del)")
            menu.addSeparator()

            zoom_in_act = menu.addAction("放大 (+20%)")
            zoom_out_act = menu.addAction("缩小 (-20%)")
            reset_act = menu.addAction("重置为原始大小")
            menu.addSeparator()

            # 透明度子菜单
            opacity_menu = menu.addMenu("透明度")
            opa_100 = opacity_menu.addAction("100% (不透明)")
            opa_75 = opacity_menu.addAction("75%")
            opa_50 = opacity_menu.addAction("50% (半透明)")
            opa_25 = opacity_menu.addAction("25%")
            opa_10 = opacity_menu.addAction("10%")
            menu.addSeparator()

            front_act = menu.addAction("置顶")
            back_act = menu.addAction("置底")
            menu.addSeparator()

            # 比对差异（选中≥2张时可用）
            diff_act = menu.addAction("比对差异并标记")
            diff_act.setEnabled(len(selected) >= 2)
            clear_diff_act = menu.addAction("清除差异标记")
            menu.addSeparator()

            save_hist_act = menu.addAction("保存当前画面到历史")
            menu.addSeparator()

            export_act = menu.addAction("导出大图...")
            menu.addSeparator()

            select_all_act = menu.addAction("全选 (Ctrl+A)")
            deselect_act = menu.addAction("取消全选")
        else:
            # ========== 空白处菜单 ==========
            paste_act = menu.addAction("粘贴图片 (Ctrl+V)")
            import_act = menu.addAction("导入图片...")
            menu.addSeparator()

            view_zoom_in_act = menu.addAction("视图放大")
            view_zoom_out_act = menu.addAction("视图缩小")
            view_reset_act = menu.addAction("视图重置为 100%")
            view_fit_act = menu.addAction("适配全部图片")
            menu.addSeparator()

            select_all_act = menu.addAction("全选 (Ctrl+A)")
            menu.addSeparator()

            clear_diff_act = menu.addAction("清除差异标记")
            menu.addSeparator()

            save_hist_act = menu.addAction("保存到历史记录")
            history_act = menu.addAction("打开历史记录...")
            menu.addSeparator()

            export_act = menu.addAction("导出拼接大图...")
            clear_act = menu.addAction("清空画布")

        action = menu.exec(global_pos)
        if not action:
            return

        # ========== 通用操作 ==========
        if has_selection:
            if action == delete_act:
                if self._main_window:
                    self._main_window.delete_selected()
            elif action == zoom_in_act:
                if self._main_window:
                    self._main_window.scale_selected(1.2)
            elif action == zoom_out_act:
                if self._main_window:
                    self._main_window.scale_selected(0.8)
            elif action == reset_act:
                if self._main_window:
                    self._main_window.reset_scale_selected()
            elif action == opa_100:
                self._set_selected_opacity(1.0)
            elif action == opa_75:
                self._set_selected_opacity(0.75)
            elif action == opa_50:
                self._set_selected_opacity(0.5)
            elif action == opa_25:
                self._set_selected_opacity(0.25)
            elif action == opa_10:
                self._set_selected_opacity(0.1)
            elif action == front_act:
                if self._main_window:
                    self._main_window.bring_to_front()
            elif action == back_act:
                if self._main_window:
                    self._main_window.send_to_back()
            elif action == diff_act:
                if self._main_window:
                    self._main_window.compare_diff()
            elif action == clear_diff_act and self._main_window:
                self._main_window.clear_diff_markers()
            elif action == save_hist_act and self._main_window:
                self._main_window.save_to_history()
            elif action == export_act and self._main_window:
                self._main_window.export_canvas()
            elif action == select_all_act:
                self._select_all_images()
            elif action == deselect_act:
                self.scene().clearSelection()
                if self._main_window:
                    self._main_window.update_status(None)
        else:
            # 空白处菜单
            if action == paste_act and self._main_window:
                self._main_window.paste_from_clipboard()
            elif action == import_act and self._main_window:
                self._main_window.import_images()
            elif action == view_zoom_in_act:
                self.zoom_view(1.2)
            elif action == view_zoom_out_act:
                self.zoom_view(1 / 1.2)
            elif action == view_reset_act:
                self.reset_view_zoom()
            elif action == view_fit_act:
                self.fit_all_items()
            elif action == select_all_act:
                self._select_all_images()
            elif action == clear_diff_act and self._main_window:
                self._main_window.clear_diff_markers()
            elif action == save_hist_act and self._main_window:
                self._main_window.save_to_history()
            elif action == history_act and self._main_window:
                self._main_window.show_history()
            elif action == export_act and self._main_window:
                self._main_window.export_canvas()
            elif action == clear_act and self._main_window:
                self._main_window.clear_canvas()

    def _set_selected_opacity(self, opacity):
        for item in self.scene().selectedItems():
            if isinstance(item, MovableImageItem):
                item.set_opacity_value(opacity)
        if self._main_window:
            self._main_window.schedule_autosave()
            # 同步滑块
            selected = [i for i in self.scene().selectedItems() if isinstance(i, MovableImageItem)]
            if selected:
                self._main_window.update_status(selected[0])

    def _select_all_images(self):
        for item in self.scene().items():
            if isinstance(item, MovableImageItem):
                item.setSelected(True)
        if self._main_window:
            selected = [i for i in self.scene().selectedItems() if isinstance(i, MovableImageItem)]
            if selected:
                self._main_window.update_status(selected[0])

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
        state = {"version": 1, "timestamp": time.time(), "images": []}
        for item in items:
            if not isinstance(item, MovableImageItem):
                continue
            iid = item.item_id()
            img_path = os.path.join(self.images_dir, f"{iid}.png")
            # 只在文件不存在时保存原图，减少IO
            if not os.path.exists(img_path):
                item.original_pixmap().save(img_path, "PNG")
            info = item.to_dict()
            info["image_file"] = f"{iid}.png"
            state["images"].append(info)
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
            scene.addItem(item)
            add_callback(item)
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
        hid = str(uuid.uuid4())[:8]
        ts = time.time()
        title = title or time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))
        state_dir = os.path.join(HISTORY_DIR, hid)
        os.makedirs(state_dir, exist_ok=True)
        state = {"version": 1, "timestamp": ts, "images": []}
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
        thumb_path = os.path.join(state_dir, "thumb.png")
        self._render_thumbnail(movable_items, all_rect, thumb_path)
        entry = {"id": hid, "title": title, "timestamp": ts, "image_count": len(movable_items)}
        self._index.insert(0, entry)
        if len(self._index) > MAX_HISTORY_ITEMS:
            old = self._index[MAX_HISTORY_ITEMS:]
            self._index = self._index[:MAX_HISTORY_ITEMS]
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
        img.fill(QColor(43, 43, 43))
        painter = QPainter(img)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.scale(scale, scale)
        sorted_items = sorted(items, key=lambda x: x.zValue())
        for item in sorted_items:
            rect = item.sceneBoundingRect()
            x = rect.left() - bounds.left() + margin
            y = rect.top() - bounds.top() + margin
            painter.setOpacity(item.opacity_value())
            painter.drawPixmap(QPointF(x, y), item.pixmap())
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
        self.setWindowTitle("图片自由拼接工具 - Image Canvas Stitcher (PySide6)")
        self.resize(1200, 800)
        self._set_app_icon()

        self._autosave_mgr = AutoSaveManager()
        self._history_mgr = HistoryManager()
        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.timeout.connect(self._do_autosave)

        self._diff_markers = []

        # 场景：BSP树索引，大量图元时查找/碰撞检测性能大幅提升
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(-5000, -5000, 10000, 10000)
        self.scene.setItemIndexMethod(QGraphicsScene.BspTreeIndex)

        self.view = ImageCanvasView(self.scene, self)
        self.view.set_main_window(self)
        self.setCentralWidget(self.view)

        self._build_toolbar()
        self._build_statusbar()
        self._z_counter = 0
        self._global_opacity = 1.0

        self._try_restore_autosave()
        # 注意：不再连接 scene.changed，改为鼠标释放时触发，减少高频信号开销

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
        tb = QToolBar("工具栏", self)
        tb.setMovable(False)
        self.addToolBar(tb)

        btn_import = QPushButton("导入图片")
        btn_import.clicked.connect(self.import_images)
        tb.addWidget(btn_import)
        btn_paste = QPushButton("粘贴 (Ctrl+V)")
        btn_paste.clicked.connect(self.paste_from_clipboard)
        tb.addWidget(btn_paste)
        btn_del = QPushButton("删除选中 (Del)")
        btn_del.clicked.connect(self.delete_selected)
        tb.addWidget(btn_del)
        tb.addSeparator()

        btn_zoom_in = QPushButton("图片放大 +")
        btn_zoom_in.clicked.connect(lambda: self.scale_selected(1.2))
        tb.addWidget(btn_zoom_in)
        btn_zoom_out = QPushButton("图片缩小 -")
        btn_zoom_out.clicked.connect(lambda: self.scale_selected(0.8))
        tb.addWidget(btn_zoom_out)
        btn_reset = QPushButton("图片重置")
        btn_reset.clicked.connect(self.reset_scale_selected)
        tb.addWidget(btn_reset)
        tb.addSeparator()

        btn_view_in = QPushButton("视图放大 ➕")
        btn_view_in.clicked.connect(lambda: self.view.zoom_view(1.2))
        tb.addWidget(btn_view_in)
        btn_view_out = QPushButton("视图缩小 ➖")
        btn_view_out.clicked.connect(lambda: self.view.zoom_view(1 / 1.2))
        tb.addWidget(btn_view_out)
        btn_view_reset = QPushButton("视图100%")
        btn_view_reset.clicked.connect(self.view.reset_view_zoom)
        tb.addWidget(btn_view_reset)
        btn_view_fit = QPushButton("适配全部")
        btn_view_fit.clicked.connect(self.view.fit_all_items)
        tb.addWidget(btn_view_fit)
        tb.addSeparator()

        btn_front = QPushButton("置顶")
        btn_front.clicked.connect(self.bring_to_front)
        tb.addWidget(btn_front)
        btn_back = QPushButton("置底")
        btn_back.clicked.connect(self.send_to_back)
        tb.addWidget(btn_back)
        tb.addSeparator()

        tb.addWidget(QLabel(" 单图透明:"))
        self.sld_item_opacity = QSlider(Qt.Horizontal)
        self.sld_item_opacity.setRange(0, 100)
        self.sld_item_opacity.setValue(100)
        self.sld_item_opacity.setFixedWidth(80)
        self.sld_item_opacity.setToolTip("选中图片的透明度")
        self.sld_item_opacity.valueChanged.connect(self._on_item_opacity_slider)
        tb.addWidget(self.sld_item_opacity)
        self.lbl_item_opacity = QLabel("100%")
        self.lbl_item_opacity.setFixedWidth(40)
        self.lbl_item_opacity.setStyleSheet("color: #888;")
        tb.addWidget(self.lbl_item_opacity)
        tb.addSeparator()

        tb.addWidget(QLabel(" 整体透明:"))
        self.sld_global_opacity = QSlider(Qt.Horizontal)
        self.sld_global_opacity.setRange(0, 100)
        self.sld_global_opacity.setValue(100)
        self.sld_global_opacity.setFixedWidth(80)
        self.sld_global_opacity.setToolTip("所有图片整体透明度")
        self.sld_global_opacity.valueChanged.connect(self._on_global_opacity_slider)
        tb.addWidget(self.sld_global_opacity)
        self.lbl_global_opacity = QLabel("100%")
        self.lbl_global_opacity.setFixedWidth(40)
        self.lbl_global_opacity.setStyleSheet("color: #888;")
        tb.addWidget(self.lbl_global_opacity)
        tb.addSeparator()

        btn_diff = QPushButton("比对差异")
        btn_diff.setToolTip("选中两张高度相似的图片，比对并标记差异区域（红色）")
        btn_diff.clicked.connect(self.compare_diff)
        tb.addWidget(btn_diff)
        btn_clear_diff = QPushButton("清除标记")
        btn_clear_diff.setToolTip("清除所有差异红色标记")
        btn_clear_diff.clicked.connect(self.clear_diff_markers)
        tb.addWidget(btn_clear_diff)
        tb.addSeparator()

        btn_save_hist = QPushButton("保存到历史")
        btn_save_hist.clicked.connect(self.save_to_history)
        tb.addWidget(btn_save_hist)
        btn_history = QPushButton("历史记录")
        btn_history.clicked.connect(self.show_history)
        tb.addWidget(btn_history)
        tb.addSeparator()

        btn_export = QPushButton("导出大图")
        btn_export.clicked.connect(self.export_canvas)
        tb.addWidget(btn_export)
        btn_clear = QPushButton("清空画布")
        btn_clear.clicked.connect(self.clear_canvas)
        tb.addWidget(btn_clear)

    def _build_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel(
            "提示：Ctrl+V粘贴 | 拖拽导入 | 左键拖图 | 空白处左键拖=框选多图 | "
            "Ctrl+滚轮缩放视图 | 空格+左键/中键平移 | 右键菜单"
        )
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
            selected_count = len([i for i in self.scene.selectedItems() if isinstance(i, MovableImageItem)])
            extra = f" (共选中{selected_count}张)" if selected_count > 1 else ""
            self.status_label.setText(
                f"已选中 - 位置:({int(pos.x())},{int(pos.y())})  "
                f"缩放:{item.scale_factor():.0%}  "
                f"透明:{item.opacity_value():.0%}  "
                f"原始:{size.width()}x{size.height()}{extra}"
            )
            self.sld_item_opacity.blockSignals(True)
            self.sld_item_opacity.setValue(int(item.opacity_value() * 100))
            self.sld_item_opacity.blockSignals(False)
            self.lbl_item_opacity.setText(f"{int(item.opacity_value() * 100)}%")
        else:
            self.status_label.setText(
                "提示：Ctrl+V粘贴 | 拖拽导入 | 左键拖图 | 空白处左键拖=框选多图 | "
                "Ctrl+滚轮缩放视图 | 空格+左键/中键平移 | 右键菜单"
            )

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
        item.setOpacity(item._opacity * self._global_opacity)
        self.scene.addItem(item)
        self.scene.clearSelection()
        item.setSelected(True)
        self.update_status(item)
        self.schedule_autosave()
        return item

    def _on_item_added(self, item):
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
        selected = [i for i in self.scene.selectedItems() if isinstance(i, MovableImageItem)]
        if selected:
            self.update_status(selected[0])
        self.schedule_autosave()

    def reset_scale_selected(self):
        for item in self.scene.selectedItems():
            if isinstance(item, MovableImageItem):
                item.set_scale_factor(1.0)
        selected = [i for i in self.scene.selectedItems() if isinstance(i, MovableImageItem)]
        if selected:
            self.update_status(selected[0])
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
        selected = [i for i in self.scene.selectedItems() if isinstance(i, MovableImageItem)]
        if len(selected) < 2:
            QMessageBox.information(
                self, "提示",
                "请先选中两张（或多张）高度相似的图片，再点击比对差异。\n"
                "空白处按住左键拖拽可框选，按住 Ctrl 点击可追加选择。"
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
                            if abs(c1.red() - c2.red()) + abs(c1.green() - c2.green()) + abs(c1.blue() - c2.blue()) > threshold:
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
                scene_rect = QRectF(pos.x() + rx * sx, pos.y() + ry * sy, rw * sx, rh * sy)
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
            cx, cy = bx // block_size, by // block_size
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
                        min_x, max_x = min(min_x, cx), max(max_x, cx)
                        min_y, max_y = min(min_y, cy), max(max_y, cy)
                        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nx, ny = cx + dx, cy + dy
                            if 0 <= nx < cols and 0 <= ny < rows and grid[ny][nx] and not visited[ny][nx]:
                                visited[ny][nx] = True
                                stack.append((nx, ny))
                    regions.append((min_x * block_size, min_y * block_size,
                                    (max_x - min_x + 1) * block_size, (max_y - min_y + 1) * block_size))
        return regions

    def clear_diff_markers(self):
        for marker in self._diff_markers:
            self.scene.removeItem(marker)
        self._diff_markers = []

    # ==================== 自动保存 ====================
    def schedule_autosave(self):
        self._autosave_timer.start(AUTOSAVE_DELAY_MS)

    def _do_autosave(self):
        items = [i for i in self.scene.items() if isinstance(i, MovableImageItem)]
        try:
            self._autosave_mgr.save_state(items)
        except Exception:
            pass

    def _try_restore_autosave(self):
        if not self._autosave_mgr.has_autosave():
            return
        count = self._autosave_mgr.load_state(self.scene, self._on_item_added)
        if count > 0:
            self.status_label.setText(f"已自动恢复上次画面，共 {count} 张图片")
            QTimer.singleShot(100, self.view.fit_all_items)

    # ==================== 历史记录 ====================
    def save_to_history(self):
        items = [i for i in self.scene.items() if isinstance(i, MovableImageItem)]
        if not items:
            QMessageBox.information(self, "提示", "画布上没有图片，无法保存到历史记录。")
            return
        self._history_mgr.save_history(items)
        QMessageBox.information(self, "已保存", "当前画面已保存到历史记录。")

    def show_history(self):
        dlg = HistoryDialog(self._history_mgr, self)
        if dlg.exec() == QDialog.Accepted:
            hid = dlg.selected_history_id()
            if hid:
                self._load_history(hid)

    def _load_history(self, hid):
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
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        sorted_items = sorted(items, key=lambda x: x.zValue())
        for item in sorted_items:
            rect = item.sceneBoundingRect()
            x = int(rect.left() - min_x + margin)
            y = int(rect.top() - min_y + margin)
            painter.setOpacity(item.opacity_value() * self._global_opacity)
            painter.drawPixmap(x, y, item.pixmap())
        painter.end()
        save_path, _ = QFileDialog.getSaveFileName(
            self, "导出拼接大图", "stitched_image.png",
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
        QMessageBox.information(self, "成功", f"已导出到:\n{save_path}\n尺寸: {total_w}x{total_h}")

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
        if event.matches(QKeySequence.SelectAll):
            self.view._select_all_images()
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
