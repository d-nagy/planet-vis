import sys
import vtk
import utils
import numpy as np


class SliderCBSeaLevel:
    def __init__(self, clipper):
        self.clipper = clipper

    def __call__(self, caller, ev):
        slider = caller
        value = slider.GetRepresentation().GetValue()
        self.clipper.SetValue(value)


warpScale = 1

dataFile = sys.argv[1]
data = utils.readDataFile(dataFile)
hMin = int(np.ceil(data.hMin / 1000)) * 1000
hMax = int(np.floor(data.hMax / 1000)) * 1000

# Read the polydata from a file
polyReader = vtk.vtkXMLPolyDataReader()
polyReader.SetFileName(f'sources/{data.vtksource}')
polyReader.Update()

normalVectors = vtk.vtkFloatArray()
normalVectors.DeepCopy(polyReader.GetOutput().GetPointData().GetNormals())
normalVectors.SetName('NormalVectors')
polyReader.GetOutput().GetPointData().SetVectors(normalVectors)
polyReader.Update()

# Read the image data from a file
textureReader = vtk.vtkJPEGReader()
textureReader.SetFileName(f'images/{data.texture}')

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

sinkSea = vtk.vtkWarpVector()
sinkSea.SetInputConnection(clip.GetOutputPort(1))
sinkSea.SetScaleFactor(5)

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
seaMapper.SetInputConnection(sinkSea.GetOutputPort())
seaMapper.ScalarVisibilityOff()

# Create actor and set the mapper and the texture
landActor = vtk.vtkActor()
landActor.SetMapper(landMapper)
landActor.SetTexture(texture)
landActor.RotateX(90)
landActor.RotateZ(data.rot)
landActor.RotateY(data.tilt)

underseaActor = vtk.vtkActor()
underseaActor.SetMapper(underseaMapper)
underseaActor.SetTexture(texture)
underseaActor.RotateX(90)
underseaActor.RotateZ(data.rot)
underseaActor.RotateY(data.tilt)

# Create actor for the sea
seaActor = vtk.vtkActor()
seaActor.SetMapper(seaMapper)
seaActor.RotateX(90)
seaActor.RotateZ(data.rot)
seaActor.RotateY(data.tilt)
seaActor.GetProperty().SetColor(0, 0, 0.5)
seaActor.GetProperty().SetOpacity(0.7)

# -- Text --
titleActor = vtk.vtkTextActor()
titleActor.SetInput(data.name)
titleActor.GetTextProperty().SetVerticalJustificationToTop()
titleActor.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
titleActor.GetPositionCoordinate().SetValue(0.05, 0.95)
titleActor.GetTextProperty().SetFontSize(40)

# Create a renderer
renderer = vtk.vtkRenderer()
renderer.AddActor(landActor)
renderer.AddActor(underseaActor)
renderer.AddActor(seaActor)
renderer.AddActor(titleActor)

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

# -- GUI slider --
# Make rep
sfSliderRep = utils.makeVtkSliderRep(
    'Relief scale factor', 1, 20, warpScale, 0.05, 0.1
)

# Make widget
sfSlider = vtk.vtkSliderWidget()
sfSlider.SetInteractor(interactor)
sfSlider.SetRepresentation(sfSliderRep)
sfSlider.SetAnimationModeToJump()
sfSlider.EnabledOn()
cb = utils.SliderCBScaleFactor(warpAboveSea, warpBelowSea)
sfSlider.AddObserver(vtk.vtkCommand.InteractionEvent, cb)

seaLevelSliderRep = utils.makeVtkSliderRep(
    'Sea Level (km)', hMin / 1000, hMax / 1000, 0, 0.05, 0.3
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
