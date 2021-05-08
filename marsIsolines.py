import sys
import vtk
import utils

HEIGHT_RANGE = [-8000, 14000]
R = 3389500
sfR = 0.001
tilt = -25
tubeRadius = 5


class SliderCBTubeRadius:
    def __init__(self, *tubeFilters):
        self.tubeFilters = tubeFilters

    def __call__(self, caller, ev):
        slider = caller
        value = slider.GetRepresentation().GetValue()
        for tf in self.tubeFilters:
            tf.SetRadius(value)


ctf = vtk.vtkColorTransferFunction()
ctf.SetColorSpaceToDiverging()
ctf.AddRGBPoint(-8, 0, 0.1, 0.85)  # Blue
ctf.AddRGBPoint(-5, 0.34, 0.55, 1)  # Lighter blue
ctf.AddRGBPoint(0, 1, 1, 1)  # white
ctf.AddRGBPoint(14, 0.99, 0.85, 0)  # Yellow


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

# Create isolines (contours)
contour = vtk.vtkContourFilter()
contour.SetInputConnection(mapToSphere.GetOutputPort())
contourValues = [
    i // 1000 for i in range(HEIGHT_RANGE[0], HEIGHT_RANGE[1] + 1000, 1000)
    if i != 0
]
for i, v in enumerate(contourValues):
    contour.SetValue(i, v)

# Get sea level contour
seaLevel = vtk.vtkContourFilter()
seaLevel.SetInputConnection(mapToSphere.GetOutputPort())
seaLevel.SetValue(0, 0)

# Turn contour lines into tubes
tubeContours = vtk.vtkTubeFilter()
tubeContours.SetInputConnection(contour.GetOutputPort())
tubeContours.SetNumberOfSides(6)
tubeContours.SetRadius(tubeRadius)

tubeSea = vtk.vtkTubeFilter()
tubeSea.SetInputConnection(seaLevel.GetOutputPort())
tubeSea.SetNumberOfSides(6)
tubeSea.SetRadius(tubeRadius)

# Create mapper and set the mapped texture as input
marsMapper = vtk.vtkPolyDataMapper()
marsMapper.SetInputConnection(mapToSphere.GetOutputPort())
marsMapper.ScalarVisibilityOff()  # Important for rendering texture properly

# Create mapper for contours
contourMapper = vtk.vtkPolyDataMapper()
contourMapper.SetInputConnection(tubeContours.GetOutputPort())
contourMapper.SetLookupTable(ctf)

# Create mapper for contours
seaMapper = vtk.vtkPolyDataMapper()
seaMapper.SetInputConnection(tubeSea.GetOutputPort())

# Create actor and set the mapper and the texture
marsActor = vtk.vtkActor()
marsActor.SetMapper(marsMapper)
marsActor.SetTexture(texture)
marsActor.RotateX(90 + tilt)

contourActor = vtk.vtkActor()
contourActor.SetMapper(contourMapper)
contourActor.RotateX(90 + tilt)

seaActor = vtk.vtkActor()
seaActor.SetMapper(seaMapper)
seaActor.RotateX(90 + tilt)
seaActor.GetProperty().SetColor(1, 0, 0)

# Create a renderer
renderer = vtk.vtkRenderer()
renderer.AddActor(marsActor)
renderer.AddActor(contourActor)
renderer.AddActor(seaActor)

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
tubeRadiusSliderRep = utils.makeVtkSliderRep(
    'Contour tube radius', 1, 10, tubeRadius, 0.05, 0.1
)

# Make widget
tubeRadiusSlider = vtk.vtkSliderWidget()
tubeRadiusSlider.SetInteractor(interactor)
tubeRadiusSlider.SetRepresentation(tubeRadiusSliderRep)
tubeRadiusSlider.SetAnimationModeToJump()
tubeRadiusSlider.EnabledOn()
cb = SliderCBTubeRadius(tubeContours, tubeSea)
tubeRadiusSlider.AddObserver(vtk.vtkCommand.EndInteractionEvent, cb)

interactor.Initialize()
renderWindow.Render()
interactor.Start()
