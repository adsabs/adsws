APP_SECRET_KEY = 'this should be changed'

#This section configures this application to act as a client, for example to query solr via adsws
CLIENT = {
  'TOKEN': 'we will provide an api key token for this application'
}

#Tests:
#This config value *should not* overwrite the parent app, since it is already defined there
CACHE = None

#Tests:
#This config value *should* be added to the parent app, since it is does not exist there
TEST_SPECIFIC_CONFIG = "foo"