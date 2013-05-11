import os
import unittest

__author__ = 'yamadanaoyuki'

class TestFabfile(unittest.TestCase):
    def test_status_cluster1(self):
        os.system("/usr/local/bin/fab status:cluster1")
