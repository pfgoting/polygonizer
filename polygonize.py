import numpy as np
import geopandas as gpd
from pyproj import Proj, transform

def arrayToRaster(array,fileName,EPSGCode,xMin,xMax,yMin,yMax,numBands):
    xPixels = array.shape[1]  # number of pixels in x
    yPixels = array.shape[0]  # number of pixels in y
    pixelXSize =(xMax-xMin)/xPixels # size of the pixel in X direction     
    pixelYSize = -(yMax-yMin)/yPixels # size of the pixel in Y direction

    driver = gdal.GetDriverByName('GTiff')
    dataset = driver.Create(fileName,xPixels,yPixels,numBands,gdal.GDT_Byte, options = [ 'PHOTOMETRIC=RGB' ])
    dataset.SetGeoTransform((xMin,pixelXSize,0,yMax,0,pixelYSize))  

    datasetSRS = osr.SpatialReference()
    datasetSRS.ImportFromEPSG(EPSGCode)
    dataset.SetProjection(datasetSRS.ExportToWkt())

    for i in range(0,numBands):
        # if numBands =! 1:
        dataset.GetRasterBand(i+1).WriteArray(array[:,:,i])
        # else:
            # dataset.GetRasterBand(i).WriteArray(array[:,:,i])
    dataset.FlushCache()  # Write to disk.

# arrayToRaster(img,'OUT.TIF',EPSGCode,long_min,long_max,lat_min,lat_max,numBands)
