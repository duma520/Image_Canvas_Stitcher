# -*- coding: utf-8 -*-
"""
图片自由拼接工具 - Image Canvas Stitcher (PySide6 版本)
功能：
- 从剪贴板粘贴图片 (Ctrl+V)
- 拖拽文件导入图片
- 鼠标拖动自由摆放图片位置
- 滚轮缩放选中的图片（选中时）或缩放整个视图（未选中时 / Ctrl+滚轮）
- 大画布可平移（按住空格+鼠标拖动 / 中键拖动）
- 右键菜单：删除、置顶、置底、缩放重置
- 导出拼接后的完整大图
- 视图整体缩放，方便看全貌和细节
"""
import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsItem, QToolBar, QPushButton,
    QLabel, QStatusBar, QMenu, QFileDialog, QMessageBox, QWidget,
    QHBoxLayout
)
from PySide6.QtGui import (
    QPixmap, QImage, QClipboard, QPainter, QAction, QCursor,
    QPen, QColor, QBrush, QIcon
)
from PySide6.QtCore import Qt, QPointF, QRectF, QSizeF
from PySide6.QtGui import QKeySequence


class MovableImageItem(QGraphicsPixmapItem):
    """可移动、可缩放的图片图元"""

    def __init__(self, pixmap, parent=None):
        super().__init__(pixmap, parent)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self._scale_factor = 1.0
        self._original_pixmap = pixmap
        self._base_size = pixmap.size()
        self.setAcceptHoverEvents(True)

    def original_size(self):
        return self._base_size

    def scale_factor(self):
        return self._scale_factor

    def set_scale_factor(self, factor):
        """设置缩放比例（以中心为锚点）"""
        factor = max(0.05, min(factor, 5.0))
        if factor == self._scale_factor:
            return
        # 记录当前中心
        center = self.sceneBoundingRect().center()
        self._scale_factor = factor
        # 重新缩放 pixmap
        new_size = self._base_size * factor
        scaled = self._original_pixmap.scaled(
            int(new_size.width()), int(new_size.height()),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.setPixmap(scaled)
        # 保持中心位置不变
        new_center = self.sceneBoundingRect().center()
        offset = center - new_center
        self.moveBy(offset.x(), offset.y())

    def scale_at(self, factor, scene_pos):
        """以指定场景坐标为锚点缩放"""
        factor = max(0.05, min(self._scale_factor * factor, 5.0)) / self._scale_factor
        if factor == 1.0:
            return
        # 计算锚点在图元本地的相对位置
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

        # 调整位置使锚点不动
        new_local_x = rel_x * self.pixmap().width()
        new_local_y = rel_y * self.pixmap().height()
        new_scene = self.mapToScene(QPointF(new_local_x, new_local_y))
        delta = scene_pos - new_scene
        self.moveBy(delta.x(), delta.y())

    def itemChange(self, change, value):
        """选中时更新边框"""
        if change == QGraphicsItem.ItemSelectedHasChanged:
            if self.isSelected():
                self.setZValue(1000)  # 选中时临时置顶显示
            else:
                self.setZValue(self.data(0) if self.data(0) is not None else 0)
        return super().itemChange(change, value)

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        # 选中边框
        if self.isSelected():
            painter.setPen(QPen(QColor(0, 120, 212), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.boundingRect())


class ImageCanvasView(QGraphicsView):
    """自定义画布视图，处理各种交互"""

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(QColor(43, 43, 43)))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self._panning = False
        self._pan_start = QPointF()
        self._space_pressed = False
        self._main_window = None  # 主窗口引用
        self._min_zoom = 0.05   # 视图最小缩放 5%
        self._max_zoom = 10.0   # 视图最大缩放 1000%

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
        """获取当前视图缩放比例"""
        return self.transform().m11()

    def zoom_view(self, factor):
        """缩放视图，限制范围"""
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
        """重置视图缩放为 100%"""
        self.resetTransform()
        if self._main_window:
            self._main_window.update_view_zoom_status()

    def fit_all_items(self):
        """适配所有内容到视图"""
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
        # 中键或空格+左键：平移
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
        if self._panning:
            # 手动平移
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
        # Ctrl + 滚轮：缩放整个视图
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
            self.zoom_view(factor)
            event.accept()
            return

        # 有选中图片时缩放单张图片
        scene_pos = self.mapToScene(event.position().toPoint())
        selected_items = self.scene().selectedItems()
        for item in selected_items:
            if isinstance(item, MovableImageItem):
                factor = 1.1 if event.angleDelta().y() > 0 else 0.9
                item.scale_at(factor, scene_pos)
                if self._main_window:
                    self._main_window.update_status(item)
                event.accept()
                return

        # 没有选中图片时缩放整个视图
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
            front_act = menu.addAction("置顶")
            back_act = menu.addAction("置底")
            menu.addSeparator()
        else:
            # 空白处右键：视图缩放选项
            view_zoom_in_act = menu.addAction("视图放大")
            view_zoom_out_act = menu.addAction("视图缩小")
            view_reset_act = menu.addAction("视图重置 (100%)")
            view_fit_act = menu.addAction("适配全部")
            menu.addSeparator()
        paste_act = menu.addAction("粘贴图片")

        action = menu.exec(global_pos)
        if not action:
            return

        if item:
            if action == delete_act:
                self.scene().removeItem(item)
                if self._main_window:
                    self._main_window.update_status(None)
            elif action == zoom_in_act:
                item.set_scale_factor(item.scale_factor() * 1.2)
                if self._main_window:
                    self._main_window.update_status(item)
            elif action == zoom_out_act:
                item.set_scale_factor(item.scale_factor() * 0.8)
                if self._main_window:
                    self._main_window.update_status(item)
            elif action == reset_act:
                item.set_scale_factor(1.0)
                if self._main_window:
                    self._main_window.update_status(item)
            elif action == front_act:
                max_z = 0
                for it in self.scene().items():
                    if isinstance(it, MovableImageItem) and it != item:
                        max_z = max(max_z, it.zValue())
                item.setZValue(max_z + 1)
                item.setData(0, max_z + 1)
            elif action == back_act:
                min_z = 0
                for it in self.scene().items():
                    if isinstance(it, MovableImageItem) and it != item:
                        min_z = min(min_z, it.zValue())
                item.setZValue(min_z - 1)
                item.setData(0, min_z - 1)
        else:
            # 空白处菜单
            if action == view_zoom_in_act:
                self.zoom_view(1.2)
            elif action == view_zoom_out_act:
                self.zoom_view(1 / 1.2)
            elif action == view_reset_act:
                self.reset_view_zoom()
            elif action == view_fit_act:
                self.fit_all_items()

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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图片自由拼接工具 - Image Canvas Stitcher (PySide6)")
        self.resize(1200, 800)

        # 设置窗口图标
        self._set_app_icon()

        # 场景和视图
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(-5000, -5000, 10000, 10000)  # 超大画布
        self.view = ImageCanvasView(self.scene, self)
        self.view.set_main_window(self)
        self.setCentralWidget(self.view)

        self._build_toolbar()
        self._build_statusbar()

        # 计数 z 值
        self._z_counter = 0

    def _set_app_icon(self):
        """设置应用程序和窗口图标"""
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

        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        app_icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

        # 导入
        btn_import = QPushButton("导入图片")
        if not app_icon.isNull():
            btn_import.setIcon(app_icon)
        btn_import.clicked.connect(self.import_images)
        tb.addWidget(btn_import)

        # 粘贴
        btn_paste = QPushButton("粘贴 (Ctrl+V)")
        if not app_icon.isNull():
            btn_paste.setIcon(app_icon)
        btn_paste.clicked.connect(self.paste_from_clipboard)
        tb.addWidget(btn_paste)

        # 删除
        btn_del = QPushButton("删除选中 (Del)")
        if not app_icon.isNull():
            btn_del.setIcon(app_icon)
        btn_del.clicked.connect(self.delete_selected)
        tb.addWidget(btn_del)

        tb.addSeparator()

        # 图片缩放
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

        # 视图缩放（新增）
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

        # 图层
        btn_front = QPushButton("置顶")
        btn_front.clicked.connect(self.bring_to_front)
        tb.addWidget(btn_front)

        btn_back = QPushButton("置底")
        btn_back.clicked.connect(self.send_to_back)
        tb.addWidget(btn_back)

        tb.addSeparator()

        # 导出
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
            "提示：Ctrl+V粘贴 | 拖拽文件导入 | 左键拖动图片 | "
            "Ctrl+滚轮缩放视图 | 选中后滚轮缩放图片 | "
            "空格+左键/中键平移 | 右键菜单"
        )
        self.status_bar.addWidget(self.status_label, 1)

        # 右侧显示视图缩放比例
        self.view_zoom_label = QLabel("视图: 100%")
        self.view_zoom_label.setStyleSheet("padding: 0 10px; color: #888;")
        self.status_bar.addPermanentWidget(self.view_zoom_label)

    def update_view_zoom_status(self):
        """更新状态栏的视图缩放显示"""
        zoom = self.view.view_scale()
        self.view_zoom_label.setText(f"视图: {zoom:.0%}")

    def update_status(self, item):
        if isinstance(item, MovableImageItem):
            pos = item.pos()
            size = item.original_size()
            self.status_label.setText(
                f"已选中 - 位置:({int(pos.x())},{int(pos.y())})  "
                f"缩放:{item.scale_factor():.0%}  "
                f"原始:{size.width()}x{size.height()}"
            )
        else:
            self.status_label.setText(
                "提示：Ctrl+V粘贴 | 拖拽文件导入 | 左键拖动图片 | "
                "Ctrl+滚轮缩放视图 | 选中后滚轮缩放图片 | "
                "空格+左键/中键平移 | 右键菜单"
            )

    def load_image(self, filepath, x=None, y=None):
        """加载图片到画布"""
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
            # 放到视图中心
            center = self.view.mapToScene(self.view.viewport().rect().center())
            item.setPos(
                center.x() - pixmap.width() / 2 + len(self.scene.items()) * 10,
                center.y() - pixmap.height() / 2 + len(self.scene.items()) * 10
            )

        self.scene.addItem(item)
        self.scene.clearSelection()
        item.setSelected(True)
        self.update_status(item)
        return item

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

    def scale_selected(self, factor):
        for item in self.scene.selectedItems():
            if isinstance(item, MovableImageItem):
                item.set_scale_factor(item.scale_factor() * factor)
                self.update_status(item)

    def reset_scale_selected(self):
        for item in self.scene.selectedItems():
            if isinstance(item, MovableImageItem):
                item.set_scale_factor(1.0)
                self.update_status(item)

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
            self.update_status(None)

    def export_canvas(self):
        items = [i for i in self.scene.items() if isinstance(i, MovableImageItem)]
        if not items:
            QMessageBox.information(self, "提示", "画布上没有图片可导出。")
            return

        # 计算所有图片的边界
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

        # 创建结果图像
        result = QImage(total_w, total_h, QImage.Format_ARGB32)
        result.fill(Qt.transparent)

        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # 按 z 值从小到大绘制
        sorted_items = sorted(items, key=lambda x: x.zValue())
        for item in sorted_items:
            rect = item.sceneBoundingRect()
            x = int(rect.left() - min_x + margin)
            y = int(rect.top() - min_y + margin)
            painter.drawPixmap(x, y, item.pixmap())

        painter.end()

        # 保存
        save_path, _ = QFileDialog.getSaveFileName(
            self, "导出拼接大图", "stitched_image.png",
            "PNG 图片 (支持透明) (*.png);;JPEG 图片 (*.jpg);;BMP 图片 (*.bmp)"
        )
        if not save_path:
            return

        ext = os.path.splitext(save_path)[1].lower()
        if ext in (".jpg", ".jpeg"):
            # JPG 转白底
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
        # Ctrl + 数字0 重置视图
        if event.key() == Qt.Key_0 and event.modifiers() & Qt.ControlModifier:
            self.view.reset_view_zoom()
            event.accept()
            return
        # Ctrl + 加号 / 减号 缩放视图
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


def main():
    # 高DPI支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    # 初始视图居中
    window.view.centerOn(0, 0)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
