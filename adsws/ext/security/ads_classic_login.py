
from flask_security.forms import LoginForm, _datastore
from adsws.modules.classic.user import ClassicUserInfo, ClassicUser
from werkzeug.security import gen_salt
from adsws.core import user_manipulator
from flask_security.confirmable import requires_confirmation

class AdsClassicFallBackLoginForm(LoginForm):
    
    def validate(self):
        r = super(AdsClassicFallBackLoginForm, self).validate()
        if r is True:
            return r
        
        cu = ClassicUserInfo(self.email.data, self.password.data)
        if cu.is_authenticated(): # Classic did let them in....
            
            if self.user is None:  # User does not exist yet
                user_manipulator.create(email=self.email.data, 
                                     password=self.password.data,
                                     name=cu.get_name(),
                                     active=True)
            else:
                if not self.user.password: # password not set
                    return False
                if not self.user.validate_password(self.password.data): # Invalid passwd 
                    self.user.password = self.password.data
                    user_manipulator.save(self.user)
                if requires_confirmation(self.user):
                    return False
                if not self.user.is_active() and cu.is_real_user(): # Disabled account
                    self.user.active = True
                    user_manipulator.save(self.user)
                
            # revalidate
            return super(AdsClassicFallBackLoginForm, self).validate()
        
        elif cu.is_real_user(): # they didn't get it, but the account at least exists...
            if self.user is None:
                user_manipulator.create(email=self.email.data, 
                                     password=gen_salt(12),
                                     name=cu.get_name(),
                                     active=False)
        return False
