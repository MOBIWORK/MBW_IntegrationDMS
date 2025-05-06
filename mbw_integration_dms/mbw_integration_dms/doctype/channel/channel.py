# Copyright (c) 2025, MBW and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Channel(Document):
	def before_save(self):
		self.is_sync = 0
