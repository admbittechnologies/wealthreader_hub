# Copyright (c) 2026, ADMBit Technologies and contributors
# For license information, please see license.txt

app_name = "wealthreader_hub"
app_title = "Wealthreader Hub"
app_publisher = "ADMBit Technologies"
app_description = "Centralized management and billing hub for Wealthreader ERPNext integrations"
app_email = "info@admbit.com"
app_license = "MIT"
required_apps = ["frappe"]

after_install = "wealthreader_hub.setup.install.after_install"

scheduler_events = {
    "daily": [
        "wealthreader_hub.wealthreader_hub.doctype.wealthreader_customer.wealthreader_customer.send_expiry_reminders"
    ]
}
