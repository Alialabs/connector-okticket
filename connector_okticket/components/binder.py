# -*- coding: utf-8 -*-
#
#    Created on 16/04/19
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

from odoo.addons.component.core import AbstractComponent
from odoo.addons.component.core import Component


class OkticketModelBinder(AbstractComponent):
    _name = 'okticket.binder'
    _inherit = ['base.binder', 'base.okticket.connector']
    _usage = 'binder'


class OkticketExpenseBinder(Component):
    _name = 'okticket.expense.binder'
    _inherit = 'okticket.binder'
    _apply_on = ['okticket.hr.expense']
    _usage = 'binder'