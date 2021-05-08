import cv2
import matplotlib.pyplot as plt
import numpy as np
from scipy import spatial
import vtk

import utils

heightRange = np.array([-8000, 14000])
R = 3389500
sfR = 0.001

cmapX = np.array([654, 2296])
cmapDims = np.array([2682, 97])
cmapSegmentWidth = 9
cmapDividerColour = np.full(3, 245)

westHemisphereX = np.array([13, 151])
eastHemisphereX = np.array([2027, 151])
hemisphereDims = np.array([1962, 1960])

sf = 8

img = cv2.imread('data/elevationData.tif')
width = int(img.shape[1] / sf)
height = int(img.shape[0] / sf)
smallImg = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)


#
# Construct colormap from image
#
rawCmap = img[
    cmapX[1] + cmapDims[1] // 2,
    cmapX[0]:cmapX[0] + cmapDims[0]
]

medianCmap = []
for i in range(0, len(rawCmap), cmapSegmentWidth):
    segment = np.copy(rawCmap[i:i+cmapSegmentWidth])
    isCmapDivider = [all(np.greater(segColor, cmapDividerColour))
                     for segColor in segment]
    if any(isCmapDivider):
        centerIndex = np.argmax(segment, axis=0)[0]
        segment = np.concatenate(
            (segment[:centerIndex-2], segment[centerIndex+3:])
        )
    medianCmap.append(np.median(segment, axis=0))

medianCmap = utils.stableUnique(np.array(medianCmap).astype(img.dtype), axis=0)
medianCmapHsv = cv2.cvtColor(np.array([medianCmap]), cv2.COLOR_BGR2HSV)[0]

cmapBgr = utils.interpColormap(medianCmap, 5)
cmapHsv = utils.interpColormap(medianCmapHsv, 10, isHsv=True)


westHemi = utils.getBoxRegion(img, westHemisphereX, hemisphereDims)
eastHemi = utils.getBoxRegion(img, eastHemisphereX, hemisphereDims)
westHemiSmall = utils.getBoxRegion(
    smallImg, westHemisphereX//sf, hemisphereDims//sf
)
eastHemiSmall = utils.getBoxRegion(
    smallImg, eastHemisphereX//sf, hemisphereDims//sf
)

#
# Plot RGB cube with colormap embedded as a black line
#
# fig = plt.figure(figsize=[10, 10])
# ax = fig.add_subplot(projection='3d')

# colors = np.column_stack(np.where(np.ones((256, 256, 256))))
# xs, ys, zs = np.where(np.ones((256, 256, 256)))

# everyNth = 750
# ax.scatter(xs[::everyNth], ys[::everyNth], zs[::everyNth], s=20, c=colors[::everyNth]/255.0, alpha=0.1)
# xs, ys, zs = np.flip(cmapBgr, axis=-1).T
# ax.scatter(xs, ys, zs, c='black')
# ax.set(xlabel='r', ylabel='g', zlabel='b')
# plt.show()


#
# Plot HSV cube with colormap embedded as a black line
#
# fig = plt.figure(figsize=[10, 10])
# ax = fig.add_subplot(projection='3d')

# colors = np.column_stack(np.where(np.ones((180, 256, 256)))).astype(img.dtype)
# colorsRgb = cv2.cvtColor(np.array([colors]), cv2.COLOR_HSV2RGB)[0]

# xs, ys, zs = np.where(np.ones((180, 256, 256)))

# everyNth = 750
# ax.scatter(xs[::everyNth], ys[::everyNth], zs[::everyNth], s=20, c=colorsRgb[::everyNth]/255.0, alpha=0.1)
# xs, ys, zs = cmapHsv.T
# ax.scatter(xs, ys, zs, c=np.arange(xs.size), cmap='plasma', alpha=1)
# ax.set(xlabel='h', ylabel='s', zlabel='v')
# plt.show()


#
# Plot spherical height data
#
fig = plt.figure(figsize=[10, 10])
ax = fig.add_subplot(projection='3d')

wxs, wys = utils.getOrthHemisphereXYCoords(westHemiSmall)
exs, eys = utils.getOrthHemisphereXYCoords(eastHemiSmall)

wcs = utils.getHemispherePixels(westHemiSmall)
ecs = utils.getHemispherePixels(eastHemiSmall)

_, wlmbdas, wphis = utils.inverseOrthographic(
    wxs, wys, max(hemisphereDims)//sf / 2, lmbda0=-90
)
_, elmbdas, ephis = utils.inverseOrthographic(
    exs, eys, max(hemisphereDims)//sf / 2, lmbda0=90
)

lmbdas = np.concatenate((wlmbdas, elmbdas))
phis = np.concatenate((wphis, ephis))

csBgr = np.concatenate((wcs, ecs))
csHsv = cv2.cvtColor(np.array([csBgr]), cv2.COLOR_BGR2HSV)[0]

mappedCsHsvIdx = utils.findNearestColorIdx(
    csHsv, cmapHsv, metric=utils.ColorMetric.L2NORM, weights=[4, 1, 2]
)

mappedCsHsv = cmapHsv[mappedCsHsvIdx]

altitudesHsv = utils.getHeightFromCmapIdx(mappedCsHsvIdx, cmapHsv, heightRange)

xs, ys, zs = utils.geoToCartesian(R * sfR, lmbdas, phis)

heightCoords = np.array([xs, ys, zs]).T
tree = spatial.KDTree(heightCoords)

sphereSource = vtk.vtkSphereSource()
sphereSource.SetRadius(R * sfR)
sphereSource.SetStartTheta(1e-5)
sphereSource.SetThetaResolution(500)
sphereSource.SetPhiResolution(500)
sphereSource.Update()

sphereHeights = vtk.vtkDoubleArray()
sphereHeights.SetName('Heights')
numPoints = sphereSource.GetOutput().GetNumberOfPoints()
sphereHeights.SetNumberOfTuples(numPoints)
spherePointsArray = sphereSource.GetOutput().GetPoints().GetData()
for i in range(numPoints):
    point = spherePointsArray.GetTuple3(i)
    heightIdx = tree.query([point])[-1][0]
    sphereHeights.SetTuple1(i, altitudesHsv[heightIdx] * sfR)
sphereSource.GetOutput().GetPointData().SetScalars(sphereHeights)

vtkWriter = vtk.vtkXMLPolyDataWriter()
vtkWriter.SetFileName('marstopo.vtp')
vtkWriter.SetInputData(sphereSource.GetOutput())
vtkWriter.Write()

# heightMapHsv = (R + altitudesHsv) * sfR
# xs, ys, zs = utils.geoToCartesian(heightMapHsv, lmbdas, phis)

# ax.scatter(xs, ys, zs, s=1, c=cv2.cvtColor(
#     np.array([mappedCsHsv]), cv2.COLOR_HSV2RGB)[0]/255.0
# )
# ax.set_box_aspect((2, 2, 2))
# ax.set(xlabel='x', ylabel='y', zlabel='z')
# plt.show()


#
# Plot spherical original pixel data
#
# fig = plt.figure(figsize=[10, 10])
# ax = fig.add_subplot(projection='3d')

# xs, ys, zs = geoToCartesian(r, lmbdas, phis)

# ax.scatter(xs, ys, zs, s=1, c=np.flip(cs, axis=-1)/255.0)
# ax.set_box_aspect((2, 2, 2))
# ax.set(xlabel='x', ylabel='y', zlabel='z')
# plt.show()

#
# Show some image
#
# cv2.imshow('img', np.tile(cmapBgr, (20, 1, 1)))
# cv2.imshow('img2', cv2.cvtColor(np.tile(cmapHsv, (20, 1, 1)), cv2.COLOR_HSV2BGR))
# # cv2.imshow('img', westHemiSmall)
# # # cv2.imwrite('wAlt.png', np.array((wAltImg)))
# cv2.imshow('img2', np.array((wAltImg)))

# wait_time = 1000
# while cv2.getWindowProperty('img', cv2.WND_PROP_VISIBLE) >= 1 or \
#       cv2.getWindowProperty('img2', cv2.WND_PROP_VISIBLE):
#     keyCode = cv2.waitKey(wait_time)
#     if (keyCode & 0xFF) == ord("q"):
#         cv2.destroyAllWindows()
#         break
