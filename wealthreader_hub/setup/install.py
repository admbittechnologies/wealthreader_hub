# Copyright (c) 2026, ADMBit Technologies and contributors
# For license information, please see license.txt

import frappe


def after_install():
    create_default_configuration()


def create_default_configuration():
    """Create the single Wealthreader Configuration record if it does not exist."""
    if not frappe.db.exists("Wealthreader Configuration", "Wealthreader Configuration"):
        config = frappe.get_doc(
            {
                "doctype": "Wealthreader Configuration",
                "environment": "sandbox",
                "default_widget_domain": frappe.utils.get_url(),
            }
        )
        config.insert()
