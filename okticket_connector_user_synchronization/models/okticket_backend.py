# -*- coding: utf-8 -*-
#
#    Created on 19/07/19
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


from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class OkticketBackend(models.Model):
    _inherit = 'okticket.backend'

    @api.model
    def _scheduler_import_employee(self):
        for backend_record in self.search([]):
            _logger.info(
                'Scheduling employees batch import from Okticket '
                'with backend %s.' % backend_record.name)
            backend_record.import_employees()

    @api.multi
    def import_employees(self):
        self.ensure_one()
        self.env['okticket.hr.employee'].sudo().import_batch(self)
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: