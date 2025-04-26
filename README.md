# K-Plate-Inventory-Tracker
K-Plate is a local food service provider aiming to expand its digital presence and optimize its back-office operations. The company faces challenges in digitally attracting its target audience and maintaining synchronized inventory data across both physical and online ordering channels using the Square Point of Sale (POS). 

Hardware
The administrative panel runs locally as a Python desktop application on K-Plate’s in-store devices. No dedicated server or cloud infrastructure is required for the backend. The only hardware requirement is a standard Windows or macOS machine capable of running Python applications, with at least 4 GB of RAM and 2 CPU cores to ensure smooth operation.

Software
The admin panel is developed in Python using the PyQt5 framework and compiled into a standalone executable for ease of installation. SQLite is used for local data storage, and the Square API is leveraged to sync sales and inventory data. The customer-facing website is managed through Weebly’s web-based content management system, which requires no additional software installations.

Scalability
The local application is optimized for small business operations but designed to support increased complexity over time. New menu items, meats, and prediction modules can be added without needing to modify the core structure. The system remains efficient even as more historical order data accumulates, and can be adapted for multi-location use if needed.

Security
The admin panel is password-protected and limited to authorized staff. Sensitive data, such as Square API credentials, is encrypted and stored securely on the local device. The system does not transmit customer information externally beyond Square’s secure API, ensuring compliance with basic data privacy standards.

Usage
The application is designed for staff with minimal technical expertise. All key functions—including inventory updates, meat usage tracking, and report generation—are accessible through an intuitive graphical interface. A brief training session and an included user manual ensure easy onboarding for future employees.

Look/Feel
The admin panel features a clean, professional interface consistent with K-Plate’s modern brand. Charts and data visualizations are styled for readability, with color-coded insights and organized tabs for inventory, analytics, and rewards. The customer-facing website retains K-Plate’s branding and is mobile-friendly, with a minimalist layout for quick browsing and ordering.

