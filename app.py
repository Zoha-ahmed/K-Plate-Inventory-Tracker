import sys
import os
import sqlite3
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QTabWidget, QTableWidget, 
                            QTableWidgetItem, QMessageBox, QHeaderView, QInputDialog, 
                            QDialog, QFormLayout, QSpinBox, QDialogButtonBox, QFrame,
                            QComboBox)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import datetime
import pytz
from dateutil import parser
from collections import defaultdict
import io
import random

class OrderAnalyticsFigure(FigureCanvas):
    """A class to create a matplotlib figure embedded in Qt"""
    def __init__(self, parent=None, width=10, height=6, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(OrderAnalyticsFigure, self).__init__(fig)
        
class KPlateAdminApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set window properties
        self.setWindowTitle("K-Plate Admin Panel")
        self.resize(800, 600)
        
        # Database path
        self.db_path = "kplate.db"
        self.create_db_tables()
        
        # Current user
        self.current_user = None
        
        # Theme mode (default to dark)
        self.theme_mode = "dark"
        
        # Set up UI
        self.init_ui()
        self.apply_theme()
        
    def create_db_tables(self):
        """Create database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        ''')
        
        # Create ingredients table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            expected_restock INTEGER DEFAULT 0
        )
        ''')
        
        # Create orders table for analytics
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            order_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            day_of_week INTEGER NOT NULL,
            hour INTEGER NOT NULL
        )
        ''')
        
        # Check if admin user exists, if not create one
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        admin = cursor.fetchone()
        if not admin:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                          ('admin', 'password'))  # In a real app, hash the password
            
            # Add initial inventory data
            initial_ingredients = [
                ('K-Plate', 562, 400),
                ('Spicy Chicken Plate', 190, 120),
                ('Spicy Pork Plate', 93, 60),
                ('Short Plate', 60, 40),
                ('Soy Chicken Plate', 44, 0),
                ('Beef Dumplings', 124, 80),
                ('Kimchi Dumplings', 48, 0),
                ('Fries', 46, 30),
                ('6 Wings', 60, 40),
                ('12 Wings', 24, 0),
                ('18 Wings', 6, 0),
                ('Mixed Veggie Plate', 22, 0)
            ]
            
            cursor.executemany(
                "INSERT INTO ingredients (name, quantity, expected_restock) VALUES (?, ?, ?)",
                initial_ingredients
            )
            
            # Generate initial mock order data
            self.generate_initial_order_data(cursor)
        
        conn.commit()
        conn.close()

    def generate_initial_order_data(self, cursor):
        """Generate initial order data and save to database"""
        # Define your local timezone
        local_tz = pytz.timezone('US/Pacific')
        
        # Create mock orders for the past 2 weeks (only if table is empty)
        cursor.execute("SELECT COUNT(*) FROM orders")
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Create a realistic distribution of orders
            # Create mock orders for the past 2 weeks
            start_date = datetime.datetime.now() - datetime.timedelta(weeks=2)
            
            order_data = []
            order_id = 1000
            
            # Create a realistic distribution with two peaks (lunch and dinner)
            for day_offset in range(14):
                current_date = start_date + datetime.timedelta(days=day_offset)
                weekday = current_date.weekday()
                
                # More orders on weekends (5=Sat, 6=Sun)
                num_orders = 50 if weekday >= 5 else 30
                
                for _ in range(num_orders):
                    # Create a bimodal distribution (lunch and dinner peaks)
                    hour = None
                    r = random.random()
                    
                    if r < 0.45:  # Lunch peak (11am-2pm)
                        hour = random.choice([11, 12, 13, 14])
                        # More orders at 12-1
                        if hour in [12, 13]:
                            if random.random() < 0.7:  # 70% chance to keep this hour
                                pass
                            else:
                                continue
                    elif r < 0.9:  # Dinner peak (5pm-8pm)
                        hour = random.choice([17, 18, 19, 20])
                        # More orders at 6-7pm
                        if hour in [18, 19]:
                            if random.random() < 0.7:  # 70% chance to keep this hour
                                pass
                            else:
                                continue
                    else:  # Some scattered orders throughout the day
                        hour = random.choice([10, 15, 16, 21, 22])
                        # Lower probability of keeping these hours
                        if random.random() < 0.3:  # 30% chance to keep
                            pass
                        else:
                            continue
                    
                    minute = random.randint(0, 59)
                    
                    # Create datetime in local timezone
                    order_time = current_date.replace(hour=hour, minute=minute, second=0)
                    
                    # Convert to UTC
                    order_time_utc = order_time.astimezone(pytz.UTC)
                    
                    # Format as ISO string for Square API compatibility
                    created_at = order_time_utc.isoformat()
                    
                    # Add to order data
                    order_data.append((
                        f"order_{order_id}",
                        created_at,
                        weekday,
                        hour
                    ))
                    
                    order_id += 1
            
            # Insert into database
            cursor.executemany(
                "INSERT INTO orders (order_id, created_at, day_of_week, hour) VALUES (?, ?, ?, ?)",
                order_data
            )
            print(f"Added {len(order_data)} mock orders to database")
        
    def check_orders_database(self):
        """Check the orders database and report status"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if orders table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                self.analytics_status.setText("Error: Orders table does not exist in database")
                conn.close()
                return False
            
            # Count orders
            cursor.execute("SELECT COUNT(*) FROM orders")
            count = cursor.fetchone()[0]
            
            if count == 0:
                # No orders found, regenerate sample data
                self.analytics_status.setText("No orders found. Generating sample data...")
                self.generate_initial_order_data(cursor)
                conn.commit()
                
                # Check count again
                cursor.execute("SELECT COUNT(*) FROM orders")
                new_count = cursor.fetchone()[0]
                self.analytics_status.setText(f"Generated {new_count} sample orders")
            else:
                self.analytics_status.setText(f"Found {count} orders in database")
            
            conn.close()
            return True
        except Exception as e:
            self.analytics_status.setText(f"Database error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
            
    def init_ui(self):
        """Initialize the user interface"""
        # Create central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Create stacked widgets for login and admin panel
        self.setup_login_ui()
        self.setup_admin_ui()
        
        # Initially show login screen
        self.admin_widget.hide()
        self.login_widget.show()
    
    def setup_login_ui(self):
        """Set up the login screen UI"""
        self.login_widget = QWidget()
        self.main_layout.addWidget(self.login_widget)
        
        # Login layout
        login_layout = QVBoxLayout(self.login_widget)
        
        # Theme toggle button
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Theme:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setCurrentIndex(0 if self.theme_mode == "dark" else 1)
        self.theme_combo.currentIndexChanged.connect(self.toggle_theme)
        theme_layout.addStretch()
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        login_layout.addLayout(theme_layout)
        
        # Title label
        title_label = QLabel("K-Plate Admin Panel")
        title_label.setFont(QFont("Arial", 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        login_layout.addWidget(title_label)
        
        # Login form container
        login_form_container = QFrame()
        login_form_container.setFrameShape(QFrame.StyledPanel)
        login_form_container.setMaximumWidth(400)
        login_form_container.setObjectName("loginForm")
        login_form_layout = QVBoxLayout(login_form_container)
        
        # Login form title
        login_title = QLabel("Admin Login")
        login_title.setFont(QFont("Arial", 16, QFont.Bold))
        login_title.setAlignment(Qt.AlignCenter)
        login_form_layout.addWidget(login_title)
        
        # Username
        username_label = QLabel("Username:")
        username_label.setObjectName("formLabel")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        self.username_input.setMinimumHeight(35)
        login_form_layout.addWidget(username_label)
        login_form_layout.addWidget(self.username_input)
        
        # Password
        password_label = QLabel("Password:")
        password_label.setObjectName("formLabel")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(35)
        login_form_layout.addWidget(password_label)
        login_form_layout.addWidget(self.password_input)
        
        # Login button
        login_button = QPushButton("Login")
        login_button.setObjectName("primaryButton")
        login_button.setMinimumHeight(40)
        login_button.clicked.connect(self.login)
        login_form_layout.addWidget(login_button, alignment=Qt.AlignCenter)
        
        # Error message
        self.login_error = QLabel("")
        self.login_error.setStyleSheet("color: #FF5252;")
        login_form_layout.addWidget(self.login_error, alignment=Qt.AlignCenter)
        
        # Add spacers and center the form
        login_layout.addStretch()
        login_layout.addWidget(login_form_container, alignment=Qt.AlignCenter)
        login_layout.addStretch()
    
    def setup_analytics_tab(self, tab):
        layout = QVBoxLayout(tab)
        
        # Title
        title = QLabel("Order Analytics")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        
        # Dropdown for selecting weekday
        weekday_layout = QHBoxLayout()
        weekday_label = QLabel("Select Day:")
        weekday_label.setObjectName("formLabel")
        
        self.weekday_combo = QComboBox()
        self.weekday_combo.addItems(["All Days", "Monday", "Tuesday", "Wednesday", 
                                    "Thursday", "Friday", "Saturday", "Sunday"])
        self.weekday_combo.currentIndexChanged.connect(self.update_analytics_chart)
        
        weekday_layout.addWidget(weekday_label)
        weekday_layout.addWidget(self.weekday_combo)
        weekday_layout.addStretch()
        layout.addLayout(weekday_layout)
        
        # Section for the chart
        chart_container = QWidget()
        chart_layout = QVBoxLayout(chart_container)
        
        # Create matplotlib figure
        self.order_figure = OrderAnalyticsFigure(width=10, height=6)
        chart_layout.addWidget(self.order_figure)
        
        # Add a refresh button
        #refresh_button = QPushButton("Refresh Data")
        #refresh_button.setObjectName("successButton")
        #refresh_button.setMinimumHeight(36)
        #refresh_button.clicked.connect(self.fetch_order_data)
        #chart_layout.addWidget(refresh_button, alignment=Qt.AlignRight)
        
        layout.addWidget(chart_container)
        
        # Add status label
        self.analytics_status = QLabel("Select a day to view order patterns")
        self.analytics_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.analytics_status)
        
        # List to store the order data
        self.orders_data = None
        self.weekday_orders = None
        
        # Set a timer to fetch data when the tab is shown
        QTimer.singleShot(500, self.fetch_order_data)

    def fetch_order_data(self):
        """Fetch order data from the database"""
        self.analytics_status.setText("Fetching order data...")
        
        # First check database status
        if not self.check_orders_database():
            return
        
        try:
            # Clear previous data
            self.orders_data = []
            
            # Clear previous figure
            if hasattr(self, 'order_figure') and self.order_figure:
                self.order_figure.figure.clear()
            
            # Get data from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all orders
            cursor.execute("SELECT order_id, created_at, day_of_week, hour FROM orders")
            orders_db = cursor.fetchall()
            conn.close()
            
            # Convert to dict format (similar to Square API format)
            for order_id, created_at, day_of_week, hour in orders_db:
                order = {
                    "id": order_id,
                    "created_at": created_at
                }
                self.orders_data.append(order)
            
            # Group the orders by weekday
            self.weekday_orders = self.group_orders_by_weekday(self.orders_data)
            
            # Update the chart for all days initially
            self.weekday_combo.setCurrentIndex(0)
            self.update_analytics_chart(0)
            
            self.analytics_status.setText(f"Order data loaded: {len(self.orders_data)} orders")
        except Exception as e:
            self.analytics_status.setText(f"Error loading order data: {str(e)}")
            import traceback
            traceback.print_exc()

    def group_orders_by_weekday(self, orders):
        """Group orders by weekday (Monday-Sunday)"""
        if not orders:
            return {}
        
        # Initialize a dictionary for orders by weekday
        weekday_orders = {i: [] for i in range(7)}
        
        # Get local timezone
        local_tz = pytz.timezone('US/Pacific')  # Replace with your business timezone
        
        weekday_names = {
            0: "Monday",
            1: "Tuesday",
            2: "Wednesday", 
            3: "Thursday",
            4: "Friday",
            5: "Saturday",
            6: "Sunday"
        }
        
        for order in orders:
            if order.get("created_at"):
                # Parse the UTC timestamp
                order_date_utc = parser.isoparse(order["created_at"])
                # Convert to local timezone
                order_date_local = order_date_utc.astimezone(local_tz)
                
                # Get weekday (0 = Monday, 6 = Sunday)
                weekday = order_date_local.weekday()
                
                # Add order to the appropriate weekday list
                weekday_orders[weekday].append(order)
        
        # Return dictionary with weekday names as keys
        return {weekday_names[day]: orders for day, orders in weekday_orders.items()}

    def update_analytics_chart(self, index=None):
        """Update the analytics chart based on the selected weekday"""
        if not self.weekday_orders:
            self.analytics_status.setText("No order data available")
            return
        
        selected_day = self.weekday_combo.currentText()
        
        # Define the local timezone 
        local_tz = pytz.timezone('US/Pacific')  # Replace with your business timezone
        
        # Set colors based on theme
        bar_color = 'skyblue' if self.theme_mode == "light" else '#2979FF'
        text_color = '#333333' if self.theme_mode == "light" else '#FFFFFF'
        grid_color = '#E0E0E0' if self.theme_mode == "light" else '#333333'
        bg_color = 'white' if self.theme_mode == "light" else '#201c1c'
        
        # Configure figure and axes background
        self.order_figure.figure.patch.set_facecolor(bg_color)
        
        if selected_day == "All Days":
            # Create a subplot for each day
            self.order_figure.figure.clear()
            
            # Update status message for All Days view
            self.analytics_status.setText(f"Showing order data for All Days")
            
            # Create a 3x3 grid of subplots (7 days + 2 empty)
            for i, day in enumerate(["Monday", "Tuesday", "Wednesday", 
                                    "Thursday", "Friday", "Saturday", "Sunday"]):
                
                orders = self.weekday_orders.get(day, [])
                
                # Create subplot (add 1 because subplot indices start at 1)
                ax = self.order_figure.figure.add_subplot(3, 3, i+1)
                
                # Count orders per hour
                hour_counts = defaultdict(int)
                for order in orders:
                    if order.get("created_at"):
                        dt_utc = parser.isoparse(order["created_at"])
                        dt_local = dt_utc.astimezone(local_tz)
                        hour_counts[dt_local.hour] += 1
                
                # Create a list of counts for each hour
                hours = list(range(24))
                counts = [hour_counts.get(hour, 0) for hour in hours]
                
                # Check if we have any data
                if sum(counts) == 0:
                    ax.text(0.5, 0.5, "No data", ha='center', va='center', color=text_color)
                    ax.set_facecolor(bg_color)
                else:
                    # Plot on the current subplot
                    ax.bar(hours, counts, color=bar_color)
                    ax.set_facecolor(bg_color)
                
                ax.set_title(day, color=text_color)
                ax.set_xlabel("Hour", color=text_color)
                ax.set_ylabel("Orders", color=text_color)
                ax.set_xticks([0, 6, 12, 18, 23])
                ax.tick_params(colors=text_color)
                
                # Only show grid if we have data
                if sum(counts) > 0:
                    ax.grid(axis='y', linestyle='--', alpha=0.7, color=grid_color)
            
            self.order_figure.figure.tight_layout()
        else:
            # Clear the current figure and create a new axis
            self.order_figure.figure.clear()
            self.order_figure.axes = self.order_figure.figure.add_subplot(111)
            
            # Get orders for the selected day
            orders = self.weekday_orders.get(selected_day, [])
            
            # Count orders per hour for the selected day
            hour_counts = defaultdict(int)
            for order in orders:
                if order.get("created_at"):
                    dt_utc = parser.isoparse(order["created_at"])
                    dt_local = dt_utc.astimezone(local_tz)
                    hour_counts[dt_local.hour] += 1
            
            # Create a list of counts for each hour
            hours = list(range(24))
            counts = [hour_counts.get(hour, 0) for hour in hours]
            
            # Set background color
            self.order_figure.axes.set_facecolor(bg_color)
            
            # Check if we have any data
            if sum(counts) == 0:
                self.order_figure.axes.text(0.5, 0.5, "No data available for this day", 
                                        ha='center', va='center', 
                                        fontsize=12, color=text_color)
                self.analytics_status.setText(f"No orders found for {selected_day}")
            else:
                # Plot the bar graph
                self.order_figure.axes.bar(hours, counts, color=bar_color)
                self.order_figure.axes.grid(axis='y', linestyle='--', alpha=0.7, color=grid_color)
                self.analytics_status.setText(f"Showing order data for {selected_day}")
            
            self.order_figure.axes.set_title(f"Order Frequency by Hour on {selected_day}", color=text_color)
            self.order_figure.axes.set_xlabel("Hour of Day (Local Time)", color=text_color)
            self.order_figure.axes.set_ylabel("Number of Orders", color=text_color)
            self.order_figure.axes.set_xticks(hours)
            self.order_figure.axes.tick_params(colors=text_color)
        
        # Update the figure
        self.order_figure.figure.canvas.draw()
    
    def setup_admin_ui(self):
        """Set up the admin panel UI"""
        self.admin_widget = QWidget()
        self.main_layout.addWidget(self.admin_widget)
        
        # Admin layout
        admin_layout = QVBoxLayout(self.admin_widget)
        
        # Header with logout button and theme toggle
        header = QWidget()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        
        # Theme toggle in header
        theme_label = QLabel("Theme:")
        theme_label.setObjectName("headerLabel")
        self.admin_theme_combo = QComboBox()
        self.admin_theme_combo.setObjectName("themeCombo")
        self.admin_theme_combo.addItems(["Dark", "Light"])
        self.admin_theme_combo.setCurrentIndex(0 if self.theme_mode == "dark" else 1)
        self.admin_theme_combo.currentIndexChanged.connect(self.toggle_theme)
        
        title_label = QLabel("K-Plate Admin Panel")
        title_label.setObjectName("headerTitle")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        
        logout_button = QPushButton("Logout")
        logout_button.setObjectName("warningButton")
        logout_button.clicked.connect(self.logout)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(theme_label)
        header_layout.addWidget(self.admin_theme_combo)
        header_layout.addWidget(logout_button)
        
        admin_layout.addWidget(header)
        
        # Welcome message
        self.welcome_label = QLabel()
        self.welcome_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.welcome_label.setObjectName("welcomeLabel")
        admin_layout.addWidget(self.welcome_label)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("tabWidget")
        
        # Current inventory tab
        current_tab = QWidget()
        self.tab_widget.addTab(current_tab, "Current Inventory")
        
        # Future inventory tab
        future_tab = QWidget()
        self.tab_widget.addTab(future_tab, "Future Inventory")
        
        # Add ingredient tab
        add_tab = QWidget()
        self.tab_widget.addTab(add_tab, "Add Ingredient")
        
        # Add analytics tab - NEW
        analytics_tab = QWidget()
        self.tab_widget.addTab(analytics_tab, "Analytics")
        
        # Add tab widget to layout
        admin_layout.addWidget(self.tab_widget)
        
        # Set up tabs
        self.setup_current_inventory_tab(current_tab)
        self.setup_future_inventory_tab(future_tab)
        self.setup_add_ingredient_tab(add_tab)
        self.setup_analytics_tab(analytics_tab)
    
    def setup_current_inventory_tab(self, tab):
        """Set up the current inventory tab"""
        layout = QVBoxLayout(tab)
        
        # Title
        title = QLabel("Current Inventory")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        
        # Table
        self.current_table = QTableWidget()
        self.current_table.setObjectName("inventoryTable")
        self.current_table.setColumnCount(3)
        self.current_table.setHorizontalHeaderLabels(["ID", "Ingredient", "Quantity"])
        self.current_table.setShowGrid(True)
        self.current_table.setAlternatingRowColors(True)
        
        # Set column widths
        self.current_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.current_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.current_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.current_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        update_button = QPushButton("Update Quantity")
        update_button.setObjectName("primaryButton")
        update_button.setMinimumHeight(36)
        update_button.clicked.connect(self.update_quantity)
        button_layout.addWidget(update_button)
        
        delete_button = QPushButton("Delete Ingredient")
        delete_button.setObjectName("warningButton")
        delete_button.setMinimumHeight(36)
        delete_button.clicked.connect(self.delete_ingredient)
        button_layout.addWidget(delete_button)
        
        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("successButton")
        refresh_button.setMinimumHeight(36)
        refresh_button.clicked.connect(lambda: self.load_ingredients(current=True))
        button_layout.addWidget(refresh_button)
        
        layout.addLayout(button_layout)
    
    def setup_future_inventory_tab(self, tab):
        """Set up the future inventory tab"""
        layout = QVBoxLayout(tab)
        
        # Title
        title = QLabel("Future Inventory Tracking")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        
        # Table
        self.future_table = QTableWidget()
        self.future_table.setObjectName("inventoryTable")
        self.future_table.setColumnCount(4)
        self.future_table.setHorizontalHeaderLabels(["ID", "Ingredient", "Expected Restock", "Predicted Inventory"])
        self.future_table.setShowGrid(True)
        self.future_table.setAlternatingRowColors(True)
        
        # Set column widths
        self.future_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.future_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.future_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.future_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.future_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        update_button = QPushButton("Update Expected Restock")
        update_button.setObjectName("primaryButton")
        update_button.setMinimumHeight(36)
        update_button.clicked.connect(self.update_restock)
        button_layout.addWidget(update_button)
        
        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("successButton")
        refresh_button.setMinimumHeight(36)
        refresh_button.clicked.connect(lambda: self.load_ingredients(future=True))
        button_layout.addWidget(refresh_button)
        
        layout.addLayout(button_layout)
    
    def setup_add_ingredient_tab(self, tab):
        """Set up the add ingredient tab"""
        layout = QVBoxLayout(tab)
        
        # Title
        title = QLabel("Add New Ingredient")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        
        # Form frame
        form_frame = QFrame()
        form_frame.setFrameShape(QFrame.StyledPanel)
        form_frame.setObjectName("formContainer")
        form_layout = QFormLayout(form_frame)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFormAlignment(Qt.AlignLeft)
        form_layout.setSpacing(15)
        
# Name field
        name_label = QLabel("Ingredient Name:")
        name_label.setObjectName("formLabel")
        self.new_name_input = QLineEdit()
        self.new_name_input.setMinimumHeight(36)
        form_layout.addRow(name_label, self.new_name_input)
        
        # Quantity field
        quantity_label = QLabel("Quantity:")
        quantity_label.setObjectName("formLabel")
        self.new_quantity_input = QSpinBox()
        self.new_quantity_input.setMinimumHeight(36)
        self.new_quantity_input.setMinimum(0)
        self.new_quantity_input.setMaximum(9999)
        form_layout.addRow(quantity_label, self.new_quantity_input)
        
        # Expected restock field
        restock_label = QLabel("Expected Restock:")
        restock_label.setObjectName("formLabel")
        self.new_restock_input = QSpinBox()
        self.new_restock_input.setMinimumHeight(36)
        self.new_restock_input.setMinimum(0)
        self.new_restock_input.setMaximum(9999)
        form_layout.addRow(restock_label, self.new_restock_input)
        
        # Add button
        add_button = QPushButton("Add Ingredient")
        add_button.setObjectName("primaryButton")
        add_button.setMinimumHeight(40)
        add_button.clicked.connect(self.add_ingredient)
        
        # Status message
        self.add_status = QLabel("")
        self.add_status.setAlignment(Qt.AlignCenter)
        
        # Add button container for centering
        button_container = QWidget()
        button_layout = QVBoxLayout(button_container)
        button_layout.addWidget(add_button, alignment=Qt.AlignCenter)
        button_layout.addWidget(self.add_status, alignment=Qt.AlignCenter)
        
        form_layout.addRow("", button_container)
        
        # Add form to layout with some spacing
        layout.addStretch()
        layout.addWidget(form_frame)
        layout.addStretch()
    
    def login(self):
        """Handle login attempt"""
        username = self.username_input.text()
        password = self.password_input.text()
        
        if not username or not password:
            self.login_error.setText("Please enter both username and password")
            return
        
        # Check credentials in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            self.current_user = username
            self.welcome_label.setText(f"Welcome, {self.current_user}")
            
            # Transfer theme setting
            self.admin_theme_combo.setCurrentIndex(self.theme_combo.currentIndex())
            
            # Switch to admin panel
            self.login_widget.hide()
            self.admin_widget.show()
            
            # Load data
            self.load_ingredients(current=True, future=True)
        else:
            self.login_error.setText("Invalid username or password")
    
    def logout(self):
        """Handle logout"""
        self.current_user = None
        self.username_input.clear()
        self.password_input.clear()
        self.login_error.clear()
        
        # Transfer theme setting
        self.theme_combo.setCurrentIndex(self.admin_theme_combo.currentIndex())
        
        # Switch to login screen
        self.admin_widget.hide()
        self.login_widget.show()
    
    def toggle_theme(self, index):
        """Toggle between light and dark themes"""
        self.theme_mode = "dark" if index == 0 else "light"
        
        # Sync both theme selectors
        if self.sender() == self.theme_combo:
            self.admin_theme_combo.setCurrentIndex(index)
        elif self.sender() == self.admin_theme_combo:
            self.theme_combo.setCurrentIndex(index)
            
        self.apply_theme()
        
        # Update analytics chart with new theme colors
        if hasattr(self, 'order_figure') and self.order_figure:
            # Update the chart with the new theme
            self.update_analytics_chart()
    
    def apply_theme(self):
        """Apply the current theme to the application"""
        if self.theme_mode == "dark":
            # Dark theme colors
            self.setStyleSheet("""
                QWidget {
                    background-color: #201c1c;
                    color: #FFFFFF;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                
                QLabel#headerTitle {
                    font-size: 18px;
                    font-weight: bold;
                    color: #FFFFFF;
                }
                
                QLabel#welcomeLabel {
                    color: #64B5F6;
                    margin: 10px;
                    font-size: 16px;
                }
                
                QLabel#sectionTitle {
                    color: #64B5F6;
                    margin-bottom: 10px;
                }
                
                QLabel#headerLabel {
                    color: #BBDEFB;
                }
                
                QLabel#formLabel {
                    color: #BBDEFB;
                    font-weight: bold;
                }
                
                QWidget#header {
                    background-color: #1E1E1E;
                    border-bottom: 1px solid #333333;
                    margin: 0;
                    padding: 10px;
                }
                
                QWidget#loginForm {
                    background-color: #1E1E1E;
                    border: 1px solid #333333;
                    border-radius: 8px;
                    padding: 20px;
                }
                
                QFrame#formContainer {
                    background-color: #1E1E1E;
                    border: 1px solid #333333;
                    border-radius: 8px;
                    padding: 20px;
                }
                
                QTabWidget::pane {
                    border: 1px solid #333333;
                    background-color: #1E1E1E;
                }
                
                QTabBar::tab {
                    background-color: #2D2D2D;
                    color: #BBDEFB;
                    padding: 8px 16px;
                    margin-right: 2px;
                    border: 1px solid #333333;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                
                QTabBar::tab:selected {
                    background-color: #1E1E1E;
                    border-bottom-color: #1E1E1E;
                    color: #FFFFFF;
                }
                
                QTableWidget {
                    background-color: #1E1E1E;
                    alternate-background-color: #2D2D2D;
                    border: 1px solid #333333;
                    gridline-color: #333333;
                }
                
                QTableWidget::item {
                    padding: 6px;
                    color: #FFFFFF;
                }
                
                QTableWidget::item:selected {
                    background-color: #2979FF;
                }
                
                QHeaderView::section {
                    background-color: #252525;
                    color: #FFFFFF;
                    padding: 6px;
                    border: 1px solid #333333;
                    font-weight: bold;
                }
                
                QLineEdit, QSpinBox, QComboBox {
                    background-color: #333333;
                    color: #FFFFFF;
                    border: 1px solid #555555;
                    padding: 5px;
                    border-radius: 4px;
                }
                
                QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                    border: 1px solid #2979FF;
                }
                
                QPushButton {
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                
                QPushButton#primaryButton {
                    background-color: #2979FF;
                    color: white;
                    border: none;
                }
                
                QPushButton#primaryButton:hover {
                    background-color: #2196F3;
                }
                
                QPushButton#primaryButton:pressed {
                    background-color: #0D47A1;
                }
                
                QPushButton#warningButton {
                    background-color: #F44336;
                    color: white;
                    border: none;
                }
                
                QPushButton#warningButton:hover {
                    background-color: #E53935;
                }
                
                QPushButton#warningButton:pressed {
                    background-color: #B71C1C;
                }
                
                QPushButton#successButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                }
                
                QPushButton#successButton:hover {
                    background-color: #43A047;
                }
                
                QPushButton#successButton:pressed {
                    background-color: #1B5E20;
                }
            """)
        else:
            # Light theme colors
            self.setStyleSheet("""
                QWidget {
                    background-color: #FFFFFF;
                    color: #333333;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                
                QLabel#headerTitle {
                    font-size: 18px;
                    font-weight: bold;
                    color: #FFFFFF;
                    background-color: transparent
                }
                
                QLabel#welcomeLabel {
                    color: #1976D2;
                    margin: 10px;
                    font-size: 16px;
                }
                
                QLabel#sectionTitle {
                    color: #1976D2;
                    margin-bottom: 10px;
                }
                
                QLabel#headerLabel {
                    color: #FFFFFF;
                    background-color: transparent;
                }
                
                QLabel#formLabel {
                    color: #424242;
                    font-weight: bold;
                }
                
                QWidget#header {
                    background-color: #2196F3;
                    border-bottom: 1px solid #1976D2;
                    margin: 0;
                    padding: 10px;
                }
                
                QWidget#loginForm {
                    background-color: #FFFFFF;
                    border: 1px solid #E0E0E0;
                    border-radius: 8px;
                    padding: 20px;
                }
                
                QFrame#formContainer {
                    background-color: #FFFFFF;
                    border: 1px solid #E0E0E0;
                    border-radius: 8px;
                    padding: 20px;
                }
                
                QTabWidget::pane {
                    border: 1px solid #E0E0E0;
                    background-color: #FFFFFF;
                }
                
                QTabBar::tab {
                    background-color: #EEEEEE;
                    color: #666666;
                    padding: 8px 16px;
                    margin-right: 2px;
                    border: 1px solid #E0E0E0;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                
                QTabBar::tab:selected {
                    background-color: #FFFFFF;
                    border-bottom-color: #FFFFFF;
                    color: #333333;
                }
                
                QTableWidget {
                    background-color: #FFFFFF;
                    alternate-background-color: #F5F5F5;
                    border: 1px solid #E0E0E0;
                    gridline-color: #E0E0E0;
                }
                
                QTableWidget::item {
                    padding: 6px;
                    color: #333333;
                }
                
                QTableWidget::item:selected {
                    background-color: #2196F3;
                    color: #FFFFFF;
                }
                
                QHeaderView::section {
                    background-color: #F5F5F5;
                    color: #333333;
                    padding: 6px;
                    border: 1px solid #E0E0E0;
                    font-weight: bold;
                }
                
                QLineEdit, QSpinBox, QComboBox {
                    background-color: #FFFFFF;
                    color: #333333;
                    border: 1px solid #BDBDBD;
                    padding: 5px;
                    border-radius: 4px;
                }
                
                QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                    border: 1px solid #2196F3;
                }
                
                QPushButton {
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                
                QPushButton#primaryButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                }
                
                QPushButton#primaryButton:hover {
                    background-color: #1E88E5;
                }
                
                QPushButton#primaryButton:pressed {
                    background-color: #0D47A1;
                }
                
                QPushButton#warningButton {
                    background-color: #F44336;
                    color: white;
                    border: none;
                }
                
                QPushButton#warningButton:hover {
                    background-color: #E53935;
                }
                
                QPushButton#warningButton:pressed {
                    background-color: #B71C1C;
                }
                
                QPushButton#successButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                }
                
                QPushButton#successButton:hover {
                    background-color: #43A047;
                }
                
                QPushButton#successButton:pressed {
                    background-color: #1B5E20;
                }
            """)
    
    def load_ingredients(self, current=False, future=False):
        """Load ingredients into tables"""
        # Get ingredients from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, quantity, expected_restock FROM ingredients ORDER BY name")
        ingredients = cursor.fetchall()
        conn.close()
        
        # Update current inventory table
        if current:
            self.current_table.setRowCount(0)  # Clear table
            
            for row, ingredient in enumerate(ingredients):
                id, name, quantity, _ = ingredient
                
                self.current_table.insertRow(row)
                self.current_table.setItem(row, 0, QTableWidgetItem(str(id)))
                self.current_table.setItem(row, 1, QTableWidgetItem(name))
                self.current_table.setItem(row, 2, QTableWidgetItem(str(quantity)))
        
        # Update future inventory table
        if future:
            self.future_table.setRowCount(0)  # Clear table
            
            for row, ingredient in enumerate(ingredients):
                id, name, quantity, expected = ingredient
                predicted = quantity + expected
                
                self.future_table.insertRow(row)
                self.future_table.setItem(row, 0, QTableWidgetItem(str(id)))
                self.future_table.setItem(row, 1, QTableWidgetItem(name))
                self.future_table.setItem(row, 2, QTableWidgetItem(str(expected)))
                self.future_table.setItem(row, 3, QTableWidgetItem(str(predicted)))
    
    def update_quantity(self):
        """Update the quantity of the selected ingredient"""
        selected_items = self.current_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select an ingredient to update")
            return
        
        # Get the row and ingredient ID
        row = selected_items[0].row()
        id_item = self.current_table.item(row, 0)
        name_item = self.current_table.item(row, 1)
        quantity_item = self.current_table.item(row, 2)
        
        if id_item and name_item and quantity_item:
            ingredient_id = int(id_item.text())
            ingredient_name = name_item.text()
            current_quantity = int(quantity_item.text())
            
            # Ask for new quantity
            new_quantity, ok = QInputDialog.getInt(
                self, "Update Quantity", 
                f"Enter new quantity for {ingredient_name}:",
                current_quantity, 0, 9999
            )
            
            if ok:
                # Update database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("UPDATE ingredients SET quantity = ? WHERE id = ?", (new_quantity, ingredient_id))
                conn.commit()
                conn.close()
                
                # Refresh tables
                self.load_ingredients(current=True, future=True)
                
                QMessageBox.information(self, "Success", f"{ingredient_name} quantity updated to {new_quantity}")
    
    def update_restock(self):
        """Update the expected restock amount for the selected ingredient"""
        selected_items = self.future_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select an ingredient to update")
            return
        
        # Get the row and ingredient ID
        row = selected_items[0].row()
        id_item = self.future_table.item(row, 0)
        name_item = self.future_table.item(row, 1)
        restock_item = self.future_table.item(row, 2)
        
        if id_item and name_item and restock_item:
            ingredient_id = int(id_item.text())
            ingredient_name = name_item.text()
            current_restock = int(restock_item.text())
            
            # Ask for new restock amount
            new_restock, ok = QInputDialog.getInt(
                self, "Update Expected Restock", 
                f"Enter new expected restock for {ingredient_name}:",
                current_restock, 0, 9999
            )
            
            if ok:
                # Update database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("UPDATE ingredients SET expected_restock = ? WHERE id = ?", (new_restock, ingredient_id))
                conn.commit()
                conn.close()
                
                # Refresh tables
                self.load_ingredients(current=True, future=True)
                
                QMessageBox.information(self, "Success", f"{ingredient_name} expected restock updated to {new_restock}")
    
    def delete_ingredient(self):
        """Delete the selected ingredient"""
        selected_items = self.current_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "Please select an ingredient to delete")
            return
        
        # Get the row and ingredient ID
        row = selected_items[0].row()
        id_item = self.current_table.item(row, 0)
        name_item = self.current_table.item(row, 1)
        
        if id_item and name_item:
            ingredient_id = int(id_item.text())
            ingredient_name = name_item.text()
            
            # Confirm deletion
            reply = QMessageBox.question(
                self, "Confirm Deletion", 
                f"Are you sure you want to delete {ingredient_name}?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Delete from database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM ingredients WHERE id = ?", (ingredient_id,))
                conn.commit()
                conn.close()
                
                # Refresh tables
                self.load_ingredients(current=True, future=True)
                
                QMessageBox.information(self, "Success", f"{ingredient_name} deleted successfully")
    
    def add_ingredient(self):
        """Add a new ingredient"""
        name = self.new_name_input.text()
        quantity = self.new_quantity_input.value()
        restock = self.new_restock_input.value()
        
        if not name:
            self.add_status.setText("Please enter an ingredient name")
            self.add_status.setStyleSheet("color: #FF5252;")
            return
        
        # Check if ingredient already exists
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ingredients WHERE name = ?", (name,))
        exists = cursor.fetchone()
        
        if exists:
            self.add_status.setText(f"Ingredient '{name}' already exists")
            self.add_status.setStyleSheet("color: #FF5252;")
            conn.close()
            return
        
        # Add to database
        cursor.execute(
            "INSERT INTO ingredients (name, quantity, expected_restock) VALUES (?, ?, ?)",
            (name, quantity, restock)
        )
        conn.commit()
        conn.close()
        
        # Refresh tables
        self.load_ingredients(current=True, future=True)
        
        # Clear form
        self.new_name_input.clear()
        self.new_quantity_input.setValue(0)
        self.new_restock_input.setValue(0)
        
        # Show success message
        self.add_status.setText(f"{name} added successfully")
        self.add_status.setStyleSheet("color: #4CAF50;")


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')  # Use Fusion style for a consistent look
    
    window = KPlateAdminApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()