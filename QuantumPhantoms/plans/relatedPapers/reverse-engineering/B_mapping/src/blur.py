"""Wootton's quantum blur [B04, B05] (statevector, ideal) next to its classical Gaussian baseline."""
import numpy as np
from scipy.ndimage import gaussian_filter


def _bits(shape):
    ks = []
    for d in shape:
        k = int(np.log2(d))
        if 2 ** k != d:
            raise ValueError("every axis must be a power of two")
        ks.append(k)
    return ks


def encode(arr: np.ndarray) -> np.ndarray:
    """Amplitudes sqrt(h / sum h), index = row-major flattening = bitstring of the coordinates."""
    a = np.asarray(arr, float)
    return np.sqrt(a / a.sum()).ravel().astype(complex)


def apply_rx_all(psi: np.ndarray, n: int, theta: float) -> np.ndarray:
    """Rx(theta) on every qubit of an n-qubit statevector."""
    c, s = np.cos(theta / 2), -1j * np.sin(theta / 2)
    t = psi.reshape((2,) * n)
    for ax in range(n):
        t = np.moveaxis(np.tensordot(np.array([[c, s], [s, c]]), t, axes=([1], [ax])), 0, ax)
    return t.ravel()


def quantum_blur(arr: np.ndarray, theta: float) -> np.ndarray:
    """Blurred map = output probabilities, rescaled to the input's total mass."""
    n = sum(_bits(arr.shape))
    p = np.abs(apply_rx_all(encode(arr), n, theta)) ** 2
    return (p * np.asarray(arr, float).sum()).reshape(arr.shape)


def gaussian_blur(arr: np.ndarray, sigma: float) -> np.ndarray:
    return gaussian_filter(np.asarray(arr, float), sigma, mode="constant")


def corr(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.corrcoef(a.ravel(), b.ravel())[0, 1])


def best_gaussian(arr: np.ndarray, target: np.ndarray, sigmas=np.linspace(0.25, 6, 47)):
    """Gaussian sigma that best correlates with the quantum blur (the fairest classical match)."""
    scores = [corr(gaussian_blur(arr, s), target) for s in sigmas]
    i = int(np.argmax(scores))
    return float(sigmas[i]), float(scores[i])
