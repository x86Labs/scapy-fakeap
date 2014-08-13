
from scapy.all import *
from time import time, sleep
from .eap import *
from .utility import *
from .callbacks import Callbacks
from .constants import *


class FakeAccessPoint(object):
    class FakeBeaconTransmitter(threading.Thread):
        def __init__(self, ap):
            threading.Thread.__init__(self)
            self.ap = ap
            self.setDaemon(True)
            self.interval = 0.1

        def run(self):
            while True:
                for ssid in self.ap.ssids:
                    self.ap.callbacks.cb_dot11_beacon(ssid)

                # Sleep
                sleep(self.interval)

    def __init__(self, interface, channel, mac, wpa=False):
        self.ssids = []

        self.mac = mac
        self.ip = "192.168.3.1"
        self.channel = channel
        self.boottime = time()
        self.sc = 0
        self.aid = 0
        self.mutex = threading.Lock()
        self.wpa = wpa
        self.eap_manager = EAPManager()
        self.interface = interface

        self.beaconTransmitter = self.FakeBeaconTransmitter(self)
        self.beaconTransmitter.start()

        self.callbacks = Callbacks(self)

    def add_ssid(self, ssid):
        if not ssid in self.ssids and ssid != '':
            self.ssids.append(ssid)

    def remove_ssid(self, ssid):
        if ssid in self.ssids:
            self.ssids.remove(ssid)

    def current_timestamp(self):
        return (time() - self.boottime) * 1000000

    def next_sc(self):
        self.mutex.acquire()
        self.sc = (self.sc + 1) % 4096
        temp = self.sc
        self.mutex.release()

        return temp * 16  # Fragment number -> right 4 bits

    def next_aid(self):
        self.mutex.acquire()
        self.aid = (self.aid + 1) % 2008
        temp = self.aid
        self.mutex.release()

        return temp

    def get_radiotap_header(self):
        radiotap_packet = RadioTap(len=18, present='Flags+Rate+Channel+dBm_AntSignal+Antenna', notdecoded='\x00\x6c' + get_frequency(self.channel) + '\xc0\x00\xc0\x01\x00\x00')
        return radiotap_packet

    def handle_dhcp(self, pkt):
        # TODO this DHCP handling is extremely basic. More features will be added later.
        clientIp = "192.168.3.2" # For now just use only one client
        clientMac = pkt.addr2

        #If DHCP Discover then DHCP Offer
        if DHCP in pkt and pkt[DHCP].options[0][1] == 1:
            debug_print("DHCP Discover packet detected", 2)
            self.callbacks.cb_dhcp_discover(clientMac, clientIp, pkt[BOOTP].xid)

        #If DHCP Request then DHCP Ack
        if DHCP in pkt and pkt[DHCP].options[0][1] == 3:
            debug_print("DHCP Request packet detected", 2)
            self.callbacks.cb_dhcp_request(clientMac, clientIp, pkt[BOOTP].xid)

    def run(self):
        # TODO: Fix filter
        sniff(iface=self.interface, prn=self.callbacks.cb_recv_pkt, store=0, filter="")