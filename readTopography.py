import cv2
import matplotlib.pyplot as plt
import numpy as np

from utils import *

heightRange = np.array([-8000, 14000])

cmapX = np.array([654, 2296])
cmapDims = np.array([2682, 97])
cmapSegmentWidth = 9
cmapDividerColour = np.full(3, 245)

westHemisphereX = np.array([13, 151])
eastHemisphereX = np.array([2027, 151])
hemisphereDims = np.array([1962, 1960])

sf = 8

img = cv2.imread('data/elevationData.tif')
# img = cv2.imread('data/elevationData_colour_enhanced.tif')
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

medianCmap = stableUnique(np.array(medianCmap).astype(img.dtype), axis=0)
medianCmapHsv = cv2.cvtColor(np.array([medianCmap]), cv2.COLOR_BGR2HSV)[0]

cmapBgr = interpColormap(medianCmap, 5)
cmapHsv = interpColormap(medianCmapHsv, 10, isHsv=True)


westHemi = getBoxRegion(img, westHemisphereX, hemisphereDims)
eastHemi = getBoxRegion(img, eastHemisphereX, hemisphereDims)
westHemiSmall = getBoxRegion(smallImg, westHemisphereX//sf, hemisphereDims//sf)
eastHemiSmall = getBoxRegion(smallImg, eastHemisphereX//sf, hemisphereDims//sf)

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

wxs, wys = getOrthHemisphereXYCoords(westHemiSmall)
exs, eys = getOrthHemisphereXYCoords(eastHemiSmall)

wcs = getHemispherePixels(westHemiSmall)
ecs = getHemispherePixels(eastHemiSmall)

r, wlmbdas, wphis = inverseOrthographic(
    wxs, wys, max(hemisphereDims)//sf / 2, lmbda0=-90
)
_, elmbdas, ephis = inverseOrthographic(
    exs, eys, max(hemisphereDims)//sf / 2, lmbda0=90
)

lmbdas = np.concatenate((wlmbdas, elmbdas))
phis = np.concatenate((wphis, ephis))

csBgr = np.concatenate((wcs, ecs))
csHsv = cv2.cvtColor(np.array([csBgr]), cv2.COLOR_BGR2HSV)[0]

mappedCsHsvIdx = findNearestColorIdx(
    csHsv, cmapHsv, metric=ColorMetric.L2NORM, weights=[4, 1, 2]
)
# mappedCsBgrIdx = findNearestColorIdx(csBgr, cmapBgr)

#
# East hemisphere altitudes
#
# mappedWcsHsvIdx = findNearestColorIdx(cv2.cvtColor(np.array([ecs]), cv2.COLOR_BGR2HSV)[0], cmapHsv)
# mappedWcsHsv = cmapHsv[mappedWcsHsvIdx]
# wAltitudes = getHeightFromCmapIdx(mappedWcsHsvIdx, cmapHsv, heightRange)
# wAltPixels = (wAltitudes-heightRange.min())/((heightRange.max()-heightRange.min())/255.0)
# wAltPixels = (np.around(wAltPixels)).astype(img.dtype)

# nonzeroCounts = np.count_nonzero(np.count_nonzero(westHemiSmall, axis=-1), axis=-1)
# splitIndices = np.cumsum(nonzeroCounts) - 5
# wAltImg = []
# for row in np.split(wAltPixels, splitIndices):
#     newRowLen = westHemiSmall.shape[1]
#     spaceToFill = newRowLen - len(row)
#     if (spaceToFill) % 2 == 0:
#         pad = spaceToFill // 2
#     else:
#         pad = ((spaceToFill // 2 + 1), spaceToFill // 2)

#     wAltImg.append(np.pad(row, pad, 'constant'))

# wAltImg = np.array(wAltImg)

# diffs = np.abs(mappedCsBgrIdx-mappedCsHsvIdx)

# mappedCsBgr = cmapBgr[mappedCsBgrIdx]
mappedCsHsv = cmapHsv[mappedCsHsvIdx]

# altitudesBgr = getHeightFromCmapIdx(mappedCsBgrIdx, cmapBgr, heightRange)
altitudesHsv = getHeightFromCmapIdx(mappedCsHsvIdx, cmapHsv, heightRange)
# heightMapBgr = r + 0.0005 * altitudesBgr
heightMapHsv = r + 0.0005 * altitudesHsv

xs, ys, zs = geoToCartesian(heightMapHsv, lmbdas, phis)

# ax.scatter(xs, ys, zs, s=1, c=np.flip(mappedCsBgr, axis=-1)/255.0)
ax.scatter(xs, ys, zs, s=1, c=cv2.cvtColor(
    np.array([mappedCsHsv]), cv2.COLOR_HSV2RGB)[0]/255.0
)
ax.set_box_aspect((2, 2, 2))
ax.set(xlabel='x', ylabel='y', zlabel='z')
plt.show()


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
