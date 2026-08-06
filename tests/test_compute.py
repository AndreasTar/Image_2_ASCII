###########################################################################
# Copyright (c) 2024-2026, Andy Pandy                                          #
# All rights reserved.                                                    #
#                                                                         #
# This source code is licensed under the BSD-style license found in the   #
# LICENSE file in the root directory of this source tree.                 #
#                                                                         #
###########################################################################

"""
Checks the device abstraction, and that a device produces the same picture as the CPU.

The equivalence tests run against PyTorch pinned to the CPU. That is not a stand-in for a
GPU run: a CUDA tensor goes through the identical code, with only the device string
differing, so this exercises the real device path on a machine with no GPU in it. The same
tests run against CuPy and against a real GPU when either is available.
"""

import numpy as np
import pytest
from PIL import Image

from src import backend, compute, tools
from tests.conftest import GRID_CASES

RAMP = tools.GRAYSCALES[70]


def deviceBackends():
    """Every non-CPU backend that can actually be built on this machine, with a label."""
    found = []

    torchCpu = compute.getTorchCpuBackend()
    if torchCpu is not None:
        found.append(pytest.param(torchCpu, id = 'torch-cpu-tensors'))

    for name in ('cupy', 'torch'):
        backendObject, _ = (compute.pTryCupy if name == 'cupy' else compute.pTryTorch)()
        if backendObject is not None:
            found.append(pytest.param(backendObject, id = f'{name}-gpu'))

    return found


DEVICE_BACKENDS = deviceBackends()
requiresDevice = pytest.mark.skipif(not DEVICE_BACKENDS, reason = "no device backend installed")


# ================= Backend selection ================

def testCpuBackendIsAlwaysAvailable():
    cpu = compute.getCpuBackend()

    assert cpu.device is compute.Device.CPU
    assert not cpu.usesDeviceArrays


@pytest.mark.parametrize('request_', [None, 'cpu'])
def testNoGpuRequestGivesCpu(request_):
    assert compute.getBackend(request_).device is compute.Device.CPU


def testUnavailableGpuFallsBackToCpu(capsys):
    """
    A missing GPU library must not stop the run. It must also say so, rather than
    quietly producing CPU results while the user believes the GPU is doing the work.
    """
    result = compute.getBackend('auto')
    output = capsys.readouterr().out

    if result.device is compute.Device.CPU:
        assert 'GPU was requested but is not available' in output
        assert 'Falling back to the CPU' in output
    else:
        assert output == ''


def testTorchCpuBackendTakesTheDeviceArrayPath():
    """
    The torch-on-CPU backend exists to exercise the tensor code, so it must not be
    short-circuited into the numpy path.
    """
    torchCpu = compute.getTorchCpuBackend()
    if torchCpu is None:
        pytest.skip("PyTorch is not installed")

    assert torchCpu.usesDeviceArrays


# ================= CPU and device agreement ================

@requiresDevice
@pytest.mark.parametrize('device', DEVICE_BACKENDS)
@pytest.mark.parametrize('cols,rows', GRID_CASES)
def testValueGridMatchesCpu(grayImage, device, cols, rows):
    cpu = compute.getCpuBackend()

    expected = backend.toValueGrid(grayImage, cols, rows, cpu)
    actual = backend.toValueGrid(grayImage, cols, rows, device)

    # The device reduction accumulates a running total in float32, so it loses a little
    # more precision than the CPU's per-tile sums. Well inside one grayscale level.
    assert np.abs(actual - expected).max() < 0.05


@requiresDevice
@pytest.mark.parametrize('device', DEVICE_BACKENDS)
def testCharacterGridMatchesCpu(grayImage, device):
    """
    What actually matters is that the user gets the same picture on both devices. A cell
    may still flip when its average sits within float32 noise of a ramp boundary, so a
    handful out of many thousands is tolerated, but no more than that.
    """
    cpu = compute.getCpuBackend()
    mismatched = total = 0

    for cols, rows in GRID_CASES:
        expected = backend.toCharGrid(backend.toValueGrid(grayImage, cols, rows, cpu), RAMP)
        actual = backend.toCharGrid(backend.toValueGrid(grayImage, cols, rows, device), RAMP)

        mismatched += int((expected != actual).sum())
        total += expected.size

    assert mismatched / total < 0.0005, f"{mismatched} of {total} characters differ"


