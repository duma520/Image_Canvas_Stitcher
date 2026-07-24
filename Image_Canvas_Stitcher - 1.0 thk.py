# -*- coding: utf-8 -*-
"""
图片自由拼接工具 - Image Canvas Stitcher
功能：
- 从剪贴板粘贴图片 (Ctrl+V)
- 拖拽文件导入图片（需安装 tkinterdnd2）
- 鼠标拖动自由摆放图片位置
- 滚轮缩放选中的图片
- 大画布可平移（按住空格+鼠标拖动 / 中键拖动）
- 右键菜单：删除、置顶、置底、缩放重置
- 导出拼接后的完整大图
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageGrab
import os
import io
import sys

# 可选：拖放文件支持
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

# 可选：win32剪贴板（Windows下增强粘贴）
try:
    import win32clipboard
    WIN32_CLIPBOARD = True
except ImportError:
    WIN32_CLIPBOARD = False


class ImageItem:
    """画布上的单张图片对象"""
    def __init__(self, canvas, pil_image, x=0, y=0):
        self.canvas = canvas
        self.original_image = pil_image.convert("RGBA")
        self.scale = 1.0
        self.x = x
        self.y = y
        self.image_id = None
        self._tk_image = None
        self.selected = False
        self._update_display()

    def _update_display(self):
        """根据当前缩放比例更新显示"""
        w = max(1, int(self.original_image.width * self.scale))
        h = max(1, int(self.original_image.height * self.scale))
        resized = self.original_image.resize((w, h), Image.LANCZOS)
        self._tk_image = ImageTk.PhotoImage(resized)

        if self.image_id is not None:
            self.canvas.delete(self.image_id)
        self.image_id = self.canvas.create_image(
            self.x, self.y, image=self._tk_image, anchor="nw", tags=("image",)
        )
        self._update_selection_border()

    def _update_selection_border(self):
        """更新选中边框"""
        border_tag = f"border_{self.image_id}"
        self.canvas.delete(border_tag)
        if self.selected:
            bbox = self.canvas.bbox(self.image_id)
            if bbox:
                self.canvas.create_rectangle(
                    bbox, outline="#0078D4", width=2, tags=("border", border_tag)
                )

    def move_to(self, x, y):
        dx = x - self.x
        dy = y - self.y
        self.x = x
        self.y = y
        self.canvas.move(self.image_id, dx, dy)
        self._update_selection_border()

    def set_scale(self, scale):
        scale = max(0.05, min(scale, 5.0))
        cx = self.x + self.original_image.width * self.scale / 2
        cy = self.y + self.original_image.height * self.scale / 2
        self.scale = scale
        new_w = self.original_image.width * self.scale
        new_h = self.original_image.height * self.scale
        self.x = cx - new_w / 2
        self.y = cy - new_h / 2
        self._update_display()

    def scale_by(self, factor, anchor_x=None, anchor_y=None):
        if anchor_x is not None and anchor_y is not None:
            rel_x = (anchor_x - self.x) / (self.original_image.width * self.scale)
            rel_y = (anchor_y - self.y) / (self.original_image.height * self.scale)
            new_scale = max(0.05, min(self.scale * factor, 5.0))
            new_w = self.original_image.width * new_scale
            new_h = self.original_image.height * new_scale
            self.x = anchor_x - rel_x * new_w
            self.y = anchor_y - rel_y * new_h
            self.scale = new_scale
        else:
            new_scale = max(0.05, min(self.scale * factor, 5.0))
            cx = self.x + self.original_image.width * self.scale / 2
            cy = self.y + self.original_image.height * self.scale / 2
            self.scale = new_scale
            new_w = self.original_image.width * self.scale
            new_h = self.original_image.height * self.scale
            self.x = cx - new_w / 2
            self.y = cy - new_h / 2
        self._update_display()

    def set_selected(self, selected):
        self.selected = selected
        self._update_selection_border()

    def contains_point(self, x, y):
        w = self.original_image.width * self.scale
        h = self.original_image.height * self.scale
        return self.x <= x <= self.x + w and self.y <= y <= self.y + h

    def destroy(self):
        if self.image_id is not None:
            self.canvas.delete(self.image_id)
            self.canvas.delete(f"border_{self.image_id}")


class ImageCanvasStitcher:
    def __init__(self, root):
        self.root = root
        self.root.title("图片自由拼接工具 - Image Canvas Stitcher")
        self.root.geometry("1200x800")

        self.images = []
        self.selected_image = None
        self._panning = False
        self._pan_start = (0, 0)
        self._space_pressed = False
        self._dragging = False
        self._drag_start = (0, 0)

        self._build_ui()
        self._bind_events()

        # 超大虚拟画布
        self.canvas.configure(scrollregion=(-5000, -5000, 5000, 5000))
        self.canvas.xview_moveto(0.5)
        self.canvas.yview_moveto(0.5)

    def _build_ui(self):
        toolbar = ttk.Frame(self.root, padding=5)
        toolbar.pack(side="top", fill="x")

        ttk.Button(toolbar, text="导入图片", command=self.import_images).pack(side="left", padx=2)
        ttk.Button(toolbar, text="粘贴图片 (Ctrl+V)", command=self.paste_from_clipboard).pack(side="left", padx=2)
        ttk.Button(toolbar, text="删除选中 (Del)", command=self.delete_selected).pack(side="left", padx=2)
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=5)
        ttk.Button(toolbar, text="放大 +", command=lambda: self.scale_selected(1.2)).pack(side="left", padx=2)
        ttk.Button(toolbar, text="缩小 -", command=lambda: self.scale_selected(0.8)).pack(side="left", padx=2)
        ttk.Button(toolbar, text="重置大小", command=self.reset_scale_selected).pack(side="left", padx=2)
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=5)
        ttk.Button(toolbar, text="置顶", command=self.bring_to_front).pack(side="left", padx=2)
        ttk.Button(toolbar, text="置底", command=self.send_to_back).pack(side="left", padx=2)
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=5)
        ttk.Button(toolbar, text="导出大图", command=self.export_canvas).pack(side="left", padx=2)
        ttk.Button(toolbar, text="清空画布", command=self.clear_canvas).pack(side="left", padx=2)

        hint = "提示：Ctrl+V粘贴 | 左键拖动图片 | 滚轮缩放选中 | 空格+左键/中键平移画布 | 右键菜单"
        if DND_AVAILABLE:
            hint = "提示：Ctrl+V粘贴 | 拖拽文件导入 | 左键拖动图片 | 滚轮缩放选中 | 空格+左键平移 | 右键菜单"
        self.status_var = tk.StringVar(value=hint)
        status_bar = ttk.Label(self.root, textvariable=self.status_var, anchor="w", padding=5)
        status_bar.pack(side="bottom", fill="x")

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True)

        h_scroll = ttk.Scrollbar(main_frame, orient="horizontal")
        v_scroll = ttk.Scrollbar(main_frame, orient="vertical")

        self.canvas = tk.Canvas(
            main_frame, bg="#2B2B2B",
            xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set,
            highlightthickness=0,
        )
        h_scroll.config(command=self.canvas.xview)
        v_scroll.config(command=self.canvas.yview)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # 右键菜单
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="删除", command=self.delete_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="放大", command=lambda: self.scale_selected(1.2))
        self.context_menu.add_command(label="缩小", command=lambda: self.scale_selected(0.8))
        self.context_menu.add_command(label="重置大小", command=self.reset_scale_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="置顶", command=self.bring_to_front)
        self.context_menu.add_command(label="置底", command=self.send_to_back)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="粘贴图片", command=self.paste_from_clipboard)

    def _bind_events(self):
        self.canvas.bind("<ButtonPress-1>", self._on_left_press)
        self.canvas.bind("<B1-Motion>", self._on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_left_release)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", lambda e: self._on_mousewheel_linux(e, 1))
        self.canvas.bind("<Button-5>", lambda e: self._on_mousewheel_linux(e, -1))
        self.canvas.bind("<ButtonPress-2>", self._on_middle_press)
        self.canvas.bind("<B2-Motion>", self._on_middle_drag)
        self.canvas.bind("<ButtonRelease-2>", self._on_middle_release)
        self.canvas.bind("<Button-3>", self._on_right_click)

        self.root.bind("<Control-v>", lambda e: self.paste_from_clipboard())
        self.root.bind("<Control-V>", lambda e: self.paste_from_clipboard())
        self.root.bind("<Delete>", lambda e: self.delete_selected())
        self.root.bind("<KeyPress-space>", self._on_space_press)
        self.root.bind("<KeyRelease-space>", self._on_space_release)

        # 拖放文件
        if DND_AVAILABLE:
            self.canvas.drop_target_register(DND_FILES)
            self.canvas.dnd_bind("<<Drop>>", self._on_drop_files)

    def _canvas_coords(self, event_x, event_y):
        return self.canvas.canvasx(event_x), self.canvas.canvasy(event_y)

    def _find_image_at(self, x, y):
        for img in reversed(self.images):
            if img.contains_point(x, y):
                return img
        return None

    def _on_left_press(self, event):
        x, y = self._canvas_coords(event.x, event.y)
        if self._space_pressed:
            self._panning = True
            self._pan_start = (event.x, event.y)
            return
        img = self._find_image_at(x, y)
        if img:
            self._select_image(img)
            self._dragging = True
            self._drag_start = (x - img.x, y - img.y)
            self._bring_to_front(img)
        else:
            self._select_image(None)

    def _on_left_drag(self, event):
        if self._panning:
            dx = self._pan_start[0] - event.x
            dy = self._pan_start[1] - event.y
            self.canvas.xview_scroll(int(dx), "units")
            self.canvas.yview_scroll(int(dy), "units")
            self._pan_start = (event.x, event.y)
        elif self._dragging and self.selected_image:
            x, y = self._canvas_coords(event.x, event.y)
            self.selected_image.move_to(x - self._drag_start[0], y - self._drag_start[1])

    def _on_left_release(self, event):
        self._panning = False
        self._dragging = False

    def _on_middle_press(self, event):
        self._panning = True
        self._pan_start = (event.x, event.y)

    def _on_middle_drag(self, event):
        if self._panning:
            dx = self._pan_start[0] - event.x
            dy = self._pan_start[1] - event.y
            self.canvas.xview_scroll(int(dx), "units")
            self.canvas.yview_scroll(int(dy), "units")
            self._pan_start = (event.x, event.y)

    def _on_middle_release(self, event):
        self._panning = False

    def _on_mousewheel(self, event):
        x, y = self._canvas_coords(event.x, event.y)
        if self.selected_image:
            factor = 1.1 if event.delta > 0 else 0.9
            self.selected_image.scale_by(factor, x, y)
        else:
            self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def _on_mousewheel_linux(self, event, direction):
        x, y = self._canvas_coords(event.x, event.y)
        if self.selected_image:
            factor = 1.1 if direction > 0 else 0.9
            self.selected_image.scale_by(factor, x, y)

    def _on_right_click(self, event):
        x, y = self._canvas_coords(event.x, event.y)
        img = self._find_image_at(x, y)
        if img:
            self._select_image(img)
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def _on_space_press(self, event):
        self._space_pressed = True
        self.root.config(cursor="fleur")

    def _on_space_release(self, event):
        self._space_pressed = False
        self.root.config(cursor="")

    def _select_image(self, img):
        if self.selected_image == img:
            return
        if self.selected_image:
            self.selected_image.set_selected(False)
        self.selected_image = img
        if img:
            self.status_var.set(
                f"已选中 - 位置:({int(img.x)},{int(img.y)})  缩放:{img.scale:.0%}  原始:{img.original_image.size}"
            )
        else:
            hint = "提示：Ctrl+V粘贴 | 左键拖动图片 | 滚轮缩放选中 | 空格+左键/中键平移画布 | 右键菜单"
            if DND_AVAILABLE:
                hint = "提示：Ctrl+V粘贴 | 拖拽文件导入 | 左键拖动图片 | 滚轮缩放选中 | 空格+左键平移 | 右键菜单"
            self.status_var.set(hint)

    def _bring_to_front(self, img):
        if img in self.images:
            self.images.remove(img)
            self.images.append(img)
            self.canvas.tag_raise(img.image_id)
            self.canvas.tag_raise(f"border_{img.image_id}")

    def _send_to_back(self, img):
        if img in self.images:
            self.images.remove(img)
            self.images.insert(0, img)
            self.canvas.tag_lower(img.image_id)
            self.canvas.tag_lower(f"border_{img.image_id}")

    def add_image(self, pil_image, x=None, y=None):
        if x is None or y is None:
            x = self.canvas.canvasx(self.canvas.winfo_width() / 2) - pil_image.width / 2
            y = self.canvas.canvasy(self.canvas.winfo_height() / 2) - pil_image.height / 2
            offset = len(self.images) * 20
            x += offset
            y += offset
        img_item = ImageItem(self.canvas, pil_image, x, y)
        self.images.append(img_item)
        self._select_image(img_item)
        return img_item

    def import_images(self):
        filepaths = filedialog.askopenfilenames(
            title="选择图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff"), ("所有文件", "*.*")]
        )
        for fp in filepaths:
            try:
                img = Image.open(fp)
                self.add_image(img)
            except Exception as e:
                messagebox.showerror("错误", f"无法打开图片 {fp}:\n{e}")

    def paste_from_clipboard(self):
        try:
            # 方案1: PIL ImageGrab
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                self.add_image(img)
                return

            # 方案2: win32clipboard 读取 DIB
            if WIN32_CLIPBOARD:
                try:
                    win32clipboard.OpenClipboard()
                    try:
                        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
                            data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
                            img = Image.open(io.BytesIO(data))
                            self.add_image(img)
                            return
                    finally:
                        win32clipboard.CloseClipboard()
                except Exception:
                    pass

            messagebox.showinfo("提示", "剪贴板中没有图片，请先截图或复制图片后再粘贴。")
        except Exception as e:
            messagebox.showerror("错误", f"粘贴失败:\n{e}")

    def _on_drop_files(self, event):
        data = event.data
        files = []
        if data.startswith("{") and data.endswith("}"):
            data = data[1:-1]
            files = data.split("} {")
        else:
            files = [data]
        for fp in files:
            fp = fp.strip()
            if os.path.isfile(fp):
                try:
                    img = Image.open(fp)
                    x, y = self._canvas_coords(event.x, event.y)
                    self.add_image(img, x, y)
                except Exception as e:
                    messagebox.showerror("错误", f"无法打开图片 {fp}:\n{e}")

    def delete_selected(self):
        if self.selected_image:
            self.selected_image.destroy()
            self.images.remove(self.selected_image)
            self.selected_image = None
            self.status_var.set("已删除选中图片")

    def scale_selected(self, factor):
        if self.selected_image:
            self.selected_image.scale_by(factor)

    def reset_scale_selected(self):
        if self.selected_image:
            self.selected_image.set_scale(1.0)

    def bring_to_front(self):
        if self.selected_image:
            self._bring_to_front(self.selected_image)

    def send_to_back(self):
        if self.selected_image:
            self._send_to_back(self.selected_image)

    def clear_canvas(self):
        if not self.images:
            return
        if not messagebox.askyesno("确认", "确定要清空所有图片吗？"):
            return
        for img in self.images:
            img.destroy()
        self.images.clear()
        self.selected_image = None

    def export_canvas(self):
        if not self.images:
            messagebox.showinfo("提示", "画布上没有图片可导出。")
            return

        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")
        for img in self.images:
            w = img.original_image.width * img.scale
            h = img.original_image.height * img.scale
            min_x = min(min_x, img.x)
            min_y = min(min_y, img.y)
            max_x = max(max_x, img.x + w)
            max_y = max(max_y, img.y + h)

        margin = 20
        total_w = int(max_x - min_x + margin * 2)
        total_h = int(max_y - min_y + margin * 2)

        if total_w > 20000 or total_h > 20000:
            if not messagebox.askyesno("警告", f"导出尺寸较大 ({total_w}x{total_h})，确定继续吗？"):
                return

        result = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
        for img in self.images:
            w = int(img.original_image.width * img.scale)
            h = int(img.original_image.height * img.scale)
            resized = img.original_image.resize((w, h), Image.LANCZOS)
            px = int(img.x - min_x + margin)
            py = int(img.y - min_y + margin)
            result.paste(resized, (px, py), resized)

        save_path = filedialog.asksaveasfilename(
            title="导出拼接大图",
            defaultextension=".png",
            initialfile="stitched_image.png",
            filetypes=[("PNG 图片 (支持透明)", "*.png"), ("JPEG 图片", "*.jpg"), ("BMP 图片", "*.bmp")]
        )
        if not save_path:
            return
        try:
            ext = os.path.splitext(save_path)[1].lower()
            if ext in (".jpg", ".jpeg"):
                bg = Image.new("RGB", result.size, (255, 255, 255))
                bg.paste(result, mask=result.split()[3])
                bg.save(save_path, quality=95)
            else:
                result.save(save_path)
            messagebox.showinfo("成功", f"已导出到:\n{save_path}\n尺寸: {total_w}x{total_h}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败:\n{e}")


def main():
    # 高DPI支持
    if sys.platform.startswith("win"):
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    app = ImageCanvasStitcher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
