import sys
import vtk
import utils
import numpy as np


class SliderCBSeaLevel:
    '''
    Callback for VTK slider that controls the visualised sea level.
    '''
    def __init__(self, clipper):
        self.clipper = clipper

    def __call__(self, caller, ev):
        slider = caller
        value = slider.GetRepresentation().GetValue()
        self.clipper.SetValue(value)


warpScale = 1

# Open and load planet config from file
dataFile = sys.argv[1]
data = utils.readDataFile(dataFile)

# Calculate min and max elevations rounded to nearest km for making the
# isolines
hMin = int(np.ceil(data.hMin / 1000)) * 1000
hMax = int(np.floor(data.hMax / 1000)) * 1000

# Read the polydata from a file
polyReader = vtk.vtkXMLPolyDataReader()
polyReader.SetFileName(f'sources/{data.vtksource}')
polyReader.Update()

# Set polydata vectors to be sphere normals. These will be used in the
# WarpVector filters.
normalVectors = vtk.vtkFloatArray()
normalVectors.DeepCopy(polyReader.GetOutput().GetPointData().GetNormals())
normalVectors.SetName('NormalVectors')
polyReader.GetOutput().GetPointData().SetVectors(normalVectors)
polyReader.Update()

# Read the image data from a file
textureFilename = f'images/{data.texture}'
readerFactory = vtk.vtkImageReader2Factory()
textureReader = readerFactory.CreateImageReader2(textureFilename)
textureReader.SetFileName(textureFilename)
textureReader.Update()

# Flip the image for texture mapping
flip = vtk.vtkImageFlip()
flip.SetInputConnection(textureReader.GetOutputPort())
flip.SetFilteredAxis(1)

# Create texture object
texture = vtk.vtkTexture()
texture.SetInputConnection(flip.GetOutputPort())

# Map texture to sphere
mapToSphere = vtk.vtkTextureMapToSphere()
mapToSphere.SetInputConnection(polyReader.GetOutputPort())
mapToSphere.PreventSeamOff()

# Clip based on sea level
clip = vtk.vtkClipPolyData()
clip.SetInputConnection(mapToSphere.GetOutputPort())
clip.GenerateClippedOutputOn()
clip.SetValue(0)
clip.Update()

# Warp the sphere surface based on the scalar height data
warpAboveSea = vtk.vtkWarpScalar()
warpAboveSea.SetInputConnection(clip.GetOutputPort(0))  # Above the sea
warpAboveSea.SetScaleFactor(warpScale)

# Separate above and below sea ever so slightly
# sinkUndersea = vtk.vtkWarpVector()
# sinkUndersea.SetInputConnection(clip.GetOutputPort(1))
# sinkUndersea.SetScaleFactor(-10)
# sinkUndersea.Update()

warpBelowSea = vtk.vtkWarpScalar()
warpBelowSea.SetInputConnection(clip.GetOutputPort(1))  # Below the sea
warpBelowSea.SetScaleFactor(warpScale)

# Raise sea slightly above the terrain to avoid nasty clipping
sea = vtk.vtkWarpVector()
sea.SetInputConnection(clip.GetOutputPort(1))
sea.SetScaleFactor(5)

# Create mapper and set the mapped texture as input
landMapper = vtk.vtkPolyDataMapper()
landMapper.SetInputConnection(warpAboveSea.GetOutputPort())
landMapper.ScalarVisibilityOff()  # Important for rendering texture properly

# Create mapper and set the mapped texture as input
underseaMapper = vtk.vtkPolyDataMapper()
underseaMapper.SetInputConnection(warpBelowSea.GetOutputPort())
underseaMapper.ScalarVisibilityOff()

# Create mapper for sea
seaMapper = vtk.vtkPolyDataMapper()
seaMapper.SetInputConnection(sea.GetOutputPort())
seaMapper.ScalarVisibilityOff()

# Create actors and set mappers and textures for terrain
landActor = vtk.vtkActor()
landActor.SetMapper(landMapper)
landActor.SetTexture(texture)
landActor.RotateX(90)
landActor.RotateZ(data.rot)
landActor.RotateY(data.tilt)

underseaActor = vtk.vtkActor()
underseaActor.SetMapper(underseaMapper)
underseaActor.SetTexture(texture)
underseaActor.SetUserMatrix(landActor.GetMatrix())

# Create actor for the sea
seaActor = vtk.vtkActor()
seaActor.SetMapper(seaMapper)
seaActor.SetUserMatrix(landActor.GetMatrix())
seaActor.GetProperty().SetColor(0, 0, 0.5)
seaActor.GetProperty().SetOpacity(0.7)

# Create a title that displays the planet name
titleActor = vtk.vtkTextActor()
titleActor.SetInput(data.name)
titleActor.GetTextProperty().SetVerticalJustificationToTop()
titleActor.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
titleActor.GetPositionCoordinate().SetValue(0.05, 0.95)
titleActor.GetTextProperty().SetFontSize(40)

# Create a line that goes through the poles of the planet
line = vtk.vtkLineSource()
line.SetPoint1(0, 0, data.R * data.sfR * 1.1)
line.SetPoint2(0, 0, data.R * data.sfR * -1.1)

lineMapper = vtk.vtkPolyDataMapper()
lineMapper.SetInputConnection(line.GetOutputPort())

lineActor = vtk.vtkActor()
lineActor.SetMapper(lineMapper)
lineActor.GetProperty().SetLineWidth(2)
lineActor.SetUserMatrix(landActor.GetMatrix())

# Create a renderer
renderer = vtk.vtkRenderer()
renderer.AddActor(landActor)
renderer.AddActor(underseaActor)
renderer.AddActor(seaActor)
renderer.AddActor(titleActor)
renderer.AddActor(lineActor)

# Setup render window
renderWindow = vtk.vtkRenderWindow()
renderWindow.AddRenderer(renderer)
renderWindow.SetSize(1280, 720)

# Setup interactor
interactor = vtk.vtkRenderWindowInteractor()
interactor.SetRenderWindow(renderWindow)
interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())

# Setup camera
activeCam = renderer.GetActiveCamera()
activeCam.SetThickness(40000)
activeCam.SetPosition(0, 0, 20000)
activeCam.SetRoll(180)

renderWindow.Render()

# -- GUI sliders --
# Slider for topography scaling
sfSliderRep = utils.makeVtkSliderRep(
    'Relief scale factor', 1, 20, warpScale, 0.05, 0.1
)

sfSlider = vtk.vtkSliderWidget()
sfSlider.SetInteractor(interactor)
sfSlider.SetRepresentation(sfSliderRep)
sfSlider.SetAnimationModeToJump()
sfSlider.EnabledOn()
cb = utils.SliderCBScaleFactor(warpAboveSea, warpBelowSea)
sfSlider.AddObserver(vtk.vtkCommand.InteractionEvent, cb)

# Slider for sea level
seaLevelSliderRep = utils.makeVtkSliderRep(
    'Sea Level (km)', hMin / 1000, hMax / 1000, 0, 0.05, 0.25
)

seaLevelSlider = vtk.vtkSliderWidget()
seaLevelSlider.SetInteractor(interactor)
seaLevelSlider.SetRepresentation(seaLevelSliderRep)
seaLevelSlider.SetAnimationModeToJump()
seaLevelSlider.EnabledOn()
cb = SliderCBSeaLevel(clip)
seaLevelSlider.AddObserver(vtk.vtkCommand.InteractionEvent, cb)

interactor.Initialize()
renderWindow.Render()
interactor.Start()
