import os
import sys
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image

# Import TkinterDnD for drag-and-drop support
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False


def get_resource_path(relative_path: str) -> str:
    """Helper function to get absolute path to resource, works for dev and PyInstaller .exe"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# App Theme Setup
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Target Byte Pattern: FF FE 0D 0A 63 6C 73 0D 0A
TARGET_BYTES = bytes([0xFF, 0xFE, 0x0D, 0x0A, 0x63, 0x6C, 0x73, 0x0D, 0x0A])


class ByteCore:
    """Core logic engine for inspecting and altering header bytes."""

    @staticmethod
    def inspect_file(filepath: str) -> dict:
        """Reads header bytes and checks for the exact target signature."""
        if not os.path.exists(filepath):
            raise FileNotFoundError("Target file does not exist.")

        size = os.path.getsize(filepath)
        with open(filepath, "rb") as f:
            header_data = f.read(16)

        has_header = header_data.startswith(TARGET_BYTES)
        return {
            "size_bytes": size,
            "header_data": header_data,
            "has_header": has_header,
            "hex_formatted": header_data.hex(' ').upper()
        }

    @staticmethod
    def apply_header(filepath: str, output_path: str):
        """Prepends TARGET_BYTES to the file atomically."""
        with open(filepath, "rb") as f:
            original_content = f.read()

        if original_content.startswith(TARGET_BYTES):
            raise ValueError("Header sequence is already present at file start.")

        temp_out = output_path + ".tmp"
        with open(temp_out, "wb") as f:
            f.write(TARGET_BYTES)
            f.write(original_content)

        if os.path.exists(output_path) and output_path == filepath:
            os.replace(temp_out, output_path)
        else:
            os.rename(temp_out, output_path)

    @staticmethod
    def strip_header(filepath: str, output_path: str):
        """Strips TARGET_BYTES from the file start atomically."""
        with open(filepath, "rb") as f:
            original_content = f.read()

        if not original_content.startswith(TARGET_BYTES):
            raise ValueError("File does not start with the target header sequence.")

        stripped_content = original_content[len(TARGET_BYTES):]

        temp_out = output_path + ".tmp"
        with open(temp_out, "wb") as f:
            f.write(stripped_content)

        if os.path.exists(output_path) and output_path == filepath:
            os.replace(temp_out, output_path)
        else:
            os.rename(temp_out, output_path)


# Enable DnD base class if available
BaseClass = TkinterDnD.DnDWrapper if HAS_DND else object


class ByteMasterApp(ctk.CTk, BaseClass):
    def __init__(self):
        if HAS_DND:
            super().__init__()
            try:
                self.TkdndVersion = TkinterDnD._require(self)
            except Exception:
                pass
        else:
            super().__init__()

        # Main Window Configuration
        self.title("Batch Obfuscator & Deobfuscator")
        self.geometry("680x640")
        self.resizable(False, False)

        # Apply Titlebar & Taskbar Icon
        self._apply_custom_icon()

        self.active_filepath = ""
        self.file_info = None

        self._build_ui()

    def _apply_custom_icon(self):
        if sys.platform == "win32":
            import ctypes
            try:
                myappid = "bytemaster.pro.headerinjector.1.0"
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception:
                pass

        icon_path = get_resource_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception as e:
                print(f"Icon load failed: {e}")

    def _build_ui(self):
        # Header / Title Banner Frame
        self.frame_header = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_header.pack(fill="x", padx=25, pady=(20, 10))

        # Optional In-App Logo Image (.png)
        logo_png_path = get_resource_path("logo.png")
        if os.path.exists(logo_png_path):
            try:
                raw_img = Image.open(logo_png_path)
                self.img_logo = ctk.CTkImage(light_image=raw_img, dark_image=raw_img, size=(48, 48))
                self.lbl_logo_icon = ctk.CTkLabel(self.frame_header, image=self.img_logo, text="")
                self.lbl_logo_icon.pack(side="left", padx=(0, 15))
            except Exception as e:
                print(f"Logo load failed: {e}")

        # Title text container
        self.frame_title_text = ctk.CTkFrame(self.frame_header, fg_color="transparent")
        self.frame_title_text.pack(side="left", fill="both", expand=True)

        self.lbl_app_title = ctk.CTkLabel(
            self.frame_title_text, text="Batch Obfuscator & Deobfuscator", font=ctk.CTkFont(size=20, weight="bold")
        )
        self.lbl_app_title.pack(anchor="w")

        self.lbl_target_pattern = ctk.CTkLabel(
            self.frame_title_text,
            text="NOTICE: IF THE FILE STAYS UNREADABLE, ITS NOT MY FAULT. I CANNOT FIX THAT",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color="#8A8A8A"
        )
        self.lbl_target_pattern.pack(anchor="w", pady=(2, 0))

        # Drag & Drop / File Input Zone
        self.frame_dropzone = ctk.CTkFrame(self, corner_radius=12, border_width=2, border_color="#3B3B3B")
        self.frame_dropzone.pack(fill="x", padx=25, pady=10)

        drop_text = "Drag & Drop a .BAT or .CMD file here\n— or click to select —" if HAS_DND else "Click 'Browse File' to select a script"
        self.lbl_drop_prompt = ctk.CTkLabel(
            self.frame_dropzone,
            text=drop_text,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#A0A0A0",
            height=70
        )
        self.lbl_drop_prompt.pack(fill="both", expand=True, padx=20, pady=10)

        if HAS_DND:
            try:
                self.frame_dropzone.drop_target_register(DND_FILES)
                self.frame_dropzone.dnd_bind('<<Drop>>', self._handle_drop)
            except Exception:
                pass
        self.lbl_drop_prompt.bind("<Button-1>", lambda e: self.browse_file())

        # File Selector Controls
        self.frame_file_picker = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_file_picker.pack(fill="x", padx=25, pady=5)

        self.entry_path = ctk.CTkEntry(
            self.frame_file_picker, placeholder_text="No file selected...", font=ctk.CTkFont(size=12), height=35
        )
        self.entry_path.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_browse = ctk.CTkButton(
            self.frame_file_picker, text="Browse File", width=110, height=35, command=self.browse_file
        )
        self.btn_browse.pack(side="right")

        # Inspector Dashboard Panel
        self.frame_inspector = ctk.CTkFrame(self, corner_radius=10, fg_color="#1E1E1E")
        self.frame_inspector.pack(fill="x", padx=25, pady=15)

        self.lbl_inspect_title = ctk.CTkLabel(
            self.frame_inspector, text="FILE SIGNATURE INSPECTOR", font=ctk.CTkFont(size=11, weight="bold"), text_color="#7A7A7A"
        )
        self.lbl_inspect_title.pack(anchor="w", padx=15, pady=(10, 5))

        # Status & Hex View Box
        self.frame_status_grid = ctk.CTkFrame(self.frame_inspector, fg_color="transparent")
        self.frame_status_grid.pack(fill="x", padx=15, pady=(0, 10))

        self.lbl_status_badge = ctk.CTkLabel(
            self.frame_status_grid,
            text="STATUS: NO FILE LOADED",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#888888",
            corner_radius=6,
            fg_color="#2B2B2B",
            padx=10,
            pady=4
        )
        self.lbl_status_badge.pack(anchor="w", side="left")

        self.lbl_hex_preview = ctk.CTkLabel(
            self.frame_inspector,
            text="Header Hex: [ Waiting for input... ]",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color="#4CAF50",
            anchor="w"
        )
        self.lbl_hex_preview.pack(fill="x", padx=15, pady=(0, 12))

        # Output Mode & Controls
        self.switch_overwrite = ctk.CTkSwitch(
            self,
            text="In-place Overwrite (Directly modify original file)",
            font=ctk.CTkFont(size=12)
        )
        self.switch_overwrite.pack(anchor="w", padx=25, pady=10)

        # Action Buttons
        self.frame_actions = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_actions.pack(fill="x", padx=25, pady=15)

        self.btn_add = ctk.CTkButton(
            self.frame_actions,
            text="Inject Header Bytes",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=45,
            fg_color="#2B8A3E",
            hover_color="#1C6B2D",
            state="disabled",
            command=self.execute_add
        )
        self.btn_add.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_strip = ctk.CTkButton(
            self.frame_actions,
            text="Strip Header Bytes",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=45,
            fg_color="#C92A2A",
            hover_color="#9E1B1B",
            state="disabled",
            command=self.execute_strip
        )
        self.btn_strip.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # Bottom Status Bar
        self.lbl_footer_status = ctk.CTkLabel(
            self, text="Ready.", font=ctk.CTkFont(size=12), text_color="#8A8A8A"
        )
        self.lbl_footer_status.pack(pady=5)

    def _handle_drop(self, event):
        filepath = event.data.strip('{}')
        self.load_file(filepath)

    def browse_file(self):
        filepath = filedialog.askopenfilename(
            title="Select Script File",
            filetypes=[("Batch Scripts", "*.bat *.cmd"), ("All Files", "*.*")]
        )
        if filepath:
            self.load_file(filepath)

    def load_file(self, filepath: str):
        if not os.path.isfile(filepath):
            messagebox.showerror("Invalid File", "Selected path is not a valid file.")
            return

        self.active_filepath = filepath
        self.entry_path.delete(0, "end")
        self.entry_path.insert(0, filepath)

        try:
            self.file_info = ByteCore.inspect_file(filepath)
            has_header = self.file_info["has_header"]

            hex_text = self.file_info["hex_formatted"]
            self.lbl_hex_preview.configure(text=f"First 16 Bytes:  {hex_text}")

            if has_header:
                self.lbl_status_badge.configure(
                    text="MATCH DETECTED: Header Present", fg_color="#1E4620", text_color="#4EFA57"
                )
                self.btn_add.configure(state="disabled")
                self.btn_strip.configure(state="normal")
                self.lbl_footer_status.configure(text="Ready to strip target header bytes.", text_color="#4EFA57")
            else:
                self.lbl_status_badge.configure(
                    text="NO MATCH: Header Missing", fg_color="#4A3B10", text_color="#FFC107"
                )
                self.btn_add.configure(state="normal")
                self.btn_strip.configure(state="disabled")
                self.lbl_footer_status.configure(text="Ready to inject target header bytes.", text_color="#FFC107")

        except Exception as e:
            messagebox.showerror("Read Error", f"Failed to analyze file:\n{str(e)}")

    def _get_target_path(self, action_name: str) -> str:
        if self.switch_overwrite.get():
            return self.active_filepath

        prefix = "injected_" if action_name == "inject" else "stripped_"
        base_dir, base_name = os.path.split(self.active_filepath)
        default_name = prefix + base_name

        save_path = filedialog.asksaveasfilename(
            title="Save Output File As",
            initialdir=base_dir,
            initialfile=default_name,
            filetypes=[("Batch File", "*.bat"), ("CMD Script", "*.cmd"), ("All Files", "*.*")]
        )
        return save_path

    def execute_add(self):
        out_path = self._get_target_path("inject")
        if not out_path:
            return

        try:
            ByteCore.apply_header(self.active_filepath, out_path)
            messagebox.showinfo("Success", f"Header successfully injected!\nFile: {out_path}")
            self.load_file(out_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to inject header:\n{str(e)}")

    def execute_strip(self):
        out_path = self._get_target_path("strip")
        if not out_path:
            return

        try:
            ByteCore.strip_header(self.active_filepath, out_path)
            messagebox.showinfo("Success", f"Header successfully stripped!\nFile: {out_path}")
            self.load_file(out_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to strip header:\n{str(e)}")


if __name__ == "__main__":
    app = ByteMasterApp()
    app.mainloop()