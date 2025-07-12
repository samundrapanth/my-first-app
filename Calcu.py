import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QDateEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QGroupBox, QSpinBox
)
from PyQt5.QtCore import Qt, QDate
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import datetime

# Nepali months mapping (index 1 = Baisakh, ... 12 = Chaitra)
NEPALI_MONTHS = [
    "", "Baisakh", "Jestha", "Ashar", "Shrawan", "Bhadra", "Ashwin", "Kartik",
    "Mangsir", "Poush", "Magh", "Falgun", "Chaitra"
]

def eng_to_nep(eng_date: QDate):
    ad_year, ad_month, ad_day = eng_date.year(), eng_date.month(), eng_date.day()
    if ad_month < 4:
        bs_year = ad_year + 56
    else:
        bs_year = ad_year + 57
    nep_month = ((ad_month + 8 - 1) % 12) + 1
    return bs_year, nep_month, ad_day

def nep_to_eng(bs_year, nep_month, nep_day):
    if nep_month >= 1:
        ad_year = bs_year - 57
    else:
        ad_year = bs_year - 56
    ad_month = ((nep_month - 8 - 1) % 12) + 1
    return QDate(ad_year, ad_month, nep_day)

def qdate_to_datetime(qdate):
    return datetime.date(qdate.year(), qdate.month(), qdate.day())

class NepaliDatePicker(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout()
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2000, 2100)
        self.month_combo = QComboBox()
        self.month_combo.addItems(NEPALI_MONTHS[1:])
        self.day_spin = QSpinBox()
        self.day_spin.setRange(1, 32)
        layout.addWidget(QLabel("Year"))
        layout.addWidget(self.year_spin)
        layout.addWidget(QLabel("Month"))
        layout.addWidget(self.month_combo)
        layout.addWidget(QLabel("Day"))
        layout.addWidget(self.day_spin)
        self.setLayout(layout)
        self.setMaximumHeight(40)

    def setDate(self, year, month, day):
        self.year_spin.setValue(year)
        self.month_combo.setCurrentIndex(month-1)
        self.day_spin.setValue(day)

    def date(self):
        return self.year_spin.value(), self.month_combo.currentIndex()+1, self.day_spin.value()

class ExpenseTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Daily Expense & Income Tracker")
        self.records = [] # Each record: {'type': 'expense'/'income', 'amount': float, 'category': str, 'date': datetime.date, 'calendar': str}
        self.language = 'English'
        self.time_format = '24h'
        self.init_ui()

    def init_ui(self):
        # Settings
        settings_box = QGroupBox("Settings")
        settings_layout = QHBoxLayout()
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Nepali"])
        self.language_combo.currentIndexChanged.connect(self.change_language)
        self.time_combo = QComboBox()
        self.time_combo.addItems(["24h", "12h"])
        self.time_combo.currentIndexChanged.connect(self.change_time_format)
        settings_layout.addWidget(QLabel("Language:"))
        settings_layout.addWidget(self.language_combo)
        settings_layout.addWidget(QLabel("Time Format:"))
        settings_layout.addWidget(self.time_combo)
        settings_box.setLayout(settings_layout)

        # Record Input
        input_box = QGroupBox("Add Income/Expense")
        input_layout = QHBoxLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Expense", "Income"])
        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("Amount")
        self.category_edit = QLineEdit()
        self.category_edit.setPlaceholderText("Category")
        self.calendar_combo = QComboBox()
        self.calendar_combo.addItems(["English", "Nepali"])
        self.calendar_combo.currentIndexChanged.connect(self.update_date_widgets)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.dateChanged.connect(self.sync_nepali_picker)

        self.nepali_picker = NepaliDatePicker()
        self.nepali_picker.setVisible(False)
        self.nepali_picker.year_spin.valueChanged.connect(self.sync_english_picker_from_nepali)
        self.nepali_picker.month_combo.currentIndexChanged.connect(self.sync_english_picker_from_nepali)
        self.nepali_picker.day_spin.valueChanged.connect(self.sync_english_picker_from_nepali)

        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self.add_record)

        input_layout.addWidget(QLabel("Type:"))
        input_layout.addWidget(self.type_combo)
        input_layout.addWidget(QLabel("Amount:"))
        input_layout.addWidget(self.amount_edit)
        input_layout.addWidget(QLabel("Category:"))
        input_layout.addWidget(self.category_edit)
        input_layout.addWidget(QLabel("Calendar:"))
        input_layout.addWidget(self.calendar_combo)
        input_layout.addWidget(QLabel("Date:"))
        input_layout.addWidget(self.date_edit)
        input_layout.addWidget(self.nepali_picker)
        input_layout.addWidget(self.add_btn)
        input_box.setLayout(input_layout)

        # Table for Records
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Type", "Amount", "Category", "Date", "Calendar"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Summary and Pie/Bar Chart Controls
        summary_box = QGroupBox("Summary & Chart")
        summary_layout = QHBoxLayout()

        self.period_combo = QComboBox()
        self.period_combo.addItems(["Week", "Month", "Year"])
        self.period_combo.currentIndexChanged.connect(self.update_summary_and_chart)

        self.summary_label = QLabel("Total Income: 0 | Total Expense: 0 | Balance: 0")

        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["Pie Chart", "Bar Chart"])
        self.chart_type_combo.currentIndexChanged.connect(self.update_summary_and_chart)

        self.chart_btn = QPushButton("Show Chart")
        self.chart_btn.clicked.connect(self.update_summary_and_chart)

        summary_layout.addWidget(QLabel("Period:"))
        summary_layout.addWidget(self.period_combo)
        summary_layout.addWidget(QLabel("Chart:"))
        summary_layout.addWidget(self.chart_type_combo)
        summary_layout.addWidget(self.chart_btn)
        summary_layout.addWidget(self.summary_label)
        summary_box.setLayout(summary_layout)

        # Chart
        self.figure = Figure(figsize=(4, 3))
        self.canvas = FigureCanvas(self.figure)

        # Main Layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(settings_box)
        main_layout.addWidget(input_box)
        main_layout.addWidget(self.table)
        main_layout.addWidget(summary_box)
        main_layout.addWidget(self.canvas)

        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        self.update_date_widgets()
        self.update_summary_and_chart()

    def update_date_widgets(self):
        if self.calendar_combo.currentText() == "Nepali":
            self.nepali_picker.setVisible(True)
            ad_date = self.date_edit.date()
            bs_year, nep_month, nep_day = eng_to_nep(ad_date)
            self.nepali_picker.setDate(bs_year, nep_month, nep_day)
        else:
            self.nepali_picker.setVisible(False)

    def sync_nepali_picker(self):
        if self.calendar_combo.currentText() == "Nepali":
            ad_date = self.date_edit.date()
            bs_year, nep_month, nep_day = eng_to_nep(ad_date)
            self.nepali_picker.setDate(bs_year, nep_month, nep_day)

    def sync_english_picker_from_nepali(self):
        if self.calendar_combo.currentText() == "Nepali":
            bs_year, nep_month, nep_day = self.nepali_picker.date()
            ad_date = nep_to_eng(bs_year, nep_month, nep_day)
            self.date_edit.setDate(ad_date)

    def add_record(self):
        try:
            rtype = self.type_combo.currentText().lower()
            amount = float(self.amount_edit.text())
            category = self.category_edit.text().strip()
            calendar = self.calendar_combo.currentText()
            if calendar == "Nepali":
                bs_year, nep_month, nep_day = self.nepali_picker.date()
                nepali_str = f"{bs_year} {NEPALI_MONTHS[nep_month]} {nep_day}"
                # internally store as English date for easier period calculations
                ad_date = nep_to_eng(bs_year, nep_month, nep_day)
                date_obj = qdate_to_datetime(ad_date)
                date_str = nepali_str
            else:
                qd = self.date_edit.date()
                date_obj = qdate_to_datetime(qd)
                date_str = qd.toString("yyyy-MM-dd")
            self.records.append({
                'type': rtype,
                'amount': amount,
                'category': category,
                'date': date_obj,
                'calendar': calendar,
                'display_date': date_str
            })
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(rtype.capitalize()))
            self.table.setItem(row, 1, QTableWidgetItem(f"{amount:.2f}"))
            self.table.setItem(row, 2, QTableWidgetItem(category))
            self.table.setItem(row, 3, QTableWidgetItem(date_str))
            self.table.setItem(row, 4, QTableWidgetItem(calendar))
            self.amount_edit.clear()
            self.category_edit.clear()
            self.update_summary_and_chart()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to add record: {e}")

    def filter_records_by_period(self):
        """Returns filtered records for the selected period (week/month/year)"""
        period = self.period_combo.currentText()
        today = datetime.date.today()
        filtered = []
        for rec in self.records:
            date = rec['date']
            if period == "Week":
                if date.isocalendar()[1] == today.isocalendar()[1] and date.year == today.year:
                    filtered.append(rec)
            elif period == "Month":
                if date.month == today.month and date.year == today.year:
                    filtered.append(rec)
            elif period == "Year":
                if date.year == today.year:
                    filtered.append(rec)
        return filtered

    def update_summary_and_chart(self):
        records = self.filter_records_by_period()
        income = sum(r['amount'] for r in records if r['type'] == 'income')
        expense = sum(r['amount'] for r in records if r['type'] == 'expense')
        balance = income - expense
        self.summary_label.setText(f"Total Income: {income:.2f} | Total Expense: {expense:.2f} | Balance: {balance:.2f}")
        self.draw_chart(records, income, expense)

    def draw_chart(self, records, income, expense):
        chart_type = self.chart_type_combo.currentText()
        self.figure.clear()
        if chart_type == "Pie Chart":
            ax = self.figure.add_subplot(121)
            ax2 = self.figure.add_subplot(122)
            # Pie chart for expenses by category (left)
            expense_cats = {}
            for r in records:
                if r['type'] == 'expense':
                    expense_cats[r['category']] = expense_cats.get(r['category'], 0) + r['amount']
            if expense_cats:
                ax.pie(expense_cats.values(), labels=expense_cats.keys(), autopct='%1.1f%%')
                ax.set_title("Expenses")
            else:
                ax.set_title("No Expenses")
            # Pie chart for income by category (right)
            income_cats = {}
            for r in records:
                if r['type'] == 'income':
                    income_cats[r['category']] = income_cats.get(r['category'], 0) + r['amount']
            if income_cats:
                ax2.pie(income_cats.values(), labels=income_cats.keys(), autopct='%1.1f%%')
                ax2.set_title("Income")
            else:
                ax2.set_title("No Income")
        else:  # Bar Chart
            # Show bar for total income and total expense in period
            ax = self.figure.add_subplot(111)
            ax.bar(["Income", "Expense"], [income, expense], color=["green", "red"])
            ax.set_ylabel("Amount")
            ax.set_title(f"Income vs Expense ({self.period_combo.currentText()})")
        self.canvas.draw()

    def change_language(self):
        self.language = self.language_combo.currentText()
        if self.language == "Nepali":
            self.setWindowTitle("दैनिक खर्च र आम्दानी ट्रैकर")
        else:
            self.setWindowTitle("Daily Expense & Income Tracker")

    def change_time_format(self):
        self.time_format = self.time_combo.currentText()
        # Implement actual time formatting if needed

if __name__ == "__main__":
    app = QApplication(sys.argv)
    tracker = ExpenseTracker()
    tracker.resize(1100, 700)
    tracker.show()
    sys.exit(app.exec_())