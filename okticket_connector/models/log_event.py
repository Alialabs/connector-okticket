# Copyright 2021 Alia Technologies, S.L. - http://www.alialabs.com
# @author: Alia
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


def generate_log_event_content(values):
    """
    Log.event message format
    """
    if values.get('msg'):
        content = values['msg']
    else:
        content = values.get('tag', 'OP') + ' (' + str(values['status']) + '): ' + values['url']
        if values.get('type', '') == 'error':
            content = content + ' - ' + values.get('result')
    return content


def prepare_log_event(values):
    """
    Dict with needed values for log.event creation.
    Builds log.event message based on the available information
    :param values: dict
    :return: values dict for log.event
    """
    return {
        'backend_id': values['backend_id'],
        'type': values.get('type'),
        'tag': values.get('tag'),
        'msg': generate_log_event_content(values),
    }


class LogEvent(models.Model):
    _name = 'log.event'
    _order = 'datetime_event desc,id desc'

    type = fields.Selection([('info', 'Info'),
                             ('success', 'Success'),
                             ('warning', 'Warning'),
                             ('error', 'Error')],
                            string='Type',
                            default='info',
                            required=False)
    tag = fields.Selection([('AUTH', 'Authentication'),
                            ('POST', 'Post'),
                            ('GET', 'Get'),
                            ('PUT', 'Put'),
                            ('PATCH', 'Patch'),
                            ('DELETE', 'Delete'),
                            ('OP', 'Operation')],
                           string='Tag',
                           default='Operation',
                           required=False)
    backend_id = fields.Many2one(comodel_name='okticket.backend',
                                 string='Backend',
                                 required=False,
                                 ondelete='cascade', )
    datetime_event = fields.Datetime(string='Datetime event',
                                     default=fields.Datetime.now,
                                     readonly=True)
    content = fields.Text(string='Content',
                          required=True)

    def add_event(self, values):
        """
        Prepares and creates log.event
        :param values: dict
        :return: log.event
        """
        dict_values = prepare_log_event(values)
        return self.create({
            'backend_id': dict_values['backend_id'],
            'type': dict_values['type'],
            'tag': dict_values['tag'],
            'content': dict_values['msg'],
        })
