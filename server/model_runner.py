"""
DeepMID model interface.

The model takes two NMR spectra (reference + query) and outputs a similarity
probability. This module is designed to be imported by the FastAPI server at
startup: model and reference library are loaded once and cached in memory.

Workflow:
  1. init()            — called once at server startup
  2. match(query_dir)  — called per request, returns sorted match results

To integrate with the actual DeepMID model, implement:
  - init(): load DeepMID_Ori.load_DeepMID() + readBruker.read_bruker_hs_base()
  - match(): readBruker.read_bruker_h_base() + DeepMID_Ori.predict_DeepMID()
"""

import os

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SERVER_DIR, 'data', 'plant_flavors')
MODEL_PATH = os.path.join(SERVER_DIR, 'model', 'model_1', 'test_nmr')

_model = None
_plant_flavors = None


def init():
    """Load model weights and preprocess reference library. Called once at startup."""
    global _model, _plant_flavors
    # TODO: import and load DeepMID model
    # from deepmid.DeepMID_Ori import load_DeepMID
    # from deepmid.readBruker import read_bruker_hs_base
    # _model = load_DeepMID(MODEL_PATH)
    # _plant_flavors = read_bruker_hs_base(DATA_PATH, False, True, False)
    _model = None
    _plant_flavors = []


def match(query_dir):
    """
    Compare query spectrum against all reference spectra.

    Args:
        query_dir: path to a Bruker spectrum directory (contains 1/pdata/1/)

    Returns:
        dict: {
            'query_name': str,
            'query_ppm': list[float],
            'query_fid': list[float],
            'results': list[dict] sorted by probability descending
        }
        Each result dict: {'name': str, 'probability': float, 'ppm': list, 'fid': list}
    """
    # TODO: preprocess query and run prediction
    # from deepmid.readBruker import read_bruker_h_base
    # query = read_bruker_h_base(query_dir, False, True)
    # ... build R/Q matrices ... predict_DeepMID(model, [R, Q]) ...
    # ... sort and return results ...
    return {
        'query_name': os.path.basename(os.path.normpath(query_dir)),
        'query_ppm': [],
        'query_fid': [],
        'results': [],
    }
