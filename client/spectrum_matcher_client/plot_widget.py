"""Interactive matplotlib plot widget for NMR spectrum comparison."""

from PySide6.QtWidgets import QVBoxLayout, QWidget

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

_LINE_COLORS = ["#dc2626", "#2563eb", "#16a34a", "#9333ea", "#ea580c"]
_QUERY_COLOR = "#1e1e2e"


class SpectrumPlotWidget(QWidget):
    """Interactive NMR comparison plot with zoom, pan, and save support."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._figure = Figure(figsize=(14, 6))
        self._canvas = FigureCanvasQTAgg(self._figure)
        self._toolbar = NavigationToolbar2QT(self._canvas, self)
        self._toolbar.setVisible(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._toolbar)
        layout.addWidget(self._canvas)

    def toolbar(self):
        return self._toolbar

    def set_toolbar_visible(self, visible):
        self._toolbar.setVisible(visible)

    def render_comparison(self, query_ppm, query_fid, results, top_n=3):
        """Render a comparison plot from downsampled spectrum data."""
        self._figure.clear()
        ax = self._figure.add_subplot(111)

        ax.plot(query_ppm, query_fid, color=_QUERY_COLOR, linewidth=1.2,
                label="Query Spectrum")
        ax.fill_between(query_ppm, 0, query_fid, color=_QUERY_COLOR, alpha=0.08)

        refs_to_plot = []
        for r in results[:top_n]:
            if "ppm_ds" in r and "fid_ds" in r and len(r["ppm_ds"]) > 0:
                refs_to_plot.append(r)

        for i, ref in enumerate(refs_to_plot):
            color = _LINE_COLORS[i % len(_LINE_COLORS)]
            prob = ref.get("probability", 0)
            label = f"{ref['name']}  ({prob:.3f})"
            ax.plot(ref["ppm_ds"], ref["fid_ds"], color=color, linewidth=1.0,
                    alpha=0.85, label=label)

        ax.set_xlim(max(query_ppm), min(query_ppm))
        ax.set_xlabel("Chemical Shift (ppm)", fontsize=13)
        ax.set_ylabel("Intensity (normalized)", fontsize=13)
        ax.set_title("NMR Spectrum Comparison — Query vs Top Matches  (DeepMID)",
                     fontsize=15)
        ax.legend(fontsize=10, loc="upper left", framealpha=0.9)
        ax.grid(True, alpha=0.20)
        self._figure.tight_layout(pad=1.2)
        self._canvas.draw()

    def render_fallback(self, pixmap):
        """Display a static QPixmap when downsampled data is unavailable."""
        self._figure.clear()
        ax = self._figure.add_subplot(111)
        ax.imshow(pixmap.toImage(), aspect="auto")
        ax.axis("off")
        self._figure.tight_layout(pad=0)
        self._canvas.draw()

    def clear(self):
        self._figure.clear()
        self._canvas.draw()

    def save_figure(self, filepath):
        self._figure.savefig(filepath, dpi=200)
