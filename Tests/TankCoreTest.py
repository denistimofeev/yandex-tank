from Tests.TankTests import TankTestCase
import unittest
import tankcore

class  TankCoreTestCase(TankTestCase):
    def setUp(self):
        self.foo = self.get_core()

    def tearDown(self):
        del self.foo
        self.foo = None

    def test_tankCoreFail(self):
        paths = ['config_err/load_err.conf']
        self.foo.load_configs(paths)
        try:
            self.foo.load_plugins()
            self.fail()
        except ImportError:
            pass

    def test_tankCore(self):
        paths = ['config/load.conf']
        self.foo.load_configs(paths)
        self.assertEquals('passed', self.foo.get_option('dotted', 'test'))
        
        self.foo.load_plugins()
        self.foo.plugins_configure()
        self.foo.plugins_prepare_test()
        self.foo.plugins_start_test()
        self.foo.wait_for_finish()
        self.foo.add_artifact_file(__file__, 1)
        self.foo.plugins_end_test(0)
        self.foo.plugins_post_process(0)
        
    def test_strstplit(self):
        str1='-Jtarget.address=webtest7h.yandex.ru -Jtarget.port=26 -J "load_profile=const(1,60s) line(0,1000,10m)"'
        arr1=tankcore.splitstring(str1)
        self.assertEquals(len(arr1), 5)

if __name__ == '__main__':
    unittest.main()

