from adsws.testsuite import make_test_suite, \
    run_test_suite, AdsWSAppTestCase, FlaskAppTestCase, AdsWSTestCase

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
        self.assertEqual(self.app.config.get('FOO'), 'bar', "The app didn't get property: foo")
        rootf = os.path.realpath(os.path.join(os.path.dirname(inspect.getfile(inspect.currentframe())), '../adsws'))
        self.assertEqual(self.app.root_path, rootf, "root_path is not correct")
        self.assertEqual(self.app.instance_path, os.path.realpath(os.path.join(rootf, '../instance')), "instance_path is not correct")

class FactoryTestCustomInstanceDir(FlaskAppTestCase):
    @property
    def config(self):
        if not self._config.has_key('instance_path'):
            instance_path = tempfile.mkdtemp()
            with open(os.path.join(instance_path, 'local_config.py'), 'w') as fo:
                fo.write("BAR='baz'\n")
            self._config['instance_path'] = instance_path
        return self._config
        
        
    def test_custom_config(self):
        rootf = os.path.realpath(os.path.join(os.path.dirname(inspect.getfile(inspect.currentframe())), '../adsws'))
        self.assertEqual(self.app.config.get('BAR'), 'baz')
        self.assertEqual(self.app.root_path, rootf, "root_path is not correct")
        self.assertEqual(self.app.instance_path, self.config['instance_path'])
            
        
        
TEST_SUITE = make_test_suite(FactoryTest, FactoryTestCustomInstanceDir)


if __name__ == "__main__":
    run_test_suite(TEST_SUITE)             
