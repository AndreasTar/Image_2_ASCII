###########################################################################
# Copyright (c) 2024, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

"""
Device selection for the maths in `backend`.

The tool ships CPU-only on purpose: nothing in here is imported unless the user actually
asks for a GPU with `--gpu`, and neither CuPy nor PyTorch appears in requirements.txt.
A machine with just `numpy`, `pillow` and `svg.py` installed runs the whole tool.

Every backend exposes the same handful of array operations, which is all `backend` needs.
NumPy and CuPy share an implementation because CuPy is API-compatible with NumPy;
PyTorch gets a thin adapter because its spelling differs (`.to()` instead of `.astype()`,
`atan2` instead of `arctan2`, and so on).
"""

from enum import Enum
from typing import Any

import numpy as np

from src import tools

# Names accepted by the --gpu flag.
BACKEND_CHOICES = ('auto', 'cupy', 'torch')


class Device(Enum):
    CPU = 'cpu'
    CUPY = 'cupy'
    TORCH = 'torch'


class ComputeBackend:
    """
    The array operations `backend` needs, spelled the same way on every device.

    Arrays handed to these methods are always device arrays produced by `asarray`,
    except where noted. Plain Python indexing, slicing, arithmetic and broadcasting
    behave identically on all three libraries, so they are used directly rather than
    being wrapped here.
    """

    device: Device
    deviceName: str

    @property
    def usesDeviceArrays(self) -> bool:
        """
        Whether `backend` should run the array maths itself instead of handing the work
        to Pillow's C resampler.

        True for every backend except plain NumPy. Note this is deliberately True for a
        PyTorch backend pinned to the CPU as well: that configuration exists so the tensor
        code path can be exercised on a machine with no GPU.
        """
        return self.device is not Device.CPU

    def asarray(self, data: Any, dtype: str = 'float32') -> Any:
        """Moves a host array onto this device."""
        raise tools.Errors.Unimplemented()

    def toHost(self, array: Any) -> np.ndarray:
        """Brings a device array back as a NumPy array."""
        raise tools.Errors.Unimplemented()

    def zeros(self, shape: tuple[int, ...], dtype: str = 'float32') -> Any:
        raise tools.Errors.Unimplemented()

    def cumsum(self, array: Any, axis: int) -> Any:
        raise tools.Errors.Unimplemented()

    def hypot(self, a: Any, b: Any) -> Any:
        raise tools.Errors.Unimplemented()

    def atan2(self, a: Any, b: Any) -> Any:
        raise tools.Errors.Unimplemented()

    def clip(self, array: Any, low: float, high: float) -> Any:
        raise tools.Errors.Unimplemented()

    def synchronize(self) -> None:
        """
        Blocks until queued device work has finished.

        GPU calls are asynchronous, so timings taken without this are meaningless.
        A no-op on the CPU.
        """
        return None


class PNamespaceBackend(ComputeBackend):
    """
    --- Private class! ---\n
    Backs onto a NumPy-compatible module. Serves both NumPy (CPU) and CuPy (GPU),
    since CuPy deliberately mirrors the NumPy API.
    """

    def __init__(self, namespace: Any, device: Device, deviceName: str) -> None:
        self.pXp = namespace
        self.device = device
        self.deviceName = deviceName

    def asarray(self, data: Any, dtype: str = 'float32') -> Any:
        return self.pXp.asarray(data, dtype = dtype)

    def toHost(self, array: Any) -> np.ndarray:
        if self.device is Device.CPU:
            return np.asarray(array)
        return self.pXp.asnumpy(array)

    def zeros(self, shape: tuple[int, ...], dtype: str = 'float32') -> Any:
        return self.pXp.zeros(shape, dtype = dtype)

    def cumsum(self, array: Any, axis: int) -> Any:
        return self.pXp.cumsum(array, axis = axis)

    def hypot(self, a: Any, b: Any) -> Any:
        return self.pXp.hypot(a, b)

    def atan2(self, a: Any, b: Any) -> Any:
        return self.pXp.arctan2(a, b)

    def clip(self, array: Any, low: float, high: float) -> Any:
        return self.pXp.clip(array, low, high)

    def synchronize(self) -> None:
        if self.device is Device.CUPY:
            self.pXp.cuda.Stream.null.synchronize()


