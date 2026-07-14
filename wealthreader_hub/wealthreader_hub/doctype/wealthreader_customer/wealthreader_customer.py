# Copyright (c) 2026, ADMBit Technologies and contributors
# For license information, please see license.txt

import secrets

import frappe
from frappe.model.document import Document


class WealthreaderCustomer(Document):
	def validate(self):
		if not self.activation_key:
			self.activation_key = self.generate_activation_key()

	@staticmethod
	def generate_activation_key():
		return secrets.token_urlsafe(32)


def send_expiry_reminders():
	"""Scheduler hook to notify ADMBit about customers expiring soon."""
	from frappe.utils import add_days, today

	expiring = frappe.get_all(
		"Wealthreader Customer",
		filters={
			"status": "Active",
			"expiry_date": ["between", [today(), add_days(today(), 7)]],
		},
		fields=["name", "customer_name", "expiry_date"],
	)
	for customer in expiring:
		frappe.sendmail(
			recipients=[frappe.conf.get("auto_email_id") or "info@admbit.com"],
			subject="Wealthreader customer expiring soon",
			message=f"Customer {customer.customer_name} expires on {customer.expiry_date}.",
		)
