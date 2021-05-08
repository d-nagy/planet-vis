import sys
import vtk


class SliderCBScaleFactor:
    def __init__(self, warpFilter):
        self.warpFilter = warpFilter

    def __call__(self, caller, ev):
        slider = caller
        value = slider.GetRepresentation().GetValue()
        self.warpFilter.SetScaleFactor(value)


topoFile = sys.argv[1]
textureFile = sys.argv[2]

# Read the polydata from a file
polyReader = vtk.vtkXMLPolyDataReader()
polyReader.SetFileName(topoFile)

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

warp = vtk.vtkWarpScalar()
warp.SetInputConnection(mapToSphere.GetOutputPort())
warp.SetScaleFactor(1)
warp.Update()

# Create mapper and set the mapped texture as input
mapper = vtk.vtkPolyDataMapper()
mapper.SetInputConnection(warp.GetOutputPort())
mapper.ScalarVisibilityOff()

# Create actor and set the mapper and the texture
actor = vtk.vtkActor()
actor.SetMapper(mapper)
actor.SetTexture(texture)
actor.RotateX(90-25)

# Create a renderer
renderer = vtk.vtkRenderer()
renderer.AddActor(actor)

# Setup render window
renderWindow = vtk.vtkRenderWindow()
renderWindow.AddRenderer(renderer)
renderWindow.SetSize(1280, 720)

# Setup interactor
interactor = vtk.vtkRenderWindowInteractor()
interactor.SetRenderWindow(renderWindow)

# Setup camera
activeCam = renderer.GetActiveCamera()
activeCam.SetThickness(30000)
activeCam.SetPosition(0, 0, 20000)
activeCam.SetRoll(180)

renderWindow.Render()

# -- GUI slider --
# Make rep
slider = vtk.vtkSliderRepresentation2D()
slider.SetTitleText('Height map scale factor')

slider.SetMinimumValue(1)
slider.SetMaximumValue(30)
slider.SetValue(10)

slider.GetPoint1Coordinate().SetCoordinateSystemToNormalizedDisplay()
slider.GetPoint1Coordinate().SetValue(0.05, 0.1)
slider.GetPoint2Coordinate().SetCoordinateSystemToNormalizedDisplay()
slider.GetPoint2Coordinate().SetValue(0.25, 0.1)

# Make widget
sfSlider = vtk.vtkSliderWidget()
sfSlider.SetInteractor(interactor)
sfSlider.SetRepresentation(slider)
sfSlider.SetAnimationModeToJump()
sfSlider.EnabledOn()
cb = SliderCBScaleFactor(warp)
sfSlider.AddObserver(vtk.vtkCommand.InteractionEvent, cb)

interactor.Initialize()
renderWindow.Render()
interactor.Start()
