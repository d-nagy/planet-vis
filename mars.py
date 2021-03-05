import sys
import vtk

textureFile = sys.argv[1]

# Create a render window
renderer = vtk.vtkRenderer()
renderWindow = vtk.vtkRenderWindow()
renderWindow.AddRenderer(renderer)
renderWindow.SetSize(1280,720)
interactor = vtk.vtkRenderWindowInteractor()
interactor.SetRenderWindow(renderWindow)

# Create sphere source
sphere = vtk.vtkSphereSource()
sphere.SetRadius(1)
sphere.SetStartTheta(1e-5)
sphere.SetThetaResolution(100)
sphere.SetPhiResolution(100)

# Read the image data from a file
reader = vtk.vtkJPEGReader()
reader.SetFileName(textureFile)

# Create texture object
texture = vtk.vtkTexture()
texture.SetInputConnection(reader.GetOutputPort())

# Map texture to sphere
mapToSphere = vtk.vtkTextureMapToSphere()
mapToSphere.SetInputConnection(sphere.GetOutputPort())
mapToSphere.PreventSeamOff()

# Create mapper and set the mapped texture as input
mapper = vtk.vtkPolyDataMapper()
mapper.SetInputConnection(mapToSphere.GetOutputPort())

# Create actor and set the mapper and the texture
actor = vtk.vtkActor()
actor.SetMapper(mapper)
actor.SetTexture(texture)
actor.RotateX(90+25)

renderer.AddActor(actor)
renderer.GetActiveCamera().Dolly(0.2)

interactor.Initialize()
renderWindow.Render()
interactor.Start()
