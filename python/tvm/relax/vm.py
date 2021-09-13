# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import tvm
from tvm.runtime import Object
from tvm._ffi.base import _LIB, check_call
from . import _ffi_api
from ..rpc.base import RPC_SESS_MASK


@tvm._ffi.register_object("relax.Executable")
class Executable(Object):
    """The executable object emitted by the VM compiler or the ExecBuilder."""
    def __init__(self):
        self.__init_handle_by_constructor__(_ffi_api.Executable)

    def stats(self):
        """print the detailed statistics of the executable."""
        return _ffi_api.ExecutableStats(self)

    def save_to_file(self, file_name):
        """serialize and write the executable to a file."""
        return _ffi_api.ExecutableSaveToFile(self, file_name)

    def astext(self):
        """print the instructions as text format."""
        return _ffi_api.ExecutableAsText(self)
    
    def aspython(self):
        """print the instructions as python program."""
        return _ffi_api.ExecutableAsPython(self)

def load_exec_from_file(file_name):
    return _ffi_api.ExecutableLoadFromFile(file_name)

class VirtualMachine(object):
    """Relax VM runtime."""

    NAIVE_ALLOCATOR = 1
    POOLED_ALLOCATOR = 2
    
    def __init__(self, exec, device, memory_cfg=None, mod=None):
        """
        Construct a VirtualMachine wrapper object.

        Parameters
        ----------
        exec: Executable
            The VM executable.

        device : tvm.runtime.Device or List[tvm.runtime.Device]
            The device to deploy the module.

        memory_cfg : str or Dict[tvm.runtime.Device, str], optional
            Config the type of memory allocator. The allocator type can be ["naive",
            "pooled"]. If memory_cfg is None, all devices will use pooled allocator
            by default. If memory_cfg is string, all devices will use the specified
            allocator type. If memory_cfg is a dict, each device uses the allocator
            type specified in the dict, or pooled allocator if not specified in the
            dict.

        Returns
        -------
        vm: VirtualMachine
            A VM wrapper object.
        """
        self.module = _ffi_api.VirtualMachine(exec, mod)
        self._setup_device(device, memory_cfg)

    def _setup_device(self, dev, memory_cfg):
        """init devices and allocators."""
        devs = dev
        if not isinstance(dev, (list, tuple)):
            if not isinstance(dev, tvm.runtime.Device):
                raise TypeError(
                    "dev is expected to be Device or \
                                List[Device]"
                )
            devs = [dev]

        # CPU is required for executing shape functions
        if not any(c.device_type % RPC_SESS_MASK == tvm.cpu().device_type for c in devs):
            devs.append(tvm.cpu())

        default_alloc_type = VirtualMachine.POOLED_ALLOCATOR
        if memory_cfg is None:
            memory_cfg = {}
        elif isinstance(memory_cfg, str):
            assert memory_cfg in ["naive", "pooled"]
            if memory_cfg == "naive":
                default_alloc_type = VirtualMachine.NAIVE_ALLOCATOR
            memory_cfg = {}
        elif not isinstance(memory_cfg, dict):
            raise TypeError(
                "memory_cfg is expected be string or dictionary, "
                + "but received {}".format(type(memory_cfg))
            )
        init_args = []
        for device in devs:
            init_args.append(device.device_type % RPC_SESS_MASK)
            init_args.append(device.device_id)
            alloc_type = memory_cfg[device] if device in memory_cfg else default_alloc_type
            init_args.append(alloc_type)
        _ffi_api.VirtualMachineInit(self.module, *init_args)

    def __getitem__(self, key):
        return self.module[key]