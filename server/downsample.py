"""Uniform downsampling of spectrum arrays for network-efficient transfer."""


def downsample(arr, target_points=3000):
    """Uniformly subsample a 1D array to approximately target_points points.

    Uses stride-based sampling (every N-th point) to preserve the overall
    envelope shape while reducing data volume by ~91% for 32,724-point arrays.
    Works on both Python lists and numpy arrays.
    """
    n = len(arr)
    if n <= target_points:
        return list(arr)
    stride = n / target_points
    result = []
    i = 0.0
    while i < n:
        result.append(arr[int(i)])
        i += stride
    return result
