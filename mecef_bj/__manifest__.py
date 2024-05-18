# -*- coding: utf-8 -*-
{
    'name': 'e-MECeF BJ',
    'version': '17.0.1.0',
    'summary': 'Generate Standardized Customer Invoices from the e-MECeF Platform',
    'category': 'Accounting',
    'author': 'GLOBALNET',
    'support': 'support@globalnetsc.com',
    'website': 'https://www.globalnetsc.com',
    'license': 'OPL-1',
    'price': 0,
    'currency': 'USD',
    'data': [
        'data/report_paperformat.xml',
        'data/report_templates_inherit.xml',
        'views/res_users_view.xml',
        'views/report_invoice.xml',
        'views/account_move_view.xml',
        # 'views/res_config_settings_views.xml',
    ],
    'depends': ['account'],
    'qweb': [],
    'images': [
        'static/description/mecef_logo.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
