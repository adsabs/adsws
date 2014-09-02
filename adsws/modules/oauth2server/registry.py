from __future__ import absolute_import

from flask_registry import RegistryProxy, DictRegistry, RegistryError
from .models import Scope


class ScopesRegistry(DictRegistry):

    """
    Registry for OAuth scopes.
    """

    def register(self, scope):
        """ Register an OAuth scope. """
        if not isinstance(scope, Scope):
            raise RegistryError("Invalid scope value.")
        super(ScopesRegistry, self).register(scope.id, scope)

    def choices(self, exclude_internal=True):
        items = self.items()
        items.sort()
        return [(k, scope) for k, scope in items if
                not exclude_internal or not scope.is_internal]


scopes = RegistryProxy('oauth2server.scopes', ScopesRegistry)