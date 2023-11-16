# -*- coding: utf-8 -*-
####################################
#
#    Created on 4 de jul. de 2017
#
#    @author:loxo
#
##############################################################################
#
# 2017 ALIA Technologies
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
##############################################################################

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
            content = str(content) + ' - ' + str(values.get('result'))
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
