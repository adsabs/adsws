# Ratelimits explained

Every user has one entry in the `users` table. The attribute `ratelimit_level` controls
how big a quota all the user's OAuth applications can use. Actually, to be more precise, 
this limit controls how many and how big OAuth clients can this particular user create.

For example, the default is 2.0 - which means that every user can create two OAuth applications.
This has been our practice, one app is for the BBB client, the other one is for the generated
API key.

The OAuth application can be created by accessing /account/bootstrap endpoint. The endpoint
accepts parameters that control behaviour of the application:

    - ratelimit
    - name
    - redirect_uri
    - scopes
    
See the code for details.

When creating the new (or updating the existing app), adsws will check what is the combined
limits of all the applications that belong to the user; if we detect that the user has already
used `ratelimit_level` we'll fail with 40x error. Otherwise, we will create the new OAuth
application and return its secret, access and refresh tokens etc.

Note, user can have as many OAuth applications as they want/need (so long as the combined
ratelimits is lower than `ratelimit_level`). Each OAuth application will have its own 
`ratelimit` which can be a fraction - for example, 0.1 will give the OAuth application 
rights to issue 10% of all the requests allocated for an endpoint. Let's say `/search` is 
protected by `10/60s` limit (i.e. 10 requests/minute) -- a newly created OAuth application
with a ratelimit of 0.1 will have right to query `/search` once per minute.


Also, the ratelimit can be set to `0.0` in which case the access is only allowed to non-ratelimited
endpoints (administration of OAuth applications is one such a case).