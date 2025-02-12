from tests.rdmacm_utils import active_side, passive_side
from multiprocessing import Process, Pipe
from tests.base import RDMATestCase
import pyverbs.device as d
import subprocess
import unittest
import json


class CMTestCase(RDMATestCase):
    def setUp(self):
        if self.dev_name is not None:
            net_name = self.get_net_name(self.dev_name)
            try:
                self.ip_addr = self.get_ip_address(net_name)
            except KeyError:
                raise unittest.SkipTest('Device {} doesn\'t have net interface'
                                        .format(self.dev_name))
        else:
            dev_list = d.get_device_list()
            for dev in dev_list:
                net_name = self.get_net_name(dev.name.decode())
                try:
                    self.ip_addr = self.get_ip_address(net_name)
                except IndexError:
                    continue
                else:
                    self.dev_name = dev.name.decode()
                    break
            if self.dev_name is None:
                raise unittest.SkipTest('No devices with net interface')
        super().setUp()

    @staticmethod
    def get_net_name(dev):
        process = subprocess.Popen(['ls', '/sys/class/infiniband/{}/device/net/'
                                   .format(dev)], stdout=subprocess.PIPE)
        out, err = process.communicate()
        return out.decode().split('\n')[0]

    @staticmethod
    def get_ip_address(ifname):
        process = subprocess.Popen(['ip', '-j', 'addr', 'show', ifname],
                                   stdout=subprocess.PIPE)
        out, err = process.communicate()
        loaded_json = json.loads(out.decode())
        interface = loaded_json[0]['addr_info'][0]['local']
        if 'fe80::' in interface:
            interface = interface + '%' + ifname
        return interface

    def test_rdmacm_sync_traffic(self):
        active_pipe, passive_pipe = Pipe()
        passive = Process(target=passive_side,
                          args=[self.ip_addr, passive_pipe])
        active = Process(target=active_side, args=[self.ip_addr, active_pipe])
        passive.start()
        active.start()
        passive.join()
        active.join()
