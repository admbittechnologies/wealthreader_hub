# Copyright (c) 2026, ADMBit Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, formatdate, getdate, today

from wealthreader_hub.wealthreader_hub.utils import (
	get_hub_config,
	get_signing_secret,
	sign_payload,
	verify_payload,
)


@frappe.whitelist(methods=["POST"], allow_guest=True)
def activate():
	"""Client site calls this with an activation key to receive its configuration."""
	data = frappe.parse_json(frappe.request.get_data(as_text=True) or "{}")
	activation_key = data.get("activation_key")
	site_url = data.get("site_url")
	site_name = data.get("site_name")

	if not activation_key:
		return _error("activation_key is required")

	customer = frappe.get_doc("Wealthreader Customer", {"activation_key": activation_key})
	if not customer:
		return _error("Invalid activation key")

	if customer.status != "Active":
		return _error(f"Customer account is {customer.status}")

	if customer.expiry_date and getdate(customer.expiry_date) < today():
		customer.status = "Expired"
		customer.save()
		return _error("Activation key expired")

	if site_url:
		customer.site_url = site_url
	if site_name:
		customer.site_name = site_name
	customer.save()

	config = get_hub_config()
	if not config.api_key:
		return _error("Wealthreader API key is not configured in the hub")

	response_payload = {
		"api_key": config.get_password("api_key"),
		"environment": config.environment,
		"widget_domain": config.default_widget_domain,
		"allowed_connections": customer.allowed_connections,
		"expiry_date": formatdate(customer.expiry_date) if customer.expiry_date else None,
		"usage_report_url": "/api/method/wealthreader_hub.wealthreader_hub.api.report_usage",
	}

	secret = get_signing_secret()
	response_payload["signature"] = sign_payload(response_payload, secret)

	return {"status": "ok", "data": response_payload}


@frappe.whitelist(methods=["POST"], allow_guest=True)
def report_usage():
	"""Receive a signed daily usage report from a client site."""
	data = frappe.parse_json(frappe.request.get_data(as_text=True) or "{}")

	activation_key = data.get("activation_key")
	signature = data.pop("signature", None)

	if not activation_key or not signature:
		return _error("activation_key and signature are required")

	customer = frappe.get_doc("Wealthreader Customer", {"activation_key": activation_key})
	if not customer:
		return _error("Invalid activation key")

	secret = get_signing_secret()
	if not verify_payload(data, signature, secret):
		return _error("Invalid signature")

	active_connections = cint(data.get("active_connections"))
	report_date = data.get("report_date") or today()

	# Update customer timestamp
	customer.last_usage_report = frappe.utils.now()
	customer.save()

	# Avoid duplicate reports for the same day
	existing = frappe.db.exists(
		"Wealthreader Usage Report",
		{"customer": customer.name, "report_date": report_date},
	)
	if existing:
		report = frappe.get_doc("Wealthreader Usage Report", existing)
	else:
		report = frappe.get_doc(
			{
				"doctype": "Wealthreader Usage Report",
				"customer": customer.name,
				"report_date": report_date,
			}
		)

	report.active_connections = active_connections
	report.monthly_amount = active_connections * 15
	report.raw_payload = frappe.as_json(data)
	report.save(ignore_permissions=True)

	return {"status": "ok"}


@frappe.whitelist(methods=["POST"])
def revoke():
	"""Revoke a customer activation key."""
	data = frappe.parse_json(frappe.request.get_data(as_text=True) or "{}")
	activation_key = data.get("activation_key")
	if not activation_key:
		return _error("activation_key is required")

	customer = frappe.get_doc("Wealthreader Customer", {"activation_key": activation_key})
	if not customer:
		return _error("Invalid activation key")

	customer.status = "Inactive"
	customer.save()
	return {"status": "ok"}


def _error(message):
	frappe.response["http_status_code"] = 400
	return {"status": "error", "message": message}
