import cv2
import matplotlib.pyplot as plt
import numpy as np
from scipy import spatial
import vtk
import sys

import utils

hMin, hMax = [-8200, 21229]  # Min/max elevations in m
R = 3389500
sfR = 0.001

sf = 10

og_img = cv2.imread('data/Mars_MGS_MOLA_DEM_small.png', 0)
width = int(og_img.shape[1] / sf)
height = int(og_img.shape[0] / sf)
img = cv2.resize(og_img, (width, height), interpolation=cv2.INTER_AREA)
img = cv2.flip(img, 0)

del og_img

ycoords, xcoords = np.where(img >= 0)

img -= np.min(img)

# In equirectangular projection, x and y coords are longitudes and latitudes
# respectively, so just need to scale them to appropriate ranges.

# Longitudes go from -180 to +180, and latitudes go from -90 to +90
lmbdas = (xcoords * (360 / np.max(xcoords))) - 180
phis = (ycoords * (180 / np.max(ycoords))) - 90
rs = img.reshape(-1) * ((hMax - hMin) / np.max(img))
rs += hMin

xs, ys, zs = utils.geoToCartesian(R * sfR, lmbdas, phis)

# Create sphere dataset and save as VTP file
heightCoords = np.array([xs, ys, zs]).T
sys.setrecursionlimit(10000)
tree = spatial.KDTree(heightCoords)

sphereSource = vtk.vtkSphereSource()
sphereSource.SetRadius(R * sfR)
sphereSource.SetStartTheta(1e-5)
sphereSource.SetThetaResolution(800)
sphereSource.SetPhiResolution(800)
sphereSource.Update()

sphereHeights = vtk.vtkDoubleArray()
sphereHeights.SetName('Heights')
numPoints = sphereSource.GetOutput().GetNumberOfPoints()
sphereHeights.SetNumberOfTuples(numPoints)
spherePointsArray = sphereSource.GetOutput().GetPoints().GetData()
for i in range(numPoints):
    point = spherePointsArray.GetTuple3(i)
    heightIdx = tree.query([point])[-1][0]
    sphereHeights.SetTuple1(i, rs[heightIdx] * sfR)
sphereSource.GetOutput().GetPointData().SetScalars(sphereHeights)

vtkWriter = vtk.vtkXMLPolyDataWriter()
vtkWriter.SetFileName('marstopoV2.vtp')
vtkWriter.SetInputData(sphereSource.GetOutput())
vtkWriter.Write()

# Show heights that have been computed
fig = plt.figure(figsize=[10, 10])
ax = fig.add_subplot(projection='3d')

ax.scatter(xs, ys, zs, s=1, c=img.reshape(-1)/255.0, cmap='binary_r')

ax.set_box_aspect((2, 2, 2))
ax.set(xlabel='x', ylabel='y', zlabel='z')
plt.show()
