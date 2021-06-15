import numpy as np
from enum import Enum, auto
from collections import namedtuple


class ColorMetric(Enum):
    L2NORM = auto()
    L1NORM = auto()
    MSE = auto()
    MAE = auto()


PlanetData = namedtuple('PlanetData', [
    'hMin', 'hMax', 'R', 'tilt', 'sfR', 'sf', 'topo', 'texture', 'vtksource'
])


def readDataFile(filename):
    with open(filename, 'r') as f:
        lines = [line.strip().split(' = ') for line in f.readlines()]

    for i, (_, v) in enumerate(lines):
        try:
            lines[i][1] = float(v)
        except ValueError:
            pass

    return PlanetData(**dict(lines))


def orthographic(r, lmbda, phi, lmbda0=0, phi0=0):
    '''
    Compute orthographic project of spherical coords. to cartesian (x, y).

    r     = radius,
    lmbda = longitude in degrees (vertical lines),
    phi   = latitude in degrees (horizontal lines)

    (lbmda0, phi0) = centre of projection
    '''
    l, l0 = np.radians(lmbda), np.radians(lmbda0)
    p, p0 = np.radians(phi), np.radians(phi0)

    x = r * np.cos(p) * np.sin(l-l0)
    y = r * (np.cos(p0)*np.sin(p) - np.sin(p0)*np.cos(p)*np.cos(l-l0))

    return x, y


def inverseOrthographic(x, y, r, lmbda0=0, phi0=0):
    '''
    Compute inverse orthographic projection from (x, y) to long/lat coords.
    '''
    l0, p0 = np.radians(lmbda0), np.radians(phi0)

    rho = np.sqrt(x**2 + y**2)
    rhoOverR = rho/r
    rhoOverR[rhoOverR > 1] = 1
    rhoOverR[rhoOverR < -1] = -1
    c = np.arcsin(rhoOverR)

    sc, cc = np.sin(c), np.cos(c)
    sp0, cp0 = np.sin(p0), np.cos(p0)

    tempRho = np.copy(rho)
    tempRho[rho == 0] = 1
    p = np.arcsin(cc*sp0 + y*sc*cp0/tempRho)
    lm = l0 + np.arctan2(x*sc, rho*cc*cp0 - y*sc*sp0)

    lmbda, phi = np.degrees(lm), np.degrees(p)

    return r, lmbda, phi


def geoToCartesian(r, lmbda, phi):
    '''
    Convert geographical coordinates into equivalent 3D Cartesian coords.
    '''
    theta, p = np.radians(lmbda), np.radians(90-phi)

    x = r * np.sin(p) * np.cos(theta)
    y = r * np.sin(p) * np.sin(theta)
    z = r * np.cos(p)

    return x, y, z


def stableUnique(arr: np.ndarray, axis: int):
    u, idx = np.unique(arr, axis=axis, return_index=True)
    return arr[np.sort(idx)]


def interpColormap(colormap: np.ndarray, pointsPerSample: int, isHsv=False):
    if isHsv:
        limits = [180, 256, 256]
    else:
        limits = 256

    N = len(colormap)
    signedCmap = colormap.astype(int)
    newSize = N + (N-1) * pointsPerSample
    interp = np.zeros((newSize, 3))

    interp[np.arange(N)*(pointsPerSample+1)] = signedCmap
    starts, ends = np.arange(N-1), np.arange(1, N)

    for i in range(1, pointsPerSample+1):
        diffs = signedCmap[ends] - signedCmap[starts]

        if isHsv:
            shortcuts = diffs[:, 0][np.abs(diffs[:, 0]) > 90]
            if shortcuts.size > 0:
                shortcuts = (-np.abs(shortcuts)) % 180
                diffs[:, 0][np.abs(diffs[:, 0]) > 90] = shortcuts

        idx = starts * (pointsPerSample+1) + i
        interp[idx] = (signedCmap[starts] +
                       i * (diffs/(pointsPerSample+1))) % limits

    interp = np.around(interp).astype(colormap.dtype)
    interp = stableUnique(interp, axis=0)

    return interp


def getBoxRegion(img: np.ndarray, topleft: np.ndarray, dims: np.ndarray):
    return img[
        topleft[1]:(topleft+dims)[1],
        topleft[0]:(topleft+dims)[0]
    ]


