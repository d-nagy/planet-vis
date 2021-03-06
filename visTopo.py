import sys
import vtk
import utils

# Open and load planet config from file
dataFile = sys.argv[1]
data = utils.readDataFile(dataFile)

# Read the polydata from a file
polyReader = vtk.vtkXMLPolyDataReader()
polyReader.SetFileName(f'sources/{data.vtksource}')

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

# Warp the sphere surface based on the scalar height data
warp = vtk.vtkWarpScalar()
warp.SetInputConnection(mapToSphere.GetOutputPort())
warp.SetScaleFactor(10)
warp.Update()

# Create mapper and set the mapped texture as input
planetMapper = vtk.vtkPolyDataMapper()
planetMapper.SetInputConnection(warp.GetOutputPort())
planetMapper.ScalarVisibilityOff()  # Important for rendering texture properly

# Create actor and set the mapper and the texture
planetActor = vtk.vtkActor()
planetActor.SetMapper(planetMapper)
planetActor.SetTexture(texture)
planetActor.RotateX(90)
planetActor.RotateZ(data.rot)
planetActor.RotateY(data.tilt)

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
lineActor.SetUserMatrix(planetActor.GetMatrix())

# Create a renderer
renderer = vtk.vtkRenderer()
renderer.AddActor(planetActor)
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
activeCam.SetThickness(30000)
activeCam.SetPosition(0, 0, 20000)
activeCam.SetRoll(180)

renderWindow.Render()

# -- GUI slider --
# Make rep
slider = vtk.vtkSliderRepresentation2D()
slider.SetTitleText('Relief scale factor')

slider.SetMinimumValue(1)
slider.SetMaximumValue(20)
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
cb = utils.SliderCBScaleFactor(warp)
sfSlider.AddObserver(vtk.vtkCommand.InteractionEvent, cb)

interactor.Initialize()
renderWindow.Render()
interactor.Start()
