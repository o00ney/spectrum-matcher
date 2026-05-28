"""
Spectrum visualization using matplotlib (Agg backend).

Generates a PNG comparison plot: query spectrum overlaid with top-N reference
spectra. Plot files are saved to static/plots/ and served via GET endpoint.
"""

import os
import uuid

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PLOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'plots')

# colors for reference spectra
_LINE_COLORS = ['#dc2626', '#2563eb', '#16a34a', '#9333ea', '#ea580c']


def plot_comparison(query_ppm, query_fid, results, top_n=3):
    """
    Generate a comparison plot of query vs top-N reference spectra.

    Args:
        query_ppm: ppm values of query spectrum
        query_fid: intensity values of query spectrum
        results: list of result dicts, each may have 'ppm'/'fid' for plotting
        top_n: number of top results to overlay

    Returns:
        filename of the saved plot (e.g. 'abc123.png')
    """
    os.makedirs(PLOT_DIR, exist_ok=True)

    fig, ax = plt.subplots(figsize=(14, 6))

    ax.plot(query_ppm, query_fid, color='#1e1e2e', linewidth=1.2,
            label='Query Spectrum')
    ax.fill_between(query_ppm, 0, query_fid, color='#1e1e2e', alpha=0.08)

    refs_to_plot = [r for r in results[:top_n]
                    if 'ppm' in r and 'fid' in r
                    and len(r['ppm']) > 0]

    for i, ref in enumerate(refs_to_plot):
        color = _LINE_COLORS[i % len(_LINE_COLORS)]
        prob = ref.get('probability', 0)
        label = f"{ref['name']}  ({prob:.3f})"
        ax.plot(ref['ppm'], ref['fid'], color=color, linewidth=1.0,
                alpha=0.85, label=label)

    ax.set_xlim(max(query_ppm), min(query_ppm))
    ax.set_xlabel('Chemical Shift (ppm)', fontsize=13)
    ax.set_ylabel('Intensity (normalized)', fontsize=13)
    ax.set_title('NMR Spectrum Comparison — Query vs Top Matches  (DeepMID)', fontsize=15)
    ax.legend(fontsize=10, loc='upper left', framealpha=0.9)
    ax.grid(True, alpha=0.20)
    fig.tight_layout(pad=1.2)

    filename = f"{uuid.uuid4().hex}.png"
    filepath = os.path.join(PLOT_DIR, filename)
    fig.savefig(filepath, dpi=200)
    plt.close(fig)

    return filename
