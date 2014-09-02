
import string
from time import time
from itertools import chain
from random import seed, choice, sample

from flask_security.forms import LoginForm, _datastore
from adsws.modules.classic.user import ClassicUserInfo, ClassicUser
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
                                     password=mkpasswd(),
                                     name=cu.get_name(),
                                     active=False)
        return False
    


def mkpasswd(length=8, digits=2, upper=2, lower=2):
    """Create a random password

    Create a random password with the specified length and no. of
    digit, upper and lower case letters.

    :param length: Maximum no. of characters in the password
    :type length: int

    :param digits: Minimum no. of digits in the password
    :type digits: int

    :param upper: Minimum no. of upper case letters in the password
    :type upper: int

    :param lower: Minimum no. of lower case letters in the password
    :type lower: int

    :returns: A random password with the above constaints
    :rtype: str
    """

    seed(time())

    lowercase = string.lowercase.translate(None, "o")
    uppercase = string.uppercase.translate(None, "O")
    letters = "{0:s}{1:s}".format(lowercase, uppercase)
    
    password = list(
        chain(
            (choice(uppercase) for _ in range(upper)),
            (choice(lowercase) for _ in range(lower)),
            (choice(string.digits) for _ in range(digits)),
            (choice(letters) for _ in range((length - digits - upper - lower)))
        )
    )

    return "".join(sample(password, len(password)))