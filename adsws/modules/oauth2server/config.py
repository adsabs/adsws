# -*- coding: utf-8 -*-
LOG_STDOUT = True

OAUTH2_CACHE_TYPE = 'redis'
""" Type of cache to use for storing the temporary grant token """

OAUTH2_PROVIDER_ERROR_ENDPOINT = 'oauth2server.errors'
""" Error view endpoint """

OAUTH2_PROVIDER_GRANT_EXPIRES_IN = 100
""" Life time of a grant token """

OAUTH2_PROVIDER_TOKEN_EXPIRES_IN = 3600
""" Life time of an access token """

OAUTH2_CLIENT_ID_SALT_LEN = 40
""" Length of client id """

OAUTH2_CLIENT_SECRET_SALT_LEN = 60
""" Length of the client secret """

OAUTH2_TOKEN_PERSONAL_SALT_LEN = 60
""" Length of the personal access token """

OAUTH2_DEFAULT_SCOPES = {
    'user:email': 'Read access to user email only.',
    'user': 'Any user operation'
}

OAUTH2_ALLOWED_GRANT_TYPES = [
    'authorization_code', 'client_credentials', 'refresh_token'
]
"""
A list of allowed grant types - allowed values are `authorization_code`,
`password`, `client_credentials`, `refresh_token`). By default password is
disabled, as it requires the client application to gain access to the username
and password of the resource owner
"""

OAUTH2_ALLOWED_RESPONSE_TYPES = [
    "code", "token"
]
"""
A list of allowed grant types - allowed values are `authorization_code`,
`password`, `client_credentials`, `refresh_token`)
"""
