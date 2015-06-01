#!/usr/bin/env python
from distutils.core import setup
setup(name="nsx_api",
      version="0.1",
      data_files=[('nsx_debug_conf',['nsx_debug_conf/gateway_service.conf',
                                     'nsx_debug_conf/lrouter.conf',
                                     'nsx_debug_conf/lrouter_port.conf',
                                     'nsx_debug_conf/lrouter_port_attatchment.conf',
                                     'nsx_debug_conf/lswitch.conf',
                                     'nsx_debug_conf/lswitch_port.conf',
                                     'nsx_debug_conf/lswitch_port_attatchment.conf',
                                     'nsx_debug_conf/transport_node.conf'
                                     ]),
                  ('configs',['configs/demo1/gateway_service.conf',
                              'configs/demo1/lrouter.conf',
                              'configs/demo1/lswitch.conf',
                              'configs/demo1/lswitch_port.conf',
                              'configs/demo1/lswitch_port_attatchment.conf',
                              'configs/demo1/transport_node.conf',
                              'configs/demo2/gateway_service.conf',
                              'configs/demo2/lrouter.conf',
                              'configs/demo2/lswitch.conf',
                              'configs/demo2/lswitch_port.conf',
                              'configs/demo2/lswitch_port_attatchment.conf',
                              'configs/demo2/transport_node.conf',
                              'configs/demo3/gateway_service.conf',
                              'configs/demo3/lrouter.conf',
                              'configs/demo3/lrouter_port.conf',
                              'configs/demo3/lrouter_port_attatchment.conf',
                              'configs/demo3/lswitch.conf',
                              'configs/demo3/lswitch_port.conf',
                              'configs/demo3/lswitch_port_attatchment.conf',
                              'configs/demo3/transport_node.conf'
                              ])],
      py_modules=["auto_config_v_0_1","get_certificate",
                  "logo", "make_body",
                  "global_value","__init__"])