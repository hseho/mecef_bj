# -*- coding: utf-8 -*-
###############################################################################
#
#    Global Network Services and Consulting Ltd.
# #    Copyright (C) 2022-TODAY GlobalNet(<http://www.globalnetsc.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import api, fields, models, _
from datetime import datetime


class AccountMove(models.Model):
    _inherit = 'account.move'

    emecef_code = fields.Char('MECeF/DGI Code', size=30, readonly=True, store=True)
    emecef_counters = fields.Char('MECeF Counters', size=12, readonly=True, store=True)
    emecef_date_time = fields.Char('MECeF Time', size=30, readonly=True, store=True)
    emecef_date = fields.Date('MECeF Date', compute='_compute_emecef_date', store=True)
    emecef_nim = fields.Char('MECeF NIM', size=12, readonly=True, store=True)
    emecef_product_count = fields.Char(string="Product Count", readonly=True, store=True)
    emecef_qrcode = fields.Binary(string="MECeF QR Code", readonly=True, store=True)
    emecef_flag = fields.Boolean('MECeF Status')
    emecef_ref = fields.Char('MECeF Reference', readonly=True, store=True)

    @api.depends('emecef_date_time')
    def _compute_emecef_date(self):
        for record in self:
            if not record.emecef_date_time:
                record.emecef_date = None
            else:
                date_time_str = str(record.emecef_date_time)
                date_time_obj = (datetime.strptime(date_time_str, '%d/%m/%Y %H:%M:%S')).date()
                record.emecef_date = date_time_obj

