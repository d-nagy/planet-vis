import sys
import vtk
import utils
import numpy as np


R = 3389500
sfR = 0.001
warpScale = 10
tilt = -25


class SliderCBScaleFactor:
    def __init__(self, *warps):
        self.warps = warps

    def __call__(self, caller, ev):
        slider = caller
        value = slider.GetRepresentation().GetValue()
        for warp in self.warps:
            warp.SetScaleFactor(value)


class SliderCBSeaLevel:
    def __init__(self, clipper):
        self.clipper = clipper

    def __call__(self, caller, ev):
        slider = caller
        value = slider.GetRepresentation().GetValue()
        self.clipper.SetValue(value)


topoFile = sys.argv[1]
textureFile = sys.argv[2]

# Read the polydata from a file
polyReader = vtk.vtkXMLPolyDataReader()
polyReader.SetFileName(topoFile)
polyReader.Update()
hMin, hMax = polyReader.GetOutput().GetPointData().GetScalars().GetRange()
hMin, hMax = int(np.ceil(hMin) / sfR), int(np.floor(hMax) / sfR)

normalVectors = vtk.vtkFloatArray()
normalVectors.DeepCopy(polyReader.GetOutput().GetPointData().GetNormals())
normalVectors.SetName('NormalVectors')
polyReader.GetOutput().GetPointData().SetVectors(normalVectors)

# Read the image data from a file
textureReader = vtk.vtkJPEGReader()
textureReader.SetFileName(textureFile)

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
sinkUndersea = vtk.vtkWarpVector()
sinkUndersea.SetInputConnection(clip.GetOutputPort(1))
sinkUndersea.SetScaleFactor(-10)

warpBelowSea = vtk.vtkWarpScalar()
warpBelowSea.SetInputConnection(sinkUndersea.GetOutputPort())  # Below the sea
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
landActor.RotateX(90 + tilt)

underseaActor = vtk.vtkActor()
underseaActor.SetMapper(underseaMapper)
underseaActor.SetTexture(texture)
underseaActor.RotateX(90 + tilt)

# Create actor for the sea
seaActor = vtk.vtkActor()
seaActor.SetMapper(seaMapper)
seaActor.RotateX(90 + tilt)
seaActor.GetProperty().SetColor(0, 0, 0.5)
seaActor.GetProperty().SetOpacity(0.7)

# Create a renderer
renderer = vtk.vtkRenderer()
renderer.AddActor(landActor)
renderer.AddActor(underseaActor)
renderer.AddActor(seaActor)

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
    'Relief scale factor', 1, 30, warpScale, 0.05, 0.1
)

# Make widget
sfSlider = vtk.vtkSliderWidget()
sfSlider.SetInteractor(interactor)
sfSlider.SetRepresentation(sfSliderRep)
sfSlider.SetAnimationModeToJump()
sfSlider.EnabledOn()
cb = SliderCBScaleFactor(warpAboveSea, warpBelowSea)
sfSlider.AddObserver(vtk.vtkCommand.InteractionEvent, cb)

seaLevelSliderRep = utils.makeVtkSliderRep(
    'Sea Level (km)', hMin * sfR, hMax * sfR, 0, 0.05, 0.3
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
