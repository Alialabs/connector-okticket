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
                                 ondelete='cascade',)
    datetime_event = fields.Datetime(string='Datetime event',
                                     default=fields.Datetime.now,
                                     readonly=True)
    content = fields.Text(string='Content',
                          required=True)

    def generate_log_event_content(self, vals):
        '''
        Formato del mensaje de log.event
        '''
        if vals.get('msg'):
            content = vals['msg']
        else:
            content = vals.get('tag', 'OP') + ' (' + str(vals['status']) + '): ' + vals['url']
            if vals.get('type', '') == 'error':
                content = content + ' - ' + vals.get('result')
        return content

    def prepare_log_event(self, vals):
        '''
        Diccionario de valores necesarios para la creacion de un log.event
        Construye el mensaje del log.event en base a la informacion disponible
        :param vals: dict
        :return: dict con vals para construir log.event
        '''
        return {
            'backend_id': vals['backend_id'],
            'type': vals.get('type'),
            'tag': vals.get('tag'),
            'msg': self.generate_log_event_content(vals),
        }

    def add_event(self, vals):
        '''
        Prepara vals y crea un log.event
        :param vals: dict
        :return: log.event
        '''
        dict_vals = self.prepare_log_event(vals)
        return self.create({
                'backend_id': dict_vals['backend_id'],
                'type': dict_vals['type'],
                'tag': dict_vals['tag'],
                'content': dict_vals['msg'],
            })

        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
