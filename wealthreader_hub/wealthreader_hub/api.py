# Copyright (c) 2026, ADMBit Technologies and contributors
# For license information, please see license.txt

import frappe
import requests
from functools import wraps
from frappe import _
from frappe.utils import cint, formatdate, getdate, today

from wealthreader_hub.wealthreader_hub.utils import (
	get_hub_config,
	get_signing_secret,
	sign_payload,
	verify_payload,
)


def _as_admin(fn):
	"""Run an allow_guest endpoint as Administrator so DocType permissions are satisfied."""

	@wraps(fn)
	def wrapper(*args, **kwargs):
		original_user = frappe.session.user
		frappe.set_user("Administrator")
		try:
			return fn(*args, **kwargs)
		finally:
			frappe.set_user(original_user)

	return wrapper


@frappe.whitelist(methods=["POST"], allow_guest=True)
@_as_admin
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
@_as_admin
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


@frappe.whitelist(methods=["POST"], allow_guest=True)
@_as_admin
def register_domain():
	"""Register a client site's domain and callback URL with Wealthreader.

	This lets ADMBit keep the shared Wealthreader API key in the Hub while
	client sites are provisioned automatically.
	"""
	data = frappe.parse_json(frappe.request.get_data(as_text=True) or "{}")
	activation_key = data.get("activation_key")
	site_url = data.get("site_url")
	callback_url = data.get("callback_url")

	if not activation_key:
		return _error("activation_key is required")

	customer = frappe.get_doc("Wealthreader Customer", {"activation_key": activation_key})
	if not customer:
		return _error("Invalid activation key")

	if customer.status != "Active":
		return _error(f"Customer account is {customer.status}")

	config = get_hub_config()
	api_key = config.get_password("api_key")
	if not api_key:
		return _error("Wealthreader API key is not configured in the hub")

	domain = (site_url or callback_url or customer.site_url or "").rstrip("/")
	if not domain:
		return _error("site_url or callback_url is required")

	wealthreader_url = "https://api.wealthreader.com/domains/"
	if config.environment == "sandbox":
		wealthreader_url = "https://sandbox.wealthreader.com/domains/"

	payload = {
		"method": "add",
		"api_key": api_key,
		"domain": domain,
		"access_type": "iframe",
	}
	if callback_url:
		payload["callback_url"] = callback_url

	try:
		response = requests.post(wealthreader_url, data=payload, timeout=30)
		response.raise_for_status()
		try:
			result = response.json()
		except ValueError:
			result = {"body": response.text}
		return {"status": "ok", "data": result}
	except requests.exceptions.HTTPError as e:
		message = f"Wealthreader domain registration failed: {e.response.status_code} - {e.response.text[:500]}"
		frappe.log_error(message, _("Wealthreader Domain Registration"))
		return _error(message)
	except requests.exceptions.RequestException as e:
		message = f"Wealthreader domain registration request error: {str(e)}"
		frappe.log_error(message, _("Wealthreader Domain Registration"))
		return _error(message)


def _error(message):
	frappe.response["http_status_code"] = 400
	return {"status": "error", "message": message}
