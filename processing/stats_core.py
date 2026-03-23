import math
import numpy as np
from qgis.core import QgsRasterBandStats

def compute_raster_stats(raster, band_idx, progress_callback=None):
    provider = raster.dataProvider()

    if progress_callback: progress_callback(5)

    stats = provider.bandStatistics(
        band_idx,
        QgsRasterBandStats.All,
        raster.extent(),
        0
    )

    res_x = raster.rasterUnitsPerPixelX()
    res_y = raster.rasterUnitsPerPixelY()
    total_pixels = raster.width() * raster.height()

    block = provider.block(band_idx, raster.extent(), raster.width(), raster.height())
    nodata = provider.sourceNoDataValue(band_idx)

    if progress_callback: progress_callback(25)

    values = []
    for col in range(block.width()):
        for row in range(block.height()):
            v = block.value(row, col)
            if nodata is not None and math.isclose(v, nodata): continue
            if math.isnan(v): continue
            values.append(v)

    if progress_callback: progress_callback(60)

    arr = np.array(values, dtype=float)
    valid_pixels = arr.size
    nodata_count = total_pixels - valid_pixels

    if valid_pixels > 0:
        median = float(np.median(arr))
        p5 = float(np.percentile(arr, 5))
        p25 = float(np.percentile(arr, 25))
        p75 = float(np.percentile(arr, 75))
        p95 = float(np.percentile(arr, 95))
        iqr = p75 - p25 # IQR (Interquartile Range)
        std = arr.std()
        var = arr.var() # variance
        mean = arr.mean()
        value_range = stats.maximumValue - stats.minimumValue # Range (max - min)
        skewness = float(((arr - mean)**3).mean() / (std**3)) if std != 0 else float('nan')
        kurtosis = float(((arr - mean)**4).mean() / (var**2)) if var != 0 else float('nan')
        coeff_var = float(std / mean) if mean != 0 else float('nan')
    else:
        median = p5 = p25 = p75 = p95 = skewness = kurtosis = coeff_var = float('nan')

    if progress_callback: progress_callback(90)

    stats_dict = {
        "Cell size x": res_x,
        "Cell size y": res_y,
        "Total pixels": total_pixels,
        "Valid pixels": valid_pixels,
        "NoData pixels": nodata_count,
        "Min": stats.minimumValue,
        "Max": stats.maximumValue,
        "Range": value_range,
        "Mean": stats.mean,
        "Stddev": stats.stdDev,
        "Variance": var,
        "Median": median,
        "p5": p5,
        "p25": p25,
        "p75": p75,
        "p95": p95,
        "IQR": iqr,
        "Skewness": skewness,
        "Kurtosis": kurtosis,
        "Coeff_var": coeff_var,
    }

    if progress_callback: progress_callback(100)

    return stats_dict, arr
