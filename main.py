#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from collections import deque
import sys


# алгоритмическая часть
def northwest_corner(supply, demand, costs):
    # построение начального опорного плана методом северо-западного угла
    m = len(supply)
    n = len(demand)
    sup = supply[:]
    dem = demand[:]
    alloc = [[0] * n for _ in range(m)]
    basic = []
    i, j = 0, 0
    while i < m and j < n:
        qty = min(sup[i], dem[j])
        if qty > 0:
            alloc[i][j] = qty
            basic.append((i, j))
            sup[i] -= qty
            dem[j] -= qty
        # переход к следующей клетке
        if sup[i] == 0 and i < m - 1:
            i += 1
        elif dem[j] == 0 and j < n - 1:
            j += 1
        else:
            if sup[i] == 0 and dem[j] == 0:
                if i + 1 < m:
                    i += 1
                elif j + 1 < n:
                    j += 1
                else:
                    break
            elif sup[i] == 0:
                i += 1
            else:
                j += 1
    needed = m + n - 1
    # добавление нулевых базисных клеток при вырожденности
    if len(basic) < needed:
        all_cells = [(i, j) for i in range(m) for j in range(n)]
        for cell in all_cells:
            if cell not in basic and len(basic) < needed:
                basic.append(cell)
    return alloc, basic, sup, dem


def compute_potentials(basic, costs, m, n):
    # вычисление потенциалов строк u и столбцов v для базисных клеток
    u = [None] * m
    v = [None] * n
    row_adj = [[] for _ in range(m)]
    col_adj = [[] for _ in range(n)]
    for (i, j) in basic:
        row_adj[i].append(j)
        col_adj[j].append(i)
    u[0] = 0
    q = deque()
    q.append(('u', 0))
    # обход графа базисных клеток для расчёта потенциалов
    while q:
        typ, idx = q.popleft()
        if typ == 'u':
            for j in row_adj[idx]:
                if v[j] is None:
                    v[j] = costs[idx][j] - u[idx]
                    q.append(('v', j))
        else:
            for i in col_adj[idx]:
                if u[i] is None:
                    u[i] = costs[i][idx] - v[idx]
                    q.append(('u', i))
    # обнуление неопределённых потенциалов (несвязный базис)
    for i in range(m):
        if u[i] is None:
            u[i] = 0
    for j in range(n):
        if v[j] is None:
            v[j] = 0
    return u, v


def find_cycle(enter_cell, basic, m, n):
    # поиск замкнутого цикла для вводимой клетки методом BFS
    ei, ej = enter_cell
    adj_rows = [[] for _ in range(m)]
    adj_cols = [[] for _ in range(n)]
    for (i, j) in basic:
        adj_rows[i].append(j)
        adj_cols[j].append(i)
    parent = {}
    q = deque()
    start_node = ('r', ei)
    parent[start_node] = None
    q.append(start_node)
    target_found = None
    while q:
        node = q.popleft()
        typ, idx = node
        if typ == 'r':
            for j in adj_rows[idx]:
                next_node = ('c', j)
                if next_node not in parent:
                    parent[next_node] = node
                    q.append(next_node)
                    if j == ej:
                        target_found = next_node
                        break
        else:
            for i in adj_cols[idx]:
                next_node = ('r', i)
                if next_node not in parent:
                    parent[next_node] = node
                    q.append(next_node)
        if target_found:
            break
    if not target_found:
        raise RuntimeError("Цикл не найден")
    # восстановление пути от целевого узла к начальному
    path_nodes = []
    cur = target_found
    while cur is not None:
        path_nodes.append(cur)
        cur = parent[cur]
    path_nodes.reverse()
    cells = [enter_cell]
    for k in range(len(path_nodes) - 1):
        n1 = path_nodes[k]
        n2 = path_nodes[k + 1]
        if n1[0] == 'r' and n2[0] == 'c':
            i, j = n1[1], n2[1]
        elif n1[0] == 'c' and n2[0] == 'r':
            i, j = n2[1], n1[1]
        else:
            continue
        cells.append((i, j))
    return cells


