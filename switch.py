#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
import os
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name

mac_table = dict()
vlan_table = dict()

def parse_config(switch_id, vlan_table):
    # parse switch config to populate VLAN table
    config_file_path = os.path.join("configs", f"switch{switch_id}.cfg")
    try:
        with open(config_file_path, 'r') as file:
            for line_number, line in enumerate(file):
                if line_number == 0:
                    continue  # skip the header line
                line = line.strip()
                if line:
                    # if the line ends in 'T', it's a trunk port; otherwise, it specifies a VLAN ID
                    if line[-1] != 'T':
                        vlan_table[line_number - 1] = int(line[-1])
                    else:
                        vlan_table[line_number - 1] = -1
    except FileNotFoundError:
        # error if config file is missing
        print(f"[ERROR] Configuration file for switch {switch_id} not found at {config_file_path}", flush=True)
    except ValueError:
        # error if VLAN config is invalid
        print(f"[ERROR] Invalid VLAN configuration in file {config_file_path}", flush=True)


# check if MAC address is unicast
# broadcast addresses have all bits set (ff:ff:ff:ff:ff:ff)
def is_unicast(mac_address):
    return mac_address != b'\xff\xff\xff\xff\xff\xff'

# function for forwarding the packages
# verifies the type of interface (trunk or acces)
def forward_packets(interface, interfaces, data, length, vlan_id, src_mac, dest_mac):
    # add source MAC to mac table
    mac_table[src_mac] = interface
    
    if is_unicast(dest_mac):
            if dest_mac in mac_table:
                # known destination MAC: forward to specific interface if VLAN matches
                if vlan_table[mac_table[dest_mac]] == vlan_id:
                    send_to_link(mac_table[dest_mac], length, data)
                else:
                    # VLAN mismatch: add VLAN tag and forward
                    tagged_frame = data[0:12] + create_vlan_tag(vlan_id) + data[12:]
                    send_to_link(mac_table[dest_mac], length + 4, tagged_frame)

            else:
                # unknown destination MAC: broadcast within the same VLAN
                for o in interfaces:
                    if o != interface:
                        if vlan_table[o] == vlan_id:
                            send_to_link(o, length, data)
                        else:
                            tagged_frame = data[0:12] + create_vlan_tag(vlan_id) + data[12:]
                            send_to_link(o, length + 4, tagged_frame)
    else:
            # broadcast or multicast: send to all interfaces within the same VLAN
            for o in interfaces:
                if o != interface:
                    if vlan_table[o] == vlan_id:
                        send_to_link(o, length , data)
                    else:
                        tagged_frame = data[0:12] + create_vlan_tag(vlan_id) + data[12:]
                        send_to_link(o, length + 4, tagged_frame)

def parse_ethernet_header(data):
    # Unpack the header fields from the byte array
    #dest_mac, src_mac, ethertype = struct.unpack('!6s6sH', data[:14])
    dest_mac = data[0:6]
    src_mac = data[6:12]
    
    # Extract ethertype. Under 802.1Q, this may be the bytes from the VLAN TAG
    ether_type = (data[12] << 8) + data[13]

    vlan_id = -1
    # Check for VLAN tag (0x8100 in network byte order is b'\x81\x00')
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
        ether_type = (data[16] << 8) + data[17]

    return dest_mac, src_mac, ether_type, vlan_id

def create_vlan_tag(vlan_id):
    # 0x8100 for the Ethertype for 802.1Q
    # vlan_id & 0x0FFF ensures that only the last 12 bits are used
    return struct.pack('!H', 0x8200) + struct.pack('!H', vlan_id & 0x0FFF)

def send_bdpu_every_sec():
    while True:
        # TODO Send BDPU every second if necessary
        time.sleep(1)

def main():
    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]
    
    # load VLAN configuration for the given switch into the VLAN table
    parse_config(switch_id, vlan_table)

    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)

    print("# Starting switch with id {}".format(switch_id), flush=True)
    print("[INFO] Switch MAC", ':'.join(f'{b:02x}' for b in get_switch_mac()))

    # Create and start a new thread that deals with sending BDPU
    t = threading.Thread(target=send_bdpu_every_sec)
    t.start()

    # Printing interface names
    for i in interfaces:
        print(get_interface_name(i))

    while True:
        # Note that data is of type bytes([...]).
        # b1 = bytes([72, 101, 108, 108, 111])  # "Hello"
        # b2 = bytes([32, 87, 111, 114, 108, 100])  # " World"
        # b3 = b1[0:2] + b[3:4].
        interface, data, length = recv_from_any_link()

        dest_mac, src_mac, ethertype, vlan_id = parse_ethernet_header(data)

        # Print the MAC src and MAC dst in human readable format
        dest_mac = ':'.join(f'{b:02x}' for b in dest_mac)
        src_mac = ':'.join(f'{b:02x}' for b in src_mac)

        # Note. Adding a VLAN tag can be as easy as
        # tagged_frame = data[0:12] + create_vlan_tag(10) + data[12:]

        print(f'Destination MAC: {dest_mac}')
        print(f'Source MAC: {src_mac}')
        print(f'EtherType: {ethertype}')

        print("Received frame of size {} on interface {}".format(length, interface), flush=True)

        # TODO: Implement forwarding with learning
        # TODO: Implement VLAN support

        # determine VLAN based on whether it's from an access or trunk port
        if vlan_id < 0:
            vlan = vlan_table.get(interface)
        else:
            vlan = vlan_id

        # if the packet comes from a trunk port, remove the VLAN tag
        if vlan_id >= 0:
            data_without_vlan = data[:12] + data[16:]
            forward_packets(interface, interfaces, data_without_vlan, length - 4, vlan, src_mac, dest_mac)
        else:
            # if the packet comes from an access port, forward it as it is
            forward_packets(interface, interfaces, data, length, vlan, src_mac, dest_mac)

        # TODO: Implement STP support

        # data is of type bytes.
        # send_to_link(i, length, data)

if __name__ == "__main__":
    main()
