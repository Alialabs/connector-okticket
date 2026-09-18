from odoo import models, fields


def generate_log_event_content(values):
    """
    Generate log.event message format based on provided values.
    :param values: dict
    :return: str
    """
    if 'msg' in values:
        return values['msg']
    content = f"{values.get('tag', 'OP')} ({values['status']}): {values['url']}"
    if values.get('type') == 'error':
        content += f" - {values.get('result')}"
    return content


def prepare_log_event(values):
    """
    Prepare a dictionary with needed values for log.event creation.
    :param values: dict
    :return: dict
    """
    return {
        'backend_id': values['backend_id'],
        'type': values.get('type'),
        'tag': values.get('tag'),
        'msg': generate_log_event_content(values),
    }


class LogEvent(models.Model):
    _name = 'log.event'
    _description = 'Log Event'
    _order = 'datetime_event desc, id desc'

    type = fields.Selection(
        [
            ('info', 'Info'),
            ('success', 'Success'),
            ('warning', 'Warning'),
            ('error', 'Error')
        ],
        string='Type',
        default='info'
    )
    tag = fields.Selection(
        [
            ('AUTH', 'Authentication'),
            ('POST', 'Post'),
            ('GET', 'Get'),
            ('PUT', 'Put'),
            ('PATCH', 'Patch'),
            ('DELETE', 'Delete'),
            ('OP', 'Operation')
        ],
        string='Tag',
        default='Operation'
    )
    backend_id = fields.Many2one(
        comodel_name='okticket.backend',
        string='Backend',
        ondelete='cascade'
    )
    datetime_event = fields.Datetime(
        string='Datetime Event',
        default=fields.Datetime.now,
        readonly=True
    )
    content = fields.Text(
        string='Content',
        required=True
    )

    def add_event(self, values):
        """
        Prepare and create a log.event.
        :param values: dict
        :return: log.event

        Written with ``sudo``: the connector log is infrastructure, not user
        data, and whoever happens to trigger an operation must not decide
        whether it gets recorded. Creating a log entry is restricted to the two
        connector groups, so without this an employee submitting their own
        expense sheet got an access error -- ``action_submit_sheet`` reports the
        status change to OkTicket, which logs the call. Granting the connector
        group to every employee would fix the symptom by handing out write
        access to backends and bindings, and putting ``sudo`` on each flow
        action leaves the next caller to trip over the same thing.
        """
        event_values = prepare_log_event(values)
        return self.sudo().create({
            'backend_id': event_values['backend_id'],
            'type': event_values['type'],
            'tag': event_values['tag'],
            'content': event_values['msg'],
        })
