import unittest

from link_state_routing import ForwardingTable
from emulator import EmulatorInProgress


class TestForwardingTable(unittest.TestCase):

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
    def setUp(self):       
        self.forwarding_table = ForwardingTable()
        
        self.emulator_1 = EmulatorInProgress(True, '1.0.0.0', 1, ['2.0.0.0,2', '3.0.0.0,3'], 0)
        self.emulator_2 = EmulatorInProgress(True, '2.0.0.0', 2, ['1.0.0.0,1', '3.0.0.0,3', '4.0.0.0,4'], 1)
        self.emulator_3 = EmulatorInProgress(True, '3.0.0.0', 3, ['1.0.0.0,1', '2.0.0.0,2', '5.0.0.0,5'], 1)
        self.emulator_4 = EmulatorInProgress(True, '4.0.0.0', 4, ['2.0.0.0,2', '5.0.0.0,5'], 2)
        self.emulator_5 = EmulatorInProgress(True, '5.0.0.0', 5, ['3.0.0.0,3', '4.0.0.0,4'], 2)

        self.forwarding_table.add_entry(self.emulator_1, self.emulator_1)
        self.forwarding_table.add_emulator_to_sp_tree(self.emulator_1)

        self.forwarding_table.add_entry(self.emulator_2, self.emulator_2)
        self.forwarding_table.add_emulator_to_sp_tree(self.emulator_2)

        self.forwarding_table.add_entry(self.emulator_3, self.emulator_3)
        self.forwarding_table.add_emulator_to_sp_tree(self.emulator_3)

        self.forwarding_table.add_entry(self.emulator_4, self.emulator_2)
        self.forwarding_table.add_emulator_to_sp_tree(self.emulator_4)

        self.forwarding_table.add_entry(self.emulator_5, self.emulator_3)
        self.forwarding_table.add_emulator_to_sp_tree(self.emulator_5)


    def test_update_entry_next_hop(self):
        ''' Tests that the Forwarding Table correctly updates the next hop of an existing emulator entry. '''
        
        # Update an existing emulator in the forwarding table
        # Expected behavior is that the existing emulator's next hop is updated in the forwarding table
        self.assertEqual(self.forwarding_table.get_next_hop(self.emulator_5), self.emulator_3)
        self.forwarding_table.update_next_hop(self.emulator_5, self.emulator_4)
        self.assertEqual(self.forwarding_table.get_next_hop(self.emulator_5), self.emulator_4)

        # Try to update an emulator that does not exist in the forwarding table
        # Expected behavior is that an error is raised
        try:
            emulator_6 = EmulatorInProgress(True, '6.0.0.0', 6, ['4.0.0.0,4', '5.0.0.0,5'], 3)
            self.forwarding_table.update_next_hop(emulator_6, self.emulator_5)
        except Exception as err:
            self.assertEqual(str(err), "Exception in update_next_hop function - entry not found!")


    def test_is_emulator_in_forwarding_table(self):
        ''' Tests that emulator entries in the Forwarding Table return True, and emulators not in the Forwarding Table return False. '''

        # Get the 'in forwarding table' status of emulator entries in the forwarding table
        # Expected behavior is that True is returned
        self.assertTrue(self.forwarding_table.is_emulator_in_forwarding_table(self.emulator_1))
        self.assertTrue(self.forwarding_table.is_emulator_in_forwarding_table(self.emulator_2))
        self.assertTrue(self.forwarding_table.is_emulator_in_forwarding_table(self.emulator_3))
        self.assertTrue(self.forwarding_table.is_emulator_in_forwarding_table(self.emulator_4))
        self.assertTrue(self.forwarding_table.is_emulator_in_forwarding_table(self.emulator_5))

        # Get the 'in forwarding table' status of an emulator entry not in the forwarding table
        # Expected behavior is that False is returned
        emulator_6 = EmulatorInProgress(True, '6.0.0.0', 6, ['4.0.0.0,4', '5.0.0.0,5'], 3)
        self.assertFalse(self.forwarding_table.is_emulator_in_forwarding_table(emulator_6))


    def test_is_emulator_in_spf_tree(self):
        ''' Tests the function that gets the status of whether the emulator is in the Dijkstra's Shortest Path First Tree. '''
        
        # Get the SPF tree status of emulator entries in the forwarding table and who's SPF tree status is True
        # Expected behavior is that True is returned
        self.assertTrue(self.forwarding_table.is_emulator_in_spf_tree(self.emulator_1))
        self.assertTrue(self.forwarding_table.is_emulator_in_spf_tree(self.emulator_2))
        self.assertTrue(self.forwarding_table.is_emulator_in_spf_tree(self.emulator_3))
        self.assertTrue(self.forwarding_table.is_emulator_in_spf_tree(self.emulator_4))
        self.assertTrue(self.forwarding_table.is_emulator_in_spf_tree(self.emulator_5))

        # Get the SPF tree status of emulator entries in the forwarding table and who's SPF tree status is False
        # Expected behavior is that False is returned
        emulator_6 = EmulatorInProgress(True, '6.0.0.0', 6, ['4.0.0.0,4', '5.0.0.0,5'], 3)
        self.forwarding_table.add_entry(emulator_6, self.emulator_5)
        self.assertFalse(self.forwarding_table.is_emulator_in_spf_tree(emulator_6))

        # Try to get the SPF tree status of an emulator entry not in the forwarding table
        # Expected behavior is that an error is raised
        try:
            emulator_7 = EmulatorInProgress(True, '7.0.0.0', 7, ['4.0.0.0,4', '5.0.0.0,5'], 3)
            self.forwarding_table.update_next_hop(emulator_7, self.emulator_5)
        except Exception as err:
            self.assertEqual(str(err), "Exception in update_next_hop function - entry not found!")


    def test_find_next_hop(self):
        ''' Tests the function that finds the next-hop from the starting emulator to the predecessor emulator using the Forwarding Table. '''
        
        '''
        Add emulator_6 to the default forwarding table created by setUp().
        emulator_6 should be assigned the next-hop 'emulator_3' and the network topology will look like this:

                  2 - 4
                 / \   \
                1 - 3 - 5 - '6'
        '''
        # Create emulator
        emulator_6 = EmulatorInProgress(True, '6.0.0.0', 6, ['5.0.0.0,5'])

        # Find next-hop and assert it is equal to expected next-hop
        next_hop = self.forwarding_table.find_next_hop(self.emulator_1, self.emulator_5, emulator_6)
        self.assertEqual(next_hop, self.emulator_3)

        # Add new emulator / next-hop pair to the forwarding table & SPF tree
        self.forwarding_table.add_entry(emulator_6, next_hop)
        self.forwarding_table.add_emulator_to_sp_tree(emulator_6)


        '''
        Add emulator_7 to the default forwarding table created by setUp().
        emulator_7 should be assigned the next-hop 'emulator_2' and the network topology will look like this:

           '7' -  2 - 4
                 / \   \
                1 - 3 - 5 - 6
        '''
        # Create emulator
        emulator_7 = EmulatorInProgress(True, '7.0.0.0', 7, ['2.0.0.0,2'])

        # Find next-hop and assert it is equal to expected next-hop
        next_hop = self.forwarding_table.find_next_hop(self.emulator_1, self.emulator_2, emulator_7)
        self.assertEqual(next_hop, self.emulator_2)

        # Add new emulator / next-hop pair to the forwarding table & SPF tree
        self.forwarding_table.add_entry(emulator_7, next_hop)
        self.forwarding_table.add_emulator_to_sp_tree(emulator_7)


        '''
        Add emulator_8 to the default forwarding table created by setUp().
        emulator_8 should be assigned the next-hop 'emulator_1' and the network topology will look like this:

             7 -  2 - 4
                 / \   \
          '8' - 1 - 3 - 5 - 6
        '''
        # Create emulator
        emulator_8 = EmulatorInProgress(True, '8.0.0.0', 8, ['1.0.0.0,1'])

        # Find next-hop and assert it is equal to expected next-hop
        next_hop = self.forwarding_table.find_next_hop(self.emulator_1, self.emulator_1, emulator_8)
        self.assertEqual(next_hop, emulator_8)

        # Add new emulator / next-hop pair to the forwarding table & SPF tree
        self.forwarding_table.add_entry(emulator_8, next_hop)
        self.forwarding_table.add_emulator_to_sp_tree(emulator_8)


    def tearDown(self):
        del self.forwarding_table


if __name__ == '__main__':
    unittest.main()