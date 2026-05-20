"""
Spectrum visualization using matplotlib.

Generates a PNG comparison plot: query spectrum overlaid with top-N reference
spectra. The plot is saved to a static directory and served via GET endpoint.
"""

import os

PLOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'plots')


def plot_comparison(query_ppm, query_fid, results, top_n=3):
    """
    Generate a comparison plot of query vs top-N reference spectra.

    Args:
        query_ppm: ppm values of query spectrum
        query_fid: intensity values of query spectrum
        results: list of result dicts (sorted by probability, from model_runner.match())
        top_n: number of top matches to overlay

    Returns:
        str: filename of the saved plot (e.g. 'abc123.png')
    """
    os.makedirs(PLOT_DIR, exist_ok=True)
    # TODO: use matplotlib to plot query spectrum + top_n reference spectra
    # import matplotlib.pyplot as plt
    # fig, ax = plt.subplots()
    # ax.plot(query_ppm, query_fid, label='Query', color='black')
    # for r in results[:top_n]:
    #     ax.plot(r['ppm'], r['fid'], label=f"{r['name']} ({r['probability']:.2f})")
    # ...
    # fig.savefig(os.path.join(PLOT_DIR, filename))
    filename = 'placeholder.png'
    return filename