class PTorchBackend(ComputeBackend):
    """
    --- Private class! ---\n
    Adapter for PyTorch, whose API differs from NumPy in a few spellings.
    Covers CUDA and Apple MPS; the same code runs on CPU tensors, which is what
    makes this path testable without a GPU present.
    """

    def __init__(self, torch: Any, torchDevice: str, deviceName: str) -> None:
        self.pTorch = torch
        self.pDevice = torchDevice
        self.device = Device.TORCH
        self.deviceName = deviceName
        self.pDtypes = {
            'float32': torch.float32,
            'float64': torch.float64,
            'int64'  : torch.int64,
        }

    def asarray(self, data: Any, dtype: str = 'float32') -> Any:
        # NumPy arrays are not always writeable (Pillow buffers are not), and torch
        # warns loudly about that, so copy through a contiguous array first.
        if isinstance(data, np.ndarray):
            data = np.ascontiguousarray(data)
        return self.pTorch.as_tensor(data, dtype = self.pDtypes[dtype], device = self.pDevice)

    def toHost(self, array: Any) -> np.ndarray:
        return array.detach().cpu().numpy()

    def zeros(self, shape: tuple[int, ...], dtype: str = 'float32') -> Any:
        return self.pTorch.zeros(shape, dtype = self.pDtypes[dtype], device = self.pDevice)

    def cumsum(self, array: Any, axis: int) -> Any:
        return self.pTorch.cumsum(array, dim = axis)

    def hypot(self, a: Any, b: Any) -> Any:
        return self.pTorch.hypot(a, b)

    def atan2(self, a: Any, b: Any) -> Any:
        return self.pTorch.atan2(a, b)

    def clip(self, array: Any, low: float, high: float) -> Any:
        return self.pTorch.clamp(array, low, high)

    def synchronize(self) -> None:
        if self.pDevice.startswith('cuda'):
            self.pTorch.cuda.synchronize()
        elif self.pDevice == 'mps':
            self.pTorch.mps.synchronize()


def getCpuBackend() -> ComputeBackend:
    """The always-available backend. Needs nothing beyond NumPy."""
    return PNamespaceBackend(np, Device.CPU, 'CPU (numpy)')


def getBackend(request: str | None) -> ComputeBackend:
    """
    Resolves the `--gpu` argument to a usable backend.

    `request` is None (or 'cpu') for the CPU, 'auto' to try every GPU library in turn,
    or an explicit 'cupy' / 'torch'. When a GPU was asked for but cannot be provided,
    this explains why and falls back to the CPU rather than failing the run.
    """
    if request is None or request == 'cpu':
        return getCpuBackend()

    attempts = (pTryCupy, pTryTorch) if request == 'auto' else \
               ((pTryCupy,) if request == 'cupy' else (pTryTorch,))

    reasons = []
    for attempt in attempts:
        backend, reason = attempt()
        if backend is not None:
            return backend
        reasons.append(reason)

    print("\nGPU was requested but is not available:")
    for reason in reasons:
        print(f"\t- {reason}")
    print("\tFalling back to the CPU. See the README for optional GPU install instructions.\n")

    return getCpuBackend()


def pTryCupy() -> tuple[ComputeBackend | None, str]:
    """
    --- Private method! ---\n
    Returns a CuPy backend, or None plus the reason it could not be built.
    """
    try:
        import cupy
    except ImportError:
        return None, "CuPy is not installed (pip install cupy-cuda12x)"

    try:
        deviceId = cupy.cuda.runtime.getDevice()
        name = cupy.cuda.runtime.getDeviceProperties(deviceId)['name'].decode()
    except Exception as e:
        # CuPy imports fine without a working driver, and only fails on first use.
        return None, f"CuPy is installed but no usable CUDA device was found ({e})"

    return PNamespaceBackend(cupy, Device.CUPY, f"{name} (cupy)"), ""


def pTryTorch() -> tuple[ComputeBackend | None, str]:
    """
    --- Private method! ---\n
    Returns a PyTorch backend, or None plus the reason it could not be built.
    """
    try:
        import torch
    except ImportError:
        return None, "PyTorch is not installed (see pytorch.org for a CUDA build)"

    if torch.cuda.is_available():
        return PTorchBackend(torch, 'cuda', f"{torch.cuda.get_device_name(0)} (torch)"), ""

    if getattr(torch.backends, 'mps', None) is not None and torch.backends.mps.is_available():
        return PTorchBackend(torch, 'mps', "Apple GPU (torch/mps)"), ""

    return None, f"PyTorch {torch.__version__} has no GPU support built in (this is a CPU-only build)"


def getTorchCpuBackend() -> ComputeBackend | None:
    """
    Builds a PyTorch backend pinned to the CPU.

    Only useful for testing: it exercises exactly the same tensor code path that a CUDA
    device would, so the torch adapter can be verified on a machine without a GPU.
    Returns None when PyTorch is not installed.
    """
    try:
        import torch
    except ImportError:
        return None

    return PTorchBackend(torch, 'cpu', 'CPU (torch)')
