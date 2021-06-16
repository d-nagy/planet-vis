import sys
import vtk
import utils


dataFile = sys.argv[1]
data = utils.readDataFile(dataFile)

# Read the polydata from a file
polyReader = vtk.vtkXMLPolyDataReader()
polyReader.SetFileName(f'sources/{data.vtksource}')

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

# Create a renderer
renderer = vtk.vtkRenderer()
renderer.AddActor(planetActor)

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
