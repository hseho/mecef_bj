# -*- coding: utf-8 -*-
# Part of OpenEduCat. See LICENSE file for full copyright & licensing details.

##############################################################################
#
#    Global Network Services and Consulting Ltd.
#    Copyright (C) 2021-TODAY GlobalNet(<http://www.globalnetsc.com>).
#
#############################################################################

from odoo import models, fields


class ResUsers(models.Model):
    _inherit = "res.users"

    code = fields.Char('Code', size=2)

    _sql_constraints = [
        ('unique_code',
         'unique(code)', 'Code should be unique!'),
    ]

