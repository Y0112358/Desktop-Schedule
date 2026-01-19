import sys
import os
import sqlite3
import datetime
import threading
import time
from typing import List, Set

# UI Framework
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QDateEdit, QTimeEdit, 
    QCheckBox, QSystemTrayIcon, QMenu, QScrollArea, QFrame,
    QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QDate, QTime, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont, QAction, QColor, QPalette, QCursor

# Backend Logic
from apscheduler.schedulers.background import BackgroundScheduler
from plyer import notification
import google.generativeai as genai

# Configuration
DB_NAME = 'reminders.db'
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Database Manager ---
class DatabaseManager:
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                remind_time DATETIME NOT NULL,
                repeat_days TEXT, -- e.g., "1,3,5" (Mon, Wed, Fri)
                category TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def add_task(self, content, remind_time, repeat_days="", category="未分類"):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('''
            INSERT INTO reminders (content, remind_time, repeat_days, category, is_active)
            VALUES (?, ?, ?, ?, ?)
        ''', (content, remind_time.strftime('%Y-%m-%d %H:%M:%S'), repeat_days, category, 1))
        conn.commit()
        task_id = c.lastrowid
        conn.close()
        return task_id

    def get_active_tasks(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM reminders WHERE is_active = 1 ORDER BY remind_time ASC')
        rows = c.fetchall()
        conn.close()
        return rows
    
    def get_todays_tasks(self):
        # Logic: Get tasks that trigger today (either specific date match OR repeat day match)
        today = datetime.datetime.now()
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM reminders WHERE is_active = 1')
        all_tasks = c.fetchall()
        conn.close()
        
        todays_tasks = []
        weekday = str(today.weekday()) # 0=Mon, 6=Sun
        
        for task in all_tasks:
            task_time = datetime.datetime.strptime(task['remind_time'], '%Y-%m-%d %H:%M:%S')
            is_repeat = bool(task['repeat_days'])
            
            if is_repeat:
                if weekday in task['repeat_days'].split(','):
                    todays_tasks.append(task)
            else:
                if task_time.date() == today.date():
                    todays_tasks.append(task)
                    
        return todays_tasks

    def delete_task(self, task_id):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('DELETE FROM reminders WHERE id = ?', (task_id,))
        conn.commit()
        conn.close()

    def update_category(self, task_id, category):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('UPDATE reminders SET category = ? WHERE id = ?', (category, task_id))
        conn.commit()
        conn.close()

# --- AI Workers (QThread) ---
class AISummaryWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, tasks):
        super().__init__()
        self.tasks = tasks

    def run(self):
        if not GEMINI_API_KEY:
            self.finished.emit("請先設定 GEMINI_API_KEY 環境變數以啟用 AI 功能。")
            return

        if not self.tasks:
            self.finished.emit("今天沒有待辦事項，好好休息吧！")
            return

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')

        task_list_str = ""
        for t in self.tasks:
            time_str = datetime.datetime.strptime(t['remind_time'], '%Y-%m-%d %H:%M:%S').strftime('%H:%M')
            task_list_str += f"- {t['content']} ({time_str})\n"

        prompt = f"""
        你是一位專業的職場秘書。請閱讀以下今天的待辦事項，並以繁體中文撰寫一段 100 字以內的「今日重點摘要」。
        語氣要專業、溫柔且充滿活力。
        在摘要之後，請附上一句簡短的職場鼓勵語。

        待辦事項清單：
        {task_list_str}
        """

        try:
            response = model.generate_content(prompt)
            self.finished.emit(response.text)
        except Exception as e:
            self.finished.emit(f"AI 摘要生成失敗: {str(e)}")

class AICategorizeWorker(QThread):
    finished = pyqtSignal(int, str) # task_id, category

    def __init__(self, task_id, content):
        super().__init__()
        self.task_id = task_id
        self.content = content

    def run(self):
        if not GEMINI_API_KEY:
            self.finished.emit(self.task_id, "未分類")
            return

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        請將以下任務歸類為其中一個類別：研發, 行政, 個人, 其他。
        任務內容：{self.content}
        只需回傳類別名稱，不要有其他文字。
        """
        
        try:
            response = model.generate_content(prompt)
            category = response.text.strip()
            # Basic validation
            if category not in ['研發', '行政', '個人', '其他']:
                category = '其他'
            self.finished.emit(self.task_id, category)
        except:
            self.finished.emit(self.task_id, "其他")

# --- UI Components ---
class MinimalistStyle:
    STYLESHEET = """
    QMainWindow, QWidget {
        background-color: #FFFFFF;
        font-family: 'Segoe UI', sans-serif;
    }
    QLabel {
        color: #333333;
    }
    QLineEdit {
        border: none;
        border-bottom: 2px solid #F0F0F0;
        padding: 8px;
        font-size: 14px;
        background-color: transparent;
    }
    QLineEdit:focus {
        border-bottom: 2px solid #333333;
    }
    QPushButton {
        background-color: #FAFAFA;
        border: 1px solid #E0E0E0;
        border-radius: 6px;
        padding: 6px 12px;
        color: #555;
    }
    QPushButton:hover {
        background-color: #F0F0F0;
        border-color: #CCC;
        color: #333;
    }
    QPushButton#PrimaryButton {
        background-color: #333333;
        color: white;
        border: none;
        font-weight: bold;
    }
    QPushButton#PrimaryButton:hover {
        background-color: #000000;
    }
    QDateEdit, QTimeEdit {
        border: 1px solid #E0E0E0;
        border-radius: 4px;
        padding: 4px;
        background: white;
    }
    QCheckBox {
        spacing: 5px;
        color: #666;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1px solid #CCC;
        border-radius: 3px;
    }
    QCheckBox::indicator:checked {
        background-color: #333;
        border-color: #333;
    }
    QScrollArea {
        border: none;
        background-color: transparent;
    }
    """

class TaskWidget(QFrame):
    def __init__(self, task_id, content, time_str, repeat_str, category, delete_callback):
        super().__init__()
        self.task_id = task_id
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("""
            QFrame {
                background-color: #FAFAFA;
                border-radius: 8px;
                margin-bottom: 8px;
            }
            QLabel#Content {
                font-size: 14px;
                font-weight: 500;
            }
            QLabel#Meta {
                color: #888;
                font-size: 11px;
            }
            QLabel#Category {
                background-color: #EFEFEF;
                color: #666;
                padding: 2px 6px;
                border-radius: 4px;
                font-size: 10px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Info Layout
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        # Top Row: Content + Category
        top_row = QHBoxLayout()
        self.content_label = QLabel(content)
        self.content_label.setObjectName("Content")
        self.category_label = QLabel(category)
        self.category_label.setObjectName("Category")
        
        top_row.addWidget(self.content_label)
        top_row.addWidget(self.category_label)
        top_row.addStretch()
        
        # Bottom Row: Time + Repeat
        meta_text = f"⏰ {time_str}"
        if repeat_str:
            days_map = {'0':'週一','1':'週二','2':'週三','3':'週四','4':'週五','5':'週六','6':'週日'}
            days_labels = [days_map[d] for d in repeat_str.split(',')]
            meta_text += f" | 🔁 {','.join(days_labels)}"
        else:
            meta_text += " | 📅 單次"
            
        self.meta_label = QLabel(meta_text)
        self.meta_label.setObjectName("Meta")
        
        info_layout.addLayout(top_row)
        info_layout.addWidget(self.meta_label)
        
        layout.addLayout(info_layout)
        
        # Delete Button
        self.del_btn = QPushButton("✕")
        self.del_btn.setFixedSize(30, 30)
        self.del_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent; border: none; color: #BBB; font-size: 16px;
            }
            QPushButton:hover {
                color: #FF5555; background-color: transparent;
            }
        """)
        self.del_btn.clicked.connect(lambda: delete_callback(self.task_id))
        layout.addWidget(self.del_btn)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.setWindowTitle("AI Smart Desktop Assistant")
        self.setWindowIcon(QIcon("icon.png")) # Placeholder
        self.resize(450, 700)
        self.init_ui()
        self.init_tray()
        self.init_scheduler()
        
        # Apply minimalist styles
        self.setStyleSheet(MinimalistStyle.STYLESHEET)
        
        # Startup AI Summary (simulated "daily first launch" logic could be added)
        QTimer.singleShot(1000, self.generate_daily_summary)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(25, 25, 25, 25)

        # 1. Header with AI Button
        header_layout = QHBoxLayout()
        title = QLabel("待辦事項")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        
        self.ai_btn = QPushButton("✨ AI 今日摘要")
        self.ai_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ai_btn.clicked.connect(self.generate_daily_summary)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.ai_btn)
        main_layout.addLayout(header_layout)

        # 2. Input Area
        input_group = QFrame()
        input_group.setObjectName("InputGroup")
        input_layout = QVBoxLayout(input_group)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        # Task Content
        self.content_input = QLineEdit()
        self.content_input.setPlaceholderText("輸入新任務 (例如：3D DRAM 研發進度會議)...")
        input_layout.addWidget(self.content_input)
        
        # Date & Time Row
        dt_row = QHBoxLayout()
        
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True) # Dropdown calendar
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setFixedWidth(110)
        
        self.time_edit = QTimeEdit(QTime.currentTime())
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setFixedWidth(70)
        
        dt_row.addWidget(QLabel("日期:"))
        dt_row.addWidget(self.date_edit)
        dt_row.addWidget(QLabel("時間:"))
        dt_row.addWidget(self.time_edit)
        dt_row.addStretch()
        
        input_layout.addLayout(dt_row)
        
        # Quick Buttons
        quick_row = QHBoxLayout()
        btn_1h = QPushButton("+1 小時")
        btn_1h.clicked.connect(self.set_one_hour_later)
        btn_tmr = QPushButton("明天 09:00")
        btn_tmr.clicked.connect(self.set_tomorrow_morning)
        
        quick_row.addWidget(btn_1h)
        quick_row.addWidget(btn_tmr)
        quick_row.addStretch()
        input_layout.addLayout(quick_row)
        
        # Repeats (Mon-Sun)
        self.day_checks = []
        days_layout = QHBoxLayout()
        days_layout.setSpacing(10)
        days = ['一', '二', '三', '四', '五', '六', '日']
        for i, d in enumerate(days):
            chk = QCheckBox(d)
            self.day_checks.append(chk)
            days_layout.addWidget(chk)
        
        input_layout.addWidget(QLabel("重複週期:"))
        input_layout.addLayout(days_layout)
        
        # Add Button
        self.add_btn = QPushButton("新增任務")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self.add_task)
        input_layout.addWidget(self.add_btn)
        
        main_layout.addWidget(input_group)

        # 3. Task List
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.task_container = QWidget()
        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.task_container)
        
        main_layout.addWidget(self.scroll_area)
        
        # Load initial tasks
        self.refresh_task_list()

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        # Use a simple icon or a standard system icon if file not found
        self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        
        # Tray Menu
        menu = QMenu()
        
        action_show = QAction("開啟設定 / 主介面", self)
        action_show.triggered.connect(self.show_normal)
        menu.addAction(action_show)
        
        action_summary = QAction("AI 今日摘要", self)
        action_summary.triggered.connect(self.generate_daily_summary)
        menu.addAction(action_summary)
        
        menu.addSeparator()
        
        action_exit = QAction("結束程式", self)
        action_exit.triggered.connect(self.quit_app)
        menu.addAction(action_exit)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def init_scheduler(self):
        # Using APScheduler for precision
        self.scheduler = BackgroundScheduler()
        # Check every 30 seconds
        self.scheduler.add_job(self.check_reminders, 'interval', seconds=30)
        self.scheduler.start()
        
        # Keep track of notified tasks to prevent double notification in the same minute
        self.notified_cache = set() 

    # --- Logic ---

    def set_one_hour_later(self):
        now = datetime.datetime.now()
        target = now + datetime.timedelta(hours=1)
        self.date_edit.setDate(target.date())
        self.time_edit.setTime(target.time())

    def set_tomorrow_morning(self):
        now = datetime.datetime.now()
        target = now + datetime.timedelta(days=1)
        target = target.replace(hour=9, minute=0)
        self.date_edit.setDate(target.date())
        self.time_edit.setTime(target.time())

    def add_task(self):
        content = self.content_input.text().strip()
        if not content:
            return

        date = self.date_edit.date().toPyDate()
        time_val = self.time_edit.time().toPyTime()
        dt = datetime.datetime.combine(date, time_val)
        
        repeat_days = []
        for i, chk in enumerate(self.day_checks):
            if chk.isChecked():
                repeat_days.append(str(i)) # 0=Mon
        
        repeat_str = ",".join(repeat_days)
        
        # Save to DB
        task_id = self.db.add_task(content, dt, repeat_str)
        
        # Trigger AI Categorization in background
        self.ai_cat_worker = AICategorizeWorker(task_id, content)
        self.ai_cat_worker.finished.connect(self.on_categorized)
        self.ai_cat_worker.start()
        
        # Reset UI
        self.content_input.clear()
        self.refresh_task_list()
        
        # Show temp category
        QMessageBox.information(self, "任務已新增", "任務已儲存！AI 正在背景進行分類...")

    def on_categorized(self, task_id, category):
        self.db.update_category(task_id, category)
        self.refresh_task_list()

    def refresh_task_list(self):
        # Clear list
        for i in reversed(range(self.task_layout.count())):
            widget = self.task_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Fetch active tasks
        tasks = self.db.get_active_tasks()
        
        for t in tasks:
            task_time = datetime.datetime.strptime(t['remind_time'], '%Y-%m-%d %H:%M:%S')
            time_display = task_time.strftime('%Y-%m-%d %H:%M')
            if t['repeat_days']:
                time_display = task_time.strftime('%H:%M') # Just show time for recurring
            
            w = TaskWidget(
                t['id'], t['content'], time_display, 
                t['repeat_days'], t['category'] or "分析中...", 
                self.delete_task_handler
            )
            self.task_layout.addWidget(w)

    def delete_task_handler(self, task_id):
        self.db.delete_task(task_id)
        self.refresh_task_list()

    def generate_daily_summary(self):
        tasks = self.db.get_todays_tasks()
        if not tasks:
            self.show_summary_popup("今日無任務", "今天沒有待辦事項，好好放鬆吧！")
            return

        self.ai_btn.setText("AI 生成中...")
        self.ai_btn.setEnabled(False)
        
        self.ai_worker = AISummaryWorker(tasks)
        self.ai_worker.finished.connect(self.on_summary_generated)
        self.ai_worker.start()

    def on_summary_generated(self, text):
        self.ai_btn.setText("✨ AI 今日摘要")
        self.ai_btn.setEnabled(True)
        self.show_summary_popup("AI 秘書摘要", text)

    def show_summary_popup(self, title, text):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()

    def check_reminders(self):
        now = datetime.datetime.now()
        tasks = self.db.get_active_tasks()
        
        for t in tasks:
            task_time = datetime.datetime.strptime(t['remind_time'], '%Y-%m-%d %H:%M:%S')
            repeat_days = t['repeat_days'].split(',') if t['repeat_days'] else []
            
            should_notify = False
            
            # Check Time Match (Hour and Minute)
            if task_time.hour == now.hour and task_time.minute == now.minute:
                # 1. One-time task: Check Date
                if not repeat_days:
                    if task_time.date() == now.date():
                        should_notify = True
                # 2. Recurring task: Check Weekday
                else:
                    current_weekday = str(now.weekday()) # 0=Mon
                    if current_weekday in repeat_days:
                        should_notify = True
            
            if should_notify:
                # Dedup key: ID + Day + Hour + Minute (avoids multi-firing in same minute)
                key = f"{t['id']}-{now.day}-{now.hour}-{now.minute}"
                if key not in self.notified_cache:
                    self.send_notification(t['content'])
                    self.notified_cache.add(key)
        
        # Cleanup cache periodically (optional, simple logic here)
        if len(self.notified_cache) > 1000:
            self.notified_cache.clear()

    def send_notification(self, message):
        try:
            notification.notify(
                title='AI Smart Assistant',
                message=message,
                app_name='AI Assistant',
                timeout=10
            )
        except Exception as e:
            print(f"Notification failed: {e}")

    # --- System Tray & Event Overrides ---
    
    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "AI Assistant",
                "程式已縮小至系統托盤",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            event.ignore()
        else:
            event.accept()

    def show_normal(self):
        self.show()
        self.setWindowState(Qt.WindowState.WindowNoState)
        self.activateWindow()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_normal()

    def quit_app(self):
        self.scheduler.shutdown()
        QApplication.quit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # Important for tray apps
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())