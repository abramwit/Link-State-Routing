import unittest

from link_state_routing import ForwardingTable


class TestForwardingTable(unittest.TestCase):

    def setUp(self):
        self.forwarding_table = ForwardingTable()

        '''
        Set-up the forwarding table below for all test-cases using the network topology below:

                  2 - 4
                 / \   \
                1 - 3 - 5

        The forwarding table for the emulator with port 1 should be:

                2.0.0.0,2 2.0.0.0,2
                3.0.0.0,3 3.0.0.0,3
                4.0.0.0,4 3.0.0.0,3
                5.0.0.0,5 2.0.0.0,2
        
        If the emulator with port 3 went down/was disabled, the new forwarding table should be:

                2.0.0.0,2 2.0.0.0,2
                4.0.0.0,4 2.0.0.0,2
                5.0.0.0,5 2.0.0.0,2
        '''


    def test_update_entry(self):
        pass


    def test_is_emulator_in_forwarding_table(self):
        pass


    def test_is_emulator_in_sp_tree(self):
        pass


    def test_get_next_hop(self):
        pass


    def tearDown(self):
        del self.forwarding_table


if __name__ == '__main__':
    unittest.main()