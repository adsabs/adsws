from adsws.testsuite import make_test_suite, \
    run_test_suite, FlaskAppTestCase
from flask import session
import os 
import inspect
import tempfile

class FactoryTest(FlaskAppTestCase):
    
    @property
    def config(self):
        return {
           'SQLALCHEMY_DATABASE_URI' : 'sqlite://',
           'FOO': 'bar'
        }
        
    def test_factory(self):
        self.assertEqual(
            self.app.config.get('FOO'),
            'bar',
            "The app didn't get property: foo"
        )
        rootf = os.path.realpath(os.path.join(os.path.dirname(inspect.getfile(inspect.currentframe())), '../../adsws'))
        self.assertEqual(self.app.root_path, rootf, "root_path is not correct")
        self.assertEqual(self.app.instance_path, os.path.realpath(os.path.join(rootf, '../instance')), "instance_path is not correct")

    def test_sesssion(self):
        """
        Ensure that session.permanent=True
        """
        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            self.assertTrue(session.permanent, True)

class FactoryTestCustomInstanceDir(FlaskAppTestCase):
    @property
    def config(self):
        if 'instance_path' not in self._config:
            instance_path = tempfile.mkdtemp()
            with open(os.path.join(instance_path, 'local_config.py'), 'w') as fo:
                fo.write("BAR='baz'\n")
            self._config['instance_path'] = instance_path
        return self._config
        
        
    def test_custom_config(self):
        rootf = os.path.realpath(os.path.join(os.path.dirname(inspect.getfile(inspect.currentframe())), '../../adsws'))
        self.assertEqual(self.app.config.get('BAR'), 'baz')
        self.assertEqual(self.app.root_path, rootf, "root_path is not correct")
        self.assertEqual(self.app.instance_path, self.config['instance_path'])


class FactoryTestSecretKey(FlaskAppTestCase):
    @property
    def config(self):
        return {
           'SECRET_KEY' : '73696768'
        }
        
    def test_custom_config(self):
        self.assertEqual(self.app.config.get('SECRET_KEY'), 'sigh')

        
class FactoryTestSecretKeyNonHex(FlaskAppTestCase):
    @property
    def config(self):
        return {
           'SECRET_KEY' : 'X73696768'
        }
        
    def test_custom_config(self):
        self.assertEqual(self.app.config.get('SECRET_KEY'), 'X73696768')

        
TEST_SUITE = make_test_suite(FactoryTest, FactoryTestCustomInstanceDir, FactoryTestSecretKey,
                             FactoryTestSecretKeyNonHex)


if __name__ == "__main__":
    run_test_suite(TEST_SUITE)             
