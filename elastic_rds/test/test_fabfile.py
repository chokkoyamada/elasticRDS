import os
import unittest

__author__ = 'yamadanaoyuki'

class TestFabfile(unittest.TestCase):
    def test_startup_cluster1(self):
        os.system("/usr/local/bin/fab startup_cluster:cluster1")
