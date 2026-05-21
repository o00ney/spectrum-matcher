"""
DeepMID model interface.

When the real model is available, calls DeepMID_Ori and readBruker.
When not, returns synthetic mock data so the API remains functional for testing.
"""

import os
import math

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SERVER_DIR, 'data', 'plant_flavors')
MODEL_PATH = os.path.join(SERVER_DIR, 'model', 'model_1', 'test_nmr')

_model = None
_plant_flavors = None
_mock_mode = True

_PLANT_NAMES = [
    "Alfalfa Extraction", "Carob Extraction", "Chicory Extraction",
    "Fig Extraction", "Galbanum Extraction", "Hops Extraction",
    "Plum Extraction", "Raisin Extraction", "Roman Chamomile Extraction-A",
    "Roman Chamomile Extraction-B", "Tobacco Maillard Reactants",
    "Valerian Root Extraction", "Yunnan Tobacco Extraction",
]


def _generate_mock_spectrum(n_points=32724, ppm_start=10.7, ppm_end=0.3, seed=0):
    """Generate synthetic NMR-like spectrum data for testing."""
    rng = None
    ppm = [ppm_start - (ppm_start - ppm_end) * i / (n_points - 1)
           for i in range(n_points)]
    fid = []
    for i, p in enumerate(ppm):
        v = 0.0
        if seed == 0:
            r = math.sin(i * 0.003) * 0.1 + 0.5  # base
        else:
            r = 0.3
        # a few Gaussian-like peaks at characteristic shifts
        for center, width, amp in _mock_peak_params(seed):
            v += amp * math.exp(-((p - center) ** 2) / (2 * width * width))
        v += r * (0.5 + 0.5 * math.sin(p * 3.7 + seed))
        fid.append(max(0.0, min(1.0, v)))
    return ppm, fid


def _mock_peak_params(seed):
    """Return a set of (center, width, amplitude) peaks that vary by seed."""
    base_peaks = [
        (0.9, 0.02, 1.0), (1.3, 0.03, 0.7), (2.1, 0.01, 0.5),
        (3.5, 0.04, 0.6), (5.2, 0.02, 0.8), (7.1, 0.03, 0.4),
    ]
    return [(c + seed * 0.04, w, a * (0.5 + 0.5 * math.sin(seed * 2.7 + i)))
            for i, (c, w, a) in enumerate(base_peaks)]


def _make_mock_result(name, index):
    ppm, fid = _generate_mock_spectrum(seed=index)
    probability = round(0.15 + 0.85 * math.exp(-index * 0.25), 4)
    return {
        'name': name,
        'probability': probability,
        'ppm': ppm,
        'fid': fid,
    }


def init():
    """Load model. Falls back to mock data if model or data is missing."""
    global _model, _plant_flavors, _mock_mode
    has_model = os.path.exists(MODEL_PATH + '.h5')
    has_data = os.path.isdir(DATA_PATH)
    if has_model and has_data:
        try:
            from deepmid.DeepMID_Ori import load_DeepMID
            from deepmid.readBruker import read_bruker_hs_base
            _model = load_DeepMID(MODEL_PATH)
            _plant_flavors = read_bruker_hs_base(DATA_PATH, False, True, False)
            _mock_mode = False
            return
        except Exception:
            pass
    _mock_mode = True
    _plant_flavors = [{'name': n, 'index': i}
                      for i, n in enumerate(_PLANT_NAMES)]


def match(query_dir):
    """
    Compare query spectrum against all reference spectra.

    Args:
        query_dir: path to a Bruker spectrum directory

    Returns:
        dict with query_ppm, query_fid, and results sorted by probability.
    """
    query_name = os.path.basename(os.path.normpath(query_dir))

    if _mock_mode:
        query_ppm, query_fid = _generate_mock_spectrum(seed=99)
        results = [_make_mock_result(ref['name'], ref['index'])
                   for ref in _plant_flavors]
        results.sort(key=lambda r: r['probability'], reverse=True)
        # keep ppm/fid for top 3 so plotter can render them
        for i, r in enumerate(results):
            if i >= 3:
                r.pop('ppm', None)
                r.pop('fid', None)
        return {
            'query_name': query_name,
            'query_ppm': query_ppm,
            'query_fid': query_fid,
            'results': results,
        }

    from deepmid.readBruker import read_bruker_h_base
    import numpy as np
    from deepmid.DeepMID_Ori import predict_DeepMID

    query = read_bruker_h_base(query_dir, False, True)
    refs = _plant_flavors
    n = len(refs)
    p = query['ppm'].shape[0]

    R = np.zeros((n, p), dtype=np.float32)
    Q = np.zeros((n, p), dtype=np.float32)
    for i in range(n):
        R[i] = refs[i]['fid']
        Q[i] = query['fid']

    yp = predict_DeepMID(_model, [R, Q])

    results = []
    for i in range(n):
        results.append({
            'name': refs[i]['name'],
            'probability': float(yp[i][0]),
        })

    results.sort(key=lambda r: r['probability'], reverse=True)

    # return spectrum data for top 3 references (for plotting)
    for i, r in enumerate(results):
        if i < 3:
            r['ppm'] = refs[i]['ppm'].tolist()
            r['fid'] = refs[i]['fid'].tolist()

    return {
        'query_name': query['name'],
        'query_ppm': query['ppm'].tolist(),
        'query_fid': query['fid'].tolist(),
        'results': results,
    }
