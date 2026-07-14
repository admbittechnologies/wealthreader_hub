# Copyright (c) 2026, ADMBit Technologies and contributors
# For license information, please see license.txt

import unittest

from wealthreader_hub.wealthreader_hub.utils import sign_payload, verify_payload


class TestUtils(unittest.TestCase):
	def test_sign_and_verify(self):
		secret = "test-secret"
		payload = {"site_name": "test", "active_connections": 3}
		signature = sign_payload(payload, secret)
		self.assertTrue(verify_payload(payload, signature, secret))

	def test_verify_with_wrong_secret_fails(self):
		secret = "test-secret"
		payload = {"site_name": "test", "active_connections": 3}
		signature = sign_payload(payload, secret)
		self.assertFalse(verify_payload(payload, signature, "wrong-secret"))

	def test_verify_with_tampered_payload_fails(self):
		secret = "test-secret"
		payload = {"site_name": "test", "active_connections": 3}
		signature = sign_payload(payload, secret)
		payload["active_connections"] = 99
		self.assertFalse(verify_payload(payload, signature, secret))
