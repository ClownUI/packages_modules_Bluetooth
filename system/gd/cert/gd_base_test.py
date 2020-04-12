#!/usr/bin/env python3
#
#   Copyright 2019 - The Android Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import importlib
import logging
import os
import signal
import subprocess

from acts import asserts
from acts.context import get_current_context
from acts.base_test import BaseTestClass
from cert.os_utils import get_gd_root, is_subprocess_alive
from facade import rootservice_pb2 as facade_rootservice


class GdBaseTestClass(BaseTestClass):

    SUBPROCESS_WAIT_TIMEOUT_SECONDS = 10

    def setup_class(self, dut_module, cert_module):
        self.dut_module = dut_module
        self.cert_module = cert_module
        self.log_path_base = get_current_context().get_full_output_path()

        # Start root-canal if needed
        self.rootcanal_running = False
        if 'rootcanal' in self.controller_configs:
            self.rootcanal_running = True
            rootcanal_logpath = os.path.join(self.log_path_base,
                                             'rootcanal_logs.txt')
            self.rootcanal_logs = open(rootcanal_logpath, 'w')
            rootcanal_config = self.controller_configs['rootcanal']
            rootcanal_hci_port = str(rootcanal_config.get("hci_port", "6402"))
            rootcanal = os.path.join(get_gd_root(), "root-canal")
            self.rootcanal_process = subprocess.Popen(
                [
                    rootcanal,
                    str(rootcanal_config.get("test_port", "6401")),
                    rootcanal_hci_port,
                    str(rootcanal_config.get("link_layer_port", "6403"))
                ],
                cwd=get_gd_root(),
                env=os.environ.copy(),
                stdout=self.rootcanal_logs,
                stderr=self.rootcanal_logs)
            asserts.assert_true(
                self.rootcanal_process,
                msg="Cannot start root-canal at " + str(rootcanal))
            asserts.assert_true(
                is_subprocess_alive(self.rootcanal_process),
                msg="root-canal stopped immediately after running")
            # Modify the device config to include the correct root-canal port
            for gd_device_config in self.controller_configs.get("GdDevice"):
                gd_device_config["rootcanal_port"] = rootcanal_hci_port

        # Parse and construct GD device objects
        self.register_controller(
            importlib.import_module('cert.gd_device'), builtin=True)
        self.dut = self.gd_devices[1]
        self.cert = self.gd_devices[0]

    def teardown_class(self):
        if self.rootcanal_running:
            stop_signal = signal.SIGINT
            self.rootcanal_process.send_signal(stop_signal)
            try:
                return_code = self.rootcanal_process.wait(
                    timeout=self.SUBPROCESS_WAIT_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                logging.error(
                    "Failed to interrupt root canal via SIGINT, sending SIGKILL"
                )
                stop_signal = signal.SIGKILL
                self.rootcanal_process.kill()
                try:
                    return_code = self.rootcanal_process.wait(
                        timeout=self.SUBPROCESS_WAIT_TIMEOUT_SECONDS)
                except subprocess.TimeoutExpired:
                    logging.error("Failed to kill root canal")
                    return_code = -65536
            if return_code != 0 and return_code != -stop_signal:
                logging.error("rootcanal stopped with code: %d" % return_code)
            self.rootcanal_logs.close()

    def setup_test(self):
        self.dut.rootservice.StartStack(
            facade_rootservice.StartStackRequest(
                module_under_test=facade_rootservice.BluetoothModule.Value(
                    self.dut_module),))
        self.cert.rootservice.StartStack(
            facade_rootservice.StartStackRequest(
                module_under_test=facade_rootservice.BluetoothModule.Value(
                    self.cert_module),))

        self.dut.wait_channel_ready()
        self.cert.wait_channel_ready()

    def teardown_test(self):
        self.cert.rootservice.StopStack(facade_rootservice.StopStackRequest())
        self.dut.rootservice.StopStack(facade_rootservice.StopStackRequest())
