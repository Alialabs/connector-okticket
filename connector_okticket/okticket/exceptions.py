# -*- coding: utf-8 -*-
#
#    Created on 8/04/19
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

"""
This is a list of all exceptions that OkTicket connector can throw.
"""

class BaseOkticketError(Exception):
    """
    Base exception class for Okticket exceptions.
    """
    def __init__(self, *args, **kwargs):
        super(BaseOkticketError, self).__init__(*args, **kwargs)


class ResourceError(BaseOkticketError):
    """
    Unsupported Okticket resource exception.
    """
    def __init__(self):
        super(ResourceError, self).__init__('Unsupported Okticket resource')


class NoFileError(BaseOkticketError):
    """
    File doesn't exist exception.
    """
    def __init__(self):
        super(NoFileError, self).__init__("Can't upload the file that doesn't exist")


class ResourceNotFoundError(BaseOkticketError):
    """
    Requested resource doesn't exist.
    """
    def __init__(self):
        super(ResourceNotFoundError, self).__init__("Requested resource doesn't exist")


class ConflictError(BaseOkticketError):
    """
    Resource version on the server is newer than on the client.
    """
    def __init__(self):
        super(ConflictError, self).__init__("Resource version on the server is newer than on the client")


class AuthError(BaseOkticketError):
    """
    Invalid authentication details.
    """
    def __init__(self):
        super(AuthError, self).__init__('Invalid authentication details')


class ImpersonateError(BaseOkticketError):
    """
    Invalid impersonate login provided.
    """
    def __init__(self):
        super(ImpersonateError, self).__init__("Impersonate login provided doesn't exist or isn't active")


class ServerError(BaseOkticketError):
    """
    Okticket internal error.
    """
    def __init__(self):
        super(ServerError, self).__init__('Okticket returned internal error, perhaps you are doing something wrong')


class RequestEntityTooLargeError(BaseOkticketError):
    """
    Size of the request exceeds the capacity limit on the server.
    """
    def __init__(self):
        super(RequestEntityTooLargeError, self).__init__(
            "The requested resource doesn't allow POST requests or the size of the request exceeds the capacity limit")


class UnknownError(BaseOkticketError):
    """
    Okticket returned unknown error.
    """
    def __init__(self, code):
        super(UnknownError, self).__init__("Okticket returned unknown error with the code {0}".format(code))


class ValidationError(BaseOkticketError):
    """
    Okticket validation errors occured on create/update resource.
    """
    def __init__(self, error):
        super(ValidationError, self).__init__(error)


class ResourceSetIndexError(BaseOkticketError):
    """
    Index doesn't exist in the ResourceSet.
    """
    def __init__(self):
        super(ResourceSetIndexError, self).__init__('Resource not available by requested index')


class ResourceSetFilterParamError(BaseOkticketError):
    """
    Resource set filter method expects to receive either a list or tuple.
    """
    def __init__(self):
        super(ResourceSetFilterParamError, self).__init__('Method expects to receive either a list or tuple of ids')


class ResourceBadMethodError(BaseOkticketError):
    """
    Resource doesn't support the requested method.
    """
    def __init__(self):
        super(ResourceBadMethodError, self).__init__("Resource doesn't support the requested method")


class ResourceFilterError(BaseOkticketError):
    """
    Resource doesn't support requested filter(s).
    """
    def __init__(self):
        super(ResourceFilterError, self).__init__("Resource doesn't support requested filter(s)")


class ResourceNoFiltersProvidedError(BaseOkticketError):
    """
    No filter(s) provided.
    """
    def __init__(self):
        super(ResourceNoFiltersProvidedError, self).__init__('Resource needs some filters to be filtered on')


class ResourceNoFieldsProvidedError(BaseOkticketError):
    """
    No field(s) provided.
    """
    def __init__(self):
        super(ResourceNoFieldsProvidedError, self).__init__(
            'Resource needs some fields to be set to be created/updated')


class ResourceAttrError(BaseOkticketError, AttributeError):
    """
    Resource doesn't have the requested attribute.
    """
    def __init__(self):
        super(ResourceAttrError, self).__init__("Resource doesn't have the requested attribute")


class ReadonlyAttrError(BaseOkticketError):
    """
    Resource can't set attribute that is read only.
    """
    def __init__(self):
        super(ReadonlyAttrError, self).__init__("Can't set read only attribute")


class VersionMismatchError(BaseOkticketError):
    """
    Feature isn't supported on specified Okticket version.
    """
    def __init__(self, feature):
        super(VersionMismatchError, self).__init__("{0} isn't supported on specified Okticket version".format(feature))


class ResourceVersionMismatchError(VersionMismatchError):
    """
    Resource isn't supported on specified Okticket version.
    """
    def __init__(self):
        super(ResourceVersionMismatchError, self).__init__('Resource')


class ResultSetTotalCountError(BaseOkticketError):
    """
    ResultSet hasn't been yet evaluated and cannot yield a total_count.
    """
    def __init__(self):
        super(ResultSetTotalCountError, self).__init__('Total count is unknown before evaluation')


class CustomFieldValueError(BaseOkticketError):
    """
    Custom fields should be passed as a list of dictionaries.
    """
    def __init__(self):
        super(CustomFieldValueError, self).__init__(
            "Custom fields should be passed as a list of dictionaries in the form of [{'id': 1, 'value': 'foo'}]")


class ResourceRequirementsError(BaseOkticketError):
    """
    Resource requires specified Okticket plugin(s) to function.
    """
    def __init__(self, requirements):
        super(ResourceRequirementsError, self).__init__(
            'The following requirements must be installed for resource to function: {0}'.format(
                ', '.join(req if isinstance(req, str) else ' >= '.join(req) for req in requirements)))


class FileUrlError(BaseOkticketError):
    """
    URL provided to download a file can't be parsed.
    """
    def __init__(self):
        super(FileUrlError, self).__init__("URL provided to download a file can't be parsed")


class ForbiddenError(BaseOkticketError):
    """
    Requested resource is forbidden.
    """
    def __init__(self):
        super(ForbiddenError, self).__init__("Requested resource is forbidden")


class JSONDecodeError(BaseOkticketError):
    """
    Unable to decode received JSON.
    """
    def __init__(self, response):
        self.response = response
        super(JSONDecodeError, self).__init__(
            'Unable to decode received JSON, you can inspect exception\'s '
            '"response" attribute to find out what the response was'
        )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: