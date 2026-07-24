# Copyright (c) 2026, ADMBit Technologies and contributors
# For license information, please see license.txt

from urllib.parse import urlparse

import frappe
from frappe import _


def get_context(context):
	"""Render the public widget hosting page for a client site."""
	context.no_cache = 1

	activation_key = frappe.form_dict.get("activation_key")
	operation_id = frappe.form_dict.get("operation_id")
	product_types = frappe.form_dict.get("product_types") or "accounts,cards"
	date_from = frappe.form_dict.get("date_from") or ""
	callback_url = frappe.form_dict.get("callback_url")
	parent_origin = frappe.form_dict.get("parent_origin")

	# Allow the client site to embed this Hub-hosted widget in an iframe.
	try:
		response = getattr(frappe.local, "response", None) or frappe.response
		headers = getattr(response, "headers", None)
		if headers is not None:
			headers.pop("X-Frame-Options", None)
			frame_ancestors = "'self'"
			if parent_origin:
				frame_ancestors += f" {parent_origin}"
			headers["Content-Security-Policy"] = f"frame-ancestors {frame_ancestors}"
	except Exception:
		pass

	if not activation_key or not operation_id or not callback_url or not parent_origin:
		context.error = _("Missing required parameters.")
		return context

	customers = frappe.get_all(
		"Wealthreader Customer",
		filters={"activation_key": activation_key},
		fields=["name", "status", "site_url"],
		ignore_permissions=True,
	)
	if not customers:
		context.error = _("Invalid activation key.")
		return context

	customer = customers[0]
	if customer.status != "Active":
		context.error = _("Customer account is not active.")
		return context

	if customer.site_url and customer.site_url.rstrip("/") != parent_origin.rstrip("/"):
		context.error = _("Site URL does not match the registered customer.")
		return context

	# Remember where to forward the Wealthreader callback for this operation.
	frappe.cache.set_value(
		f"wr_callback_{operation_id}", callback_url, expires_in_sec=7200
	)

	context.operation_id = operation_id
	context.product_types = product_types
	context.date_from = date_from
	context.widget_domain = _host_from_url(frappe.utils.get_url())
	context.parent_origin = parent_origin
	context.error = None
	return context


def _host_from_url(url):
	if not url:
		return url
	parsed = urlparse(url)
	return parsed.netloc or url
