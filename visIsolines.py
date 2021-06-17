import sys
import vtk
import utils
import numpy as np


class SliderCBTubeRadius:
    '''
    Callback for VTK slider that controls the contour tube radii.
    '''
    def __init__(self, *tubeFilters):
        self.tubeFilters = tubeFilters

    def __call__(self, caller, ev):
        slider = caller
        value = slider.GetRepresentation().GetValue()
        for tf in self.tubeFilters:
            tf.SetRadius(value)


tubeRadius = 3

# Open and load planet config from file
dataFile = sys.argv[1]
data = utils.readDataFile(dataFile)
hMin = int(np.ceil(data.hMin / 1000)) * 1000
hMax = int(np.floor(data.hMax / 1000)) * 1000

# Read the polydata from a file
polyReader = vtk.vtkXMLPolyDataReader()
polyReader.SetFileName(f'sources/{data.vtksource}')
polyReader.Update()

ctf = vtk.vtkColorTransferFunction()
ctf.SetColorSpaceToDiverging()
ctf.AddRGBPoint(hMin / 1000, 0, 0.1, 0.85)  # Blue
ctf.AddRGBPoint(hMin * (2 / 3) / 1000, 0.34, 0.55, 1)  # Lighter blue
ctf.AddRGBPoint(0, 1, 1, 1)  # white
ctf.AddRGBPoint(hMax / 1000, 0.99, 0.85, 0)  # Yellow

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

# Create isolines (contours)
contour = vtk.vtkContourFilter()
contour.SetInputConnection(mapToSphere.GetOutputPort())
contourValues = [
    i // 1000 for i in range(hMin, hMax + 1000, 1000)
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
planetMapper = vtk.vtkPolyDataMapper()
planetMapper.SetInputConnection(mapToSphere.GetOutputPort())
planetMapper.ScalarVisibilityOff()  # Important for rendering texture properly

# Create mapper for contours
contourMapper = vtk.vtkPolyDataMapper()
contourMapper.SetInputConnection(tubeContours.GetOutputPort())
contourMapper.SetLookupTable(ctf)

# Create mapper for contours
seaMapper = vtk.vtkPolyDataMapper()
seaMapper.SetInputConnection(tubeSea.GetOutputPort())

# Create actors, set mappers and textures
planetActor = vtk.vtkActor()
planetActor.SetMapper(planetMapper)
planetActor.SetTexture(texture)
planetActor.RotateX(90)
planetActor.RotateZ(data.rot)
planetActor.RotateY(data.tilt)

contourActor = vtk.vtkActor()
contourActor.SetMapper(contourMapper)
contourActor.SetUserMatrix(planetActor.GetMatrix())

seaActor = vtk.vtkActor()
seaActor.SetMapper(seaMapper)
seaActor.SetUserMatrix(planetActor.GetMatrix())
seaActor.GetProperty().SetColor(1, 0, 0)

# Create legend for contour line colors.
scalarBar = vtk.vtkScalarBarActor()
scalarBar.SetLookupTable(contourMapper.GetLookupTable())
scalarBar.SetTitle('Elevation (km)')
scalarBar.UnconstrainedFontSizeOn()
scalarBar.GetTitleTextProperty().SetLineOffset(-20)
scalarBar.GetTitleTextProperty().SetFontSize(20)
scalarBar.GetLabelTextProperty().SetFontSize(16)
scalarBar.SetMaximumWidthInPixels(100)
scalarBar.SetMaximumHeightInPixels(500)
scalarBar.SetNumberOfLabels(len(contourValues) + 1)
scalarBar.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
scalarBar.GetPositionCoordinate().SetValue(0.85, 0.05)

# Create a title that displays the planet name
titleActor = vtk.vtkTextActor()
titleActor.SetInput(data.name)
titleActor.GetTextProperty().SetVerticalJustificationToTop()
titleActor.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
titleActor.GetPositionCoordinate().SetValue(0.05, 0.95)
titleActor.GetTextProperty().SetFontSize(40)

# Add caption to inform user of the red 0km elevation contour
subtitleActor = vtk.vtkTextActor()
subtitleActor.SetInput('0km elevation shown in red.')
subtitleActor.GetTextProperty().SetJustificationToRight()
subtitleActor.GetTextProperty().SetVerticalJustificationToTop()
subtitleActor.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
subtitleActor.GetPositionCoordinate().SetValue(0.95, 0.95)
subtitleActor.GetTextProperty().SetFontSize(20)

# Create a line that goes through the poles of the planet
line = vtk.vtkLineSource()
line.SetPoint1(0, 0, data.R * data.sfR * 1.1)
line.SetPoint2(0, 0, data.R * data.sfR * -1.1)

lineMapper = vtk.vtkPolyDataMapper()
lineMapper.SetInputConnection(line.GetOutputPort())

lineActor = vtk.vtkActor()
lineActor.SetMapper(lineMapper)
lineActor.GetProperty().SetLineWidth(2)
lineActor.SetUserMatrix(planetActor.GetMatrix())

# Create a renderer
renderer = vtk.vtkRenderer()
renderer.AddActor(planetActor)
renderer.AddActor(contourActor)
renderer.AddActor(seaActor)
renderer.AddActor2D(scalarBar)
renderer.AddActor2D(titleActor)
renderer.AddActor2D(subtitleActor)
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
activeCam.SetThickness(30000)
activeCam.SetPosition(0, 0, 20000)
activeCam.SetRoll(180)

renderWindow.Render()

# -- GUI slider --
# Make rep
tubeRadiusSliderRep = utils.makeVtkSliderRep(
    'Contour tube radius', 1, 6, tubeRadius, 0.05, 0.1
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