class ModiOptimizer:
    # пошаговая оптимизация методом потенциалов (МОДИ)
    def __init__(self, alloc, basic, costs, supply, demand):
        self.alloc = [row[:] for row in alloc]
        self.basic = basic[:]
        self.costs = costs
        self.supply = supply
        self.demand = demand
        self.m = len(alloc)
        self.n = len(alloc[0])
        self.iteration = 0
        self.done = False

    def step(self):
        # выполнение одной итерации МОДИ. Возвращает словарь с результатами
        if self.done:
            return None
        self.iteration += 1
        u, v = compute_potentials(self.basic, self.costs, self.m, self.n)
        # поиск клетки с минимальной отрицательной оценкой
        min_delta = 0.0
        enter_cell = None
        for i in range(self.m):
            for j in range(self.n):
                if (i, j) not in self.basic:
                    d = self.costs[i][j] - (u[i] + v[j])
                    if d < min_delta - 1e-9:
                        min_delta = d
                        enter_cell = (i, j)
        if enter_cell is None or min_delta >= -1e-9:
            self.done = True
            return {
                'done': True,
                'iteration': self.iteration,
                'u': u, 'v': v,
                'min_delta': None,
                'enter_cell': None,
                'cycle': None,
                'theta': None,
                'leaving': None,
                'alloc': [row[:] for row in self.alloc],
                'basic': self.basic[:],
                'message': "Оптимальный план достигнут."
            }
        cycle = find_cycle(enter_cell, self.basic, self.m, self.n)
        # определение величины сдвига θ
        theta = float('inf')
        minus_cells = []
        for idx, cell in enumerate(cycle):
            if idx % 2 == 1:  # минусовые клетки
                i, j = cell
                val = self.alloc[i][j]
                if val < theta:
                    theta = val
                minus_cells.append(cell)
        if theta == float('inf'):
            theta = 0
        # обновление перевозок по циклу
        for idx, (i, j) in enumerate(cycle):
            if idx % 2 == 0:
                self.alloc[i][j] += theta
            else:
                self.alloc[i][j] -= theta
        # определение клетки, выводимой из базиса
        leaving = None
        for (i, j) in minus_cells:
            if self.alloc[i][j] == 0:
                leaving = (i, j)
                break
        if leaving is None and minus_cells:
            leaving = minus_cells[0]
        if leaving:
            self.basic.remove(leaving)
        self.basic.append(enter_cell)
        # добавление нулевых перевозок при вырожденности
        if len(self.basic) < self.m + self.n - 1:
            all_cells = [(i, j) for i in range(self.m) for j in range(self.n)]
            for cell in all_cells:
                if cell not in self.basic and len(self.basic) < self.m + self.n - 1:
                    self.basic.append(cell)
        return {
            'done': False,
            'iteration': self.iteration,
            'u': u, 'v': v,
            'min_delta': min_delta,
            'enter_cell': enter_cell,
            'cycle': cycle,
            'theta': theta,
            'leaving': leaving,
            'alloc': [row[:] for row in self.alloc],
            'basic': self.basic[:],
            'message': f"Итерация {self.iteration}: Δ = {min_delta:.2f}, ввод {enter_cell}, θ = {theta}"
        }


