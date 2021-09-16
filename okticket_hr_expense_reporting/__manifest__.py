# -*- coding: utf-8 -*-
#
#    Created on 22/07/19
#
#    @author:alia
#
#
# 2019 ALIA Technologies
#       http://www.alialabs.com
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#

{
    'name': 'Alia Okticket Hr Expense Reporting',
    'version': '1.0',
    'category': 'Reporting',
    'depends': [
                'okticket_connector_hr_expense_sheet',
                'web',
                 ],
    'author': "Alia Technologies",
    'license': 'AGPL-3',
    'website': 'http://www.alialabs.com',
    'data': [
        'report/hr_expense_report.xml',
        'report/hr_expense_sheet_report.xml',
        ],
    'application': False,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: