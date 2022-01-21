from flask_security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required, login_user
from warnings import warn


security = Security()    

def setup_app(app):
    from adsws.core import db, User, Role
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    
    app.config.setdefault('SECURITY_PASSWORD_HASH', 'pbkdf2_sha512')
    app.config.setdefault('SECURITY_PASSWORD_SALT', app.config.get('SECRET_KEY'))
    register_blueprint = app.config.get('SECURITY_REGISTER_BLUEPRINT', True)

    # if desired, we'll use ADS Classic as a source for authenticating
    # users
    if app.config.get('FALL_BACK_ADS_CLASSIC_LOGIN', False):
        
        from .ads_classic_login import AdsClassicFallBackLoginForm
        security.init_app(app, user_datastore, register_blueprint=register_blueprint, login_form=AdsClassicFallBackLoginForm)
    else:
        security.init_app(app, user_datastore, register_blueprint=register_blueprint)
            

    # if there is Flask-Email extension, we'll use that one for sending
    # emails
    if 'email' in app.extensions:
        from flask_email import EmailMessage    
        def send_email(msg):
            if not 'email' in app.extensions:
                warn("Flask-Email extension has disappeared from app.extensions")
                return
            
            email = EmailMessage(
                    subject=msg.subject,
                    body=msg.body,
                    from_email=msg.sender,
                    to=msg.recipients)
            email.send(app.extensions['email'])
            
        app.extensions['security'].send_mail_task(send_email)
        
    
    return app