# графический интерфейс
class TransportApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Транспортная задача – метод потенциалов")
        self.root.geometry("900x700")
        self.optimizer = None
        self.initial_alloc = None
        self.initial_basic = None
        self.supply = []
        self.demand = []
        self.costs = []
        self.m = 0
        self.n = 0
        self.create_widgets()

    def create_widgets(self):
        # панель управления
        control_frame = ttk.Frame(self.root, padding=5)
        control_frame.pack(fill=tk.X)
        ttk.Label(control_frame, text="Поставщиков:").grid(row=0, column=0, padx=2)
        self.m_entry = ttk.Entry(control_frame, width=5)
        self.m_entry.grid(row=0, column=1, padx=2)
        ttk.Label(control_frame, text="Потребителей:").grid(row=0, column=2, padx=2)
        self.n_entry = ttk.Entry(control_frame, width=5)
        self.n_entry.grid(row=0, column=3, padx=2)
        ttk.Button(control_frame, text="Создать таблицы", command=self.create_tables).grid(row=0, column=4, padx=5)
        ttk.Button(control_frame, text="Решить (начальный план)", command=self.solve_initial).grid(row=0, column=5,
                                                                                                   padx=5)
        self.next_btn = ttk.Button(control_frame, text="Следующий шаг МОДИ", command=self.next_step, state=tk.DISABLED)
        self.next_btn.grid(row=0, column=6, padx=5)
        self.auto_btn = ttk.Button(control_frame, text="Авторешение", command=self.auto_solve, state=tk.DISABLED)
        self.auto_btn.grid(row=0, column=7, padx=5)
        ttk.Button(control_frame, text="Загрузить из файла", command=self.load_from_file).grid(row=0, column=8, padx=5)
        # фрейм для таблиц ввода
        self.input_frame = ttk.Frame(self.root)
        self.input_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        # текстовый лог
        self.log = scrolledtext.ScrolledText(self.root, height=15, font=("Courier", 10))
        self.log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        # таблица текущего плана
        self.plan_frame = ttk.Frame(self.root)
        self.plan_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        ttk.Label(self.plan_frame, text="Текущий план перевозок (базисные выделены жирным)").pack()
        self.plan_canvas = tk.Canvas(self.plan_frame, bg='white', height=150)
        self.plan_canvas.pack(fill=tk.BOTH, expand=True)

    def create_tables(self):
        # ограничения на размер задачи
        MAX_M = 10
        try:
            self.m = int(self.m_entry.get())
            self.n = int(self.n_entry.get())
            if self.m < 1 or self.n < 1:
                raise ValueError
            if self.m > MAX_M or self.n > MAX_M:
                messagebox.showerror(
                    "Ошибка",
                    f"Введите целые положительные числа: Поставщиков и потребителей должно быть от 1 до {MAX_M}"
                )
                return
        except ValueError:
            messagebox.showerror(
                "Ошибка",
                f"Введите целые положительные числа: Поставщиков и потребителей должно быть от 1 до {MAX_M}"
            )
            return
        # очистка фрейма ввода
        for widget in self.input_frame.winfo_children():
            widget.destroy()
        # создаём сетку для затрат
        ttk.Label(
            self.input_frame,
            text="Матрица тарифов (строки – поставщики, столбцы – потребители):"
        ).grid(row=0, column=0, columnspan=self.n + 2, sticky='w')
        self.cost_entries = []
        for i in range(self.m):
            row_entries = []
            ttk.Label(self.input_frame, text=f"A{i + 1}").grid(row=i + 1, column=0, padx=2, pady=2)
            for j in range(self.n):
                e = ttk.Entry(self.input_frame, width=6)
                e.grid(row=i + 1, column=j + 1, padx=1, pady=1)
                row_entries.append(e)
            self.cost_entries.append(row_entries)
        # запасы
        ttk.Label(self.input_frame, text="Запасы:").grid(
            row=self.m + 1, column=0, columnspan=self.n + 2, sticky='w', pady=(10, 0)
        )
        self.supply_entries = []
        for i in range(self.m):
            e = ttk.Entry(self.input_frame, width=8)
            e.grid(row=self.m + 2, column=i + 1, padx=2, pady=2)
            self.supply_entries.append(e)
        # потребности
        ttk.Label(self.input_frame, text="Потребности:").grid(
            row=self.m + 3, column=0, columnspan=self.n + 2, sticky='w', pady=(10, 0)
        )
        self.demand_entries = []
        for j in range(self.n):
            e = ttk.Entry(self.input_frame, width=8)
            e.grid(row=self.m + 4, column=j + 1, padx=2, pady=2)
            self.demand_entries.append(e)

    def load_from_file(self):
        # загрузка данных из текстового файла
        filepath = filedialog.askopenfilename(title="Выберите файл данных", filetypes=[("Text files", "*.txt")])
        if not filepath:
            return
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            if len(lines) < 4:
                raise ValueError("Файл должен содержать минимум 4 строки: размеры, матрица затрат, запасы, потребности")
            # первая строка: m n
            parts = lines[0].split()
            if len(parts) != 2:
                raise ValueError("Первая строка должна содержать два числа: m n")
            m, n = int(parts[0]), int(parts[1])
            MAX_M = 10
            if m < 1 or n < 1 or m > MAX_M or n > MAX_M:
                raise ValueError(f"m и n должны быть от 1 до {MAX_M}")
            if len(lines) < 1 + m + 2:
                raise ValueError(
                    "Недостаточно строк: ожидается матрица затрат (m строк), запасы (1 строка), потребности (1 строка)")
            # матрица затрат
            costs = []
            for i in range(1, 1 + m):
                row = list(map(int, lines[i].split()))
                if len(row) != n:
                    raise ValueError(f"Строка матрицы затрат {i} должна содержать {n} чисел")
                costs.append(row)
            # запасы
            supply = list(map(int, lines[1 + m].split()))
            if len(supply) != m:
                raise ValueError(f"Строка запасов должна содержать {m} чисел")
            # потребности
            demand = list(map(int, lines[1 + m + 1].split()))
            if len(demand) != n:
                raise ValueError(f"Строка потребностей должна содержать {n} чисел")

            # установка полей и создание таблицы
            self.m_entry.delete(0, tk.END)
            self.m_entry.insert(0, str(m))
            self.n_entry.delete(0, tk.END)
            self.n_entry.insert(0, str(n))
            self.create_tables()
            # заполнение полей
            for i in range(m):
                for j in range(n):
                    self.cost_entries[i][j].delete(0, tk.END)
                    self.cost_entries[i][j].insert(0, str(costs[i][j]))
            for i in range(m):
                self.supply_entries[i].delete(0, tk.END)
                self.supply_entries[i].insert(0, str(supply[i]))
            for j in range(n):
                self.demand_entries[j].delete(0, tk.END)
                self.demand_entries[j].insert(0, str(demand[j]))
            messagebox.showinfo("Успех", "Данные загружены из файла.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {e}")

    def get_input_data(self):
        # считывание данных из полей ввода
        try:
            costs = []
            for i in range(self.m):
                row = []
                for j in range(self.n):
                    val = int(self.cost_entries[i][j].get())
                    row.append(val)
                costs.append(row)
            supply = [int(e.get()) for e in self.supply_entries]
            demand = [int(e.get()) for e in self.demand_entries]
            return costs, supply, demand
        except ValueError:
            messagebox.showerror("Ошибка", "Все поля должны содержать целые числа")
            return None, None, None

    def solve_initial(self):
        # проверка что таблица создана
        if self.m == 0 or self.n == 0 or not self.cost_entries:
            messagebox.showwarning("Предупреждение",
                                   "Сначала создайте таблицу, указав количество поставщиков и потребителей.")
            return
        costs, supply, demand = self.get_input_data()
        if costs is None:
            return
        # балансировка задачи (добавление фиктивного поставщика/потребителя)
        total_supply = sum(supply)
        total_demand = sum(demand)
        if total_supply != total_demand:
            if total_supply < total_demand:
                diff = total_demand - total_supply
                supply.append(diff)
                costs.append([0] * self.n)
                self.m += 1
                messagebox.showinfo("Балансировка", f"Добавлен фиктивный поставщик A{self.m} с запасом {diff}")
            else:
                diff = total_supply - total_demand
                demand.append(diff)
                for row in costs:
                    row.append(0)
                self.n += 1
                messagebox.showinfo("Балансировка", f"Добавлен фиктивный потребитель B{self.n} с потребностью {diff}")
        self.costs = costs
        self.supply = supply
        self.demand = demand
        # построение начального плана
        alloc, basic, _, _ = northwest_corner(supply, demand, costs)
        self.initial_alloc = alloc
        self.initial_basic = basic
        self.optimizer = ModiOptimizer(alloc, basic, costs, supply, demand)
        # вывод начального плана
        self.log.delete(1.0, tk.END)
        self.log.insert(tk.END, "Начальный план (метод северо-западного угла):\n")
        self.print_plan(alloc, basic, "Начальный план")
        self.draw_plan(alloc, basic)
        self.next_btn.config(state=tk.NORMAL)
        self.auto_btn.config(state=tk.NORMAL)

    def next_step(self):
        # обработчик кнопки 'Следующий шаг МОДИ'
        if self.optimizer is None:
            return
        result = self.optimizer.step()
        if result is None:
            return
        self.log.insert(tk.END, f"\n{result['message']}\n")
        if not result['done']:
            self.log.insert(tk.END, f"Потенциалы u: {result['u']}\n")
            self.log.insert(tk.END, f"Потенциалы v: {result['v']}\n")
            self.log.insert(tk.END, f"Вводимая клетка: {result['enter_cell']}\n")
            self.log.insert(tk.END, f"Цикл: {result['cycle']}\n")
            self.log.insert(tk.END, f"Величина сдвига θ: {result['theta']}\n")
            if result['leaving']:
                self.log.insert(tk.END, f"Выводимая клетка: {result['leaving']}\n")
            self.print_plan(result['alloc'], result['basic'], f"После итерации {result['iteration']}")
            self.draw_plan(result['alloc'], result['basic'])
        else:
            self.log.insert(tk.END, "Задача решена!\n")
            self.print_plan(result['alloc'], result['basic'], "Оптимальный план")
            self.draw_plan(result['alloc'], result['basic'])
            total_cost = sum(result['alloc'][i][j] * self.costs[i][j]
                             for i in range(self.m) for j in range(self.n))
            self.log.insert(tk.END, f"\nМинимальная стоимость: {total_cost}\n")
            self.next_btn.config(state=tk.DISABLED)
            self.auto_btn.config(state=tk.DISABLED)
        self.log.see(tk.END)

    def auto_solve(self):
        # автоматическое выполнение всех итераций до оптимального плана
        if self.optimizer is None:
            return
        while not self.optimizer.done:
            self.next_step()
            self.root.update()

    def print_plan(self, alloc, basic, title):
        # форматированный вывод плана перевозок в текстовый лог
        self.log.insert(tk.END, f"\n{title}\n")
        self.log.insert(tk.END, "     " + "  ".join(f"B{j + 1:4d}" for j in range(self.n)) + "   Запасы\n")
        for i in range(self.m):
            line = f"A{i + 1}  "
            for j in range(self.n):
                if (i, j) in basic:
                    line += f"|{alloc[i][j]:3d}* "
                else:
                    line += f"| {alloc[i][j]:3d} "
            line += f"| {self.supply[i]:3d}\n"
            self.log.insert(tk.END, line)
        self.log.insert(tk.END, "     " + "  ".join(f"{d:5d}" for d in self.demand) + "   Потребности\n")

    def draw_plan(self, alloc, basic):
        # отрисовка текущего плана на Canvas
        self.plan_canvas.delete("all")
        cell_w = 60
        cell_h = 25
        x0, y0 = 40, 30
        # заголовки столбцов
        for j in range(self.n):
            x = x0 + (j + 1) * cell_w
            y = y0
            self.plan_canvas.create_text(x, y, text=f"B{j + 1}", font=("Arial", 10, "bold"))
        # заголовки строк
        for i in range(self.m):
            y = y0 + (i + 1) * cell_h
            self.plan_canvas.create_text(x0, y, text=f"A{i + 1}", font=("Arial", 10, "bold"))
        # ячейки таблицы
        for i in range(self.m):
            for j in range(self.n):
                x = x0 + (j + 1) * cell_w
                y = y0 + (i + 1) * cell_h
                val = alloc[i][j]
                txt = str(val) if val != 0 else "-"
                color = "black"
                font = ("Arial", 10, "bold" if (i, j) in basic else "normal")
                self.plan_canvas.create_text(x, y, text=txt, font=font, fill=color)
                # рамка ячейки
                self.plan_canvas.create_rectangle(x - cell_w // 2, y - cell_h // 2, x + cell_w // 2, y + cell_h // 2,
                                                  outline="gray")
        # запасы справа
        for i in range(self.m):
            x = x0 + (self.n + 1) * cell_w + 20
            y = y0 + (i + 1) * cell_h
            self.plan_canvas.create_text(x, y, text=str(self.supply[i]), font=("Arial", 10, "bold"))
        self.plan_canvas.create_text(x0 + (self.n + 1) * cell_w + 20, y0, text="Запасы", font=("Arial", 10, "bold"))
        # потребности снизу
        for j in range(self.n):
            x = x0 + (j + 1) * cell_w
            y = y0 + (self.m + 1) * cell_h + 10
            self.plan_canvas.create_text(x, y, text=str(self.demand[j]), font=("Arial", 10, "bold"))
        self.plan_canvas.create_text(x0, y0 + (self.m + 1) * cell_h + 10, text="Потр.", font=("Arial", 10, "bold"))


# запуск приложения
if __name__ == "__main__":
    root = tk.Tk()
    app = TransportApp(root)
    root.mainloop()