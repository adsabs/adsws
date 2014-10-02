from adsws.core import db

class OAuthClientLimits(db.Model):
    """
    Storage for the limits applied to each oauth client.
    """
    __tablename__ = 'oauth2client_limits'
    
    counter = db.Column(db.Integer, default=0)


    client_id = db.Column(
        db.String(255), #db.ForeignKey('oauth2client.client_id'),
        nullable=False,
        primary_key=True
    )
    #client = db.relationship('OAuthClient')

    def increase(self):
        """Increase the counter of requests."""
        self.counter = (self.counter or 0) + 1
        db.session.add(self)
        db.session.commit()
        return self

    def totals(self):
        """Total number of requests so far."""
        return self.counter or 0
