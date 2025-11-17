# iko.py
# ИКО - Индикатор кругового обзора с реалистичной отметкой цели, помехами и береговой линией

import tkinter as tk
import customtkinter as ctk
import math
import random
from collections import deque

class EPRCalculator:
    @staticmethod
    def calculate_epr_from_dimensions(length, width, height_above_water, material, aspect_angle):
        """Расчет ЭПР цели на основе физических размеров и материала"""
        base_epr = (length * width * max(0.1, height_above_water)) ** (2/3)
        material_coefficients = {
            "металл": 1.0, "сталь": 0.95, "алюминий": 0.9, "железо": 0.92,
            "пластик": 0.1, "стеклопластик": 0.08, "дерево": 0.05, "резина": 0.03, "композит": 0.07
        }
        material_factor = material_coefficients.get(material.lower(), 0.1)
        aspect_rad = math.radians(aspect_angle)
        aspect_factor = abs(math.sin(aspect_rad))
        form_factor = 0.7
        final_epr = base_epr * material_factor * (0.3 + 0.7 * aspect_factor) * form_factor
        return max(final_epr, 0.001)

class CollapsibleFrame(ctk.CTkFrame):
    """Сворачиваемый фрейм с заголовком"""
    def __init__(self, parent, title, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.is_expanded = True
        self.content = None
        
        # Заголовок
        self.header = ctk.CTkFrame(self)
        self.header.pack(fill="x", padx=0, pady=0)
        
        self.title_label = ctk.CTkLabel(self.header, text=title, font=("Arial", 12, "bold"))
        self.title_label.pack(side="left", padx=5, pady=5)
        
        self.toggle_btn = ctk.CTkButton(self.header, text="▼", width=30, height=20,
                                      command=self.toggle)
        self.toggle_btn.pack(side="right", padx=5, pady=5)
        
        # Контент
        self.content_frame = ctk.CTkFrame(self)
        
    def set_content(self, content_frame):
        """Установка содержимого"""
        self.content = content_frame
        self.content_frame.pack(fill="x", padx=5, pady=5)
        
    def toggle(self):
        """Переключение состояния"""
        if self.is_expanded:
            self.content_frame.pack_forget()
            self.toggle_btn.configure(text="▶")
            self.is_expanded = False
        else:
            self.content_frame.pack(fill="x", padx=5, pady=5)
            self.toggle_btn.configure(text="▼")
            self.is_expanded = True

class ИКО:
    def __init__(self, root):
        self.root = root
        self.root.title("ИКО - Индикатор кругового обзора")

        # Начальный размер холста (адаптивный)
        screen_width = max(800, self.root.winfo_screenwidth() - 300)
        screen_height = max(600, self.root.winfo_screenheight() - 150)
        self.canvas_size = min(screen_width, screen_height)
        self.center = self.canvas_size // 2

        # Диапазон в милях и пикселях на милю
        self.range_scale = 24.0
        self.pixel_per_mile = (self.canvas_size // 2 - 40) / self.range_scale

        # Параметры цели
        self.target_range = 8.0
        self.target_bearing = 40.0
        self.aspect_angle = 70.0
        self.target_epr = 1.0
        self.target_length = 30.0  # метры
        self.target_width = 7.0    # метры

        # Помехи и следы
        self.clutter_intensity = 0.45
        self.clutter_density = 140
        self.target_history = deque(maxlen=30)
        self.show_trails = True
        self.trail_length = 30

        # Береговая линия
        self.coastline_points = self.generate_coastline()
        self.show_coastline = True

        # Имитация движения цели
        self.target_moving = False
        self.target_course = 45.0  # градусы
        self.target_speed = 10.0   # узлов
        self.simulation_interval = 500  # мс

        # Формуляр цели
        self.show_target_form = False
        self.target_number = 1
        self.target_course_current = self.target_course
        self.target_speed_current = self.target_speed

        # Сворачивание панели управления
        self.control_panel_visible = True

        # Флаг изменения размера
        self.updating_size = False

        # Построение интерфейса
        self.setup_ui()

        # Привязка событий изменения размера
        self.canvas.master.bind("<Configure>", self.on_resize)
        self.root.bind("<Configure>", self.on_root_configure)

        # Первоначальная отрисовка
        self.draw_radar_display()

    # ---------------- ИНТЕРФЕЙС ПОЛЬЗОВАТЕЛЯ ----------------
    def setup_ui(self):
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Панель управления с возможностью сворачивания
        self.control_frame = ctk.CTkFrame(main_frame, width=350)
        self.control_frame.pack(side="left", fill="y", padx=5, pady=5)
        self.control_frame.pack_propagate(False)

        display_frame = ctk.CTkFrame(main_frame)
        display_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        self.setup_control_panel(self.control_frame)
        self.setup_display_area(display_frame)

    def setup_control_panel(self, parent):
        # Заголовок с кнопкой сворачивания - кнопка СЛЕВА
        title_frame = ctk.CTkFrame(parent)
        title_frame.pack(fill="x", padx=5, pady=5)
        
        self.toggle_btn = ctk.CTkButton(title_frame, text="◀", width=30, height=30,
                                       command=self.toggle_control_panel)
        self.toggle_btn.pack(side="left", padx=5)
        
        ctk.CTkLabel(title_frame, text="УПРАВЛЕНИЕ ИКО", font=("Arial", 14, "bold")).pack(side="left", padx=5)

        # Основной контент панели управления
        self.control_content = ctk.CTkFrame(parent)
        self.control_content.pack(fill="both", expand=True, padx=5, pady=5)

        # Создаем сворачиваемые разделы
        self.setup_collapsible_sections()

        # Информационная панель
        info_frame = ctk.CTkFrame(self.control_content)
        info_frame.pack(side="bottom", fill="x", padx=8, pady=6)
        self.info_var = ctk.StringVar(value="Готов к работе")
        ctk.CTkLabel(info_frame, textvariable=self.info_var, font=("Arial", 11)).pack()

    def setup_collapsible_sections(self):
        """Настройка сворачиваемых разделов панели управления"""
        
        # Раздел основных параметров
        main_section = CollapsibleFrame(self.control_content, "Основные параметры")
        main_section.pack(fill="x", padx=5, pady=2)
        
        main_content = ctk.CTkFrame(main_section.content_frame)
        main_content.pack(fill="x", padx=0, pady=0)
        
        # Пеленг
        bearing_frame = ctk.CTkFrame(main_content)
        bearing_frame.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(bearing_frame, text="Пеленг на цель:").pack(anchor="w")
        self.bearing_var = ctk.DoubleVar(value=self.target_bearing)
        bearing_slider = ctk.CTkSlider(bearing_frame, from_=0, to=360, variable=self.bearing_var,
                                        command=self.on_bearing_change)
        bearing_slider.pack(fill="x")
        self.bearing_value_label = ctk.CTkLabel(bearing_frame, text=f"{self.target_bearing:.0f}°")
        self.bearing_value_label.pack(anchor="e")

        # Дальность
        range_frame = ctk.CTkFrame(main_content)
        range_frame.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(range_frame, text="Дальность до цели:").pack(anchor="w")
        self.range_var = ctk.DoubleVar(value=self.target_range)
        range_slider = ctk.CTkSlider(range_frame, from_=1, to=self.range_scale-2, variable=self.range_var,
                                     command=self.on_range_change)
        range_slider.pack(fill="x")
        self.range_value_label = ctk.CTkLabel(range_frame, text=f"{self.target_range:.1f} миль")
        self.range_value_label.pack(anchor="e")

        # Аспект
        aspect_frame = ctk.CTkFrame(main_content)
        aspect_frame.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(aspect_frame, text="Угол аспекта:").pack(anchor="w")
        self.aspect_var = ctk.DoubleVar(value=self.aspect_angle)
        aspect_slider = ctk.CTkSlider(aspect_frame, from_=0, to=90, variable=self.aspect_var,
                                     command=self.on_aspect_change)
        aspect_slider.pack(fill="x")
        self.aspect_value_label = ctk.CTkLabel(aspect_frame, text=f"{self.aspect_angle:.0f}°")
        self.aspect_value_label.pack(anchor="e")

        # ЭПР
        epr_frame = ctk.CTkFrame(main_content)
        epr_frame.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(epr_frame, text="ЭПР цели:").pack(anchor="w")
        self.epr_var = ctk.DoubleVar(value=self.target_epr)
        epr_slider = ctk.CTkSlider(epr_frame, from_=0.1, to=12.0, variable=self.epr_var,
                                  command=self.on_epr_change)
        epr_slider.pack(fill="x")
        self.epr_value_label = ctk.CTkLabel(epr_frame, text=f"{self.target_epr:.1f} м²")
        self.epr_value_label.pack(anchor="e")

        main_section.set_content(main_content)

        # Раздел размеров цели
        size_section = CollapsibleFrame(self.control_content, "Размеры цели")
        size_section.pack(fill="x", padx=5, pady=2)
        
        size_content = ctk.CTkFrame(size_section.content_frame)
        size_content.pack(fill="x", padx=0, pady=0)
        
        ctk.CTkLabel(size_content, text="Длина и ширина цели (м):", font=("Arial", 11)).pack(pady=4)
        self.length_var = ctk.DoubleVar(value=self.target_length)
        length_slider = ctk.CTkSlider(size_content, from_=1, to=200, variable=self.length_var,
                                     command=self.on_length_change)
        length_slider.pack(fill="x", padx=8, pady=4)
        self.width_var = ctk.DoubleVar(value=self.target_width)
        width_slider = ctk.CTkSlider(size_content, from_=1, to=80, variable=self.width_var,
                                    command=self.on_width_change)
        width_slider.pack(fill="x", padx=8, pady=4)

        size_section.set_content(size_content)

        # Раздел помех
        clutter_section = CollapsibleFrame(self.control_content, "Помехи")
        clutter_section.pack(fill="x", padx=5, pady=2)
        
        clutter_content = ctk.CTkFrame(clutter_section.content_frame)
        clutter_content.pack(fill="x", padx=0, pady=0)
        
        clutter_frame = ctk.CTkFrame(clutter_content)
        clutter_frame.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(clutter_frame, text="Интенсивность помех:").pack(anchor="w")
        self.clutter_var = ctk.DoubleVar(value=self.clutter_intensity)
        clutter_slider = ctk.CTkSlider(clutter_frame, from_=0.0, to=1.0, variable=self.clutter_var,
                                       command=self.on_clutter_change)
        clutter_slider.pack(fill="x")
        self.clutter_value_label = ctk.CTkLabel(clutter_frame, text=f"{int(self.clutter_intensity*100)}%")
        self.clutter_value_label.pack(anchor="e")

        clutter_section.set_content(clutter_content)

        # Раздел следов цели
        trails_section = CollapsibleFrame(self.control_content, "Следы цели")
        trails_section.pack(fill="x", padx=5, pady=2)
        
        trails_content = ctk.CTkFrame(trails_section.content_frame)
        trails_content.pack(fill="x", padx=0, pady=0)
        
        # Переключатель показа следов
        self.trails_switch_var = ctk.StringVar(value="on" if self.show_trails else "off")
        trails_switch = ctk.CTkSwitch(trails_content, text="Показывать следы", 
                                     variable=self.trails_switch_var, 
                                     onvalue="on", offvalue="off",
                                     command=self.on_trails_switch_change)
        trails_switch.pack(anchor="w", padx=8, pady=4)
        
        # Длина следов
        trail_length_frame = ctk.CTkFrame(trails_content)
        trail_length_frame.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(trail_length_frame, text="Длина следов:").pack(anchor="w")
        self.trail_length_var = ctk.IntVar(value=self.trail_length)
        trail_length_slider = ctk.CTkSlider(trail_length_frame, from_=0, to=100, 
                                           variable=self.trail_length_var,
                                           command=self.on_trail_length_change)
        trail_length_slider.pack(fill="x")
        self.trail_length_label = ctk.CTkLabel(trail_length_frame, text=f"{self.trail_length}")
        self.trail_length_label.pack(anchor="e")

        trails_section.set_content(trails_content)

        # Раздел береговой линии
        coastline_section = CollapsibleFrame(self.control_content, "Береговая линия")
        coastline_section.pack(fill="x", padx=5, pady=2)
        
        coastline_content = ctk.CTkFrame(coastline_section.content_frame)
        coastline_content.pack(fill="x", padx=0, pady=0)
        
        self.coastline_switch_var = ctk.StringVar(value="on" if self.show_coastline else "off")
        coastline_switch = ctk.CTkSwitch(coastline_content, text="Показывать берег", 
                                        variable=self.coastline_switch_var, 
                                        onvalue="on", offvalue="off",
                                        command=self.on_coastline_switch_change)
        coastline_switch.pack(anchor="w", padx=8, pady=8)

        coastline_section.set_content(coastline_content)

        # Раздел формуляра цели
        form_section = CollapsibleFrame(self.control_content, "Формуляр цели")
        form_section.pack(fill="x", padx=5, pady=2)
        
        form_content = ctk.CTkFrame(form_section.content_frame)
        form_content.pack(fill="x", padx=0, pady=0)
        
        self.form_switch_var = ctk.StringVar(value="on" if self.show_target_form else "off")
        form_switch = ctk.CTkSwitch(form_content, text="Показывать формуляр", 
                                   variable=self.form_switch_var, 
                                   onvalue="on", offvalue="off",
                                   command=self.on_form_switch_change)
        form_switch.pack(anchor="w", padx=8, pady=8)

        form_section.set_content(form_content)

        # Раздел имитации движения
        movement_section = CollapsibleFrame(self.control_content, "Имитация движения")
        movement_section.pack(fill="x", padx=5, pady=2)
        
        movement_content = ctk.CTkFrame(movement_section.content_frame)
        movement_content.pack(fill="x", padx=0, pady=0)
        
        # Курс
        course_frame = ctk.CTkFrame(movement_content)
        course_frame.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(course_frame, text="Курс цели:").pack(anchor="w")
        self.course_var = ctk.DoubleVar(value=self.target_course)
        course_slider = ctk.CTkSlider(course_frame, from_=0, to=360, variable=self.course_var,
                                     command=self.on_course_change)
        course_slider.pack(fill="x")
        self.course_label = ctk.CTkLabel(course_frame, text=f"{self.target_course:.0f}°")
        self.course_label.pack(anchor="e")
        
        # Скорость
        speed_frame = ctk.CTkFrame(movement_content)
        speed_frame.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(speed_frame, text="Скорость цели:").pack(anchor="w")
        self.speed_var = ctk.DoubleVar(value=self.target_speed)
        speed_slider = ctk.CTkSlider(speed_frame, from_=0, to=30, variable=self.speed_var,
                                    command=self.on_speed_change)
        speed_slider.pack(fill="x")
        self.speed_label = ctk.CTkLabel(speed_frame, text=f"{self.target_speed:.1f} уз.")
        self.speed_label.pack(anchor="e")
        
        # Кнопки управления движением
        movement_btn_frame = ctk.CTkFrame(movement_content)
        movement_btn_frame.pack(fill="x", padx=8, pady=8)
        self.start_btn = ctk.CTkButton(movement_btn_frame, text="▶ Старт", 
                                      command=self.start_movement,
                                      fg_color="green", hover_color="dark green")
        self.start_btn.pack(side="left", padx=2, expand=True)
        
        self.stop_btn = ctk.CTkButton(movement_btn_frame, text="⏸ Стоп", 
                                     command=self.stop_movement,
                                     fg_color="red", hover_color="dark red")
        self.stop_btn.pack(side="right", padx=2, expand=True)

        movement_section.set_content(movement_content)

        # Раздел кнопок управления
        buttons_section = CollapsibleFrame(self.control_content, "Управление")
        buttons_section.pack(fill="x", padx=5, pady=2)
        
        buttons_content = ctk.CTkFrame(buttons_section.content_frame)
        buttons_content.pack(fill="x", padx=0, pady=0)
        
        btn_frame = ctk.CTkFrame(buttons_content)
        btn_frame.pack(fill="x", padx=8, pady=8)
        ctk.CTkButton(btn_frame, text="🔄 Обновить", command=self.update_display).pack(fill="x", pady=3)
        ctk.CTkButton(btn_frame, text="🎯 Случайная цель", command=self.random_target).pack(fill="x", pady=3)
        ctk.CTkButton(btn_frame, text="🏝️ Новая береговая линия", command=self.new_coastline).pack(fill="x", pady=3)
        ctk.CTkButton(btn_frame, text="🌀 Случайные помехи", command=self.random_clutter).pack(fill="x", pady=3)

        buttons_section.set_content(buttons_content)

    def setup_display_area(self, parent):
        """Настройка области отображения радара"""
        canvas_container = ctk.CTkFrame(parent)
        canvas_container.pack(fill="both", expand=True, padx=5, pady=5)
        self.canvas = tk.Canvas(canvas_container, width=self.canvas_size, height=self.canvas_size,
                                bg='black', highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.update_idletasks()

    # ---------------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------------
    def polar_to_cartesian(self, bearing, range_val):
        """Преобразование полярных координат в декартовы"""
        angle_rad = math.radians(90 - bearing)
        x = self.center + range_val * self.pixel_per_mile * math.cos(angle_rad)
        y = self.center - range_val * self.pixel_per_mile * math.sin(angle_rad)
        return x, y

    # ---------------- ОТРИСОВКА РАДАРА ----------------
    def draw_radar_display(self):
        """Основная функция отрисовки радарного дисплея"""
        if not hasattr(self, 'canvas'):
            return
        self.canvas.delete("all")
        self.update_canvas_size()
        self.draw_grid_background()
        self.draw_range_rings()
        self.draw_bearing_marks()
        self.draw_sea_clutter()
        if self.show_coastline:
            self.draw_coastline()
        if self.show_trails:
            self.draw_target_trails()
        self.draw_current_target()
        
        # Отрисовка курсора и формуляра цели
        if self.show_target_form:
            self.draw_target_cursor()
            self.draw_target_form()
            
        self.update_target_info()

    def update_canvas_size(self):
        """Обновление размера холста при изменении окна"""
        if self.updating_size:
            return
        self.updating_size = True
        try:
            container_width = max(100, self.canvas.master.winfo_width())
            container_height = max(100, self.canvas.master.winfo_height())
            new_size = min(container_width, container_height)
            new_size = max(220, new_size - 10)
            if new_size != self.canvas_size:
                self.canvas_size = new_size
                self.canvas.config(width=self.canvas_size, height=self.canvas_size)
            self.center = self.canvas_size // 2
            self.pixel_per_mile = max(1.0, (self.canvas_size // 2 - 40) / self.range_scale)
        finally:
            self.updating_size = False

    def draw_grid_background(self):
        """Отрисовка сетки фона"""
        w = self.canvas_size
        step = max(20, w // 12)
        for i in range(0, w, step):
            r = i // 2
            if r <= 0: continue
            shade = 12 + (i // max(1, step)) * 3
            shade = min(80, shade)
            color = f'#{shade:02x}{shade:02x}{shade:02x}'
            self.canvas.create_oval(self.center - r, self.center - r, self.center + r, self.center + r,
                                    outline=color, width=1)

    def draw_range_rings(self):
        """Отрисовка кругов дальности"""
        num_rings = 4
        for i in range(1, num_rings + 1):
            range_val = (self.range_scale / num_rings) * i
            radius = range_val * self.pixel_per_mile
            self.canvas.create_oval(self.center - radius, self.center - radius,
                                    self.center + radius, self.center + radius,
                                    outline='#222222', width=1, dash=(3, 5))
            x, y = self.polar_to_cartesian(0, range_val)
            self.canvas.create_text(x + 8, y - 8, text=f"{int(range_val)}", fill='#666666', font=("Arial", 9))

    def draw_bearing_marks(self):
        """Отрисовка меток пеленга"""
        for bearing in range(0, 360, 30):
            x1, y1 = self.polar_to_cartesian(bearing, self.range_scale * 0.92)
            x2, y2 = self.polar_to_cartesian(bearing, self.range_scale)
            self.canvas.create_line(x1, y1, x2, y2, fill='#222222', width=1)
            x_text, y_text = self.polar_to_cartesian(bearing, self.range_scale * 1.03)
            self.canvas.create_text(x_text, y_text, text=f"{bearing}°", fill='#444444', font=("Arial", 9))

    def draw_sea_clutter(self):
        """Отрисовка морских помех"""
        if self.clutter_intensity <= 0.01:
            return
        base_clusters = max(4, int(self.clutter_density * self.clutter_intensity / 40))
        cluster_spread = max(0.5, self.range_scale * 0.25)
        for _ in range(base_clusters):
            cluster_bearing = random.uniform(0, 360)
            cluster_range = random.uniform(1, self.range_scale * 0.9)
            cluster_count = random.randint(8, 30)
            for i in range(cluster_count):
                b = cluster_bearing + random.uniform(-8, 8)
                r = max(0.2, cluster_range + random.uniform(-cluster_spread*0.1, cluster_spread*0.1))
                size = random.uniform(0.8, 4.0) * (1.0 + (self.clutter_intensity * 2.0))
                brightness = self.calculate_clutter_brightness(random.uniform(0.05, 0.6) * self.clutter_intensity, r)
                ci = int(255 * brightness)
                color = f'#{ci:02x}{ci:02x}00'
                x, y = self.polar_to_cartesian(b % 360, r)
                w = max(1, int(size))
                h = max(1, int(size * random.uniform(0.6, 1.4)))
                self.canvas.create_oval(x - w, y - h, x + w, y + h, fill=color, outline='')

        for _ in range(int(20 * self.clutter_intensity)):
            b = random.uniform(0, 360)
            r = random.uniform(0.2, self.range_scale * 0.9)
            size = random.uniform(1.0, 3.5)
            brightness = self.calculate_clutter_brightness(random.uniform(0.4, 0.9) * self.clutter_intensity, r)
            ci = int(200 + 55 * brightness)
            color = f'#{ci:02x}{ci:02x}00'
            x, y = self.polar_to_cartesian(b, r)
            self.canvas.create_oval(x - size, y - size, x + size, y + size, fill=color, outline='')

    def draw_coastline(self):
        """Отрисовка береговой линии - теперь ближе к краю"""
        if not self.coastline_points:
            return
        pts = []
        for b, r in self.coastline_points:
            x, y = self.polar_to_cartesian(b, r)
            pts.extend([x, y])
        self.canvas.create_line(pts, fill='#CC9900', width=2, smooth=True)
        for i in range(1, 4):
            shade = int(200 - i*30)
            shade = max(40, shade)
            color = f'#{shade:02x}{int(shade*0.85):02x}30'
            self.canvas.create_line(pts, fill=color, width=2 + i, smooth=True)

    def draw_target_trails(self):
        """Отрисовка следов цели - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        if len(self.target_history) < 2:
            return
        
        # Рисуем соединительные линии между соседними точками
        for i in range(len(self.target_history) - 1):
            bearing1, range1, epr1 = self.target_history[i]
            bearing2, range2, epr2 = self.target_history[i + 1]
            
            x1, y1 = self.polar_to_cartesian(bearing1, range1)
            x2, y2 = self.polar_to_cartesian(bearing2, range2)
            
            # Плавное затухание
            t = i / max(1, (len(self.target_history) - 2))
            fade = 0.3 + 0.7 * (1.0 - t)
            alpha = int(255 * fade)
            color = f'#00ff{alpha:02x}'
            
            self.canvas.create_line(x1, y1, x2, y2, fill=color, width=2)
        
        # Точки истории
        for i, (bearing, range_val, epr) in enumerate(self.target_history):
            t = i / max(1, (len(self.target_history) - 1))
            fade = 0.4 + 0.6 * (1.0 - t)
            
            base_size = 3 + (epr * 0.5)
            size = max(2, base_size * fade)
            
            r = int(100 + 155 * (1 - fade))
            g = int(200 + 55 * fade)
            b = int(50 * (1 - fade))
            color = f'#{r:02x}{g:02x}{b:02x}'
            
            x, y = self.polar_to_cartesian(bearing, range_val)
            self.canvas.create_oval(x - size, y - size, x + size, y + size, 
                                   fill=color, outline='')

    def draw_target_cursor(self):
        """Отрисовка красного квадратного курсора вокруг цели (уменьшенный)"""
        cx, cy = self.polar_to_cartesian(self.target_bearing, self.target_range)
        cursor_size = 12  # Уменьшенный размер курсора
        
        # Рисуем красный квадрат
        self.canvas.create_rectangle(
            cx - cursor_size, cy - cursor_size,
            cx + cursor_size, cy + cursor_size,
            outline='red', width=2
        )
        
        # Добавляем диагонали для лучшей видимости
        self.canvas.create_line(
            cx - cursor_size, cy - cursor_size,
            cx + cursor_size, cy + cursor_size,
            fill='red', width=1
        )
        self.canvas.create_line(
            cx - cursor_size, cy + cursor_size,
            cx + cursor_size, cy - cursor_size,
            fill='red', width=1
        )

    def draw_target_form(self):
        """Отрисовка формуляра цели рядом с целью"""
        cx, cy = self.polar_to_cartesian(self.target_bearing, self.target_range)
        
        # Позиция формуляра (справа от цели, если помещается, иначе слева)
        form_x = cx + 15
        form_width = 110
        if form_x + form_width > self.canvas_size:
            form_x = cx - form_width - 5
        
        form_y = cy - 35
        
        # Фон формуляра
        self.canvas.create_rectangle(
            form_x, form_y,
            form_x + form_width, form_y + 70,
            fill='black', outline='white', width=1
        )
        
        # Данные цели с выравниванием слева
        form_data = [
            f"N{self.target_number:02d}",
            f"П{self.target_bearing:.0f}°",
            f"Д{self.target_range:.1f}м",
            f"К{self.target_course_current:.0f}°",
            f"V{self.target_speed_current:.1f}уз"
        ]
        
        # Текст формуляра зеленым цветом с выравниванием слева
        for i, text in enumerate(form_data):
            self.canvas.create_text(
                form_x + 8, form_y + 12 + i * 14,
                text=text, fill='#00FF00', font=("Arial", 10, "bold"),
                anchor="w"  # Выравнивание по левому краю
            )

    # ---------------- ВЫЧИСЛЕНИЯ ----------------
    def calculate_angular_width(self):
        """
        Физически обоснованный угловой размер (проекция корпуса):
        projected = L * sin(aspect) + B * cos(aspect)
        Угол (рад) ~ projected / distance. Затем сжатие до реалистичных градусов РЛС.
        """
        L = max(0.1, self.target_length)
        B = max(0.1, self.target_width)
        a_rad = math.radians(self.aspect_angle)
        sin_a = abs(math.sin(a_rad))
        cos_a = abs(math.cos(a_rad))
        projected_m = L * sin_a + B * cos_a
        distance_m = max(1.0, self.target_range * 1852.0)
        angular_rad = projected_m / distance_m
        angular_deg = math.degrees(angular_rad)
        # сжатие до реалистичной отметки радара
        angular_deg *= 0.3
        angular_deg = max(0.18, min(3.5, angular_deg))
        return angular_deg

    def calculate_target_brightness(self):
        """
        Модель яркости:
        - log10(EPR + 1) дает фактор EPR
        - аспект -> sin(aspect)
        - затухание по дальности
        """
        epr = max(0.01, self.target_epr)
        epr_factor = math.log10(epr + 1)
        aspect = max(0.0, min(1.0, abs(math.sin(math.radians(self.aspect_angle)))))
        range_factor = 1.0 - (self.target_range / self.range_scale) * 0.6
        range_factor = max(0.12, range_factor)
        base = 0.12
        brightness = base + epr_factor * aspect * range_factor * 1.5
        brightness = max(0.05, min(1.0, brightness))
        return brightness

    def calculate_clutter_brightness(self, base_intensity, range_val):
        """Расчет яркости помех в зависимости от дальности"""
        max_clutter_brightness = 0.8
        range_factor = 1.0 - (range_val / self.range_scale) * 0.45
        brightness = base_intensity * max_clutter_brightness * max(0.2, range_factor)
        return max(0.05, min(max_clutter_brightness, brightness))

    # ---------------- Отрисовка текущей цели (исправленная) ----------------
    def draw_current_target(self):
        """Отрисовка текущей цели - исправленная версия без расщепления"""
        # Вычисляем угловой размер и яркость
        angular_width = self.calculate_angular_width()
        brightness = self.calculate_target_brightness()

        # Главный цвет (желтый) масштабированный по яркости
        val = int(255 * max(0.15, min(1.0, brightness)))
        main_color = f'#{val:02x}{val:02x}00'

        # Координаты центра цели
        cx, cy = self.polar_to_cartesian(self.target_bearing, self.target_range)

        # Отрисовка основной отметки цели - ТОЛЬКО ТОЧКА
        core_r = max(3, int(3 + brightness * 4))  # Увеличенный размер точки
        self.canvas.create_oval(cx - core_r, cy - core_r, cx + core_r, cy + core_r,
                                fill=main_color, outline=main_color)

        # Отрисовка ореола вокруг цели (небольшие круги)
        halo_radius = core_r + 2
        halo_color = f'#{min(255, val+50):02x}{min(255, val+30):02x}00'
        self.canvas.create_oval(cx - halo_radius, cy - halo_radius, 
                               cx + halo_radius, cy + halo_radius,
                               outline=halo_color, width=1)

        # Дополнительный внешний ореол для больших целей
        if self.target_epr > 2.0:
            outer_radius = halo_radius + 3
            outer_color = f'#{min(255, val+20):02x}{min(255, val+10):02x}00'
            self.canvas.create_oval(cx - outer_radius, cy - outer_radius, 
                                   cx + outer_radius, cy + outer_radius,
                                   outline=outer_color, width=1)

    # ---------------- ОБРАБОТЧИКИ СОБЫТИЙ И УПРАВЛЕНИЕ ----------------
    def on_bearing_change(self, value):
        """Обработчик изменения пеленга"""
        self.target_bearing = float(value)
        self.bearing_value_label.configure(text=f"{self.target_bearing:.0f}°")
        self.add_to_history()
        self.draw_radar_display()

    def on_range_change(self, value):
        """Обработчик изменения дальности"""
        self.target_range = float(value)
        self.range_value_label.configure(text=f"{self.target_range:.1f} миль")
        self.add_to_history()
        self.draw_radar_display()

    def on_aspect_change(self, value):
        """Обработчик изменения угла аспекта"""
        self.aspect_angle = float(value)
        self.aspect_value_label.configure(text=f"{self.aspect_angle:.0f}°")
        self.draw_radar_display()

    def on_epr_change(self, value):
        """Обработчик изменения ЭПР"""
        self.target_epr = float(value)
        self.epr_value_label.configure(text=f"{self.target_epr:.1f} м²")
        self.add_to_history()
        self.draw_radar_display()

    def on_clutter_change(self, value):
        """Обработчик изменения интенсивности помех"""
        self.clutter_intensity = float(value)
        self.clutter_value_label.configure(text=f"{int(self.clutter_intensity*100)}%")
        self.draw_radar_display()

    def on_length_change(self, value):
        """Обработчик изменения длины цели"""
        self.target_length = float(value)
        self.draw_radar_display()

    def on_width_change(self, value):
        """Обработчик изменения ширины цели"""
        self.target_width = float(value)
        self.draw_radar_display()

    def on_trails_switch_change(self):
        """Обработчик переключения показа следов"""
        self.show_trails = (self.trails_switch_var.get() == "on")
        self.draw_radar_display()

    def on_trail_length_change(self, value):
        """Обработчик изменения длины следов"""
        self.trail_length = int(value)
        self.target_history = deque(maxlen=self.trail_length)
        self.trail_length_label.configure(text=f"{self.trail_length}")
        self.draw_radar_display()

    def on_coastline_switch_change(self):
        """Обработчик переключения показа береговой линии"""
        self.show_coastline = (self.coastline_switch_var.get() == "on")
        self.draw_radar_display()

    def on_form_switch_change(self):
        """Обработчик переключения показа формуляра цели"""
        self.show_target_form = (self.form_switch_var.get() == "on")
        self.draw_radar_display()

    def on_course_change(self, value):
        """Обработчик изменения курса цели"""
        self.target_course = float(value)
        self.target_course_current = self.target_course
        self.course_label.configure(text=f"{self.target_course:.0f}°")

    def on_speed_change(self, value):
        """Обработчик изменения скорости цели"""
        self.target_speed = float(value)
        self.target_speed_current = self.target_speed
        self.speed_label.configure(text=f"{self.target_speed:.1f} уз.")

    def toggle_control_panel(self):
        """Сворачивание/разворачивание панели управления"""
        if self.control_panel_visible:
            # Сворачиваем
            self.control_content.pack_forget()
            self.control_frame.configure(width=50)
            self.toggle_btn.configure(text="▶")
            self.control_panel_visible = False
        else:
            # Разворачиваем
            self.control_content.pack(fill="both", expand=True, padx=5, pady=5)
            self.control_frame.configure(width=350)
            self.toggle_btn.configure(text="◀")
            self.control_panel_visible = True

    def add_to_history(self):
        """Добавление текущей позиции в историю"""
        # Добавляем только если позиция значительно изменилась
        if len(self.target_history) == 0:
            self.target_history.appendleft((self.target_bearing, self.target_range, self.target_epr))
        else:
            last_bearing, last_range, last_epr = self.target_history[0]
            # Добавляем только если изменение больше порога
            if (abs(self.target_bearing - last_bearing) > 1.0 or 
                abs(self.target_range - last_range) > 0.1):
                self.target_history.appendleft((self.target_bearing, self.target_range, self.target_epr))

    def update_display(self):
        """Обновление дисплея"""
        self.draw_radar_display()
    
    def update_target_info(self):
        """Обновление текстовой информации о цели"""
        try:
            if hasattr(self, "info_label"):
                info_text = (
                    f"Дальность: {self.target_range:.2f} NM\n"
                    f"Пеленг:   {self.target_bearing:.1f}°\n"
                    f"ЭПР:      {self.target_epr:.2f} м²\n"
                    f"Аспект:   {self.aspect_angle:.1f}°"
                )
                self.info_label.config(text=info_text)
        except Exception:
            pass

    def random_target(self):
        """Создание случайной цели"""
        self.target_bearing = random.uniform(0, 360)
        self.target_range = random.uniform(2, max(3, self.range_scale - 2))
        self.target_epr = random.uniform(0.1, 10.0)
        self.target_length = random.uniform(5, 200)
        self.target_width = random.uniform(2, 50)
        self.aspect_angle = random.uniform(0, 90)
        self.target_number = random.randint(1, 99)
        self.bearing_var.set(self.target_bearing)
        self.range_var.set(self.target_range)
        self.epr_var.set(self.target_epr)
        self.length_var.set(self.target_length)
        self.width_var.set(self.target_width)
        self.aspect_var.set(self.aspect_angle)
        self.bearing_value_label.configure(text=f"{self.target_bearing:.0f}°")
        self.range_value_label.configure(text=f"{self.target_range:.1f} миль")
        self.epr_value_label.configure(text=f"{self.target_epr:.1f} м²")
        self.aspect_value_label.configure(text=f"{self.aspect_angle:.0f}°")
        self.add_to_history()
        self.draw_radar_display()

    def random_clutter(self):
        """Случайная настройка помех"""
        self.clutter_intensity = random.uniform(0.05, 0.95)
        self.clutter_var.set(self.clutter_intensity)
        self.clutter_value_label.configure(text=f"{int(self.clutter_intensity*100)}%")
        self.draw_radar_display()

    def new_coastline(self):
        """Генерация новой береговой линии"""
        self.coastline_points = self.generate_coastline()
        self.draw_radar_display()

    # ---------------- ИМИТАЦИЯ ДВИЖЕНИЯ ЦЕЛИ ----------------
    def start_movement(self):
        """Запуск имитации движения цели - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        if not self.target_moving:
            self.target_moving = True
            self.target_course_current = self.target_course
            self.target_speed_current = self.target_speed
            self.info_var.set("Имитация движения запущена")
            # Запускаем симуляцию
            self.simulate_movement()

    def stop_movement(self):
        """Остановка имитации движения цели"""
        self.target_moving = False
        self.info_var.set("Имитация движения остановлена")

    def simulate_movement(self):
        """Имитация движения цели по заданному курсу и скорости - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        if not self.target_moving:
            return

        try:
            # Вычисляем новые координаты цели
            # 1 узел = 1 морская миля в час = 1/3600 миль в секунду
            time_step = self.simulation_interval / 1000.0  # в секундах
            distance_moved = self.target_speed * time_step / 3600.0  # в милях
            
            # Преобразуем текущие полярные координаты в декартовы
            # Учитываем, что в полярных координатах:
            # x = range * sin(bearing), y = range * cos(bearing)
            current_x = self.target_range * math.sin(math.radians(self.target_bearing))
            current_y = self.target_range * math.cos(math.radians(self.target_bearing))
            
            # Вычисляем смещение по курсу (курс измеряется от севера по часовой стрелке)
            dx = distance_moved * math.sin(math.radians(self.target_course))
            dy = distance_moved * math.cos(math.radians(self.target_course))
            
            # Новые координаты
            new_x = current_x + dx
            new_y = current_y + dy
            
            # Преобразуем обратно в полярные координаты
            new_range = math.sqrt(new_x**2 + new_y**2)
            new_bearing = math.degrees(math.atan2(new_x, new_y)) % 360
            
            # Проверяем, не вышла ли цель за пределы радара
            if new_range >= self.range_scale - 0.5:
                self.info_var.set("Цель вышла за пределы радара")
                self.stop_movement()
                return
            
            # Обновляем позицию цели
            self.target_range = new_range
            self.target_bearing = new_bearing
            
            # Обновляем слайдеры и метки
            self.range_var.set(self.target_range)
            self.bearing_var.set(self.target_bearing)
            self.range_value_label.configure(text=f"{self.target_range:.1f} миль")
            self.bearing_value_label.configure(text=f"{self.target_bearing:.0f}°")
            
            # Добавляем в историю и перерисовываем
            self.add_to_history()
            self.draw_radar_display()
            
            # Планируем следующий шаг
            if self.target_moving:
                self.root.after(self.simulation_interval, self.simulate_movement)
                
        except Exception as e:
            self.info_var.set(f"Ошибка имитации: {str(e)}")
            self.stop_movement()

    # ---------------- ПРОЦЕДУРНАЯ ГЕНЕРАЦИЯ БЕРЕГОВОЙ ЛИНИИ ----------------
    def generate_coastline(self):
        """Генерация процедурной береговой линии - теперь ближе к краю"""
        points = []
        base_dir = (self.target_bearing + 120 + random.uniform(-20, 20)) % 360
        segments = 40
        
        # Берег теперь располагается ближе к краю развертки
        base_distance = self.range_scale * 0.75  # 75% от максимальной дальности
        
        for i in range(segments):
            angle = (base_dir - 60) + (i / (segments - 1)) * 120
            # Увеличиваем амплитуду колебаний для более интересной формы берега
            base_range = base_distance + math.sin(math.radians(i * 8 + random.uniform(-10, 10))) * (self.range_scale * 0.15)
            jitter = random.uniform(-self.range_scale * 0.05, self.range_scale * 0.05)
            r = max(self.range_scale * 0.5, min(self.range_scale - 1.0, base_range + jitter))
            points.append((angle % 360, r))
        
        # Сглаживание береговой линии
        smooth = []
        for i in range(len(points)):
            acc = 0.0
            cnt = 0
            for j in range(-2, 3):
                ni = (i + j) % len(points)
                acc += points[ni][1]
                cnt += 1
            avg = acc / cnt
            smooth.append((points[i][0], avg))
        return smooth

    # ---------------- ОБРАБОТЧИКИ ИЗМЕНЕНИЯ РАЗМЕРА ----------------
    def on_resize(self, event):
        """Обработчик изменения размера холста"""
        self.draw_radar_display()

    def on_root_configure(self, event):
        """Обработчик изменения размера окна"""
        self.draw_radar_display()


# ---------------- ОСНОВНАЯ ПРОГРАММА ----------------
def main():
    try:
        import customtkinter as ctk
    except ImportError:
        print("Установите customtkinter: pip install customtkinter")
        return

    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("ИКО - Индикатор кругового обзора")
    root.geometry("1200x850")

    app = ИКО(root)
    root.mainloop()

if __name__ == "__main__":
    main()