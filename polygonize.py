__author__ = "Prince Garnett Goting"
import requests,shutil
import numpy as np
from PIL import Image
from pyproj import Proj, transform
from osgeo import gdal,osr
import rasterio
from rasterio.features import shapes
import geopandas as gp
import os
fpath = os.path.dirname(os.path.abspath(__file__))

def reproj(x,y):
    inProj = Proj(init='epsg:3857')
    outProj = Proj(init='epsg:4326')
    x2,y2 = transform(inProj,outProj,x,y)
    return x2,y2

def reproj2(x,y):
    inProj = Proj(init='epsg:4326')
    outProj = Proj(init='epsg:3857')
    x2,y2 = transform(inProj,outProj,x,y)
    return x2,y2

# Get bbounds
def getBoundsFromUrl(url):
    bbox = url.split('bbox=')[1].split('&bboxSR')[0].split('%2C')
    to_float = list(map(lambda x: float(x),bbox))
    bbox = []
    for i in [0,2]:
        x,y = reproj(to_float[i],to_float[i+1])
        bbox.extend([x,y])
    return bbox

def getUrlFromBounds(bounds):
    bbox = []
    for i in [0,2]:
        x,y = reproj2(bounds[i],bounds[i+1])
        bbox.extend([x,y])
    return bbox


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
    
    if numBands > 1:
        for i in range(0,numBands):
            dataset.GetRasterBand(i+1).WriteArray(array[:,:,i])
    else:
        dataset.GetRasterBand(1).WriteArray(array)

    dataset.FlushCache()  # Write to disk.

def rasterToShp(rastPath,shpPath):
    mask = None
    with rasterio.open(rastPath) as src:
        image = src.read(1) # first band
        results = (
        {'properties': {'raster_val': v}, 'geometry': s}
        for i, (s, v) 
        in enumerate(
            shapes(image, mask=mask, transform=src.transform)))
    geoms = list(results)

    # Filter 0 values
    final = []
    for geo in geoms:
        rast_val = geo['properties']['raster_val']
        if rast_val != 0.0:
            final.append(geo)

    # Create geodataframe from geoms
    poly  = gp.GeoDataFrame.from_features(final)
    poly.crs = {'init' :'epsg:3857'}

    # Reproject
    poly = poly.to_crs({'init': 'epsg:4326'})
    # Save
    poly.to_file(shpPath)

def main(bounds,impath,rastPath,shpPath):
	"""
	This is the main function to extract png tiles from MGB website and convert them into raster and shp files.
	"""
    # First get bounds in 4326 then reproject as 3857
    bbox = getUrlFromBounds(bounds)
    url = "http://gdis.mgb.gov.ph/arcgis/rest/services/Flood_Landslide_Susceptibility_10K_new_web/"\
    + "MapServer/export?dpi=96&transparent=true&format=png8&"\
    + "bbox={longMin}%2C{latMin}%2C{longMax}%2C{latMax}&bboxSR=102100&imageSR=102100&size=1177%2C926&f=image"
    url = url.format(longMin=bbox[0],latMin=bbox[1],longMax=bbox[2],latMax=bbox[3])

    # Then download the source png
    r = requests.get(url,stream=True)
    with open(impath,'wb') as f:
        r.raw.decode_content = True
        shutil.copyfileobj(r.raw, f)

    # Read image array to raster
    img = np.asarray(Image.open(impath))
    epsg = 4326
    bands = 1
    xmin,ymin,xmax,ymax = bounds[0],bounds[1],bounds[2],bounds[3]
    arrayToRaster(img,rastPath,epsg,xmin,xmax,ymin,ymax,bands)

    # Read array to shape
    rasterToShp(rastPath,shpPath)

if __name__ == '__main__':
	# Change these bounds. Do not use large areas as it would cause a failure on MGB servers.
    longMin = 123.684
    latMin = 10.175
    longMax = 123.785
    latMax = 10.253
    bounds = [longMin,latMin,longMax,latMax]

    # Change here for the filenames of output files
    impath = os.path.join(fpath,'out.png')
    rastPath = os.path.join(fpath,'OUTPUT.TIF')
    shpPath = os.path.join(fpath,'output.shp')
    main(bounds,impath,rastPath,shpPath)
    print("Done!")