def getOrthHemisphereXYCoords(hemisphere: np.ndarray):
    indices = np.where(np.all(np.greater(hemisphere, np.zeros(3)), axis=-1))
    radius = np.ceil(max(hemisphere.shape) / 2) * 0.95
    xs = indices[1] - radius
    ys = radius - indices[0]
    xsNormalised = 2*radius * (xs - np.min(xs)) / np.ptp(xs) - radius
    ysNormalised = 2*radius * (ys - np.min(ys)) / np.ptp(ys) - radius
    return xsNormalised, ysNormalised


def getHemispherePixels(hemisphere: np.ndarray):
    return hemisphere[
        np.where(np.all(np.greater(hemisphere, np.zeros(3)), axis=-1))
    ]


def findNearestColorIdx(colors: np.ndarray, colormap: np.ndarray,
                        metric=ColorMetric.L1NORM, weights=[1, 1, 1]):
    if metric == ColorMetric.L2NORM:
        idx = np.linalg.norm(
            (colormap[np.newaxis, :, :] - colors[:, np.newaxis, :]) * weights,
            2,
            axis=-1
        ).argmin(axis=-1)

    elif metric == ColorMetric.L1NORM:
        idx = np.linalg.norm(
            (colormap[np.newaxis, :, :] - colors[:, np.newaxis, :]) * weights,
            1,
            axis=-1
        ).argmin(axis=-1)

    elif metric == ColorMetric.MSE:
        idx = np.mean(
            ((colormap[np.newaxis, :, :] -
              colors[:, np.newaxis, :]) * weights)**2,
            axis=-1
        ).argmin(axis=-1)

    elif metric == ColorMetric.MAE:
        idx = np.mean(
            np.abs((colormap[np.newaxis, :, :] -
                    colors[:, np.newaxis, :]) * weights),
            axis=-1
        ).argmin(axis=-1)

    else:
        raise LookupError('Invalid metric given')

    return idx


def getHeightFromCmapIdx(idx, colormap, heightRange):
    start, stop = heightRange
    return np.linspace(start, stop, len(colormap))[idx]


def makeVtkSliderRep(title, minValue, maxValue, startValue, x, y):
    import vtk
    slider = vtk.vtkSliderRepresentation2D()
    slider.SetTitleText(title)

    slider.SetMinimumValue(minValue)
    slider.SetMaximumValue(maxValue)
    slider.SetValue(startValue)

    slider.GetPoint1Coordinate().SetCoordinateSystemToNormalizedDisplay()
    slider.GetPoint1Coordinate().SetValue(x, y)
    slider.GetPoint2Coordinate().SetCoordinateSystemToNormalizedDisplay()
    slider.GetPoint2Coordinate().SetValue(x + 0.2, y)

    return slider


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import matplotlib.gridspec as gridspec

    r = 90
    lmbdas = phis = np.arange(-90, 100, 10)

    lv, pv = np.meshgrid(lmbdas, phis)
    xs, ys = orthographic(r, lv, pv)

    fig = plt.figure(figsize=[8, 12])
    gs = gridspec.GridSpec(nrows=2, ncols=2,
                           width_ratios=[1, 1], height_ratios=[1, 2])

    ax1 = fig.add_subplot(gs[0, 0])
    ax1.scatter(lv, pv, c=np.arange(len(lmbdas)**2), cmap='plasma')
    ax1.set_title('(longitude, latitude) values')
    ax1.set(xlabel='longitude (degrees)', ylabel='latitude (degrees)')

    ax2 = fig.add_subplot(gs[0, 1])
    ax2.scatter(xs, ys, c=np.arange(len(lmbdas)**2), cmap='plasma')
    ax2.set_title('projected (x, y) values')
    ax2.set(xlabel='x', ylabel='y')

    rs, lmbdas, phis = inverseOrthographic(xs, ys, r)
    xs, ys, zs = geoToCartesian(rs, lmbdas, phis)
    # xs, ys, zs = geoToCartesian(rs, lv, pv)

    ax3 = fig.add_subplot(gs[1, :], projection='3d')
    ax3.scatter(xs, ys, zs, c=np.arange(len(lmbdas)**2), cmap='plasma')
    ax3.set_box_aspect((1, 2, 2))
    ax3.set_title(
        'projected (x, y) -> inverse projected (r, long., lat.) \
         -> converted (x, y, z)',
        y=-0.2
    )
    ax3.set(xlabel='x', ylabel='y', zlabel='z')
    plt.show()
