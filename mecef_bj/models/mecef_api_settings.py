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
import pytz
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime
import json
import requests


class MECeFAPISettings(models.Model):
    _name = 'mecef.api.settings'
    _description = "MECeF API Settings"
    _inherit = ['mail.thread']

    name = fields.Char('Name')
    company_ifu = fields.Char('Company IFU')
    invoice_api_endpoint = fields.Char('Invoice API')
    information_api_endpoint = fields.Char('Information API')
    invoice_api_endpoint_test = fields.Char('Test Invoice API')
    information_api_endpoint_test = fields.Char('Test Information API')
    api_token = fields.Char('API Token')
    api_token_test = fields.Char('Test API Token')
    api_token_expiry = fields.Datetime('Token Expires', readonly=True)
    api_token_test_expiry = fields.Datetime('Token Expires', readonly=True)
    nim_production = fields.Char('NIM', readonly=True)
    nim_test = fields.Char(' NIM', readonly=True)
    state = fields.Selection(
        string="State",
        selection=[('disabled', "Disabled"), ('enabled', "Enabled"), ('test', "Test Mode")],
        default='disabled', required=True, tracking=True)
    token_status = fields.Selection(
        string="Token Status",
        selection=[('unauthorized', "Unauthorized"), ('valid', "Valid"), ('expired', "Expired")],
        default='unauthorized', required=True)
    token_status_test = fields.Selection(
        string="Token Status",
        selection=[('unauthorized', "Unauthorized"), ('valid', "Valid"), ('expired', "Expired")],
        default='unauthorized', required=True)
    website = fields.Char('API Website')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.user.company_id)

    # Message fields

    auth_msg_no_response = fields.Char(
        string="No response", help="The message displayed if server returned NO response",
        default=lambda self: _("Access to server failed. Please check the API configuration!"), translate=True)

    auth_msg_token_incorrect = fields.Char(
        string="Token Incorrect", help="The message displayed if authentication token is incorrect",
        default=lambda self: _("Access to server failed. Please check the API authentication Token!"), translate=True)

    auth_msg_token_expired = fields.Char(
        string="Token Expired", help="The message displayed if authentication token is expired",
        default=lambda self: _("Access to server failed. API authentication Token expired!"), translate=True)

    invoice_msg_api_status_check = fields.Char(
        string="API Status Check", help="The message displayed if API is invalid status",
        default=lambda self: _("Invoice cannot be processed now. \n\neMCF API is either not connected or not ready. Please contact the administrator!"), translate=True)

    def action_test(self):
        if self.token_status_test == 'unauthorized':
            error_msg = f"{self.auth_msg_no_response}"
            raise ValidationError(_('%s' % error_msg))
        elif self.token_status_test == 'expired':
            error_msg = f"{self.auth_msg_token_expired}"
            raise ValidationError(_('%s' % error_msg))

        self.state = 'test'
        return True

    def action_enable(self):
        if self.token_status == 'unauthorized':
            error_msg = f"{self.auth_msg_no_response}"
            raise ValidationError(_('%s' % error_msg))
        elif self.token_status == 'expired':
            error_msg = f"{self.auth_msg_token_expired}"
            raise ValidationError(_('%s' % error_msg))
        self.state = 'enable'
        return True

    def action_disable(self):
        self.state = 'disabled'
        return True

    def _send_authorization_request(self, api_url, token, uri: str = "", data: dict = None):
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        # if method.upper() == "GET":
        request = requests.get(
            f"{api_url}/{uri}", headers=headers, data=json.dumps(data) if data is not None else None
        )
        if not request:
            error_msg = f"{self.auth_msg_no_response}"
            raise ValidationError(_('%s' % error_msg))
        response = json.loads(request.content)

        return response

    def _get_connect_response_content(self, api_url, api_token):
        response = self._send_authorization_request(api_url, api_token)
        if not response.get("status"):
            error_msg = f"{self.auth_msg_no_response}"
            raise ValidationError(_('%s' % error_msg))

        elif response.get("status") == 401:  # Unauthorized
            error_msg = f"{self.auth_msg_token_expired}"
            raise ValidationError(_('%s' % error_msg))

        elif datetime.strptime(response.get("tokenValid"), "%Y-%m-%dT%H:%M:%S%z").replace(
                tzinfo=None
        ) <= datetime.utcnow().replace(
            tzinfo=None
        ):  # Token Validity expired
            error_msg = f"{self.auth_msg_token_expired}"
            raise ValidationError(_('%s' % error_msg))

        response_content = {
            'ifu': response.get("ifu"),
            'nim': response.get("nim"),
            'token_valid': datetime.strptime(response.get("tokenValid"), "%Y-%m-%dT%H:%M:%S%z").replace(
                tzinfo=None)
        }

        return response_content

    def action_check_test_api_access(self):

        api_url = f"{self.invoice_api_endpoint_test}"
        api_token = f"{self.api_token_test}"
        response_content = self._get_connect_response_content(api_url, api_token)
        ifu = self.company_ifu
        nim = self.nim_test
        self.write(
            {
                'company_ifu': response_content.get("ifu") if not ifu or ifu != response_content.get("ifu") else ifu,
                'nim_test': response_content.get("nim") if not nim or ifu != response_content.get("nim") else nim,
                'api_token_test_expiry': response_content.get("token_valid"),
                'token_status_test': 'valid'
            })
        return True

    def action_check_api_access(self):
        api_url = f"{self.invoice_api_endpoint}"
        api_token = f"{self.api_token}"

        response_content = self._get_connect_response_content(api_url, api_token)
        ifu = self.company_ifu
        nim = self.nim_production
        self.write(
            {
                'company_ifu': response_content.get("ifu") if not ifu or ifu != response_content.get("ifu") else ifu,
                'nim_production': response_content.get("nim") if not nim or ifu != response_content.get("nim") else nim,
                'api_token_expiry': response_content.get("token_valid"),
                'token_status': 'valid'
            })
        return True

