"""
Management commands for consul related activities
"""

import time
import json
import consulate
import boto
from adsws.consul import create_app

from flask.ext.script import Manager

consul_manager = Manager(create_app())
consul_manager.__doc__ = __doc__  # Overwrite default docstring

@consul_manager.command
def backup_consul(app_override=None):
    """
    """

    app = consul_manager.app if app_override is None else app_override
 
    consul = consulate.Consul(host=os.environ.get['CONSUL_HOST'])
    # Open backup file
    backup_file = "adsabs_consul_kv.%s.json" % time.strftime('%m%d%Y')
    handle = open(backup_file, 'w')
    # Get record for backup
    records = consul.kv.records()
    try:
        handle.write(json.dumps(records) + '\n')
        app.logger.info("Consul key/value store backup in: %s" % backup_file)
    except exceptions.ConnectionError:
        app.logger.error("Unable to create Consul backup file: %s" % backup_file)
    # Finally, move backup over to S3
    backup_dest = app.config.get('CONSUL_S3_BACKUP_BUCKET')
    # Connect to S3
    conn = boto.connect_s3()
    k = Key(backup_dest)
    k.key = backup_file
    k.set_contents_from_filename(backup_file)
    # Remove the local copy of the backup file
    os.remove(backup_file)
    
    

