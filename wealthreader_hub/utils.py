# Copyright (c) 2026, ADMBit Technologies and contributors
# For license information, please see license.txt

import hashlib
import hmac
import json


def sign_payload(payload: dict, secret: str) -> str:
	"""Return HMAC-SHA256 hex signature for a JSON payload."""
	canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
	return hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()


def verify_payload(payload: dict, signature: str, secret: str) -> bool:
	"""Verify an HMAC-SHA256 signature for a JSON payload."""
	expected = sign_payload(payload, secret)
	return hmac.compare_digest(expected, signature)


def get_signing_secret():
	import frappe

	config = frappe.get_single("Wealthreader Configuration")
	secret = config.get_password("signing_secret")
	if not secret:
		frappe.throw("Wealthreader Hub signing secret is not configured.")
	return secret


def get_hub_config():
	"""Return the single Wealthreader Configuration document."""
	import frappe

	return frappe.get_single("Wealthreader Configuration")
