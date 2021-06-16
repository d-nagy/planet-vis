import cv2
import matplotlib.pyplot as plt
import numpy as np
from scipy import spatial
import vtk
import sys

import utils

# Open and load config from file.
dataFile = sys.argv[1]
data = utils.readDataFile(dataFile)

# Open and preprocess topographic map.
og_img = cv2.imread(f'images/{data.topo}', 0)
width = int(og_img.shape[1] / data.sf)
height = int(og_img.shape[0] / data.sf)
img = cv2.resize(og_img, (width, height), interpolation=cv2.INTER_AREA)
img = cv2.flip(img, 0)

del og_img

# We need longitudes (lmbdas) and latitudes (phis) from the topographic map
# to be able to convert them to 3D cartesian coordinates.

# In our equirectangularly projected topographic map, x and y coords are
# longitudes and latitudes respectively, so just need to scale them to
# appropriate ranges.

ycoords, xcoords = np.where(img >= 0)

# Longitudes go from -180 to +180
lmbdas = (xcoords * (360 / np.max(xcoords))) - 180
# Latitudes go from -90 to +90
phis = (ycoords * (180 / np.max(ycoords))) - 90

# Get elevations from the topographic map
img -= np.min(img)
rs = img.reshape(-1) * ((data.hMax - data.hMin) / np.max(img))
rs += data.hMin

# Compute cartesian coordinates of planet surface points.
xs, ys, zs = utils.geoToCartesian(data.R * data.sfR, lmbdas, phis)

# Create sphere dataset and save as VTP file
heightCoords = np.array([xs, ys, zs]).T
sys.setrecursionlimit(10000)
tree = spatial.KDTree(heightCoords)

sphereSource = vtk.vtkSphereSource()
sphereSource.SetRadius(data.R * data.sfR)
sphereSource.SetStartTheta(1e-5)
sphereSource.SetThetaResolution(int(data.res))
sphereSource.SetPhiResolution(int(data.res))
sphereSource.Update()

sphereHeights = vtk.vtkDoubleArray()
sphereHeights.SetName('Heights')
numPoints = sphereSource.GetOutput().GetNumberOfPoints()
sphereHeights.SetNumberOfTuples(numPoints)
spherePointsArray = sphereSource.GetOutput().GetPoints().GetData()
for i in range(numPoints):
    point = spherePointsArray.GetTuple3(i)
    heightIdx = tree.query([point])[-1][0]
    sphereHeights.SetTuple1(i, rs[heightIdx] * data.sfR)
sphereSource.GetOutput().GetPointData().SetScalars(sphereHeights)

vtkWriter = vtk.vtkXMLPolyDataWriter()
vtkWriter.SetFileName(f'sources/{data.vtksource}')
vtkWriter.SetInputData(sphereSource.GetOutput())
vtkWriter.Write()

# Show heights that have been computed
fig = plt.figure(figsize=[10, 10])
ax = fig.add_subplot(projection='3d')

ax.scatter(xs, ys, zs, s=1, c=img.reshape(-1)/255.0, cmap='binary_r')

ax.set_box_aspect((2, 2, 2))
ax.set(xlabel='x', ylabel='y', zlabel='z')
plt.show()
