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
import json
import requests
from datetime import datetime
import qrcode
import base64
from io import BytesIO
from odoo.exceptions import ValidationError


class AccountTaxGroup(models.Model):
    _inherit = 'account.tax.group'

    emecef_tax_group = fields.Char(
        help="eMCF taxation group, can be either A, B, C, D, E, F",
        string="eMCF Tax Group", size=4)
    is_emecef_default_tax_group = fields.Boolean(
        help="Specify if this taxation group is default tax group",
        string="eMCF Default Group?")

    @api.model
    def create(self, vals):
        # OVERRIDE
        rslt = super(AccountTaxGroup, self).create(vals)
        api = self.env.ref('mecef_bj.mecef_api_settings')
        unique_default_tax_group = self.env['account.tax.group'].search([('is_emecef_default_tax_group', '=', True)])
        if len(unique_default_tax_group) > 1:
            error_msg = f"{api.def_tax_group_msg_constraint}"
            raise ValidationError(_('%s' % error_msg))

        return rslt

    def write(self, vals):
        # OVERRIDE
        rslt = super(AccountTaxGroup, self).write(vals)
        api = self.env.ref('mecef_bj.mecef_api_settings')
        unique_default_tax_group = self.env['account.tax.group'].search([('is_emecef_default_tax_group', '=', True)])
        if len(unique_default_tax_group) > 1:
            error_msg = f"{api.def_tax_group_msg_constraint}"
            raise ValidationError(_('%s' % error_msg))

        return rslt


