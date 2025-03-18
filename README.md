# Switch Implementation

## Task 1: MAC Learning and Forwarding

In the first task, the switch was built to handle MAC address learning, enabling efficient packet forwarding.

### Features

1. **MAC Table Initialization** 
   - A dictionary `mac_table` stores mappings between MAC addresses and their corresponding interfaces.

2. **Frame Reception** 
   - Upon receiving a frame on an interface, the switch extracts the source and destination MAC addresses from the Ethernet header.

3. **MAC Learning** 
   - The switch learns the source MAC address by adding it to `mac_table` with the interface it arrived on. This learning process allows the switch to determine where to send frames for known MAC addresses.

4. **Forwarding Logic**
   - **Unicast Frames** 
     - If the destination MAC address is in `mac_table`, the frame is forwarded to the associated interface.
     - If the destination MAC address is not in `mac_table`, the frame is broadcasted to all other interfaces except the incoming one.
   - **Broadcast/Multicast Frames** 
     - The frame is forwarded to all interfaces except the one it arrived on.
   - **Unicast Check** 
     - A helper function, `is_unicast`, checks if the destination MAC address is a unicast address by verifying it is not the broadcast address (`ff:ff:ff:ff:ff:ff`).

## Task 2: VLAN Support

In the second task, VLAN support was added to enable network segmentation at the data link layer.

### VLAN Implementation

1. **VLAN Table Initialization** 
   - A `vlan_table` dictionary stores VLAN configurations for each interface.
   - The `parse_config` function reads VLAN configurations from files located in the `configs` directory. These files specify VLAN IDs for each interface or mark them as trunk ports (which carry traffic for multiple VLANs).

2. **Reading Configuration Files** 
   - The switch reads its configuration file (e.g., `switch0.cfg`) based on its ID.
   - Each line after the first (priority line, unused in this task) contains the interface name and its VLAN ID or `T` to indicate a trunk port.
   - VLAN IDs are stored in `vlan_table`, with trunk ports assigned a VLAN ID of `-1`.

3. **Frame Processing with VLANs** 
   - **VLAN ID Determination** 
     - **Trunk Ports**: Extract the VLAN ID from the VLAN tag in the frame header, then remove the tag.
     - **Access Ports**: Obtain the VLAN ID from `vlan_table` using the interface.

4. **Forwarding with VLAN Consideration** 
   - The switch updates `mac_table` to associate MAC addresses with both the interface and VLAN ID.
   - Frames are forwarded only to interfaces that belong to the same VLAN or are trunk ports.
   - VLAN checks are applied before forwarding to ensure that frames are restricted to the correct VLAN.

5. **VLAN Tagging and Untagging** 
   - **Adding VLAN Tags**: VLAN tags are added to frames forwarded to trunk ports.
   - **Removing VLAN Tags**: VLAN tags are removed when frames are forwarded to access ports.

6. **Updating Forwarding Logic** 
   - The forwarding function was enhanced to consider VLAN IDs in addition to MAC addresses.
   - The switch checks both the MAC address and VLAN ID during forwarding.

7. **Handling Interface Types** 
   - **Trunk Ports**: Use the VLAN ID from the frame’s VLAN tag.
   - **Access Ports**: Use the VLAN ID assigned to the interface in `vlan_table`.
