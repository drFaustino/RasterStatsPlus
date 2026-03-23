import os
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
from qgis.PyQt.QtWidgets import QColorDialog
from qgis.PyQt.QtGui import QIcon

from .gui.main_dialog import RasterStatsPlusDialog
from .toolbelt.qgis_helpers import list_raster_layers, get_layer_by_id, raster_band_items
from .processing.stats_core import compute_raster_stats
from .processing.export_core import stats_to_text, export_stats_csv
from .processing.plot_export import save_histogram
from .toolbelt.qgis_helpers import format_stats


class RasterStatsPlusPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.dlg = None
        self._last_stats = None
        self._last_values = None

    def initGui(self):
        icon = os.path.join(self.plugin_dir, "resources", "images", "icon_24.png")
        self.action = QAction(QIcon(icon), "Raster Stats Plus", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToRasterMenu("Raster Stats Plus", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginRasterMenu("Raster Stats Plus", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        if not self.dlg:
            self.dlg = RasterStatsPlusDialog()
            self._connect_signals()

        self._populate_raster_combo()
        self.dlg.progressBar.setValue(0)
        self.dlg.show()

    def _connect_signals(self):
        self.dlg.cmbRaster.currentIndexChanged.connect(self._update_band_combo)
        self.dlg.btnCompute.clicked.connect(self._compute)
        self.dlg.btnExport.clicked.connect(self._export_stats)
        self.dlg.btnSalveGraph.clicked.connect(self._save_graph)
        self.dlg.btnClose.clicked.connect(self.dlg.close)
        self.dlg.pushButtonReset.clicked.connect(self._reset)
        self.dlg.btnColorHist.clicked.connect(self._choose_hist_color)

    def _populate_raster_combo(self):
        self.dlg.cmbRaster.clear()
        for lyr in list_raster_layers():
            self.dlg.cmbRaster.addItem(lyr.name(), lyr.id())

    def _update_band_combo(self):
        raster = self._get_raster()
        self.dlg.cmbBand.clear()

        if raster:
            for label, band in raster_band_items(raster):
                self.dlg.cmbBand.addItem(label, band)

            # Seleziona automaticamente la prima banda
            if self.dlg.cmbBand.count() > 0:
                self.dlg.cmbBand.setCurrentIndex(0)

    def _get_raster(self):
        idx = self.dlg.cmbRaster.currentIndex()
        if idx < 0: return None
        return get_layer_by_id(self.dlg.cmbRaster.itemData(idx))

    def _compute(self):
        raster = self._get_raster()
        if not raster:
            QMessageBox.warning(self.dlg, "Raster Stats Plus", "Seleziona un raster.")
            return

        band = self.dlg.cmbBand.currentData()
        if not band:
            QMessageBox.warning(self.dlg, "Raster Stats Plus", "Seleziona una banda.")
            return

        stats, values = compute_raster_stats(
            raster,
            band,
            progress_callback=self.dlg.progressBar.setValue
        )

        self._last_stats = stats
        self._last_values = values

        # stats è già un dict: lo copio per sicurezza
        stats_dict = dict(stats)

        # Se il checkbox è attivo → formatta
        if self.dlg.checkBoxFormat.isChecked():
            stats_dict = format_stats(stats_dict)

        # Riempie la tabella (nota: metodo sulla dialog)
        self.dlg.fill_table(stats_dict)

        # Istogramma
        if values.size > 0:
            self.dlg.histCanvas.plot_histogram(values, color=self.dlg.hist_color)

        self.dlg.progressBar.setValue(0)

    def _export_stats(self):
        if not self._last_stats:
            QMessageBox.information(self.dlg, "Raster Stats Plus", "Nessun risultato da esportare.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self.dlg,
            "Esporta risultati",
            "",
            "TXT (*.txt);;CSV (*.csv)"
        )
        if not path:
            return

        ext = os.path.splitext(path)[1].lower()

        if ext == ".txt":
            with open(path, "w", encoding="utf-8") as f:
                f.write(stats_to_text(self._last_stats))
        else:
            export_stats_csv(path, self._last_stats)

        QMessageBox.information(self.dlg, "Raster Stats Plus", "Esportazione completata.")

    def _save_graph(self):
        if self._last_values is None or self._last_values.size == 0:
            QMessageBox.information(self.dlg, "Raster Stats Plus", "Nessun istogramma da salvare.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self.dlg,
            "Salva istogramma",
            "",
            "PNG (*.png);;SVG (*.svg)"
        )
        if not path:
            return

        save_histogram(self.dlg.histCanvas.get_figure(), path)
        QMessageBox.information(self.dlg, "Raster Stats Plus", "Istogramma salvato correttamente.")

    def _reset(self):
        # Reset variabili interne
        self._last_stats = None
        self._last_values = None

        # Reset tabella e grafico
        self.dlg.reset_view()

        # Reset progress bar
        self.dlg.progressBar.setValue(0)
    
    def _choose_hist_color(self):
        # Scegli colore
        color = QColorDialog.getColor()

        if not color.isValid():
            return

        # Salva il colore scelto
        self.dlg.hist_color = color.name()

        # Aggiorna preview
        self.dlg.labelColorPreview.setStyleSheet(
            f"background-color: {self.dlg.hist_color}; border: 1px solid #444;"
        )

        # Se c'è già un istogramma, aggiorna
        if self._last_values is not None and self._last_values.size > 0:
            self.dlg.histCanvas.plot_histogram(self._last_values, color=self.dlg.hist_color)
