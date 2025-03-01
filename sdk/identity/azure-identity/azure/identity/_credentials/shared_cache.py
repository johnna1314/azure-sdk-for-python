# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
from typing import TYPE_CHECKING, Any, Optional
from azure.core.credentials import AccessToken

from .silent import SilentAuthenticationCredential
from .. import CredentialUnavailableError
from .._constants import DEVELOPER_SIGN_ON_CLIENT_ID
from .._internal import AadClient, AadClientBase
from .._internal.decorators import log_get_token
from .._internal.shared_token_cache import NO_TOKEN, SharedTokenCacheBase

if TYPE_CHECKING:
    from azure.core.credentials import TokenCredential


class SharedTokenCacheCredential:
    """Authenticates using tokens in the local cache shared between Microsoft applications.

    :param str username: Username (typically an email address) of the user to authenticate as. This is used when the
        local cache contains tokens for multiple identities.

    :keyword str authority: Authority of a Microsoft Entra endpoint, for example 'login.microsoftonline.com',
        the authority for Azure Public Cloud (which is the default). :class:`~azure.identity.AzureAuthorityHosts`
        defines authorities for other clouds.
    :keyword str tenant_id: a Microsoft Entra tenant ID. Used to select an account when the cache contains
        tokens for multiple identities.
    :keyword AuthenticationRecord authentication_record: an authentication record returned by a user credential such as
        :class:`DeviceCodeCredential` or :class:`InteractiveBrowserCredential`
    :keyword cache_persistence_options: configuration for persistent token caching. If not provided, the credential
        will use the persistent cache shared by Microsoft development applications
    :paramtype cache_persistence_options: ~azure.identity.TokenCachePersistenceOptions
    """

    def __init__(self, username: Optional[str] = None, **kwargs: Any) -> None:
        if "authentication_record" in kwargs:
            self._credential = SilentAuthenticationCredential(**kwargs)  # type: TokenCredential
        else:
            self._credential = _SharedTokenCacheCredential(username=username, **kwargs)

    def __enter__(self):
        self._credential.__enter__()
        return self

    def __exit__(self, *args):
        self._credential.__exit__(*args)

    def close(self) -> None:
        """Close the credential's transport session."""
        self.__exit__()

    @log_get_token("SharedTokenCacheCredential")
    def get_token(
        self,
        *scopes: str,
        claims: Optional[str] = None,
        tenant_id: Optional[str] = None,
        enable_cae: bool = False,
        **kwargs: Any
    ) -> AccessToken:
        """Get an access token for `scopes` from the shared cache.

        If no access token is cached, attempt to acquire one using a cached refresh token.

        This method is called automatically by Azure SDK clients.

        :param str scopes: desired scopes for the access token. This method requires at least one scope.
            For more information about scopes, see
            https://learn.microsoft.com/azure/active-directory/develop/scopes-oidc.
        :keyword str claims: additional claims required in the token, such as those returned in a resource provider's
            claims challenge following an authorization failure
        :keyword str tenant_id: not used by this credential; any value provided will be ignored.
        :keyword bool enable_cae: indicates whether to enable Continuous Access Evaluation (CAE) for the requested
            token. Defaults to False.

        :return: An access token with the desired scopes.
        :rtype: ~azure.core.credentials.AccessToken
        :raises ~azure.identity.CredentialUnavailableError: the cache is unavailable or contains insufficient user
            information
        :raises ~azure.core.exceptions.ClientAuthenticationError: authentication failed. The error's ``message``
            attribute gives a reason.
        """
        return self._credential.get_token(*scopes, claims=claims, tenant_id=tenant_id, enable_cae=enable_cae, **kwargs)

    @staticmethod
    def supported() -> bool:
        """Whether the shared token cache is supported on the current platform.

        :return: True if the shared token cache is supported on the current platform, otherwise False.
        :rtype: bool
        """
        return SharedTokenCacheBase.supported()


class _SharedTokenCacheCredential(SharedTokenCacheBase):
    """The original SharedTokenCacheCredential, which doesn't use msal.ClientApplication"""

    def __enter__(self):
        if self._client:
            self._client.__enter__()
        return self

    def __exit__(self, *args):
        if self._client:
            self._client.__exit__(*args)

    def get_token(
        self,
        *scopes: str,
        claims: Optional[str] = None,
        tenant_id: Optional[str] = None,
        enable_cae: bool = False,
        **kwargs: Any
    ) -> AccessToken:
        if not scopes:
            raise ValueError("'get_token' requires at least one scope")

        if not self._client_initialized:
            self._initialize_client()

        is_cae = enable_cae
        token_cache = self._cae_cache if is_cae else self._cache

        # Try to load the cache if it is None.
        if not token_cache:
            token_cache = self._initialize_cache(is_cae=is_cae)

            # If the cache is still None, raise an error.
            if not token_cache:
                raise CredentialUnavailableError(message="Shared token cache unavailable")

        account = self._get_account(self._username, self._tenant_id, is_cae=is_cae)

        token = self._get_cached_access_token(scopes, account, is_cae=is_cae)
        if token:
            return token

        # try each refresh token, returning the first access token acquired
        for refresh_token in self._get_refresh_tokens(account, is_cae=is_cae):
            token = self._client.obtain_token_by_refresh_token(
                scopes, refresh_token, claims=claims, tenant_id=tenant_id, **kwargs
            )
            return token

        raise CredentialUnavailableError(message=NO_TOKEN.format(account.get("username")))

    def _get_auth_client(self, **kwargs: Any) -> AadClientBase:
        return AadClient(client_id=DEVELOPER_SIGN_ON_CLIENT_ID, **kwargs)
