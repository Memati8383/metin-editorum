import tkinter as tk
from tkinter import filedialog, messagebox, font, colorchooser, ttk
import os, re, json, shutil, time, threading, logging, traceback, psutil
from datetime import datetime

class PerformanceMonitor:
    def __init__(self, editor):
        self.editor = editor
        self.process = psutil.Process()
        self.metrics = {
            "memory_usage": [],
            "cpu_usage": [],
            "response_times": [],
            "errors": [],
            "usage_stats": {
                "files_opened": 0,
                "files_saved": 0,
                "search_count": 0,
                "replace_count": 0,
                "syntax_highlighting_time": 0
            }
        }
        self.start_time = time.time()
        self.monitoring = False
        self.monitor_thread = None
        
        # Logging ayarları
        logging.basicConfig(
            filename='editor_performance.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
    def start_monitoring(self):
        """Performans izlemeyi başlatır"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_performance)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
    def stop_monitoring(self):
        """Performans izlemeyi durdurur"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
            
    def _monitor_performance(self):
        """Performans metriklerini izler"""
        while self.monitoring:
            try:
                # Bellek kullanımı
                memory_info = self.process.memory_info()
                memory_usage = memory_info.rss / 1024 / 1024  # MB cinsinden
                self.metrics["memory_usage"].append({
                    "timestamp": time.time(),
                    "value": memory_usage
                })
                
                # CPU kullanımı
                cpu_percent = self.process.cpu_percent(interval=1)
                self.metrics["cpu_usage"].append({
                    "timestamp": time.time(),
                    "value": cpu_percent
                })
                
                # Metrikleri kaydet
                self._save_metrics()
                
                # 5 saniye bekle
                time.sleep(5)
                
            except Exception as e:
                self._log_error("Performans izleme hatası", e)
                
    def record_response_time(self, operation, duration):
        """Yanıt süresini kaydeder"""
        self.metrics["response_times"].append({
            "timestamp": time.time(),
            "operation": operation,
            "duration": duration
        })
        
    def record_error(self, error_type, error_message, stack_trace=None):
        """Hatayı kaydeder"""
        error_data = {
            "timestamp": time.time(),
            "type": error_type,
            "message": error_message,
            "stack_trace": stack_trace
        }
        self.metrics["errors"].append(error_data)
        self._log_error(error_type, error_message, stack_trace)
        
    def update_usage_stats(self, stat_name, value=1):
        """Kullanım istatistiklerini günceller"""
        if stat_name in self.metrics["usage_stats"]:
            self.metrics["usage_stats"][stat_name] += value
            
    def _save_metrics(self):
        """Metrikleri dosyaya kaydeder"""
        try:
            with open('performance_metrics.json', 'w') as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            self._log_error("Metrik kaydetme hatası", e)
            
    def _log_error(self, error_type, error_message, stack_trace=None):
        """Hatayı loglar"""
        if stack_trace is None:
            stack_trace = traceback.format_exc()
        logging.error(f"{error_type}: {error_message}\n{stack_trace}")
        
    def get_performance_report(self):
        """Performans raporu oluşturur"""
        report = {
            "uptime": time.time() - self.start_time,
            "memory_usage": self.metrics["memory_usage"][-1]["value"] if self.metrics["memory_usage"] else 0,
            "cpu_usage": self.metrics["cpu_usage"][-1]["value"] if self.metrics["cpu_usage"] else 0,
            "usage_stats": self.metrics["usage_stats"],
            "error_count": len(self.metrics["errors"]),
            "average_response_time": sum(r["duration"] for r in self.metrics["response_times"]) / len(self.metrics["response_times"]) if self.metrics["response_times"] else 0
        }
        return report

class TextEditor:  
    def __init__(self, root):  
        self.root = root  
        self.root.title("Python Metin Editörü")
        
        # Tkinter değişkenleri
        self.syntax_highlighting_var = tk.BooleanVar(value=True)
        
        self.current_theme = tk.StringVar(value="Açık")
        
        # Tema isimleri
        self.theme_names = {
            "Açık": "Açık Tema",
            "Koyu": "Koyu Tema",
            "Sepya": "Sepya Tema",
            "Monokai": "Monokai",
            "Dracula": "Dracula",
            "Solarized Dark": "Solarized Dark",
            "Nord": "Nord",
            "GitHub": "GitHub",
            "One Dark": "One Dark",
            "Tokyo Night": "Tokyo Night"
        }
        
        # Sekme yönetimi
        self.tabs = {}
        self.current_tab = None
        self.tab_counter = 0
        self.last_directory = None
        
        # Notebook widget'ı
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Ttk stil tanımlamaları
        self.style = ttk.Style()
        self.style.configure("TNotebook", background="#f0f0f0")
        self.style.configure("TNotebook.Tab", background="#f0f0f0", padding=[5, 2])
        self.style.map("TNotebook.Tab",
            background=[("selected", "#ffffff")],
            foreground=[("selected", "#000000")]
        )
        
        # Tema ve sözdizimi vurgulama ayarları
        self.syntax_highlighting = True
        
        # Sözdizimi vurgulama renkleri
        self.syntax_colors = {
            "keywords": "#0000FF",      # Mavi
            "strings": "#008000",       # Yeşil
            "comments": "#808080",      # Gri
            "functions": "#800080",     # Mor
            "numbers": "#FF0000",       # Kırmızı
            "classes": "#000080",       # Koyu Mavi
            "decorators": "#800080",    # Mor
            "builtins": "#008080",      # Turkuaz
            "operators": "#000000",     # Siyah
            "variables": "#000000",     # Siyah
            "parameters": "#000000",    # Siyah
            "types": "#000080",         # Koyu Mavi
            "errors": "#FF0000",        # Kırmızı
            "warnings": "#FFA500",      # Turuncu
            "docstrings": "#008000",    # Yeşil
            "tags": "#800000",          # Bordo
            "attributes": "#008080",    # Turkuaz
            "selectors": "#0000FF",     # Mavi
            "properties": "#008080",    # Turkuaz
            "values": "#008000",        # Yeşil
            "headings": "#000080",      # Koyu Mavi
            "links": "#0000FF",         # Mavi
            "bold": "#000000",          # Siyah
            "italic": "#000000",        # Siyah
            "code": "#000000",          # Siyah
            "lists": "#000000",         # Siyah
            "quotes": "#008000"         # Yeşil
        }
        
        # Tema renkleri
        self.theme_colors = {
            "Açık": {
                "bg": "#ffffff",
                "fg": "#000000",
                "menu_bg": "#f0f0f0",
                "menu_fg": "#000000",
                "menu_active_bg": "#e0e0e0",
                "menu_active_fg": "#000000",
                "current_line_bg": "#e8e8e8",
                "search_highlight_bg": "#ffff00",
                "search_highlight_fg": "#000000",
                "status_bar_bg": "#f0f0f0",
                "status_bar_fg": "#333333",
                "insertbackground": "#000000",
                "selectbackground": "#0078d7",
                "selectforeground": "#ffffff"
            },
            "Koyu": {
                "bg": "#1e1e1e",
                "fg": "#ffffff",
                "menu_bg": "#2d2d2d",
                "menu_fg": "#ffffff",
                "menu_active_bg": "#3d3d3d",
                "menu_active_fg": "#ffffff",
                "current_line_bg": "#2d2d2d",
                "search_highlight_bg": "#ffff00",
                "search_highlight_fg": "#000000",
                "status_bar_bg": "#2d2d2d",
                "status_bar_fg": "#ffffff",
                "insertbackground": "#ffffff",
                "selectbackground": "#264f78",
                "selectforeground": "#ffffff"
            },
            "Sepya": {
                "bg": "#f4ecd8",
                "fg": "#5b4636",
                "menu_bg": "#e8dfd0",
                "menu_fg": "#5b4636",
                "menu_active_bg": "#c4b5a0",
                "menu_active_fg": "#5b4636",
                "current_line_bg": "#e8e0d0",
                "search_highlight_bg": "#e8d0b0",
                "search_highlight_fg": "#5b4636",
                "status_bar_bg": "#e8dfd0",
                "status_bar_fg": "#5b4636",
                "insertbackground": "#5b4636",
                "selectbackground": "#c4b5a0",
                "selectforeground": "#5b4636"
            },
            "Monokai": {
                "bg": "#272822",
                "fg": "#f8f8f2",
                "menu_bg": "#272822",
                "menu_fg": "#f8f8f2",
                "menu_active_bg": "#49483e",
                "menu_active_fg": "#f8f8f2",
                "current_line_bg": "#3e3d32",
                "search_highlight_bg": "#a6e22e",
                "search_highlight_fg": "#272822",
                "status_bar_bg": "#272822",
                "status_bar_fg": "#f8f8f2",
                "insertbackground": "#f8f8f2",
                "selectbackground": "#49483e",
                "selectforeground": "#f8f8f2"
            },
            "Dracula": {
                "bg": "#282a36",
                "fg": "#f8f8f2",
                "menu_bg": "#282a36",
                "menu_fg": "#f8f8f2",
                "menu_active_bg": "#44475a",
                "menu_active_fg": "#f8f8f2",
                "current_line_bg": "#44475a",
                "search_highlight_bg": "#ff79c6",
                "search_highlight_fg": "#282a36",
                "status_bar_bg": "#282a36",
                "status_bar_fg": "#f8f8f2",
                "insertbackground": "#f8f8f2",
                "selectbackground": "#44475a",
                "selectforeground": "#f8f8f2"
            },
            "Solarized Dark": {
                "bg": "#002b36",
                "fg": "#839496",
                "menu_bg": "#002b36",
                "menu_fg": "#839496",
                "menu_active_bg": "#073642",
                "menu_active_fg": "#839496",
                "current_line_bg": "#073642",
                "search_highlight_bg": "#b58900",
                "search_highlight_fg": "#002b36",
                "status_bar_bg": "#002b36",
                "status_bar_fg": "#839496",
                "insertbackground": "#839496",
                "selectbackground": "#073642",
                "selectforeground": "#839496"
            },
            "Nord": {
                "bg": "#2e3440",
                "fg": "#eceff4",
                "menu_bg": "#2e3440",
                "menu_fg": "#eceff4",
                "menu_active_bg": "#434c5e",
                "menu_active_fg": "#eceff4",
                "current_line_bg": "#3b4252",
                "search_highlight_bg": "#88c0d0",
                "search_highlight_fg": "#2e3440",
                "status_bar_bg": "#2e3440",
                "status_bar_fg": "#eceff4",
                "insertbackground": "#eceff4",
                "selectbackground": "#434c5e",
                "selectforeground": "#eceff4"
            },
            "GitHub": {
                "bg": "#ffffff",
                "fg": "#24292e",
                "menu_bg": "#f6f8fa",
                "menu_fg": "#24292e",
                "menu_active_bg": "#c8e1ff",
                "menu_active_fg": "#24292e",
                "current_line_bg": "#f6f8fa",
                "search_highlight_bg": "#ffd33d",
                "search_highlight_fg": "#24292e",
                "status_bar_bg": "#f6f8fa",
                "status_bar_fg": "#24292e",
                "insertbackground": "#24292e",
                "selectbackground": "#c8e1ff",
                "selectforeground": "#24292e"
            },
            "One Dark": {
                "bg": "#282c34",
                "fg": "#abb2bf",
                "menu_bg": "#282c34",
                "menu_fg": "#abb2bf",
                "menu_active_bg": "#3e4451",
                "menu_active_fg": "#abb2bf",
                "current_line_bg": "#2c323c",
                "search_highlight_bg": "#e5c07b",
                "search_highlight_fg": "#282c34",
                "status_bar_bg": "#282c34",
                "status_bar_fg": "#abb2bf",
                "insertbackground": "#abb2bf",
                "selectbackground": "#3e4451",
                "selectforeground": "#abb2bf"
            },
            "Tokyo Night": {
                "bg": "#1a1b26",
                "fg": "#a9b1d6",
                "menu_bg": "#1a1b26",
                "menu_fg": "#a9b1d6",
                "menu_active_bg": "#414868",
                "menu_active_fg": "#a9b1d6",
                "current_line_bg": "#24283b",
                "search_highlight_bg": "#bb9af7",
                "search_highlight_fg": "#1a1b26",
                "status_bar_bg": "#1a1b26",
                "status_bar_fg": "#a9b1d6",
                "insertbackground": "#a9b1d6",
                "selectbackground": "#414868",
                "selectforeground": "#a9b1d6"
            }
        }
        
        # Performans izleyici
        self.performance_monitor = PerformanceMonitor(self)
        self.performance_monitor.start_monitoring()
        
        # Menü oluşturma  
        self.create_menu()  
          
        # Durum çubuğu  
        self.create_status_bar()  
          
        # Klavye kısayolları  
        self.bind_shortcuts()
        
        # Arama ve değiştirme çerçevesi
        self.search_frame = None
        self.search_text = None
        self.replace_text = None
        
        # İlk temayı uygula
        self.apply_theme(self.current_theme.get())
        
        # İlk sekmeyi oluştur
        self.new_tab()
        
        # Sekme sürükle-bırak için değişkenler
        self.drag_data = {"x": 0, "y": 0, "item": None}
        self.notebook.bind("<ButtonPress-1>", self.on_tab_press)
        self.notebook.bind("<ButtonRelease-1>", self.on_tab_release)
        self.notebook.bind("<B1-Motion>", self.on_tab_motion)
        
    def new_tab(self, file_path=None):
        """Yeni bir sekme oluşturur"""
        # Sekme çerçevesi
        frame = ttk.Frame(self.notebook)
        
        # Metin alanı ve kaydırma çubukları
        text_frame = tk.Frame(frame)
        text_frame.pack(expand=True, fill="both")
        
        # Dikey kaydırma çubuğu
        scrollbar_y = tk.Scrollbar(text_frame)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Yatay kaydırma çubuğu
        scrollbar_x = tk.Scrollbar(text_frame, orient=tk.HORIZONTAL)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Metin widget'ı
        text = tk.Text(text_frame,
                      yscrollcommand=scrollbar_y.set,
                      xscrollcommand=scrollbar_x.set,
                      wrap=tk.NONE,
                      undo=True)
        text.pack(expand=True, fill="both")
        
        # Kaydırma çubuklarını metin widget'ı ile eşleştirme
        scrollbar_y.config(command=text.yview)
        scrollbar_x.config(command=text.xview)
        
        # Sekme ID'si
        tab_id = f"tab_{self.tab_counter}"
        self.tab_counter += 1
        
        # Sekme başlığı
        tab_title = "Yeni Dosya" if not file_path else os.path.basename(file_path)
        
        # Sekme başlığı için frame
        tab_header = ttk.Frame(self.notebook)
        
        # Sekme başlığı etiketi (kapatma butonu dahil)
        title_label = tk.Label(
            tab_header,
            text=f"{tab_title} ×",
            font=("Segoe UI", 9),
            cursor="hand2",
            bg="#f0f0f0",
            fg="#666666",
            padx=5
        )
        title_label.pack(side=tk.LEFT)
        
        # Hover efektleri
        def on_enter(e):
            title_label.configure(fg="#e74c3c", bg="#e0e0e0")
            
        def on_leave(e):
            title_label.configure(fg="#666666", bg="#f0f0f0")
            
        def on_click(e):
            # Tıklanan konumun kapatma butonuna denk gelip gelmediğini kontrol et
            x = e.x
            label_width = title_label.winfo_width()
            if x > label_width - 15:  # Son 15 piksel kapatma butonu alanı
                self.close_tab(tab_id)
            
        # Olayları bağla
        title_label.bind("<Enter>", on_enter)
        title_label.bind("<Leave>", on_leave)
        title_label.bind("<Button-1>", on_click)
        
        # Sekme içi kapatma butonu
        inner_close_frame = tk.Frame(text, width=20, height=20)
        inner_close_frame.place(relx=1.0, rely=0.0, anchor="ne", x=-5, y=5)
        inner_close_frame.configure(bg="#f0f0f0", highlightbackground="#cccccc", highlightthickness=1)
        inner_close_frame.lift()  # Butonu en üste getir
        
        inner_close_button = tk.Label(
            inner_close_frame,
            text="×",
            font=("Segoe UI", 12),
            cursor="hand2",
            bg="#f0f0f0",
            fg="#666666"
        )
        inner_close_button.place(relx=0.5, rely=0.5, anchor="center")
        
        # İç kapatma butonu hover efektleri
        def on_inner_enter(e):
            inner_close_button.configure(fg="#e74c3c", bg="#e0e0e0")
            inner_close_frame.configure(bg="#e0e0e0", highlightbackground="#e74c3c")
            
        def on_inner_leave(e):
            inner_close_button.configure(fg="#666666", bg="#f0f0f0")
            inner_close_frame.configure(bg="#f0f0f0", highlightbackground="#cccccc")
            
        def on_inner_click(e):
            self.close_tab(tab_id)
            
        # İç kapatma butonu olaylarını bağla
        inner_close_button.bind("<Enter>", on_inner_enter)
        inner_close_button.bind("<Leave>", on_inner_leave)
        inner_close_button.bind("<Button-1>", on_inner_click)
        inner_close_frame.bind("<Enter>", on_inner_enter)
        inner_close_frame.bind("<Leave>", on_inner_leave)
        inner_close_frame.bind("<Button-1>", on_inner_click)
        
        # Metin widget'ı kaydırma olayını yakala
        def on_text_scroll(*args):
            # Kaydırma çubuklarını güncelle
            scrollbar_y.set(*args)
            # Kapatma butonunu güncelle
            inner_close_frame.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)
            
        text.configure(yscrollcommand=on_text_scroll)
        
        # Sekmeyi notebook'a ekle
        self.notebook.add(frame, text="")  # Boş başlık
        
        # Sekme bilgilerini kaydet
        self.tabs[tab_id] = {
            "file_path": file_path,
            "text_widget": text,
            "saved": True if file_path else False,
            "close_button": title_label,
            "close_frame": tab_header,
            "inner_close_button": inner_close_button,
            "inner_close_frame": inner_close_frame,
            "frame": frame,
            "header": tab_header,
            "title_label": title_label
        }
        
        # Sekme başlığını güncelle
        if file_path:
            self.update_tab_title(tab_id)
        
        # Etiketleri yapılandır
        text.tag_configure("current_line", background="#e9e9ff")
        text.tag_configure("bracket_highlight", background="#ccffcc")
        text.tag_raise("sel")
        text.tag_lower("current_line")
        
        # Olay bağlantıları
        text.bind("<KeyRelease>", self.on_key_release)
        text.bind("<ButtonRelease>", self.on_button_release)
        text.bind("<MouseWheel>", self.on_scroll)
        text.bind("<Button-4>", self.on_scroll)
        text.bind("<Button-5>", self.on_scroll)
        text.bind("<Button-2>", lambda e: self.close_tab(tab_id))  # Orta tekerlek tıklaması
        
        # Sekmeyi seç
        self.notebook.select(frame)
        self.current_tab = tab_id
        
        # Tema uygula
        self.apply_theme_to_tab(tab_id)
        
        # Başlık frame'ini notebook'a ekle
        self.notebook.tab(frame, text="")  # Boş başlık
        self.notebook.tab(frame, text=tab_title)  # Başlık metni
        
        return tab_id

    def update_tab_title(self, tab_id):
        """Sekme başlığını günceller"""
        if tab_id not in self.tabs:
            return
            
        tab_info = self.tabs[tab_id]
        file_path = tab_info["file_path"]
        saved = tab_info["saved"]
        title_label = tab_info["title_label"]
        frame = tab_info["frame"]
        
        if file_path:
            title = os.path.basename(file_path)
            if not saved:
                title = f"● {title}"  # Kaydedilmemiş değişiklik için nokta işareti
            title_label.config(text=title)
            self.notebook.tab(frame, text=title)
        else:
            title = "Yeni Dosya"
            if not saved:
                title = f"● {title}"
            title_label.config(text=title)
            self.notebook.tab(frame, text=title)

    def on_tab_press(self, event):
        """Sekme sürükleme başlangıcı"""
        try:
            # Tıklanan sekmenin indeksini bul
            index = self.notebook.index(f"@{event.x},{event.y}")
            if index >= 0:
                self.drag_data["item"] = index
                self.drag_data["x"] = event.x
                self.drag_data["y"] = event.y
        except tk.TclError:
            # Geçersiz koordinatlar durumunda sürüklemeyi başlatma
            self.drag_data["item"] = None

    def on_tab_motion(self, event):
        """Sekme sürükleme hareketi"""
        if self.drag_data["item"] is None:
            return
            
        # Sürükleme mesafesi
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        
        # Minimum sürükleme mesafesi
        if abs(dx) < 5:
            return
            
        try:
            # Hedef sekme indeksini bul
            target = self.notebook.index(f"@{event.x},{event.y}")
            if target >= 0 and target != self.drag_data["item"]:
                # Sekmeleri yeniden sırala
                current_tab = self.notebook.select()
                self.notebook.insert(target, current_tab)
                self.drag_data["item"] = target
                
                # Tab sıralamasını güncelle
                self.update_tab_order()
        except tk.TclError:
            # Mouse tab alanı dışındaysa işlemi iptal et
            pass

    def update_tab_order(self):
        """Sekme sıralamasını günceller"""
        # Notebook'taki tüm sekmeleri al
        tabs = self.notebook.tabs()
        
        # Yeni sıralamayı oluştur
        new_tabs = {}
        for tab in tabs:
            # Her sekme için tab_id'yi bul
            for tab_id, tab_info in self.tabs.items():
                if tab_info["frame"] == tab:
                    new_tabs[tab_id] = tab_info
                    break
        
        # Sekmeleri yeni sıralamaya göre güncelle
        self.tabs = new_tabs

    def on_tab_release(self, event):
        """Sekme sürükleme sonu"""
        self.drag_data["item"] = None
        self.update_tab_order()

    def show_tab_preview(self, event):
        """Sekme önizlemesini gösterir"""
        index = self.notebook.index(f"@{event.x},{event.y}")
        if index >= 0:
            tab_id = self.get_tab_id_by_index(index)
            if tab_id:
                text_widget = self.tabs[tab_id]["text_widget"]
                content = text_widget.get("1.0", "1.100")
                
                # Önizleme penceresi
                preview = tk.Toplevel(self.root)
                preview.wm_overrideredirect(True)
                preview.geometry(f"+{event.x_root+10}+{event.y_root+10}")
                
                # Önizleme metni
                label = tk.Label(preview, text=content, justify=tk.LEFT,
                               background="#ffffe0", relief=tk.SOLID, borderwidth=1)
                label.pack()
                
                # Pencereyi kapat
                preview.after(2000, preview.destroy)

    def get_tab_id_by_index(self, index):
        """Sekme indeksine göre tab_id döndürür"""
        if index < 0:
            return None
            
        # Notebook'taki tüm sekmeleri al
        tabs = self.notebook.tabs()
        if index >= len(tabs):
            return None
            
        # İstenen sekmenin frame'ini al
        tab_frame = tabs[index]
        if not tab_frame:
            return None
            
        # Frame'e karşılık gelen tab_id'yi bul
        for tab_id, tab_info in self.tabs.items():
            if tab_info["frame"] == tab_frame:
                return tab_id
        return None

    def get_current_tab(self):
        """Mevcut sekmeyi döndürür"""
        current = self.notebook.select()
        if not current:
            return None
            
        # Frame'e karşılık gelen tab_id'yi bul
        for tab_id, tab_info in self.tabs.items():
            if tab_info["frame"] == current:
                return tab_id
        return None
        
    def get_current_text_widget(self):
        """Mevcut metin widget'ını döndürür"""
        tab_id = self.get_current_tab()
        if tab_id:
            return self.tabs[tab_id]["text_widget"]
        return None

    def close_tab(self, tab_id=None):
        """Belirtilen sekmeyi kapatır"""
        if tab_id is None:
            tab_id = self.get_current_tab()
            
        if not tab_id or tab_id not in self.tabs:
            return
            
        # Değişiklikleri kontrol et
        if not self.check_tab_changes(tab_id):
            return
            
        # Sekme bilgilerini al
        tab_info = self.tabs[tab_id]
        frame = tab_info["frame"]
        header = tab_info["header"]
        close_frame = tab_info["close_frame"]
        
        # Sekmeyi notebook'tan kaldır
        self.notebook.forget(frame)
        
        # Tüm widget'ları temizle
        header.destroy()
        close_frame.destroy()
        
        # Sekme bilgilerini sil
        del self.tabs[tab_id]
        
        # Eğer hiç sekme kalmadıysa yeni sekme oluştur
        if not self.tabs:
            self.new_tab()
        else:
            # Yeni aktif sekmeyi seç
            self.current_tab = self.get_current_tab()
            
    def check_tab_changes(self, tab_id):
        """Sekmedeki değişiklikleri kontrol eder"""
        try:
            if tab_id not in self.tabs:
                return True
                
            tab_info = self.tabs[tab_id]
            text_widget = tab_info["text_widget"]
            file_path = tab_info["file_path"]
            
            # Eğer dosya yoksa ve içerik boşsa, doğrudan kapat
            if not file_path and not text_widget.get("1.0", "end-1c").strip():
                return True
        
            if not tab_info["saved"]:
                # Dosya adını belirle
                file_name = os.path.basename(file_path) if file_path else "Yeni Dosya"
                
                # Özel mesaj kutusu oluştur
                dialog = tk.Toplevel(self.root)
                dialog.title("Kaydedilmemiş Değişiklikler")
                dialog.geometry("400x180")
                dialog.transient(self.root)
                dialog.grab_set()
                dialog.resizable(False, False)
                
                # Pencereyi kapatma butonunu devre dışı bırak
                dialog.protocol("WM_DELETE_WINDOW", lambda: None)
                
                # Arka plan rengi
                dialog.configure(bg="#ffffff")
                
                # Ana çerçeve
                main_frame = tk.Frame(dialog, bg="#ffffff", padx=20, pady=15)
                main_frame.pack(fill=tk.BOTH, expand=True)
                
                # Üst kısım (ikon ve başlık)
                top_frame = tk.Frame(main_frame, bg="#ffffff")
                top_frame.pack(fill=tk.X, pady=(0, 15))
                
                # Uyarı ikonu
                warning_icon = "⚠️"
                warning_label = tk.Label(
                    top_frame,
                    text=warning_icon,
                    font=("Segoe UI", 16),
                    bg="#ffffff"
                )
                warning_label.pack(side=tk.LEFT, padx=(0, 10))
                
                # Başlık ve mesaj
                title_frame = tk.Frame(top_frame, bg="#ffffff")
                title_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                title_label = tk.Label(
                    title_frame,
                    text="Kaydedilmemiş Değişiklikler",
                    font=("Segoe UI", 11, "bold"),
                    bg="#ffffff",
                    fg="#333333"
                )
                title_label.pack(anchor="w")
                
                message_label = tk.Label(
                    title_frame,
                    text=f'"{file_name}" dosyasında kaydedilmemiş değişiklikler var.',
                    font=("Segoe UI", 10),
                    bg="#ffffff",
                    fg="#666666",
                    wraplength=300,
                    justify=tk.LEFT
                )
                message_label.pack(anchor="w", pady=(4, 0))
                
                # Butonlar için frame
                button_frame = tk.Frame(main_frame, bg="#ffffff")
                button_frame.pack(fill=tk.X, pady=(10, 0))
                
                result = {"value": None}
                
                def on_save():
                    result["value"] = True
                    dialog.destroy()
                    
                def on_dont_save():
                    result["value"] = False
                    dialog.destroy()
                    
                def on_cancel():
                    result["value"] = None
                    dialog.destroy()
                
                # Buton stilleri
                button_style = {
                    "font": ("Segoe UI", 10),
                    "width": 10,
                    "height": 1,
                    "borderwidth": 0,
                    "cursor": "hand2",
                    "padx": 15
                }
                
                # Butonlar
                save_button = tk.Button(
                    button_frame,
                    text="Kaydet",
                    command=on_save,
                    bg="#0078d7",
                    fg="white",
                    activebackground="#106ebe",
                    activeforeground="white",
                    **button_style
                )
                save_button.pack(side=tk.RIGHT, padx=(8, 0))
                
                dont_save_button = tk.Button(
                    button_frame,
                    text="Kaydetme",
                    command=on_dont_save,
                    bg="#f0f0f0",
                    fg="#333333",
                    activebackground="#e0e0e0",
                    activeforeground="#333333",
                    **button_style
                )
                dont_save_button.pack(side=tk.RIGHT, padx=8)
                
                cancel_button = tk.Button(
                    button_frame,
                    text="İptal",
                    command=on_cancel,
                    bg="#f0f0f0",
                    fg="#333333",
                    activebackground="#e0e0e0",
                    activeforeground="#333333",
                    **button_style
                )
                cancel_button.pack(side=tk.RIGHT, padx=8)
                
                # Pencereyi ortala
                dialog.update_idletasks()
                width = dialog.winfo_width()
                height = dialog.winfo_height()
                x = (dialog.winfo_screenwidth() // 2) - (width // 2)
                y = (dialog.winfo_screenheight() // 2) - (height // 2)
                dialog.geometry(f"{width}x{height}+{x}+{y}")
                
                # Enter tuşu ile kaydet, Escape tuşu ile iptal
                dialog.bind("<Return>", lambda e: on_save())
                dialog.bind("<Escape>", lambda e: on_cancel())
                
                # Pencereyi göster ve sonucu bekle
                self.root.wait_window(dialog)
                
                if result["value"] is None:  # İptal
                    return False
                elif result["value"]:  # Kaydet
                    return self.save_tab(tab_id)
                else:  # Kaydetme
                    return True
                
            return True
            
        except Exception as e:
            print(f"Sekme değişiklik kontrolü hatası: {str(e)}")
            return True  # Hata durumunda güvenli çıkış

    def save_tab(self, tab_id=None):
        """Belirtilen sekmeyi kaydeder"""
        try:
            if tab_id is None:
                tab_id = self.get_current_tab()
                
            if not tab_id or tab_id not in self.tabs:
                return False
                
            tab_info = self.tabs[tab_id]
            text_widget = tab_info["text_widget"]
            file_path = tab_info["file_path"]
            
            if file_path:
                try:
                    content = text_widget.get(1.0, tk.END)
                    
                    # Dosya yazma izni kontrolü
                    if os.path.exists(file_path) and not os.access(file_path, os.W_OK):
                        messagebox.showerror(
                            "Hata",
                            f"Dosya yazma izni yok:\n{file_path}"
                        )
                        return False
                    
                    # Yedek dosya oluştur
                    backup_path = file_path + ".bak"
                    if os.path.exists(file_path):
                        try:
                            shutil.copy2(file_path, backup_path)
                        except Exception as e:
                            self.performance_monitor.record_error("BackupCreate", str(e))
                    
                    # Dosyayı kaydet
                    with open(file_path, 'w', encoding='utf-8') as file:
                        file.write(content)
                    
                    # Yedek dosyayı sil
                    if os.path.exists(backup_path):
                        try:
                            os.remove(backup_path)
                        except Exception as e:
                            self.performance_monitor.record_error("BackupDelete", str(e))
                    
                    tab_info["saved"] = True
                    self.update_tab_title(tab_id)
                    
                    # Dosya izleme zaman damgasını güncelle
                    if hasattr(self, 'last_mtime'):
                        self.last_mtime[tab_id] = os.path.getmtime(file_path)
                    
                    # Durum çubuğunu güncelle
                    file_size = os.path.getsize(file_path)
                    file_modified = os.path.getmtime(file_path)
                    file_info = (
                        f"Dosya: {os.path.basename(file_path)}\n"
                        f"Boyut: {self.format_file_size(file_size)}\n"
                        f"Son Değişiklik: {self.format_date(file_modified)}\n"
                        f"Kodlama: utf-8"
                    )
                    self.status_bar.config(text=file_info)
                    
                    # Performans izleme
                    self.performance_monitor.update_usage_stats("files_saved")
                    
                    return True
                except Exception as e:
                    self.performance_monitor.record_error("SaveFile", str(e))
                    messagebox.showerror("Hata", f"Dosya kaydedilirken hata oluştu:\n{str(e)}")
                    return False
            else:
                return self.save_tab_as(tab_id)
                
        except Exception as e:
            self.performance_monitor.record_error("SaveTab", str(e))
            print(f"Kaydetme hatası: {str(e)}")
            return False

    def save_tab_as(self, tab_id=None):
        """Belirtilen sekmeyi farklı kaydeder"""
        try:
            if tab_id is None:
                tab_id = self.get_current_tab()
                
            if not tab_id or tab_id not in self.tabs:
                return False
                
            # Son kaydedilen dizini al
            initial_dir = os.path.expanduser("~")
            if hasattr(self, 'last_directory') and self.last_directory:
                initial_dir = self.last_directory
                
            # Mevcut dosya yolu varsa, o dizini kullan
            tab_info = self.tabs[tab_id]
            if tab_info["file_path"]:
                initial_dir = os.path.dirname(tab_info["file_path"])
                
            file_path = filedialog.asksaveasfilename(
                initialdir=initial_dir,
                title="Farklı Kaydet",
                defaultextension=".txt",
                filetypes=[
                    ("Python Dosyaları", "*.py"),
                    ("Metin Dosyaları", "*.txt"),
                    ("HTML Dosyaları", "*.html;*.htm"),
                    ("CSS Dosyaları", "*.css"),
                    ("JavaScript Dosyaları", "*.js"),
                    ("JSON Dosyaları", "*.json"),
                    ("XML Dosyaları", "*.xml"),
                    ("Markdown Dosyaları", "*.md"),
                    ("Tüm Dosyalar", "*.*")
                ]
            )
            
            if file_path:
                # Son kaydedilen dizini güncelle
                self.last_directory = os.path.dirname(file_path)
                
                # Dosya zaten açık mı kontrol et
                for other_tab_id, other_tab_info in self.tabs.items():
                    if other_tab_id != tab_id and other_tab_info["file_path"] == file_path:
                        messagebox.showerror(
                            "Hata",
                            "Bu dosya zaten başka bir sekmede açık!"
                        )
                        return False
                
                # Dosya yazma izni kontrolü
                if os.path.exists(file_path) and not os.access(file_path, os.W_OK):
                    messagebox.showerror(
                        "Hata",
                        f"Dosya yazma izni yok:\n{file_path}"
                    )
                    return False
                
                tab_info["file_path"] = file_path
                tab_info["saved"] = True
                self.update_tab_title(tab_id)
                
                # Dosya izleme başlat
                self.start_file_watching(tab_id, file_path)
                
                # Performans izleme
                self.performance_monitor.update_usage_stats("files_saved_as")
                
                return self.save_tab(tab_id)
                
            return False
            
        except Exception as e:
            self.performance_monitor.record_error("SaveAs", str(e))
            print(f"Farklı kaydetme hatası: {str(e)}")
            return False
        
    def open_file_in_tab(self, file_path):
        """Dosyayı yeni sekmede açar"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            tab_id = self.new_tab(file_path)
            text_widget = self.tabs[tab_id]["text_widget"]
            text_widget.insert(1.0, content)
            self.tabs[tab_id]["saved"] = True
            
            # Sözdizimi vurgulaması uygula
            if self.syntax_highlighting:
                self.apply_syntax_highlighting_to_tab(tab_id)
                
            return True
        except Exception as e:
            messagebox.showerror("Hata", f"Dosya açılırken hata oluştu:\n{str(e)}")
            return False
            
    def apply_theme_to_tab(self, tab_id):
        """Belirtilen sekmeye tema uygular"""
        if tab_id not in self.tabs:
            return
            
        tab_info = self.tabs[tab_id]
        text_widget = tab_info["text_widget"]
        theme = self.theme_colors[self.current_theme.get()]
        
        text_widget.config(
            bg=theme["bg"],
            fg=theme["fg"],
            insertbackground=theme["insertbackground"],
            selectbackground=theme["selectbackground"]
        )
        
        # Sözdizimi vurgulaması uygula
        if self.syntax_highlighting:
            self.apply_syntax_highlighting_to_tab(tab_id)
            
    def apply_syntax_highlighting_to_tab(self, tab_id):
        """Belirtilen sekmeye sözdizimi vurgulaması uygular"""
        if tab_id not in self.tabs:
            return
            
        tab_info = self.tabs[tab_id]
        text_widget = tab_info["text_widget"]
        file_path = tab_info["file_path"]
        
        if not file_path:
            return
            
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Önce tüm sözdizimi etiketlerini temizle
        for tag in ["keyword", "string", "comment", "number", "operator", "method", "class", "library",
                   "decorator", "variable", "constant", "function", "parameter", "type", "builtin",
                   "error", "warning", "docstring", "tag", "attribute", "selector", "property", "value",
                   "heading", "link", "bold", "italic", "code", "list", "quote"]:
            text_widget.tag_remove(tag, "1.0", tk.END)
            
        # Dosya türüne göre sözdizimi vurgulaması uygula
        if file_ext == ".py":
            self.highlight_python_syntax(text_widget, "1.0", tk.END)
        elif file_ext in [".html", ".htm"]:
            self.highlight_html_syntax(text_widget, "1.0", tk.END)
        elif file_ext == ".css":
            self.highlight_css_syntax(text_widget, "1.0", tk.END)
        elif file_ext == ".js":
            self.highlight_javascript_syntax(text_widget, "1.0", tk.END)
        elif file_ext == ".json":
            self.highlight_json_syntax(text_widget, "1.0", tk.END)
        elif file_ext == ".xml":
            self.highlight_xml_syntax(text_widget, "1.0", tk.END)
        elif file_ext == ".md":
            self.highlight_markdown_syntax(text_widget, "1.0", tk.END)
        elif file_ext == ".txt":
            # Metin dosyaları için sözdizimi vurgulaması yok
            pass

    def highlight_html_syntax(self, text_widget, start_pos="1.0", end_pos="end"):
        """HTML sözdizimi vurgulaması uygular"""
        # Etiketleri tanımla
        text_widget.tag_configure("tag", foreground=self.syntax_colors["keywords"])
        text_widget.tag_configure("attribute", foreground=self.syntax_colors["attributes"])
        text_widget.tag_configure("string", foreground=self.syntax_colors["strings"])
        text_widget.tag_configure("comment", foreground=self.syntax_colors["comments"])
        
        # HTML etiketlerini vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'<[^>]+>', pos, end_pos, regexp=True)
            if not pos:
                break
                
            tag_end = text_widget.search(r'>', pos, end_pos)
            if not tag_end:
                break
                
            tag_text = text_widget.get(pos, tag_end)
            
            # Yorum etiketlerini kontrol et
            if tag_text.startswith('<!--'):
                comment_end = text_widget.search('-->', pos, end_pos)
                if comment_end:
                    text_widget.tag_add("comment", pos, f"{comment_end}+3c")
                    pos = f"{comment_end}+3c"
                    continue
            
            # Etiket adını vurgula
            tag_name_end = text_widget.search(r'[\s>]', pos, end_pos, regexp=True)
            if tag_name_end:
                text_widget.tag_add("tag", pos, tag_name_end)
                
                # Özellikleri vurgula
                attr_pos = tag_name_end
                while True:
                    attr_pos = text_widget.search(r'\s+[a-zA-Z-]+=', attr_pos, tag_end, regexp=True)
                    if not attr_pos:
                        break
                        
                    attr_name_end = text_widget.search(r'=', attr_pos, tag_end)
                    if attr_name_end:
                        text_widget.tag_add("attribute", attr_pos, attr_name_end)
                        
                        # Değeri vurgula
                        value_start = text_widget.search(r'["\']', attr_name_end, tag_end)
                        if value_start:
                            value_end = text_widget.search(r'["\']', f"{value_start}+1c", tag_end)
                            if value_end:
                                # Değer içindeki özel karakterleri kontrol et
                                value_text = text_widget.get(value_start, f"{value_end}+1c")
                                if any(c in value_text for c in ['&', '<', '>']):
                                    text_widget.tag_add("string", value_start, f"{value_end}+1c")
                                else:
                                    text_widget.tag_add("string", value_start, f"{value_end}+1c")
                                attr_pos = f"{value_end}+1c"
                                continue
                    
                    attr_pos = text_widget.index(f"{attr_pos}+1c")
            
            pos = f"{tag_end}+1c"

    def highlight_css_syntax(self, text_widget, start_pos="1.0", end_pos="end"):
        """CSS sözdizimi vurgulaması uygular"""
        # Etiketleri tanımla
        text_widget.tag_configure("selector", foreground=self.syntax_colors["keywords"])
        text_widget.tag_configure("property", foreground=self.syntax_colors["properties"])
        text_widget.tag_configure("value", foreground=self.syntax_colors["strings"])
        text_widget.tag_configure("comment", foreground=self.syntax_colors["comments"])
        
        # Yorumları vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'/\*', pos, end_pos, regexp=True)
            if not pos:
                break
                
            comment_end = text_widget.search(r'\*/', pos, end_pos, regexp=True)
            if comment_end:
                text_widget.tag_add("comment", pos, f"{comment_end}+2c")
                pos = f"{comment_end}+2c"
            else:
                pos = text_widget.index(f"{pos}+2c")
        
        # Seçicileri ve özellikleri vurgula
        pos = start_pos
        while True:
            # Seçiciyi bul
            pos = text_widget.search(r'[^{]+{', pos, end_pos, regexp=True)
            if not pos:
                break
                
            selector_end = text_widget.search(r'{', pos, end_pos)
            if selector_end:
                text_widget.tag_add("selector", pos, selector_end)
                
                # Özellikleri bul
                prop_pos = selector_end
                while True:
                    prop_pos = text_widget.search(r'[a-zA-Z-]+:', prop_pos, end_pos, regexp=True)
                    if not prop_pos:
                        break
                        
                    prop_name_end = text_widget.search(r':', prop_pos, end_pos)
                    if prop_name_end:
                        text_widget.tag_add("property", prop_pos, prop_name_end)
                        
                        # Değeri bul
                        value_start = prop_name_end
                        value_end = text_widget.search(r';', value_start, end_pos)
                        if value_end:
                            value_text = text_widget.get(value_start, value_end)
                            # Renk değerlerini kontrol et
                            if re.match(r'^#[0-9a-fA-F]{3,6}$', value_text.strip()) or \
                               re.match(r'^rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)$', value_text.strip()) or \
                               re.match(r'^rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[\d.]+\s*\)$', value_text.strip()):
                                text_widget.tag_add("value", value_start, value_end)
                            else:
                                text_widget.tag_add("value", value_start, value_end)
                            prop_pos = f"{value_end}+1c"
                        else:
                            break
                    else:
                        break
                
                # Kapanış parantezini bul
                block_end = text_widget.search(r'}', selector_end, end_pos)
                if block_end:
                    pos = f"{block_end}+1c"
                else:
                    break
            else:
                break

    def highlight_javascript_syntax(self, text_widget, start_pos="1.0", end_pos="end"):
        """JavaScript sözdizimi vurgulaması uygular"""
        # Etiketleri tanımla
        text_widget.tag_configure("keyword", foreground=self.syntax_colors["keywords"])
        text_widget.tag_configure("string", foreground=self.syntax_colors["strings"])
        text_widget.tag_configure("comment", foreground=self.syntax_colors["comments"])
        text_widget.tag_configure("function", foreground=self.syntax_colors["functions"])
        text_widget.tag_configure("number", foreground=self.syntax_colors["numbers"])
        text_widget.tag_configure("class", foreground=self.syntax_colors["classes"])
        text_widget.tag_configure("builtin", foreground=self.syntax_colors["builtins"])
        text_widget.tag_configure("operator", foreground=self.syntax_colors["operators"])
        text_widget.tag_configure("variable", foreground=self.syntax_colors["variables"])
        
        # JavaScript anahtar kelimeleri
        keywords = [
            "break", "case", "catch", "continue", "debugger", "default", "delete", "do", "else",
            "finally", "for", "function", "if", "in", "instanceof", "new", "return", "switch",
            "this", "throw", "try", "typeof", "var", "void", "while", "with", "const", "let",
            "class", "extends", "export", "import", "super", "static", "async", "await"
        ]
        
        # Yerleşik fonksiyonlar
        builtins = [
            "console", "document", "window", "Math", "Date", "Array", "Object", "String",
            "Number", "Boolean", "Function", "RegExp", "JSON", "Promise", "Set", "Map",
            "Error", "TypeError", "ReferenceError", "SyntaxError", "eval", "parseInt",
            "parseFloat", "isNaN", "isFinite", "decodeURI", "encodeURI", "decodeURIComponent",
            "encodeURIComponent"
        ]
        
        # Yorumları vurgula
        pos = start_pos
        while True:
            # Tek satırlık yorumlar
            pos = text_widget.search(r'//', pos, end_pos, regexp=True)
            if not pos:
                break
                
            line_end = text_widget.index(f"{pos} lineend")
            text_widget.tag_add("comment", pos, line_end)
            pos = line_end
            
            # Çok satırlı yorumlar
            pos = text_widget.search(r'/\*', pos, end_pos, regexp=True)
            if not pos:
                break
                
            comment_end = text_widget.search(r'\*/', pos, end_pos, regexp=True)
            if comment_end:
                text_widget.tag_add("comment", pos, f"{comment_end}+2c")
                pos = f"{comment_end}+2c"
            else:
                pos = text_widget.index(f"{pos}+2c")
        
        # Anahtar kelimeleri vurgula
        for keyword in keywords:
            pos = start_pos
            while True:
                pos = text_widget.search(r'\b' + keyword + r'\b', pos, end_pos, regexp=True)
                if not pos:
                    break
                    
                text_widget.tag_add("keyword", pos, f"{pos}+{len(keyword)}c")
                pos = text_widget.index(f"{pos}+{len(keyword)}c")
        
        # Yerleşik fonksiyonları vurgula
        for builtin in builtins:
            pos = start_pos
            while True:
                pos = text_widget.search(r'\b' + builtin + r'\b', pos, end_pos, regexp=True)
                if not pos:
                    break
                    
                text_widget.tag_add("builtin", pos, f"{pos}+{len(builtin)}c")
                pos = text_widget.index(f"{pos}+{len(builtin)}c")
        
        # Sayıları vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'\b\d+(\.\d+)?\b', pos, end_pos, regexp=True)
            if not pos:
                break
                
            number_end = text_widget.search(r'\b', pos, end_pos, regexp=True)
            if number_end:
                text_widget.tag_add("number", pos, number_end)
                pos = number_end
            else:
                pos = text_widget.index(f"{pos}+1c")
        
        # Stringleri vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'["\']', pos, end_pos, regexp=True)
            if not pos:
                break
                
            quote = text_widget.get(pos)
            string_end = text_widget.search(quote, f"{pos}+1c", end_pos)
            if string_end:
                text_widget.tag_add("string", pos, f"{string_end}+1c")
                pos = f"{string_end}+1c"
            else:
                pos = text_widget.index(f"{pos}+1c")
        
        # Fonksiyonları vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'\b(function|const|let|var)\s+([a-zA-Z_]\w*)', pos, end_pos, regexp=True)
            if not pos:
                break
                
            func_name_start = text_widget.search(r'[a-zA-Z_]\w*', f"{pos}+8c", end_pos)
            if func_name_start:
                func_name_end = text_widget.search(r'[(\s]', func_name_start, end_pos)
                if func_name_end:
                    text_widget.tag_add("function", func_name_start, func_name_end)
                    pos = func_name_end
                else:
                    pos = text_widget.index(f"{pos}+1c")
            else:
                pos = text_widget.index(f"{pos}+1c")
        
        # Sınıfları vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'\bclass\s+([a-zA-Z_]\w*)', pos, end_pos, regexp=True)
            if not pos:
                break
                
            class_name_start = text_widget.search(r'[a-zA-Z_]\w*', f"{pos}+6c", end_pos)
            if class_name_start:
                class_name_end = text_widget.search(r'[{\s]', class_name_start, end_pos)
                if class_name_end:
                    text_widget.tag_add("class", class_name_start, class_name_end)
                    pos = class_name_end
                else:
                    pos = text_widget.index(f"{pos}+1c")
            else:
                pos = text_widget.index(f"{pos}+1c")
        
        # Operatörleri vurgula
        operators = ['+', '-', '*', '/', '%', '=', '==', '===', '!=', '!==', '>', '<', '>=', '<=', '&&', '||', '!', '?', ':', '+=', '-=', '*=', '/=', '%=', '++', '--']
        for operator in operators:
            pos = start_pos
            while True:
                # Özel karakterler içeren operatörler için regex kullanma
                if any(c in operator for c in ['*', '+', '?', '.', '^', '$', '|', '(', ')', '[', ']', '{', '}']):
                    pos = text_widget.search(re.escape(operator), pos, end_pos)
                else:
                    pos = text_widget.search(operator, pos, end_pos)
                if not pos:
                    break
                    
                text_widget.tag_add("operator", pos, f"{pos}+{len(operator)}c")
                pos = text_widget.index(f"{pos}+{len(operator)}c")

    def highlight_json_syntax(self, text_widget, start_pos="1.0", end_pos="end"):
        """JSON sözdizimi vurgulaması uygular"""
        # Etiketleri tanımla
        text_widget.tag_configure("key", foreground=self.syntax_colors["keywords"])
        text_widget.tag_configure("string", foreground=self.syntax_colors["strings"])
        text_widget.tag_configure("number", foreground=self.syntax_colors["numbers"])
        text_widget.tag_configure("boolean", foreground=self.syntax_colors["keywords"])
        text_widget.tag_configure("null", foreground=self.syntax_colors["keywords"])
        
        # JSON anahtar kelimeleri
        keywords = ["true", "false", "null"]
        
        # Anahtar kelimeleri vurgula
        for keyword in keywords:
            pos = start_pos
            while True:
                pos = text_widget.search(r'\b' + keyword + r'\b', pos, end_pos, regexp=True)
                if not pos:
                    break
                    
                text_widget.tag_add("boolean" if keyword in ["true", "false"] else "null", 
                                  pos, f"{pos}+{len(keyword)}c")
                pos = text_widget.index(f"{pos}+{len(keyword)}c")
        
        # Sayıları vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'\b\d+(\.\d+)?([eE][+-]?\d+)?\b', pos, end_pos, regexp=True)
            if not pos:
                break
                
            number_end = text_widget.search(r'\b', pos, end_pos, regexp=True)
            if number_end:
                text_widget.tag_add("number", pos, number_end)
                pos = number_end
            else:
                pos = text_widget.index(f"{pos}+1c")
        
        # Stringleri vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'["\']', pos, end_pos, regexp=True)
            if not pos:
                break
                
            quote = text_widget.get(pos)
            string_end = text_widget.search(quote, f"{pos}+1c", end_pos)
            if string_end:
                text_widget.tag_add("string", pos, f"{string_end}+1c")
                pos = f"{string_end}+1c"
            else:
                pos = text_widget.index(f"{pos}+1c")
        
        # Anahtarları vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'["\']\s*:', pos, end_pos, regexp=True)
            if not pos:
                break
                
            key_start = text_widget.search(r'["\']', pos, end_pos, backwards=True)
            if key_start:
                text_widget.tag_add("key", key_start, pos)
                pos = text_widget.index(f"{pos}+1c")
            else:
                pos = text_widget.index(f"{pos}+1c")

    def highlight_xml_syntax(self, text_widget, start_pos="1.0", end_pos="end"):
        """XML sözdizimi vurgulaması uygular"""
        # Etiketleri tanımla
        text_widget.tag_configure("tag", foreground=self.syntax_colors["keywords"])
        text_widget.tag_configure("attribute", foreground=self.syntax_colors["attributes"])
        text_widget.tag_configure("string", foreground=self.syntax_colors["strings"])
        text_widget.tag_configure("comment", foreground=self.syntax_colors["comments"])
        text_widget.tag_configure("cdata", foreground=self.syntax_colors["strings"])
        text_widget.tag_configure("doctype", foreground=self.syntax_colors["keywords"])
        
        # XML etiketlerini vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'<[^>]+>', pos, end_pos, regexp=True)
            if not pos:
                break
                
            tag_end = text_widget.search(r'>', pos, end_pos)
            if not tag_end:
                break
                
            tag_text = text_widget.get(pos, tag_end)
            
            # Yorum etiketlerini kontrol et
            if tag_text.startswith('<!--'):
                comment_end = text_widget.search('-->', pos, end_pos)
                if comment_end:
                    text_widget.tag_add("comment", pos, f"{comment_end}+3c")
                    pos = f"{comment_end}+3c"
                    continue
            
            # CDATA bölümlerini kontrol et
            if tag_text.startswith('<![CDATA['):
                cdata_end = text_widget.search(']]>', pos, end_pos)
                if cdata_end:
                    text_widget.tag_add("cdata", pos, f"{cdata_end}+3c")
                    pos = f"{cdata_end}+3c"
                    continue
            
            # DOCTYPE tanımlamalarını kontrol et
            if tag_text.startswith('<!DOCTYPE'):
                doctype_end = text_widget.search('>', pos, end_pos)
                if doctype_end:
                    text_widget.tag_add("doctype", pos, f"{doctype_end}+1c")
                    pos = f"{doctype_end}+1c"
                    continue
            
            # Etiket adını vurgula
            tag_name_end = text_widget.search(r'[\s>]', pos, end_pos, regexp=True)
            if tag_name_end:
                text_widget.tag_add("tag", pos, tag_name_end)
                
                # Özellikleri vurgula
                attr_pos = tag_name_end
                while True:
                    attr_pos = text_widget.search(r'\s+[a-zA-Z-]+=', attr_pos, tag_end, regexp=True)
                    if not attr_pos:
                        break
                        
                    attr_name_end = text_widget.search(r'=', attr_pos, tag_end)
                    if attr_name_end:
                        text_widget.tag_add("attribute", attr_pos, attr_name_end)
                        
                        # Değeri vurgula
                        value_start = text_widget.search(r'["\']', attr_name_end, tag_end)
                        if value_start:
                            value_end = text_widget.search(r'["\']', f"{value_start}+1c", tag_end)
                            if value_end:
                                text_widget.tag_add("string", value_start, f"{value_end}+1c")
                                attr_pos = f"{value_end}+1c"
                                continue
                    
                    attr_pos = text_widget.index(f"{attr_pos}+1c")
            
            pos = f"{tag_end}+1c"

    def highlight_markdown_syntax(self, text_widget, start_pos="1.0", end_pos="end"):
        """Markdown sözdizimi vurgulaması uygular"""
        # Etiketleri tanımla
        text_widget.tag_configure("heading", foreground=self.syntax_colors["headings"])
        text_widget.tag_configure("bold", foreground=self.syntax_colors["bold"])
        text_widget.tag_configure("italic", foreground=self.syntax_colors["italic"])
        text_widget.tag_configure("code", foreground=self.syntax_colors["code"])
        text_widget.tag_configure("link", foreground=self.syntax_colors["links"])
        text_widget.tag_configure("list", foreground=self.syntax_colors["lists"])
        text_widget.tag_configure("quote", foreground=self.syntax_colors["quotes"])
        
        # Başlıkları vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'^#{1,6}\s+', pos, end_pos, regexp=True)
            if not pos:
                break
                
            line_end = text_widget.index(f"{pos} lineend")
            text_widget.tag_add("heading", pos, line_end)
            pos = line_end
        
        # Kalın metni vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'\*\*[^*]+\*\*', pos, end_pos, regexp=True)
            if not pos:
                break
                
            bold_end = text_widget.search(r'\*\*', f"{pos}+2c", end_pos)
            if bold_end:
                text_widget.tag_add("bold", pos, f"{bold_end}+2c")
                pos = f"{bold_end}+2c"
            else:
                pos = text_widget.index(f"{pos}+2c")
        
        # İtalik metni vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'\*[^*]+\*', pos, end_pos, regexp=True)
            if not pos:
                break
                
            italic_end = text_widget.search(r'\*', f"{pos}+1c", end_pos)
            if italic_end:
                text_widget.tag_add("italic", pos, f"{italic_end}+1c")
                pos = f"{italic_end}+1c"
            else:
                pos = text_widget.index(f"{pos}+1c")
        
        # Kod bloklarını vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'```', pos, end_pos, regexp=True)
            if not pos:
                break
                
            code_end = text_widget.search(r'```', f"{pos}+3c", end_pos)
            if code_end:
                text_widget.tag_add("code", pos, f"{code_end}+3c")
                pos = f"{code_end}+3c"
            else:
                pos = text_widget.index(f"{pos}+3c")
        
        # Satır içi kodları vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'`[^`]+`', pos, end_pos, regexp=True)
            if not pos:
                break
                
            code_end = text_widget.search(r'`', f"{pos}+1c", end_pos)
            if code_end:
                text_widget.tag_add("code", pos, f"{code_end}+1c")
                pos = f"{code_end}+1c"
            else:
                pos = text_widget.index(f"{pos}+1c")
        
        # Bağlantıları vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'\[[^\]]+\]\([^)]+\)', pos, end_pos, regexp=True)
            if not pos:
                break
                
            link_end = text_widget.search(r'\)', pos, end_pos)
            if link_end:
                text_widget.tag_add("link", pos, f"{link_end}+1c")
                pos = f"{link_end}+1c"
            else:
                pos = text_widget.index(f"{pos}+1c")
        
        # Listeleri vurgula
        pos = start_pos
        while True:
            # Sıralı listeler
            pos = text_widget.search(r'^\d+\.\s+', pos, end_pos, regexp=True)
            if not pos:
                break
                
            line_end = text_widget.index(f"{pos} lineend")
            text_widget.tag_add("list", pos, line_end)
            pos = line_end
            
            # Sırasız listeler
            pos = text_widget.search(r'^[-*+]\s+', pos, end_pos, regexp=True)
            if not pos:
                break
                
            line_end = text_widget.index(f"{pos} lineend")
            text_widget.tag_add("list", pos, line_end)
            pos = line_end
        
        # Alıntıları vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'^>\s+.*$', pos, end_pos, regexp=True)
            if not pos:
                break
                
            line_end = text_widget.index(f"{pos} lineend")
            text_widget.tag_add("quote", pos, line_end)
            pos = line_end

    def create_menu(self):  
        # Ana menü çubuğu  
        menubar = tk.Menu(self.root)  
          
        # Dosya menüsü  
        file_menu = tk.Menu(menubar, tearoff=0)  
        file_menu.add_command(label="Yeni", command=self.new_file, accelerator="Ctrl+N")  
        file_menu.add_command(label="Aç", command=self.open_file, accelerator="Ctrl+O")  
        file_menu.add_command(label="Kaydet", command=self.save_file, accelerator="Ctrl+S")  
        file_menu.add_command(label="Farklı Kaydet", command=self.save_as_file)  
        file_menu.add_command(label="Tümünü Kaydet", command=self.save_all_tabs, accelerator="Ctrl+Shift+S")  
        file_menu.add_separator()  
        file_menu.add_command(label="Yeni Sekme", command=lambda: self.new_tab(), accelerator="Ctrl+T")
        file_menu.add_command(label="Sekmeyi Kapat", command=lambda: self.close_tab(), accelerator="Ctrl+W")
        file_menu.add_command(label="Tüm Sekmeleri Kapat", command=self.close_all_tabs)
        file_menu.add_separator()  
        file_menu.add_command(label="Çıkış", command=self.exit_app)  
        menubar.add_cascade(label="Dosya", menu=file_menu)  
          
        # Düzenle menüsü  
        edit_menu = tk.Menu(menubar, tearoff=0)  
        edit_menu.add_command(label="Geri Al", command=self.undo, accelerator="Ctrl+Z")  
        edit_menu.add_command(label="Yinele", command=self.redo, accelerator="Ctrl+Y")  
        edit_menu.add_separator()  
        edit_menu.add_command(label="Kes", command=self.cut, accelerator="Ctrl+X")  
        edit_menu.add_command(label="Kopyala", command=self.copy, accelerator="Ctrl+C")  
        edit_menu.add_command(label="Yapıştır", command=self.paste, accelerator="Ctrl+V")  
        edit_menu.add_separator()  
        edit_menu.add_command(label="Tümünü Seç", command=self.select_all, accelerator="Ctrl+A")  
        edit_menu.add_separator()
        edit_menu.add_command(label="Ara ve Değiştir", command=self.show_search_replace, accelerator="Ctrl+F")
        menubar.add_cascade(label="Düzenle", menu=edit_menu)
        
        # Görünüm menüsü  
        view_menu = tk.Menu(menubar, tearoff=0)  
        view_menu.add_checkbutton(label="Sözdizimi Vurgulama", variable=self.syntax_highlighting_var, command=self.toggle_syntax_highlighting)  
        view_menu.add_separator()
        
        # Tema alt menüsü  
        theme_menu = tk.Menu(view_menu, tearoff=0)  
        for theme_name in self.theme_colors.keys():  
            theme_menu.add_radiobutton(  
                label=theme_name,  
                variable=self.current_theme,  
                value=theme_name,  
                command=lambda t=theme_name: self.apply_theme(t)  
            )  
        view_menu.add_cascade(label="Tema", menu=theme_menu)  
        menubar.add_cascade(label="Görünüm", menu=view_menu)
        
        # Yardım menüsü  
        help_menu = tk.Menu(menubar, tearoff=0)  
        help_menu.add_command(label="Hızlı Başlangıç Kılavuzu", command=self.show_quick_start_guide)  
        help_menu.add_command(label="Klavye Kısayolları", command=self.show_keyboard_shortcuts)  
        help_menu.add_command(label="Sık Sorulan Sorular", command=self.show_faq)  
        help_menu.add_command(label="Desteklenen Dosya Formatları", command=self.show_file_formats)  
        help_menu.add_command(label="Tema Kılavuzu", command=self.show_theme_guide)  
        help_menu.add_separator()
        help_menu.add_command(label="Performans İzleme", command=self.show_performance_guide)
        help_menu.add_command(label="Performans Raporu", command=self.show_performance_report)
        help_menu.add_separator()
        help_menu.add_command(label="Güncellemeler", command=self.show_updates)  
        help_menu.add_command(label="Hata Bildir", command=self.report_issue)  
        help_menu.add_separator()  
        help_menu.add_command(label="Hakkında", command=self.about)  
        menubar.add_cascade(label="Yardım", menu=help_menu)
        
        self.root.config(menu=menubar)

    def show_quick_start_guide(self):
        """Başlangıç kılavuzunu gösterir"""
        guide = [
            "Python Metin Editörü - Başlangıç Kılavuzu",
            "========================================",
            "",
            "1. Temel İşlemler:",
            "   • Yeni dosya açmak için: Ctrl+N",
            "   • Dosya açmak için: Ctrl+O",
            "   • Kaydetmek için: Ctrl+S",
            "   • Yeni sekme açmak için: Ctrl+T",
            "",
            "2. Metin Düzenleme:",
            "   • Geri almak için: Ctrl+Z",
            "   • İleri almak için: Ctrl+Y",
            "   • Kesmek için: Ctrl+X",
            "   • Kopyalamak için: Ctrl+C",
            "   • Yapıştırmak için: Ctrl+V",
            "",
            "3. Arama ve Değiştirme:",
            "   • Arama yapmak için: Ctrl+F",
            "   • Değiştirme yapmak için: Ctrl+H",
            "",
            "4. Tema ve Görünüm:",
            "   • Tema değiştirmek için: Biçim > Tema",
            "   • Yazı tipi değiştirmek için: Biçim > Yazı Tipi",
            "   • Sözdizimi vurgulamayı açıp kapatmak için: Biçim > Sözdizimi Vurgulama",
            "",
            "5. Sekme Yönetimi:",
            "   • Sekmeleri sürükleyip bırakarak sıralayabilirsiniz",
            "   • Sekmeyi kapatmak için: Ctrl+W",
            "   • Tüm sekmeleri kapatmak için: Dosya > Tüm Sekmeleri Kapat",
            "",
            "6. Dosya İzleme:",
            "   • Editör, açık dosyalardaki değişiklikleri otomatik olarak izler",
            "   • Dışarıdan yapılan değişiklikler için uyarı verir",
            "",
            "7. Özel Özellikler:",
            "   • Mevcut satır vurgulama",
            "   • Eşleşen parantez vurgulama",
            "   • Çoklu arama ve değiştirme",
            "   • Otomatik kaydetme kontrolü",
            "",
            "Daha fazla bilgi için diğer yardım bölümlerini inceleyebilirsiniz."
        ]
        self.show_help_window("Başlangıç Kılavuzu", guide)

    def show_keyboard_shortcuts(self):
        """Klavye kısayollarını gösterir"""
        shortcuts = [
            "Klavye Kısayolları",
            "=================",
            "",
            "Dosya İşlemleri:",
            "Ctrl+N     : Yeni dosya",
            "Ctrl+O     : Dosya aç",
            "Ctrl+S     : Kaydet",
            "Ctrl+Shift+S : Tümünü kaydet",
            "Ctrl+T     : Yeni sekme",
            "Ctrl+W     : Sekme kapat",
            "",
            "Düzenleme:",
            "Ctrl+Z     : Geri al",
            "Ctrl+Y     : İleri al",
            "Ctrl+X     : Kes",
            "Ctrl+C     : Kopyala",
            "Ctrl+V     : Yapıştır",
            "Ctrl+A     : Tümünü seç",
            "Ctrl+F     : Ara",
            "",
            "Genel:",
            "F1         : Yardım",
            "Esc        : Arama/Değiştirme penceresini kapat",
            "Enter      : Dialog pencerelerini kapat",
            "",
            "Sekme Yönetimi:",
            "Orta Tıklama : Sekmeyi kapat",
            "Sürükle-Bırak: Sekmeleri yeniden sırala"
        ]
        self.show_help_window("Klavye Kısayolları", shortcuts)

    def show_faq(self):
        """Sık sorulan soruları gösterir"""
        faq = [
            "Sık Sorulan Sorular",
            "===================",
            "",
            "1. Dosyam kaydedilmedi, nasıl kurtarabilirim?",
            "   Editör otomatik olarak değişiklikleri izler ve kapatmadan önce kaydetmenizi ister. "
            "Ancak beklenmedik bir kapanma durumunda, son oturum bilgileri kaydedilmiş olabilir.",
            "",
            "2. Sözdizimi vurgulama nasıl açılır/kapatılır?",
            "   Biçim menüsünden 'Sözdizimi Vurgulama' seçeneğini kullanabilirsiniz.",
            "",
            "3. Tema nasıl değiştirilir?",
            "   Biçim > Tema menüsünden istediğiniz temayı seçebilirsiniz.",
            "",
            "4. Dosya formatları destekleniyor?",
            "   Python, HTML, CSS, JavaScript, JSON, XML, Markdown ve düz metin dosyaları desteklenir.",
            "",
            "5. Çoklu sekme nasıl kullanılır?",
            "   Ctrl+T ile yeni sekme açabilir, sekmeleri sürükleyip bırakarak sıralayabilirsiniz.",
            "",
            "6. Arama ve değiştirme nasıl yapılır?",
            "   Ctrl+F ile arama penceresini açabilir, buradan arama ve değiştirme işlemlerini yapabilirsiniz.",
            "",
            "7. Dosya değişiklikleri nasıl izlenir?",
            "   Editör, açık dosyalardaki değişiklikleri otomatik olarak izler ve dışarıdan yapılan "
            "değişiklikler için uyarı verir.",
            "",
            "8. Yazı tipi nasıl değiştirilir?",
            "   Biçim > Yazı Tipi menüsünden yazı tipi, boyut ve stil ayarlarını yapabilirsiniz."
        ]
        self.show_help_window("Sık Sorulan Sorular", faq)

    def show_file_formats(self):
        """Desteklenen dosya formatlarını gösterir"""
        formats = [
            "Desteklenen Dosya Formatları",
            "==========================",
            "",
            "1. Python Dosyaları (.py):",
            "   • Tam sözdizimi vurgulama",
            "   • Otomatik girinti",
            "   • Python özel özellikler",
            "",
            "2. HTML Dosyaları (.html, .htm):",
            "   • HTML etiket vurgulama",
            "   • Otomatik etiket tamamlama",
            "   • HTML özel özellikler",
            "",
            "3. CSS Dosyaları (.css):",
            "   • CSS özellik vurgulama",
            "   • Renk kodları vurgulama",
            "   • CSS özel özellikler",
            "",
            "4. JavaScript Dosyaları (.js):",
            "   • JavaScript sözdizimi vurgulama",
            "   • Fonksiyon vurgulama",
            "   • JS özel özellikler",
            "",
            "5. JSON Dosyaları (.json):",
            "   • JSON sözdizimi vurgulama",
            "   • Otomatik biçimlendirme",
            "   • JSON doğrulama",
            "",
            "6. XML Dosyaları (.xml):",
            "   • XML etiket vurgulama",
            "   • XML doğrulama",
            "   • XML özel özellikler",
            "",
            "7. Markdown Dosyaları (.md):",
            "   • Markdown sözdizimi vurgulama",
            "   • Başlık vurgulama",
            "   • Bağlantı vurgulama",
            "",
            "8. Metin Dosyaları (.txt):",
            "   • Temel metin düzenleme",
            "   • Satır numaraları",
            "   • Kelime kaydırma"
        ]
        self.show_help_window("Desteklenen Dosya Formatları", formats)

    def show_theme_guide(self):
        """Tema rehberini gösterir"""
        themes = [
            "Tema Rehberi",
            "============",
            "",
            "1. Açık Tema:",
            "   • Beyaz arka plan",
            "   • Siyah metin",
            "   • Gün ışığında kullanım için ideal",
            "",
            "2. Koyu Tema:",
            "   • Koyu arka plan",
            "   • Beyaz metin",
            "   • Gece kullanımı için ideal",
            "",
            "3. Sepya Tema:",
            "   • Kahverengi tonları",
            "   • Göz yorgunluğunu azaltır",
            "   • Uzun süreli kullanım için ideal",
            "",
            "4. Monokai:",
            "   • Koyu arka plan",
            "   • Canlı renkler",
            "   • Yüksek kontrast",
            "",
            "5. Dracula:",
            "   • Mor tonları",
            "   • Modern görünüm",
            "   • Popüler tema",
            "",
            "6. Solarized Dark:",
            "   • Koyu arka plan",
            "   • Pastel renkler",
            "   • Bilimsel çalışmalar için ideal",
            "",
            "7. Nord:",
            "   • Arktik renk paleti",
            "   • Soğuk tonlar",
            "   • Minimalist tasarım",
            "",
            "8. GitHub:",
            "   • GitHub benzeri görünüm",
            "   • Tanıdık arayüz",
            "   • Geliştiriciler için ideal",
            "",
            "9. One Dark:",
            "   • Atom editör teması",
            "   • Koyu arka plan",
            "   • Canlı renkler",
            "",
            "10. Tokyo Night:",
            "    • Japon gece teması",
            "    • Mavi tonları",
            "    • Modern görünüm"
        ]
        self.show_help_window("Tema Rehberi", themes)

    def show_updates(self):
        """Güncelleme bilgilerini gösterir"""
        updates = [
            "Güncelleme Geçmişi",
            "================",
            "",
            "Sürüm 1.3.0 (2025):",
            "• Performans izleme sistemi eklendi",
            "• Otomatik dosya yedekleme özelliği",
            "• Gelişmiş hata yakalama ve raporlama",
            "• Bellek kullanımı optimizasyonları",
            "• Yeni tema: Tokyo Night",
            "",
            "Sürüm 1.2.0 (2025):",
            "• Yeni temalar eklendi (Nord, GitHub, One Dark)",
            "• Gelişmiş arama ve değiştirme özellikleri",
            "• Dosya izleme sistemi iyileştirildi",
            "• Performans optimizasyonları",
            "• Çoklu dosya kodlama desteği",
            "",
            "Sürüm 1.1.0 (2025):",
            "• Çoklu sekme desteği",
            "• Sözdizimi vurgulama",
            "• Tema sistemi",
            "• Klavye kısayolları",
            "• Dosya önizleme",
            "• Sekme sürükle-bırak desteği",
            "",
            "Sürüm 1.0.0 (2025):",
            "• İlk sürüm",
            "• Temel metin düzenleme",
            "• Dosya işlemleri",
            "• Basit arayüz",
            "• Temel tema desteği",
        ]
        self.show_help_window("Güncellemeler", updates)

    def report_issue(self):
        """Hata bildirimi penceresini gösterir"""
        report = [
            "Hata Bildirimi",
            "=============",
            "",
            "Bir hata veya sorunla karşılaştıysanız, lütfen aşağıdaki bilgileri içeren bir bildirim gönderin:",
            "",
            "1. Hatanın açıklaması:",
            "   • Ne yapmaya çalışıyordunuz?",
            "   • Beklenen davranış neydi?",
            "   • Gerçekleşen davranış ne oldu?",
            "",
            "2. Teknik bilgiler:",
            "   • İşletim sistemi:",
            "   • Python sürümü:",
            "   • Editör sürümü:",
            "",
            "3. Hata mesajları:",
            "   • Varsa hata mesajlarını ekleyin",
            "   • Ekran görüntüleri ekleyin",
            "",
            "4. Adımlar:",
            "   • Hatayı yeniden oluşturmak için adımları listeleyin",
            "",
            "Bildiriminizi göndermek için:",
            "• GitHub Issues sayfasını kullanın",
            "• E-posta ile bildirin",
            "• Geliştirici ekibiyle iletişime geçin"
        ]
        self.show_help_window("Hata Bildirimi", report)

    def show_help_window(self, title, content):
        """Yardım penceresini gösterir"""
        help_window = tk.Toplevel(self.root)
        help_window.title(title)
        help_window.geometry("600x500")
        help_window.resizable(True, True)
        
        # Ana çerçeve
        main_frame = tk.Frame(help_window, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Başlık
        title_label = tk.Label(
            main_frame,
            text=title,
            font=("Segoe UI", 14, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # İçerik için metin alanı
        text_widget = tk.Text(
            main_frame,
            wrap=tk.WORD,
            width=70,
            height=25,
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Kaydırma çubuğu
        scrollbar = tk.Scrollbar(text_widget)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=text_widget.yview)
        
        # İçeriği ekle
        for line in content:
            text_widget.insert(tk.END, line + "\n")
        
        # Metin alanını salt okunur yap
        text_widget.configure(state=tk.DISABLED)
        
        # Kapat butonu
        close_button = tk.Button(
            main_frame,
            text="Kapat",
            command=help_window.destroy,
            width=10,
            font=("Segoe UI", 10)
        )
        close_button.pack(pady=(10, 0))
        
        # Pencereyi ortala
        help_window.update_idletasks()
        width = help_window.winfo_width()
        height = help_window.winfo_height()
        x = (help_window.winfo_screenwidth() // 2) - (width // 2)
        y = (help_window.winfo_screenheight() // 2) - (height // 2)
        help_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Enter tuşu ile kapat
        help_window.bind("<Return>", lambda e: help_window.destroy())
        help_window.bind("<Escape>", lambda e: help_window.destroy())
        
        # Pencereyi modal yap
        help_window.transient(self.root)
        help_window.grab_set()
        self.root.wait_window(help_window)

    def new_file(self):
        """Yeni bir dosya açar"""
        self.new_tab()
        
    def open_file(self):
        """Dosya açma diyaloğunu gösterir ve seçilen dosyayı açar"""
        start_time = time.time()
        try:
            # Son açılan dizini al
            initial_dir = os.path.expanduser("~")
            if hasattr(self, 'last_directory') and self.last_directory:
                initial_dir = self.last_directory

            # Dosya açma diyaloğu
            file_path = filedialog.askopenfilename(
                initialdir=initial_dir,
                title="Dosya Aç",
                filetypes=[
                    ("Python Dosyaları", "*.py"),
                    ("Metin Dosyaları", "*.txt"),
                    ("HTML Dosyaları", "*.html;*.htm"),
                    ("CSS Dosyaları", "*.css"),
                    ("JavaScript Dosyaları", "*.js"),
                    ("JSON Dosyaları", "*.json"),
                    ("XML Dosyaları", "*.xml"),
                    ("Markdown Dosyaları", "*.md"),
                    ("Tüm Dosyalar", "*.*")
                ]
            )
            
            if file_path:
                # Performans metriklerini güncelle
                duration = time.time() - start_time
                self.performance_monitor.record_response_time("open_file", duration)
                self.performance_monitor.update_usage_stats("files_opened")
                
                # Son açılan dizini güncelle
                self.last_directory = os.path.dirname(file_path)
                
                # Dosya zaten açık mı kontrol et
                for tab_id, tab_info in self.tabs.items():
                    if tab_info["file_path"] == file_path:
                        # Dosya zaten açıksa o sekmeye geç
                        self.notebook.select(tab_info["frame"])
                        self.current_tab = tab_id
                        return True
                
                try:
                    # Dosya kodlamasını tespit et
                    encodings = ['utf-8', 'cp1254', 'latin1', 'ascii']
                    content = None
                    encoding_used = None
                    
                    for encoding in encodings:
                        try:
                            with open(file_path, 'r', encoding=encoding) as file:
                                content = file.read()
                                encoding_used = encoding
                                break
                        except UnicodeDecodeError:
                            continue
                    
                    if content is None:
                        # Hiçbir kodlama çalışmazsa binary modda oku
                        with open(file_path, 'rb') as file:
                            content = file.read()
                            # Binary içeriği hex formatında göster
                            content = ' '.join(f'{b:02x}' for b in content)
                            messagebox.showwarning(
                                "Uyarı",
                                "Dosya metin formatında değil. Binary içerik hex formatında gösteriliyor."
                            )
                    
                    # Yeni sekme oluştur
                    tab_id = self.new_tab(file_path)
                    text_widget = self.tabs[tab_id]["text_widget"]
                    
                    # İçeriği ekle
                    text_widget.insert(1.0, content)
                    
                    # Sözdizimi vurgulaması uygula
                    if self.syntax_highlighting:
                        syntax_start = time.time()
                        self.apply_syntax_highlighting_to_tab(tab_id)
                        syntax_duration = time.time() - syntax_start
                        self.performance_monitor.update_usage_stats("syntax_highlighting_time", syntax_duration)
                    
                    # Dosya izleme başlat
                    self.start_file_watching(tab_id, file_path)
                    
                    return True
                    
                except Exception as e:
                    self.performance_monitor.record_error("Dosya Açma Hatası", str(e))
                    messagebox.showerror(
                        "Hata",
                        f"Dosya açılırken hata oluştu:\n{str(e)}"
                    )
                    return False
            return False
            
        except Exception as e:
            self.performance_monitor.record_error("Dosya Açma Hatası", str(e))
            return False

    def format_file_size(self, size):
        """Dosya boyutunu okunabilir formata dönüştürür"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def format_date(self, timestamp):
        """Zaman damgasını okunabilir formata dönüştürür"""
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime('%d.%m.%Y %H:%M:%S')

    def start_file_watching(self, tab_id, file_path):
        """Dosya değişikliklerini izlemeye başlar"""
        if not hasattr(self, 'file_watchers'):
            self.file_watchers = {}
            
        # Önceki izleyiciyi kaldır
        if tab_id in self.file_watchers:
            self.root.after_cancel(self.file_watchers[tab_id])
            
        def check_file_changes():
            """Dosya değişikliklerini kontrol eder"""
            if tab_id not in self.tabs:
                return
                
            try:
                current_mtime = os.path.getmtime(file_path)
                if hasattr(self, 'last_mtime') and self.last_mtime.get(tab_id) != current_mtime:
                    # Dosya değişmiş, kullanıcıya sor
                    response = messagebox.askyesno(
                        "Dosya Değişti",
                        f"{os.path.basename(file_path)} dosyası dışarıdan değiştirildi. "
                        "Yeniden yüklemek ister misiniz?"
                    )
                    
                    if response:
                        # Dosyayı yeniden yükle
                        with open(file_path, 'r', encoding='utf-8') as file:
                            content = file.read()
                            text_widget = self.tabs[tab_id]["text_widget"]
                            text_widget.delete(1.0, tk.END)
                            text_widget.insert(1.0, content)
                            self.tabs[tab_id]["saved"] = True
                            self.update_tab_title(tab_id)
                            
                            # Sözdizimi vurgulamasını yeniden uygula
                            if self.syntax_highlighting:
                                self.apply_syntax_highlighting_to_tab(tab_id)
                    
                self.last_mtime[tab_id] = current_mtime
                
            except Exception:
                # Dosya silinmiş veya erişilemez
                pass
                
            # İzlemeyi devam ettir
            self.file_watchers[tab_id] = self.root.after(1000, check_file_changes)
            
        # İlk kontrolü başlat
        if not hasattr(self, 'last_mtime'):
            self.last_mtime = {}
        self.last_mtime[tab_id] = os.path.getmtime(file_path)
        self.file_watchers[tab_id] = self.root.after(1000, check_file_changes)
        
    def save_file(self):
        """Mevcut dosyayı kaydeder"""
        start_time = time.time()
        try:
            tab_id = self.get_current_tab()
            if tab_id:
                result = self.save_tab(tab_id)
                if result:
                    duration = time.time() - start_time
                    self.performance_monitor.record_response_time("save_file", duration)
                    self.performance_monitor.update_usage_stats("files_saved")
                return result
            return False
        except Exception as e:
            self.performance_monitor.record_error("Dosya Kaydetme Hatası", str(e))
            return False
        
    def save_as_file(self):
        """Dosyayı farklı kaydeder"""
        tab_id = self.get_current_tab()
        if tab_id:
            return self.save_tab_as(tab_id)
        return False
        
    def exit_app(self):
        """Uygulamadan çıkar"""
        # Performans izlemeyi durdur
        self.performance_monitor.stop_monitoring()
        
        # Tüm sekmeleri kapat
        if self.close_all_tabs():
            self.root.destroy()
        
    def undo(self):
        """Son işlemi geri alır"""
        text_widget = self.get_current_text_widget()
        if text_widget:
            try:
                text_widget.edit_undo()
            except tk.TclError:
                pass
                
    def redo(self):
        """Son geri alınan işlemi tekrarlar"""
        text_widget = self.get_current_text_widget()
        if text_widget:
            try:
                text_widget.edit_redo()
            except tk.TclError:
                pass
                
    def cut(self):
        """Seçili metni keser"""
        text_widget = self.get_current_text_widget()
        if text_widget:
            try:
                text_widget.event_generate("<<Cut>>")
            except tk.TclError:
                pass
                
    def copy(self):
        """Seçili metni kopyalar"""
        text_widget = self.get_current_text_widget()
        if text_widget:
            try:
                text_widget.event_generate("<<Copy>>")
            except tk.TclError:
                pass
                
    def paste(self):
        """Pano içeriğini yapıştırır"""
        text_widget = self.get_current_text_widget()
        if text_widget:
            try:
                text_widget.event_generate("<<Paste>>")
            except tk.TclError:
                pass
                
    def select_all(self):
        """Tüm metni seçer"""
        text_widget = self.get_current_text_widget()
        if text_widget:
            text_widget.tag_add(tk.SEL, "1.0", tk.END)
            text_widget.mark_set(tk.INSERT, "1.0")
            text_widget.see(tk.INSERT)
            return 'break'
            
    def bind_shortcuts(self):
        """Klavye kısayollarını bağlar"""
        self.root.bind("<Control-n>", lambda e: self.new_file())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-Shift-S>", lambda e: self.save_all_tabs())
        self.root.bind("<Control-t>", lambda e: self.new_tab())
        self.root.bind("<Control-w>", lambda e: self.close_tab())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<Control-x>", lambda e: self.cut())
        self.root.bind("<Control-c>", lambda e: self.copy())
        self.root.bind("<Control-v>", lambda e: self.paste())
        self.root.bind("<Control-a>", lambda e: self.select_all())
        self.root.bind("<Control-f>", lambda e: self.show_search_replace())
        self.root.bind("<F1>", lambda e: self.show_quick_start_guide())
        
    def apply_theme(self, theme_name):
        """Temayı uygular"""
        if theme_name not in self.theme_colors:
            return
            
        self.current_theme.set(theme_name)
        theme = self.theme_colors[theme_name]
        
        # Ana pencere
        self.root.configure(bg=theme["bg"])
        
        # Notebook
        self.style.configure("TNotebook", background=theme["bg"])
        self.style.configure("TNotebook.Tab", 
                           background="#ffffff",
                           foreground="#000000",
                           padding=[5, 2])
        self.style.map("TNotebook.Tab",
            background=[("selected", "#ffffff")],
            foreground=[("selected", "#000000")]
        )
        
        # Menü
        for menu in [self.root.nametowidget(menu) for menu in self.root.winfo_children() if isinstance(self.root.nametowidget(menu), tk.Menu)]:
            menu.configure(
                bg=theme["menu_bg"],
                fg=theme["menu_fg"],
                activebackground=theme["menu_active_bg"],
                activeforeground=theme["menu_active_fg"]
            )
        
        # Durum çubuğu
        self.status_bar.config(bg=theme["status_bar_bg"], fg=theme["status_bar_fg"])
        self.theme_label.config(text=f"Tema: {self.theme_names[theme_name]}")
        
        # Tüm sekmeleri güncelle
        for tab_id in self.tabs:
            self.apply_theme_to_tab(tab_id)
            
            # Kapatma butonlarını güncelle
            close_button = self.tabs[tab_id]["close_button"]
            close_frame = self.tabs[tab_id]["close_frame"]
            inner_close_button = self.tabs[tab_id]["inner_close_button"]
            inner_close_frame = self.tabs[tab_id]["inner_close_frame"]
            title_label = self.tabs[tab_id]["title_label"]
            
            # Başlık etiketini güncelle
            if isinstance(title_label, tk.Label):
                title_label.configure(
                    bg=theme["bg"],
                    fg=theme["fg"],
                    font=("Segoe UI", 9)
                )
            else:
                # Eğer ttk.Label ise, yeni bir tk.Label oluştur ve eskisini değiştir
                new_title_label = tk.Label(
                    title_label.master,
                    text=title_label.cget("text"),
                    font=("Segoe UI", 9),
                    bg=theme["bg"],
                    fg=theme["fg"]
                )
                new_title_label.pack(side=tk.LEFT, padx=(5, 0))
                title_label.destroy()
                self.tabs[tab_id]["title_label"] = new_title_label
                title_label = new_title_label
            
            # Kapatma butonu rengini güncelle
            if isinstance(close_button, tk.Label):
                close_button.configure(
                    bg=theme["bg"],
                    fg=theme["fg"]
                )
            if isinstance(close_frame, tk.Frame):
                close_frame.configure(bg=theme["bg"])
            if isinstance(inner_close_button, tk.Label):
                inner_close_button.configure(
                    bg=theme["bg"],
                    fg=theme["fg"]
                )
            if isinstance(inner_close_frame, tk.Frame):
                inner_close_frame.configure(
                    bg=theme["bg"],
                    highlightbackground=theme["fg"]
                )
            
            # Hover efektlerini güncelle
            def on_enter(e, btn=close_button, frame=close_frame):
                if isinstance(btn, tk.Label):
                    btn.configure(fg="#e74c3c", bg=theme["menu_active_bg"])
                if isinstance(frame, tk.Frame):
                    frame.configure(bg=theme["menu_active_bg"])
                
            def on_leave(e, btn=close_button, frame=close_frame):
                if isinstance(btn, tk.Label):
                    btn.configure(fg=theme["fg"], bg=theme["bg"])
                if isinstance(frame, tk.Frame):
                    frame.configure(bg=theme["bg"])
                
            def on_inner_enter(e, btn=inner_close_button, frame=inner_close_frame):
                if isinstance(btn, tk.Label):
                    btn.configure(fg="#e74c3c", bg=theme["menu_active_bg"])
                if isinstance(frame, tk.Frame):
                    frame.configure(bg=theme["menu_active_bg"], highlightbackground="#e74c3c")
                
            def on_inner_leave(e, btn=inner_close_button, frame=inner_close_frame):
                if isinstance(btn, tk.Label):
                    btn.configure(fg=theme["fg"], bg=theme["bg"])
                if isinstance(frame, tk.Frame):
                    frame.configure(bg=theme["bg"], highlightbackground=theme["fg"])
                
            # Olayları yeniden bağla
            if isinstance(close_button, tk.Label):
                close_button.bind("<Enter>", on_enter)
                close_button.bind("<Leave>", on_leave)
            if isinstance(close_frame, tk.Frame):
                close_frame.bind("<Enter>", on_enter)
                close_frame.bind("<Leave>", on_leave)
            
            if isinstance(inner_close_button, tk.Label):
                inner_close_button.bind("<Enter>", on_inner_enter)
                inner_close_button.bind("<Leave>", on_inner_leave)
            if isinstance(inner_close_frame, tk.Frame):
                inner_close_frame.bind("<Enter>", on_inner_enter)
                inner_close_frame.bind("<Leave>", on_inner_leave)
            
    def toggle_syntax_highlighting(self):
        """Sözdizimi vurgulamasını açıp kapatır"""
        self.syntax_highlighting = not self.syntax_highlighting
        
        if self.syntax_highlighting:
            # Tüm sekmelere sözdizimi vurgulaması uygula
            for tab_id in self.tabs:
                self.apply_syntax_highlighting_to_tab(tab_id)
        else:
            # Tüm sekmelerden sözdizimi vurgulamasını kaldır
            for tab_id in self.tabs:
                text_widget = self.tabs[tab_id]["text_widget"]
                for tag in ["keyword", "string", "comment", "number", "operator", "method", "class", "library"]:
                    text_widget.tag_remove(tag, "1.0", tk.END)
                    
    def on_key_release(self, event):
        """Tuş bırakıldığında çağrılan fonksiyon"""
        self.update_status_bar()
        self.highlight_current_line()
        self.matching_brackets()
        
        # Kaydedilmemiş değişiklikleri işaretle
        tab_id = self.get_current_tab()
        if tab_id:
            # Sadece gerçek değişikliklerde işaretle
            text_widget = self.tabs[tab_id]["text_widget"]
            current_content = text_widget.get("1.0", "end-1c")
            
            # Eğer dosya varsa, orijinal içerikle karşılaştır
            if self.tabs[tab_id]["file_path"]:
                try:
                    with open(self.tabs[tab_id]["file_path"], 'r', encoding='utf-8') as file:
                        original_content = file.read()
                        if current_content != original_content:
                            self.tabs[tab_id]["saved"] = False
                            self.update_tab_title(tab_id)
                except:
                    self.tabs[tab_id]["saved"] = False
                    self.update_tab_title(tab_id)
            else:
                # Yeni dosya için, içerik boş değilse işaretle
                if current_content.strip():
                    self.tabs[tab_id]["saved"] = False
                    self.update_tab_title(tab_id)
        
    def on_button_release(self, event):
        """Fare düğmesi bırakıldığında çağrılan fonksiyon"""
        self.update_status_bar()
        self.highlight_current_line()
        self.matching_brackets()
        
    def on_scroll(self, event=None):
        """Kaydırma olayını işler"""
        pass
        
    def highlight_current_line(self):
        """Mevcut satırı vurgular"""
        text_widget = self.get_current_text_widget()
        if text_widget:
            text_widget.tag_remove("current_line", 1.0, "end")
            text_widget.tag_add("current_line", "insert linestart", "insert lineend+1c")
            
    def matching_brackets(self):
        """Eşleşen parantezleri vurgular"""
        text_widget = self.get_current_text_widget()
        if not text_widget:
            return
            
        text_widget.tag_remove("bracket_highlight", "1.0", "end")

        pos = text_widget.index("insert")
        char = text_widget.get(f"{pos} -1c")

        brackets = {"(": ")", "[": "]", "{": "}"}
        reverse_brackets = {")": "(", "]": "[", "}": "{"}

        if char in brackets:
            # Eşleşen karakteri sağda ara
            match = text_widget.search(brackets[char], pos, stopindex="end", forwards=True)
            if match:
                text_widget.tag_add("bracket_highlight", f"{pos} -1c", pos)
                text_widget.tag_add("bracket_highlight", match, f"{match} +1c")
        elif char in reverse_brackets:
            # Eşleşen karakteri solda ara
            match = text_widget.search(reverse_brackets[char], pos, stopindex="1.0", backwards=True)
            if match:
                text_widget.tag_add("bracket_highlight", f"{pos} -1c", pos)
                text_widget.tag_add("bracket_highlight", match, f"{match} +1c")
                
    def update_status_bar(self, event=None):
        """Durum çubuğunu günceller"""
        text_widget = self.get_current_text_widget()
        if not text_widget:
            return
            
        cursor_position = text_widget.index(tk.INSERT)
        line, column = cursor_position.split('.')
        
        # Toplam satır sayısını al
        total_lines = text_widget.index('end-1c').split('.')[0]
        
        # Seçili metin varsa karakter sayısını al
        try:
            selected_text = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            char_count = len(selected_text)
            status_text = f"Satır: {line}/{total_lines} | Sütun: {column} | Seçili: {char_count} karakter"
        except tk.TclError:
            status_text = f"Satır: {line}/{total_lines} | Sütun: {column}"
        
        self.status_bar.config(text=status_text)
        
        # Başlıkta değişiklik olduğunu göster
        tab_id = self.get_current_tab()
        if tab_id:
            tab_info = self.tabs[tab_id]
            if tab_info["file_path"]:
                if not self.root.title().startswith("*") and not tab_info["saved"]:
                    self.root.title(f"*{os.path.basename(tab_info['file_path'])} - Python Metin Editörü")
                    
        # Sözdizimi vurgulaması etkinse, metin değiştiğinde yeniden uygula
        if self.syntax_highlighting and event is not None:
            self.apply_syntax_highlighting_to_tab(tab_id)

    def about(self):
        """Hakkında penceresini gösterir"""
        features = [
            "Temel Özellikler:",
            "✓ Çoklu sekme desteği",
            "✓ Dosya işlemleri (Aç, Kaydet, Farklı Kaydet)",
            "✓ Sürükle-bırak sekme yönetimi",
            "✓ Dosya değişiklik izleme",
            "✓ Otomatik kaydetme kontrolü",
            "",
            "Düzenleme Özellikleri:",
            "✓ Geri al/İleri al",
            "✓ Kes/Kopyala/Yapıştır",
            "✓ Tümünü seç",
            "✓ Arama ve değiştirme",
            "✓ Çoklu arama",
            "",
            "Görsel Özellikler:",
            "✓ 10 farklı tema",
            "✓ Sözdizimi vurgulama",
            "✓ Satır numaraları",
            "✓ Mevcut satır vurgulama",
            "✓ Eşleşen parantez vurgulama",
            "",
            "Dosya Desteği:",
            "✓ Python (.py)",
            "✓ Metin (.txt)",
            "✓ HTML (.html, .htm)",
            "✓ CSS (.css)",
            "✓ JavaScript (.js)",
            "✓ JSON (.json)",
            "✓ XML (.xml)",
            "✓ Markdown (.md)",
            "",
            "Klavye Kısayolları:",
            "✓ Ctrl+N: Yeni dosya",
            "✓ Ctrl+O: Dosya aç",
            "✓ Ctrl+S: Kaydet",
            "✓ Ctrl+T: Yeni sekme",
            "✓ Ctrl+W: Sekme kapat",
            "✓ Ctrl+F: Ara",
            "✓ Ctrl+A: Tümünü seç",
            "",
            "Sürüm Bilgileri:",
            "✓ Sürüm: 1.2.0",
            "✓ Son Güncelleme: 2024",
            "✓ Python Sürümü: 3.x",
            "✓ Tkinter Tema: Modern",
            "",
            "Geliştirici: Python Metin Editörü Ekibi"
        ]
        
        # Özel hakkında penceresi
        about_window = tk.Toplevel(self.root)
        about_window.title("Hakkında")
        about_window.geometry("500x600")
        about_window.resizable(False, False)
        
        # Ana çerçeve
        main_frame = tk.Frame(about_window, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Başlık
        title_label = tk.Label(
            main_frame,
            text="Python Metin Editörü",
            font=("Segoe UI", 16, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Özellikler için metin alanı
        text_widget = tk.Text(
            main_frame,
            wrap=tk.WORD,
            width=50,
            height=25,
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Özellikleri ekle
        for feature in features:
            text_widget.insert(tk.END, feature + "\n")
        
        # Metin alanını salt okunur yap
        text_widget.configure(state=tk.DISABLED)
        
        # Kapat butonu
        close_button = tk.Button(
            main_frame,
            text="Kapat",
            command=about_window.destroy,
            width=10,
            font=("Segoe UI", 10)
        )
        close_button.pack(pady=(10, 0))
        
        # Pencereyi ortala
        about_window.update_idletasks()
        width = about_window.winfo_width()
        height = about_window.winfo_height()
        x = (about_window.winfo_screenwidth() // 2) - (width // 2)
        y = (about_window.winfo_screenheight() // 2) - (height // 2)
        about_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Enter tuşu ile kapat
        about_window.bind("<Return>", lambda e: about_window.destroy())
        about_window.bind("<Escape>", lambda e: about_window.destroy())
        
        # Pencereyi modal yap
        about_window.transient(self.root)
        about_window.grab_set()
        self.root.wait_window(about_window)

    def create_status_bar(self):
        """Durum çubuğunu oluşturur"""
        self.status_bar = tk.Label(
            self.root,
            text="Satır: 1/1 | Sütun: 1",
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.W,
            font=("Segoe UI", 9)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Tema etiketi
        self.theme_label = tk.Label(
            self.status_bar,
            text="Tema: Açık",
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.E,
            font=("Segoe UI", 9)
        )
        self.theme_label.pack(side=tk.RIGHT, padx=5)

    def show_search_replace(self):
        """Arama ve değiştirme çerçevesini gösterir"""
        if self.search_frame is None:
            # Arama çerçevesi
            self.search_frame = tk.Frame(self.root)
            self.search_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
            
            # Ana çerçeve
            main_frame = tk.Frame(self.search_frame)
            main_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # Sol panel (arama ve değiştirme alanları)
            left_frame = tk.Frame(main_frame)
            left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # Arama alanı
            search_frame = tk.Frame(left_frame)
            search_frame.pack(fill=tk.X, pady=(0, 5))
            
            search_label = tk.Label(
                search_frame,
                text="Ara:",
                font=("Segoe UI", 9),
                width=8,
                anchor="w"
            )
            search_label.pack(side=tk.LEFT, padx=(0, 5))
            
            # Arama giriş alanı için çerçeve
            search_entry_frame = tk.Frame(search_frame, bd=1, relief=tk.SOLID)
            search_entry_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            self.search_text = tk.Entry(
                search_entry_frame,
                font=("Segoe UI", 9),
                width=30,
                bd=0,
                highlightthickness=0
            )
            self.search_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
            
            # Arama kısayolu etiketi
            search_shortcut = tk.Label(
                search_entry_frame,
                text="Ctrl+F",
                font=("Segoe UI", 8),
                fg="gray"
            )
            search_shortcut.pack(side=tk.RIGHT, padx=2)
            
            # Değiştirme alanı
            replace_frame = tk.Frame(left_frame)
            replace_frame.pack(fill=tk.X)
            
            replace_label = tk.Label(
                replace_frame,
                text="Değiştir:",
                font=("Segoe UI", 9),
                width=8,
                anchor="w"
            )
            replace_label.pack(side=tk.LEFT, padx=(0, 5))
            
            # Değiştirme giriş alanı için çerçeve
            replace_entry_frame = tk.Frame(replace_frame, bd=1, relief=tk.SOLID)
            replace_entry_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            self.replace_text = tk.Entry(
                replace_entry_frame,
                font=("Segoe UI", 9),
                width=30,
                bd=0,
                highlightthickness=0
            )
            self.replace_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
            
            # Değiştirme kısayolu etiketi
            replace_shortcut = tk.Label(
                replace_entry_frame,
                text="Ctrl+H",
                font=("Segoe UI", 8),
                fg="gray"
            )
            replace_shortcut.pack(side=tk.RIGHT, padx=2)
            
            # Sağ panel (butonlar)
            right_frame = tk.Frame(main_frame)
            right_frame.pack(side=tk.RIGHT, padx=(10, 0))
            
            # Modern butonlar için stil
            button_style = {
                "font": ("Segoe UI", 9),
                "relief": tk.FLAT,
                "padx": 12,
                "pady": 4,
                "cursor": "hand2",
                "bd": 0
            }
            
            # Arama butonu
            search_btn = tk.Button(
                right_frame,
                text="Ara",
                command=self.search_text_in_current_tab,
                bg="#0078d7",
                fg="white",
                activebackground="#106ebe",
                activeforeground="white",
                **button_style
            )
            search_btn.pack(side=tk.TOP, pady=(0, 5))
            
            # Değiştir butonu
            replace_btn = tk.Button(
                right_frame,
                text="Değiştir",
                command=self.replace_text_in_current_tab,
                bg="#f0f0f0",
                fg="black",
                activebackground="#e1e1e1",
                activeforeground="black",
                **button_style
            )
            replace_btn.pack(side=tk.TOP, pady=(0, 5))
            
            # Tümünü değiştir butonu
            replace_all_btn = tk.Button(
                right_frame,
                text="Tümünü Değiştir",
                command=self.replace_all_text_in_current_tab,
                bg="#f0f0f0",
                fg="black",
                activebackground="#e1e1e1",
                activeforeground="black",
                **button_style
            )
            replace_all_btn.pack(side=tk.TOP, pady=(0, 5))
            
            # Kapat butonu
            close_btn = tk.Button(
                right_frame,
                text="Kapat",
                command=self.hide_search_replace,
                bg="#f0f0f0",
                fg="black",
                activebackground="#e1e1e1",
                activeforeground="black",
                **button_style
            )
            close_btn.pack(side=tk.TOP)
            
            # Tooltips ekle
            def create_tooltip(widget, text):
                def show_tooltip(event):
                    tooltip = tk.Toplevel()
                    tooltip.wm_overrideredirect(True)
                    tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
                    
                    label = tk.Label(
                        tooltip,
                        text=text,
                        justify=tk.LEFT,
                        background="#ffffe0",
                        relief=tk.SOLID,
                        borderwidth=1,
                        font=("Segoe UI", 8)
                    )
                    label.pack()
                    
                    def hide_tooltip():
                        tooltip.destroy()
                    
                    widget.tooltip = tooltip
                    widget.bind("<Leave>", lambda e: hide_tooltip())
                
                widget.bind("<Enter>", show_tooltip)
            
            create_tooltip(search_btn, "Metinde ara (Ctrl+F)")
            create_tooltip(replace_btn, "Seçili metni değiştir (Ctrl+H)")
            create_tooltip(replace_all_btn, "Tüm eşleşmeleri değiştir")
            create_tooltip(close_btn, "Arama penceresini kapat (Esc)")
            
            # Tema uyumluluğu için renkleri güncelle
            def update_colors():
                theme = self.theme_colors[self.current_theme.get()]
                main_frame.configure(bg=theme["bg"])
                left_frame.configure(bg=theme["bg"])
                search_frame.configure(bg=theme["bg"])
                replace_frame.configure(bg=theme["bg"])
                right_frame.configure(bg=theme["bg"])
                
                search_label.configure(
                    bg=theme["bg"],
                    fg=theme["fg"]
                )
                replace_label.configure(
                    bg=theme["bg"],
                    fg=theme["fg"]
                )
                
                search_entry_frame.configure(bg=theme["bg"])
                replace_entry_frame.configure(bg=theme["bg"])
                
                self.search_text.configure(
                    bg=theme["bg"],
                    fg=theme["fg"],
                    insertbackground=theme["fg"]
                )
                self.replace_text.configure(
                    bg=theme["bg"],
                    fg=theme["fg"],
                    insertbackground=theme["fg"]
                )
                
                # Buton renklerini güncelle
                for btn in [search_btn, replace_btn, replace_all_btn, close_btn]:
                    if btn == search_btn:
                        btn.configure(
                            bg=theme["menu_active_bg"],
                            fg=theme["menu_active_fg"],
                            activebackground=theme["menu_active_bg"],
                            activeforeground=theme["menu_active_fg"]
                        )
                    else:
                        btn.configure(
                            bg=theme["menu_bg"],
                            fg=theme["menu_fg"],
                            activebackground=theme["menu_active_bg"],
                            activeforeground=theme["menu_active_fg"]
                        )
            
            # İlk renk güncellemesini yap
            update_colors()
            
            # Tema değişikliğinde renkleri güncelle
            self.root.bind("<<ThemeChanged>>", lambda e: update_colors())
            
            # Arama giriş alanına odaklan
            self.search_text.focus_set()
            
            # Enter tuşu ile arama yap
            self.search_text.bind("<Return>", lambda e: self.search_text_in_current_tab())
            self.replace_text.bind("<Return>", lambda e: self.replace_text_in_current_tab())
            
            # Escape tuşu ile kapat
            self.search_frame.bind("<Escape>", lambda e: self.hide_search_replace())
        else:
            self.search_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
            self.search_text.focus_set()
            
    def hide_search_replace(self):
        """Arama ve değiştirme çerçevesini gizler"""
        if self.search_frame:
            self.search_frame.pack_forget()
            
    def search_text_in_current_tab(self):
        """Mevcut sekmede metin arar"""
        start_time = time.time()
        try:
            text_widget = self.get_current_text_widget()
            if not text_widget or not self.search_text.get():
                return
                
            # Önceki aramayı temizle
            text_widget.tag_remove("search", "1.0", tk.END)
            
            # Aramayı başlat
            start_pos = "1.0"
            while True:
                start_pos = text_widget.search(self.search_text.get(), start_pos, tk.END, nocase=True)
                if not start_pos:
                    break
                    
                end_pos = f"{start_pos}+{len(self.search_text.get())}c"
                text_widget.tag_add("search", start_pos, end_pos)
                start_pos = end_pos
                
            # Arama sonuçlarını vurgula
            theme = self.theme_colors[self.current_theme.get()]
            text_widget.tag_config("search", background=theme["search_highlight_bg"], foreground=theme["search_highlight_fg"])
            
            # İlk eşleşmeye git
            first_match = text_widget.search(self.search_text.get(), "1.0", tk.END, nocase=True)
            if first_match:
                text_widget.see(first_match)
                text_widget.mark_set(tk.INSERT, first_match)
                text_widget.mark_set(tk.SEL_FIRST, first_match)
                text_widget.mark_set(tk.SEL_LAST, f"{first_match}+{len(self.search_text.get())}c")
            
            # Performans metriklerini güncelle
            duration = time.time() - start_time
            self.performance_monitor.record_response_time("search_text", duration)
            self.performance_monitor.update_usage_stats("search_count")
            
        except Exception as e:
            self.performance_monitor.record_error("Arama Hatası", str(e))

    def replace_text_in_current_tab(self):
        """Mevcut sekmede metni değiştirir"""
        text_widget = self.get_current_text_widget()
        if not text_widget or not self.search_text.get():
            return
            
        try:
            # Seçili metni değiştir
            text_widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
            text_widget.insert(tk.INSERT, self.replace_text.get())
        except tk.TclError:
            # Hiçbir şey seçili değilse, ilk eşleşmeyi bul ve değiştir
            start_pos = text_widget.search(self.search_text.get(), "1.0", tk.END, nocase=True)
            if start_pos:
                end_pos = f"{start_pos}+{len(self.search_text.get())}c"
                text_widget.delete(start_pos, end_pos)
                text_widget.insert(start_pos, self.replace_text.get())
                
    def replace_all_text_in_current_tab(self):
        """Mevcut sekmede tüm eşleşmeleri değiştirir"""
        text_widget = self.get_current_text_widget()
        if not text_widget or not self.search_text.get():
            return
            
        # Tüm metni al
        content = text_widget.get("1.0", tk.END)
        
        # Değiştirme işlemini yap
        new_content = content.replace(self.search_text.get(), self.replace_text.get())
        
        # Metni güncelle
        text_widget.delete("1.0", tk.END)
        text_widget.insert("1.0", new_content)

    def change_font(self):
        """Yazı tipini değiştirir"""
        try:
            from tkinter import font
            
            # Mevcut yazı tipini kaydet
            current_font = None
            if self.tabs:
                current_font = self.get_current_text_widget().cget("font")
            
            # Yazı tipi seçim penceresi
            font_window = tk.Toplevel(self.root)
            font_window.title("Yazı Tipi")
            font_window.geometry("400x450")
            font_window.resizable(False, False)
            
            # Ana çerçeve
            main_frame = tk.Frame(font_window, padx=15, pady=15)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Başlık
            title_label = tk.Label(
                main_frame,
                text="Yazı Tipi Ayarları",
                font=("Segoe UI", 12, "bold")
            )
            title_label.pack(pady=(0, 10))
            
            # Sol panel (seçenekler)
            left_frame = tk.Frame(main_frame)
            left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
            
            # Yazı tipi ailesi
            font_family_frame = tk.LabelFrame(left_frame, text="Yazı Tipi", padx=5, pady=5)
            font_family_frame.pack(fill=tk.X, pady=(0, 5))
            
            # Yazı tipi arama
            search_entry = tk.Entry(font_family_frame)
            search_entry.pack(fill=tk.X, pady=(0, 2))
            
            def filter_fonts(*args):
                try:
                    search_text = search_entry.get().lower()
                    font_listbox.delete(0, tk.END)
                    for font_name in sorted(font.families()):
                        if search_text in font_name.lower():
                            font_listbox.insert(tk.END, font_name)
                except Exception as e:
                    self.performance_monitor.record_error("FontFilter", str(e))
            
            search_entry.bind("<KeyRelease>", filter_fonts)
            
            # Yazı tipi listesi
            font_listbox = tk.Listbox(
                font_family_frame,
                height=6,
                selectmode=tk.SINGLE,
                font=("Segoe UI", 9)
            )
            font_listbox.pack(fill=tk.BOTH, expand=True)
            
            # İlk yazı tiplerini ekle
            try:
                for font_name in sorted(font.families()):
                    font_listbox.insert(tk.END, font_name)
            except Exception as e:
                self.performance_monitor.record_error("FontList", str(e))
                font_listbox.insert(tk.END, "Segoe UI")
            
            # Yazı tipi boyutu
            size_frame = tk.LabelFrame(left_frame, text="Boyut", padx=5, pady=5)
            size_frame.pack(fill=tk.X, pady=(0, 5))
            
            size_listbox = tk.Listbox(
                size_frame,
                height=4,
                selectmode=tk.SINGLE,
                font=("Segoe UI", 9)
            )
            size_listbox.pack(fill=tk.BOTH, expand=True)
            
            # Boyutları ekle
            for size in [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24]:
                size_listbox.insert(tk.END, str(size))
            
            # Stil seçenekleri
            style_frame = tk.LabelFrame(left_frame, text="Stil", padx=5, pady=5)
            style_frame.pack(fill=tk.X)
            
            bold_var = tk.BooleanVar()
            italic_var = tk.BooleanVar()
            underline_var = tk.BooleanVar()
            
            # Stil butonları için frame
            style_buttons_frame = tk.Frame(style_frame)
            style_buttons_frame.pack(fill=tk.X)
            
            # Modern stil butonları
            def create_style_button(parent, text, variable):
                btn = tk.Checkbutton(
                    parent,
                    text=text,
                    variable=variable,
                    font=("Segoe UI", 9),
                    indicatoron=False,
                    selectcolor="#0078d7",
                    activebackground="#e1e1e1",
                    activeforeground="black",
                    bg="#f0f0f0",
                    fg="black",
                    relief=tk.FLAT,
                    padx=5,
                    pady=2
                )
                return btn
            
            bold_btn = create_style_button(style_buttons_frame, "Kalın", bold_var)
            bold_btn.pack(side=tk.LEFT, padx=2)
            
            italic_btn = create_style_button(style_buttons_frame, "İtalik", italic_var)
            italic_btn.pack(side=tk.LEFT, padx=2)
            
            underline_btn = create_style_button(style_buttons_frame, "Altı Çizili", underline_var)
            underline_btn.pack(side=tk.LEFT, padx=2)
            
            # Sağ panel (önizleme)
            right_frame = tk.Frame(main_frame)
            right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
            
            preview_frame = tk.LabelFrame(right_frame, text="Önizleme", padx=5, pady=5)
            preview_frame.pack(fill=tk.BOTH, expand=True)
            
            preview_text = tk.Text(
                preview_frame,
                height=8,
                width=20,
                wrap=tk.WORD,
                relief=tk.FLAT,
                padx=5,
                pady=5
            )
            preview_text.pack(fill=tk.BOTH, expand=True)
            
            # Örnek metin
            sample_text = """The quick brown fox
Hızlı kahverengi tilki
1234567890
!@#$%^&*()"""
            preview_text.insert("1.0", sample_text)
            
            def update_preview(*args):
                try:
                    # Seçili yazı tipi ve boyut
                    selected_font = font_listbox.get(font_listbox.curselection())
                    selected_size = size_listbox.get(size_listbox.curselection())
                    
                    # Stil ayarları
                    weight = "bold" if bold_var.get() else "normal"
                    slant = "italic" if italic_var.get() else "roman"
                    underline = 1 if underline_var.get() else 0
                    
                    # Yeni yazı tipi
                    new_font = font.Font(
                        family=selected_font,
                        size=int(selected_size),
                        weight=weight,
                        slant=slant,
                        underline=underline
                    )
                    
                    # Önizlemeyi güncelle
                    preview_text.configure(font=new_font)
                    
                except (tk.TclError, ValueError, IndexError) as e:
                    self.performance_monitor.record_error("FontPreview", str(e))
            
            # Olayları bağla
            font_listbox.bind("<<ListboxSelect>>", update_preview)
            size_listbox.bind("<<ListboxSelect>>", update_preview)
            bold_var.trace("w", update_preview)
            italic_var.trace("w", update_preview)
            underline_var.trace("w", update_preview)
            
            # İlk yazı tipini seç ve uygula
            try:
                font_listbox.selection_set(0)
                font_listbox.see(0)
                size_listbox.selection_set(4)  # 12 punto
                update_preview()  # İlk seçimi uygula
            except Exception as e:
                self.performance_monitor.record_error("FontInitial", str(e))
            
            # Butonlar için frame
            button_frame = tk.Frame(main_frame)
            button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
            
            def apply_font():
                try:
                    # Seçili yazı tipi ve boyut
                    selected_font = font_listbox.get(font_listbox.curselection())
                    selected_size = size_listbox.get(size_listbox.curselection())
                    
                    # Stil ayarları
                    weight = "bold" if bold_var.get() else "normal"
                    slant = "italic" if italic_var.get() else "roman"
                    underline = 1 if underline_var.get() else 0
                    
                    # Yeni yazı tipi
                    new_font = font.Font(
                        family=selected_font,
                        size=int(selected_size),
                        weight=weight,
                        slant=slant,
                        underline=underline
                    )
                    
                    # Tüm sekmelere yeni yazı tipini uygula
                    for tab_id in self.tabs:
                        text_widget = self.tabs[tab_id]["text_widget"]
                        text_widget.configure(font=new_font)
                    
                    font_window.destroy()
                except Exception as e:
                    self.performance_monitor.record_error("FontApply", str(e))
                    font_window.destroy()
            
            def cancel():
                try:
                    # Orijinal yazı tipini geri yükle
                    if current_font:
                        for tab_id in self.tabs:
                            text_widget = self.tabs[tab_id]["text_widget"]
                            text_widget.configure(font=current_font)
                except Exception as e:
                    self.performance_monitor.record_error("FontCancel", str(e))
                finally:
                    font_window.destroy()
            
            # Modern butonlar
            def create_button(parent, text, command, is_default=False):
                btn = tk.Button(
                    parent,
                    text=text,
                    command=command,
                    font=("Segoe UI", 9),
                    width=8,
                    relief=tk.FLAT,
                    padx=10,
                    pady=2,
                    bg="#0078d7" if is_default else "#f0f0f0",
                    fg="white" if is_default else "black",
                    activebackground="#106ebe" if is_default else "#e1e1e1",
                    activeforeground="white" if is_default else "black",
                    cursor="hand2"
                )
                return btn
            
            # Butonları sağa hizala
            cancel_btn = create_button(button_frame, "İptal", cancel)
            cancel_btn.pack(side=tk.RIGHT, padx=2)
            
            apply_btn = create_button(button_frame, "Uygula", apply_font, True)
            apply_btn.pack(side=tk.RIGHT, padx=2)
            
            # Pencereyi ortala
            font_window.update_idletasks()
            width = font_window.winfo_width()
            height = font_window.winfo_height()
            x = (font_window.winfo_screenwidth() // 2) - (width // 2)
            y = (font_window.winfo_screenheight() // 2) - (height // 2)
            font_window.geometry(f"{width}x{height}+{x}+{y}")
            
            # Enter tuşu ile uygula, Escape tuşu ile iptal
            font_window.bind("<Return>", lambda e: apply_font())
            font_window.bind("<Escape>", lambda e: cancel())
            
            # Pencereyi modal yap
            font_window.transient(self.root)
            font_window.grab_set()
            
            # Pencere kapatıldığında orijinal yazı tipini geri yükle
            font_window.protocol("WM_DELETE_WINDOW", cancel)
            
            self.root.wait_window(font_window)
            
        except Exception as e:
            self.performance_monitor.record_error("FontDialog", str(e))
            if 'font_window' in locals():
                font_window.destroy()

    def close_all_tabs(self):
        """Tüm sekmeleri kapatır"""
        # Tüm sekmeleri bir listeye al
        tab_ids = list(self.tabs.keys())
        
        # Her sekmeyi kapat
        for tab_id in tab_ids:
            if not self.check_tab_changes(tab_id):
                return False
            self.close_tab(tab_id)
            
        return True

    def show_performance_report(self):
        """Performans raporunu gösterir"""
        report = self.performance_monitor.get_performance_report()
        
        # Rapor penceresi
        report_window = tk.Toplevel(self.root)
        report_window.title("Performans Raporu")
        report_window.geometry("700x500")
        
        # Ana çerçeve
        main_frame = tk.Frame(report_window, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Başlık
        title_frame = tk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = tk.Label(
            title_frame,
            text="Performans Raporu",
            font=("Segoe UI", 16, "bold")
        )
        title_label.pack(side=tk.LEFT)
        
        # Sistem bilgileri çerçevesi
        system_frame = tk.LabelFrame(main_frame, text="Sistem Bilgileri", padx=10, pady=10)
        system_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Sistem metrikleri
        metrics = [
            ("Çalışma Süresi", f"{report['uptime']:.1f} saniye"),
            ("Bellek Kullanımı", f"{report['memory_usage']:.1f} MB"),
            ("CPU Kullanımı", f"{report['cpu_usage']:.1f}%"),
            ("Ortalama Yanıt Süresi", f"{report['average_response_time']:.3f} saniye"),
            ("Hata Sayısı", str(report['error_count']))
        ]
        
        for i, (label, value) in enumerate(metrics):
            frame = tk.Frame(system_frame)
            frame.pack(fill=tk.X, pady=2)
            
            tk.Label(
                frame,
                text=label,
                font=("Segoe UI", 10),
                width=20,
                anchor="w"
            ).pack(side=tk.LEFT)
            
            tk.Label(
                frame,
                text=value,
                font=("Segoe UI", 10, "bold")
            ).pack(side=tk.LEFT, padx=(10, 0))
        
        # Kullanım istatistikleri çerçevesi
        stats_frame = tk.LabelFrame(main_frame, text="Kullanım İstatistikleri", padx=10, pady=10)
        stats_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # İstatistikler
        stats = [
            ("Açılan Dosya Sayısı", report['usage_stats']['files_opened']),
            ("Kaydedilen Dosya Sayısı", report['usage_stats']['files_saved']),
            ("Arama Sayısı", report['usage_stats']['search_count']),
            ("Değiştirme Sayısı", report['usage_stats']['replace_count']),
            ("Sözdizimi Vurgulama Süresi", f"{report['usage_stats']['syntax_highlighting_time']:.1f} saniye")
        ]
        
        for i, (label, value) in enumerate(stats):
            frame = tk.Frame(stats_frame)
            frame.pack(fill=tk.X, pady=2)
            
            tk.Label(
                frame,
                text=label,
                font=("Segoe UI", 10),
                width=25,
                anchor="w"
            ).pack(side=tk.LEFT)
            
            tk.Label(
                frame,
                text=str(value),
                font=("Segoe UI", 10, "bold")
            ).pack(side=tk.LEFT, padx=(10, 0))
        
        # Alt çerçeve (butonlar için)
        bottom_frame = tk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Kapat butonu
        close_button = tk.Button(
            bottom_frame,
            text="Kapat",
            command=report_window.destroy,
            width=10,
            font=("Segoe UI", 10)
        )
        close_button.pack(side=tk.RIGHT)
        
        # Pencereyi ortala
        report_window.update_idletasks()
        width = report_window.winfo_width()
        height = report_window.winfo_height()
        x = (report_window.winfo_screenwidth() // 2) - (width // 2)
        y = (report_window.winfo_screenheight() // 2) - (height // 2)
        report_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Enter tuşu ile kapat
        report_window.bind("<Return>", lambda e: report_window.destroy())
        report_window.bind("<Escape>", lambda e: report_window.destroy())
        
        # Pencereyi modal yap
        report_window.transient(self.root)
        report_window.grab_set()
        self.root.wait_window(report_window)

    def show_performance_guide(self):
        """Performans izleme rehberini gösterir"""
        guide = [
            "Performans İzleme Rehberi",
            "======================",
            "",
            "Performans İzleme Nedir?",
            "----------------------",
            "Performans izleme, editörün sistem kaynaklarını ve işlem sürelerini takip eden bir özelliktir. "
            "Bu özellik sayesinde editörün performansını ve kaynak kullanımını izleyebilirsiniz.",
            "",
            "İzlenen Metrikler:",
            "----------------",
            "1. Bellek Kullanımı:",
            "   • Editörün kullandığı RAM miktarı",
            "   • MB cinsinden gösterilir",
            "",
            "2. CPU Kullanımı:",
            "   • İşlemci kullanım yüzdesi",
            "   • Yüzde (%) olarak gösterilir",
            "",
            "3. Yanıt Süreleri:",
            "   • İşlemlerin tamamlanma süreleri",
            "   • Saniye cinsinden gösterilir",
            "",
            "4. Hata İstatistikleri:",
            "   • Oluşan hata sayısı",
            "   • Hata türleri ve mesajları",
            "",
            "5. Kullanım İstatistikleri:",
            "   • Açılan dosya sayısı",
            "   • Kaydedilen dosya sayısı",
            "   • Arama sayısı",
            "   • Değiştirme sayısı",
            "   • Sözdizimi vurgulama süresi",
            "",
            "Performans Raporu:",
            "----------------",
            "• Yardım > Performans Raporu menüsünden erişilebilir",
            "• Tüm metriklerin özetini gösterir",
            "• Sistem bilgilerini içerir",
            "• İşlem istatistiklerini gösterir",
            "",
            "Önemli Notlar:",
            "-------------",
            "• Performans izleme otomatik olarak başlar",
            "• Metrikler arka planda sürekli toplanır",
            "• Rapor gerçek zamanlı güncellenir",
            "• Sistem kaynaklarını etkilemez"
        ]
        self.show_help_window("Performans İzleme Rehberi", guide)

    def save_all_tabs(self):
        """Tüm açık sekmeleri kaydeder"""
        try:
            unsaved_tabs = []
            for tab_id in self.tabs:
                if not self.tabs[tab_id]["saved"]:
                    unsaved_tabs.append(tab_id)
            
            if not unsaved_tabs:
                return True
                
            # Kaydedilmemiş sekmeler varsa kullanıcıya sor
            if unsaved_tabs:
                result = messagebox.askyesnocancel(
                    "Kaydedilmemiş Değişiklikler",
                    f"{len(unsaved_tabs)} sekmede kaydedilmemiş değişiklik var.\nTümünü kaydetmek istiyor musunuz?",
                    icon='question'
                )
                
                if result is None:  # İptal
                    return False
                elif result:  # Evet
                    for tab_id in unsaved_tabs:
                        if not self.save_tab(tab_id):
                            return False
                # Hayır seçeneğinde hiçbir şey yapma
            
            return True
            
        except Exception as e:
            self.performance_monitor.record_error("SaveAll", str(e))
            messagebox.showerror("Hata", f"Tüm sekmeler kaydedilirken hata oluştu:\n{str(e)}")
            return False

    def highlight_python_syntax(self, text_widget, start_pos="1.0", end_pos="end"):
        """Python sözdizimi vurgulaması uygular"""
        # Etiketleri tanımla
        text_widget.tag_configure("keyword", foreground=self.syntax_colors["keywords"])
        text_widget.tag_configure("string", foreground=self.syntax_colors["strings"])
        text_widget.tag_configure("comment", foreground=self.syntax_colors["comments"])
        text_widget.tag_configure("function", foreground=self.syntax_colors["functions"])
        text_widget.tag_configure("number", foreground=self.syntax_colors["numbers"])
        text_widget.tag_configure("class", foreground=self.syntax_colors["classes"])
        text_widget.tag_configure("decorator", foreground=self.syntax_colors["decorators"])
        text_widget.tag_configure("builtin", foreground=self.syntax_colors["builtins"])
        
        # Python anahtar kelimeleri
        keywords = [
            "False", "None", "True", "and", "as", "assert", "async", "await", "break", "class",
            "continue", "def", "del", "elif", "else", "except", "finally", "for", "from", "global",
            "if", "import", "in", "is", "lambda", "nonlocal", "not", "or", "pass", "raise", "return",
            "try", "while", "with", "yield"
        ]
        
        # Yerleşik fonksiyonlar
        builtins = [
            "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes", "callable", "chr",
            "classmethod", "compile", "complex", "delattr", "dict", "dir", "divmod", "enumerate",
            "eval", "exec", "filter", "float", "format", "frozenset", "getattr", "globals", "hasattr",
            "hash", "help", "hex", "id", "input", "int", "isinstance", "issubclass", "iter", "len",
            "list", "locals", "map", "max", "memoryview", "min", "next", "object", "oct", "open",
            "ord", "pow", "print", "property", "range", "repr", "reversed", "round", "set", "setattr",
            "slice", "sorted", "staticmethod", "str", "sum", "super", "tuple", "type", "vars", "zip"
        ]
        
        # Yorumları vurgula
        pos = start_pos
        while True:
            # Tek satırlık yorumlar
            pos = text_widget.search(r'#', pos, end_pos, regexp=True)
            if not pos:
                break
                
            line_end = text_widget.index(f"{pos} lineend")
            text_widget.tag_add("comment", pos, line_end)
            pos = line_end
            
            # Çok satırlı yorumlar
            pos = text_widget.search(r'"""', pos, end_pos, regexp=True)
            if not pos:
                break
                
            comment_end = text_widget.search(r'"""', f"{pos}+3c", end_pos, regexp=True)
            if comment_end:
                text_widget.tag_add("comment", pos, f"{comment_end}+3c")
                pos = f"{comment_end}+3c"
            else:
                pos = text_widget.index(f"{pos}+3c")
        
        # Anahtar kelimeleri vurgula
        for keyword in keywords:
            pos = start_pos
            while True:
                pos = text_widget.search(r'\y' + keyword + r'\y', pos, end_pos, regexp=True)
                if not pos:
                    break
                text_widget.tag_add("keyword", pos, f"{pos}+{len(keyword)}c")
                pos = text_widget.index(f"{pos}+1c")
        
        # Yerleşik fonksiyonları vurgula
        for builtin in builtins:
            pos = start_pos
            while True:
                pos = text_widget.search(r'\y' + builtin + r'\y', pos, end_pos, regexp=True)
                if not pos:
                    break
                text_widget.tag_add("builtin", pos, f"{pos}+{len(builtin)}c")
                pos = text_widget.index(f"{pos}+1c")
        
        # Sayıları vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'\b\d+(\.\d+)?\b', pos, end_pos, regexp=True)
            if not pos:
                break
            number_end = text_widget.search(r'\b', pos, end_pos, regexp=True)
            if number_end:
                text_widget.tag_add("number", pos, number_end)
                pos = number_end
            else:
                pos = text_widget.index(f"{pos}+1c")
        
        # Stringleri vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'["\']', pos, end_pos, regexp=True)
            if not pos:
                break
                
            quote = text_widget.get(pos)
            string_end = text_widget.search(quote, f"{pos}+1c", end_pos)
            if string_end:
                text_widget.tag_add("string", pos, f"{string_end}+1c")
                pos = f"{string_end}+1c"
            else:
                pos = text_widget.index(f"{pos}+1c")
        
        # Fonksiyon tanımlamalarını vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'\bdef\s+([a-zA-Z_]\w*)', pos, end_pos, regexp=True)
            if not pos:
                break
                
            func_name_start = text_widget.search(r'[a-zA-Z_]\w*', f"{pos}+4c", end_pos)
            if func_name_start:
                func_name_end = text_widget.search(r'\(', func_name_start, end_pos)
                if func_name_end:
                    text_widget.tag_add("function", func_name_start, func_name_end)
                    pos = func_name_end
                else:
                    pos = text_widget.index(f"{pos}+1c")
            else:
                pos = text_widget.index(f"{pos}+1c")
        
        # Sınıf tanımlamalarını vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'\bclass\s+([a-zA-Z_]\w*)', pos, end_pos, regexp=True)
            if not pos:
                break
                
            class_name_start = text_widget.search(r'[a-zA-Z_]\w*', f"{pos}+6c", end_pos)
            if class_name_start:
                class_name_end = text_widget.search(r'[:(]', class_name_start, end_pos)
                if class_name_end:
                    text_widget.tag_add("class", class_name_start, class_name_end)
                    pos = class_name_end
                else:
                    pos = text_widget.index(f"{pos}+1c")
            else:
                pos = text_widget.index(f"{pos}+1c")
        
        # Dekoratörleri vurgula
        pos = start_pos
        while True:
            pos = text_widget.search(r'@[a-zA-Z_]\w*', pos, end_pos, regexp=True)
            if not pos:
                break
                
            decorator_end = text_widget.search(r'[(\n]', pos, end_pos)
            if decorator_end:
                text_widget.tag_add("decorator", pos, decorator_end)
                pos = decorator_end
            else:
                pos = text_widget.index(f"{pos}+1c")

if __name__ == "__main__":
    root = tk.Tk()
    editor = TextEditor(root)
    
    # Set dark theme as default
    editor.apply_theme("Koyu")
    
    # Start in fullscreen mode
    root.state('zoomed')  # For Windows
    
    # Çıkış yapmadan önce değişiklikleri kontrol et
    root.protocol("WM_DELETE_WINDOW", editor.exit_app)
    
    root.mainloop() 