class AccountMove(models.Model):
    _inherit = 'account.move'

    emecef_code = fields.Char('MECeF/DGI Code', size=30, readonly=True, copy=False)
    emecef_counters = fields.Char('MECeF Counters', size=12, readonly=True, copy=False)
    emecef_date_time = fields.Char('MECeF Time', size=30, readonly=True, copy=False)
    emecef_date = fields.Date('MECeF Date', compute='_compute_emecef_date', copy=False)
    emecef_nim = fields.Char('MECeF NIM', size=12, readonly=True, copy=False)
    emecef_product_count = fields.Char(string="Product Count", readonly=True, copy=False)
    emecef_qrcode = fields.Binary(string="MECeF QR Code", readonly=True, copy=False)
    emecef_flag = fields.Boolean('MECeF Status', copy=False)
    emecef_ref = fields.Char('MECeF Reference', readonly=True, copy=False)

    @api.depends('emecef_date_time')
    def _compute_emecef_date(self):
        for record in self:
            if not record.emecef_date_time:
                record.emecef_date = None
            else:
                date_time_str = str(record.emecef_date_time)
                date_time_obj = (datetime.strptime(date_time_str, '%d/%m/%Y %H:%M:%S')).date()
                record.emecef_date = date_time_obj

    def _generate_qr_code(self, datastr: str):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=20,
            border=4,
        )
        qr.add_data(datastr)
        qr.make(fit=True)
        img = qr.make_image()
        temp = BytesIO()
        img.save(temp, format="PNG")
        qr_img = base64.b64encode(temp.getvalue())
        return qr_img

    def _get_item_tax_group(self, invoice_line):

        api = self.env.ref('mecef_bj.mecef_api_settings')

        # Step 1: if no tax is selected on invoice, Default Tax Group will be passed on to the line item
        # or a validation error will be thrown to prompt user to a set Default Tax Group.
        tax_group = False
        if not invoice_line.tax_ids:
            default_tax_group_id = self.env['account.tax.group'].search(
                [('is_emecef_default_tax_group', '=', True)])
            if not default_tax_group_id:
                error_msg = f"{api.def_tax_group_msg_check}"
                raise ValidationError(_('%s' % error_msg))
            tax_group = default_tax_group_id.emecef_tax_group

        # Step 2: if only one tax is set on the line, tax group will be the Tax Group of line item tax ID.
        # If more than one tax id is set, a validation error will be thrown to prompt user to set only ONE tax id.
        else:
            if len(invoice_line.tax_ids) == 1:
                tax_group = invoice_line.tax_ids[0].tax_group_id.emecef_tax_group

            elif len(invoice_line.tax_ids) > 1:
                error_msg = f"{api.invoice_line_tax_check}"
                raise ValidationError(_('%s' % error_msg + str(invoice_line.name)))

        return tax_group

    def _get_out_refund_mecef_data(self):
        for record in self:
            if record.move_type == 'out_refund':
                refund_invoice = record.reversed_entry_id
                mecef_code = refund_invoice.emecef_code
                nim = refund_invoice.emecef_nim
                counters = refund_invoice.emecef_counters
                # Step 1: Split counters in form of XXXX/XXXX FV by space and pick first item in list, then split by "/"
                counters_split = (str(counters).split()[0]).split("/")
                # Step 2: Split result of Step 1 in form of XXXX/XXXX and then pick second item in list
                counter = counters_split[1]
                reference = str(nim) + "-" + str(counter)
                return mecef_code, reference

    def _prepare_invoice_data(self):
        for record in self:
            api = self.env.ref('mecef_bj.mecef_api_settings')
            partner = record.partner_id
            if record.partner_id.state_id:
                partner_address = str(partner.street) + ', ' + str(partner.city) + ', ' + str(
                    partner.state_id.name) + ', ' + str(partner.country_id.name)
            else:
                partner_address = str(partner.street) + ', ' + str(partner.city) + ', ' + str(partner.country_id.name)
            items = []
            for line in record.invoice_line_ids:
                items.append({
                    'name': line.name,
                    'price': line.price_total / line.quantity,
                    'quantity': line.quantity,
                    'taxGroup': self._get_item_tax_group(line),
                })

            invoice_data = {
                'ifu': f"{api.company_ifu}",
                'items': items,
                'client': {
                    'contact': str(record.partner_id.phone) or str(record.partner_id.mobile),
                    'ifu': str(record.partner_id.vat),
                    'name': str(record.partner_id.name),
                    'address': partner_address,
                },
                'operator': {"id": str(record.user_id.id), "name": str(record.user_id.name)}
            }

            if record.move_type == 'out_invoice':
                invoice_type = "FV"
                invoice_data.update({'type': invoice_type})
            if record.move_type == 'out_refund':
                invoice_type = "FA"
                invoice_data.update({'type': invoice_type, 'reference': self._get_out_refund_mecef_data()[0]})
            print('invoice_data Code', invoice_data)
            return invoice_data

    def action_post(self):

        # Step 1: Exclude Invoices not in "out_invoice" and "out_refund" for this procedure ##

        if self.move_type not in ['out_invoice', 'out_refund']:
            return super(AccountMove, self).action_post()

        else:  # Step 2: Check that API settings and status are ok before posting invoice

            api = self.env.ref('mecef_bj.mecef_api_settings')

            if all([
                (api.state == 'enabled' and api.token_status == 'valid' or
                 api.state == 'test' and api.token_status_test == 'valid')]):

                rslt = super(AccountMove, self).action_post()

                if not self.emecef_flag:  # Exclude invoice if it had been processed before

                    # Step 3: Obtain Invoice Data #
                    invoice_data = self._prepare_invoice_data()
                    print('Invoice Data', invoice_data)
                    raise ValidationError(_('%s' % invoice_data))

                    # Step 4: POST request to eMECeF API to obtain invoice uid.
                    invoice_uid = self.validate_invoice(invoice_data)

                    raise ValidationError(_('%s' % invoice_uid))

                    # Step 5: PUT a request to eMECeF API to get NIM, DGI_CODE, TC/TF, TIME and append on invoice
                    self.confirm_invoice_validation(invoice_uid)

                else:
                    pass
                return rslt
            else:
                error_msg = f"{api.invoice_msg_api_status_check}"
                raise ValidationError(_('%s' % error_msg))

    def _send_request(self, data: dict = None, uri: str = "", method: str = "GET"):

        api = self.env.ref('mecef_bj.mecef_api_settings')

        authentication_token = False

        if api.state == 'enabled':
            api_url = f"{api.invoice_api_endpoint}"
            authentication_token = f"{api.api_token}"
        elif api.state == 'test':
            api_url = f"{api.invoice_api_endpoint_test}"
            authentication_token = f"{api.api_token_test}"

        headers = {"Authorization": f"Bearer {authentication_token}", "Content-Type": "application/json"}
        if method.upper() == "POST":
            response = requests.post(
                f"{api_url}/{uri}", headers=headers, data=json.dumps(data) if data is not None else None
            )
            return response.status_code, json.loads(response.content)
        elif method.upper() == "PUT":
            response = requests.put(
                f"{api_url}/{uri}", headers=headers, data=json.dumps(data) if data is not None else None
            )
            return response.status_code, json.loads(response.content)

    def validate_invoice(self, invoice: dict):
        api = self.env.ref('mecef_bj.mecef_api_settings')

        validation_response_code, validation_response_content = self._send_request(
            data=invoice, method="POST"
        )
        print('Validation Code', validation_response_code)
        if not validation_response_code == 200:
            error_msg = f"{api.invoice_validation_error}"
            raise ValidationError(_('%s' % error_msg + str(validation_response_code)))

        if not len(validation_response_content.get("uid")) > 0:
            error_msg = f"{api.invoice_validation_no_uid}"
            raise ValidationError(_('%s' % error_msg))

        invoice_uid = validation_response_content['uid']

        return invoice_uid

    def confirm_invoice_validation(self, invoice_uid, action="confirm"):
        # Finalize the invoice
        api = self.env.ref('mecef_bj.mecef_api_settings')

        confirmation_response_code, confirmation_response_content = self._send_request(
            method="PUT", uri=f"{invoice_uid}/{action}"
        )
        if not confirmation_response_code == 200:
            error_msg = f"{api.invoice_validation_error}"
            raise ValidationError(_('%s' % error_msg + str(confirmation_response_code)))

        confirmationDate = confirmation_response_content.get("dateTime")
        qrCode = confirmation_response_content.get("qrCode")
        nim = confirmation_response_content.get("nim")
        codeMECeFDGI = confirmation_response_content.get("codeMECeFDGI")
        counters = confirmation_response_content.get("counters")
        self.write({
            "emecef_flag": True,
            "emecef_nim": nim,
            "emecef_counters": counters,
            "emecef_code": codeMECeFDGI,
            "emecef_date_time": confirmationDate,
            "emecef_qrcode": self._generate_qr_code(qrCode),
            "emecef_product_count": len(self.invoice_line_ids),
            "emecef_ref": self._get_out_refund_mecef_data()[1] if self.reversed_entry_id else False
        })
        return True