@requiresDevice
@pytest.mark.parametrize('device', DEVICE_BACKENDS)
def testColorGridMatchesCpu(sampleImage, device):
    cpu = compute.getCpuBackend()

    expected = backend.toColorGrid(sampleImage, 64, 40, cpu).astype(int)
    actual = backend.toColorGrid(sampleImage, 64, 40, device).astype(int)

    assert np.abs(actual - expected).max() <= 1


@requiresDevice
@pytest.mark.parametrize('device', DEVICE_BACKENDS)
def testEdgeGridsMatchCpu(grayImage, device):
    cpu = compute.getCpuBackend()

    expectedMag, expectedAngle = backend.toEdgeGrids(grayImage, 80, 25, cpu)
    actualMag, actualAngle = backend.toEdgeGrids(grayImage, 80, 25, device)

    assert np.abs(actualMag - expectedMag).max() < 0.05
    assert np.abs(np.cos(actualAngle) - np.cos(expectedAngle)).max() < 0.01


# ================= The array operations themselves ================

@requiresDevice
@pytest.mark.parametrize('device', DEVICE_BACKENDS)
def testRoundTripThroughDevicePreservesValues(device):
    source = np.linspace(0, 255, 64, dtype = np.float32).reshape(8, 8)

    assert np.allclose(device.toHost(device.asarray(source)), source, atol = 1e-4)


@requiresDevice
@pytest.mark.parametrize('device', DEVICE_BACKENDS)
def testArrayOperationsMatchNumpy(device):
    """Each wrapped operation must mean the same thing on every backend."""
    a = np.array([[3.0, -4.0], [5.0, 12.0]], dtype = np.float32)
    b = np.array([[4.0, 3.0], [12.0, 5.0]], dtype = np.float32)
    deviceA, deviceB = device.asarray(a), device.asarray(b)

    assert np.allclose(device.toHost(device.zeros((2, 3))), np.zeros((2, 3)))
    assert np.allclose(device.toHost(device.cumsum(deviceA, axis = 0)), np.cumsum(a, axis = 0), atol = 1e-4)
    assert np.allclose(device.toHost(device.cumsum(deviceA, axis = 1)), np.cumsum(a, axis = 1), atol = 1e-4)
    assert np.allclose(device.toHost(device.hypot(deviceA, deviceB)), np.hypot(a, b), atol = 1e-3)
    assert np.allclose(device.toHost(device.atan2(deviceA, deviceB)), np.arctan2(a, b), atol = 1e-5)
    assert np.allclose(device.toHost(device.clip(deviceA, 0, 5)), np.clip(a, 0, 5), atol = 1e-4)


@requiresDevice
@pytest.mark.parametrize('device', DEVICE_BACKENDS)
def testIntegerIndexingWorksOnDevice(device):
    """The block mean indexes with an integer array, so that has to behave identically."""
    source = np.arange(40, dtype = np.float32).reshape(5, 8)
    indices = device.asarray(np.array([0, 2, 4]), 'int64')
    picked = device.toHost(device.asarray(source)[indices])

    assert np.allclose(picked, source[[0, 2, 4]])


@requiresDevice
@pytest.mark.parametrize('device', DEVICE_BACKENDS)
def testSynchronizeIsSafeToCall(device):
    device.synchronize()


def testWholeConversionIsIdenticalAcrossBackends(grayImage):
    """End to end: the rendered rows must come out the same whichever backend ran."""
    torchCpu = compute.getTorchCpuBackend()
    if torchCpu is None:
        pytest.skip("PyTorch is not installed")

    cpuRows = backend.gridToRows(backend.toCharGrid(
        backend.toValueGrid(grayImage, 64, 40, compute.getCpuBackend()), tools.GRAYSCALES[10]))
    deviceRows = backend.gridToRows(backend.toCharGrid(
        backend.toValueGrid(grayImage, 64, 40, torchCpu), tools.GRAYSCALES[10]))

    assert cpuRows == deviceRows
