# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if


class OkticketHrEmployeeBindingExportListener(Component):
    _name = 'okticket.hr.employee.binding.export.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['hr.employee']

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_record_create(self, record, fields=None):
        fields = {}
        if record.work_email and \
                ('ignore_okticket_synch' not in self.env.context or not self.env.context['ignore_okticket_synch']):
            fields['work_email'] = record.work_email
            record.synchronize_record(fields=fields)
