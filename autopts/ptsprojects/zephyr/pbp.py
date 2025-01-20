#
# auto-pts - The Bluetooth PTS Automation Framework
#
# Copyright (c) 2024, Nordic Semiconductor ASA.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms and conditions of the GNU General Public License,
# version 2, as published by the Free Software Foundation.
#
# This program is distributed in the hope it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
from enum import IntEnum, IntFlag
import struct

from autopts.pybtp import btp
from autopts.client import get_unique_name
from autopts.ptsprojects.stack import get_stack, SynchPoint
from autopts.ptsprojects.testcase import TestFunc
from autopts.ptsprojects.zephyr.pbp_wid import pbp_wid_hdl
from autopts.ptsprojects.zephyr.ztestcase import ZTestCase, ZTestCaseSlave
from autopts.pybtp.defs import PACS_AUDIO_CONTEXT_TYPE_CONVERSATIONAL, PACS_AUDIO_CONTEXT_TYPE_MEDIA
from autopts.pybtp.types import Addr, AdType, Context
from autopts.utils import ResultWithFlag

class Uuid(IntEnum):
    ASCS = 0x184E
    BASS = 0x184F
    PACS = 0x1850
    BAAS = 0x1852
    CAS  = 0x1853


def set_pixits(ptses):
    pts = ptses[0]

    pts.set_pixit("PBP", "TSPX_time_guard", "180000")
    pts.set_pixit("PBP", "TSPX_use_implicit_send", "TRUE")

sink_contexts = Context.LIVE | Context.CONVERSATIONAL | Context.MEDIA | Context.RINGTONE
source_contexts = Context.LIVE | Context.CONVERSATIONAL

def announcements(adv_data, rsp_data, targeted):
    """Setup Announcements"""

    # CAP General/Targeted Announcement
    adv_data[AdType.uuid16_svc_data] = [struct.pack('<HB', Uuid.CAS, 1 if targeted else 0) ]

    # BAP General/Targeted Announcement
    adv_data[AdType.uuid16_svc_data] += [struct.pack('<HBHHB', Uuid.ASCS, 1 if targeted else 0, sink_contexts, source_contexts, 0) ]

    # Generate the Resolvable Set Identifier (RSI)
    rsi = btp.cas_get_member_rsi()
    adv_data[AdType.rsi] = struct.pack('<6B', *rsi)

    stack = get_stack()
    stack.gap.ad = adv_data

def test_cases(ptses):
    """
    Returns a list of PBP test cases
    ptses -- list of PyPTS instances
    """

    pts = ptses[0]

    pts_bd_addr = pts.q_bd_addr
    iut_device_name = get_unique_name(pts)
    stack = get_stack()

    adv_data, rsp_data = {}, {}

    iut_addr = ResultWithFlag()

    def set_addr(addr):
        iut_addr.set(addr)

    pre_conditions = [
        TestFunc(btp.core_reg_svc_gap),
        TestFunc(stack.gap_init, iut_device_name),
        TestFunc(btp.gap_read_ctrl_info),
        TestFunc(btp.core_reg_svc_gatt),
        TestFunc(btp.set_pts_addr, pts_bd_addr, Addr.le_public),
        TestFunc(stack.gatt_init),
        TestFunc(btp.gap_set_conn),
        TestFunc(btp.core_reg_svc_ascs),
        TestFunc(btp.core_reg_svc_bap),
        TestFunc(stack.ascs_init),
        TestFunc(stack.bap_init),
        TestFunc(stack.cap_init),
        TestFunc(btp.core_reg_svc_cap),
        TestFunc(btp.core_reg_svc_cas),
        TestFunc(btp.core_reg_svc_pbp),
        TestFunc(stack.pbp_init),
        TestFunc(btp.gap_set_extended_advertising_on),
        # Gives a signal to the LT2 to continue its preconditions
        TestFunc(lambda: set_addr(stack.gap.iut_addr_get_str())),

        TestFunc(lambda: pts.update_pixit_param("PBP", "TSPX_bd_addr_iut",
                                                stack.gap.iut_addr_get_str()))
    ]

    test_case_name_list = pts.get_test_case_list('PBP')
    tc_list = []

    # Use the same preconditions and MMI/WID handler for all test cases of the profile
    for tc_name in test_case_name_list:
        instance = ZTestCase('PBP', tc_name, cmds=pre_conditions,
                             generic_wid_hdl=pbp_wid_hdl)

        tc_list.append(instance)

    return tc_list