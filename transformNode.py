# CISC472
# 2017-24-01 Homework


createModelsLogic = slicer.modules.createmodels.logic()

preModelNode = createModelsLogic.CreateCoordinate(100,100)
preModelNode.SetName('PreModel')



# Create Transform Node

preModelToRas = slicer.vtkMRMLLinearTransformNode()
preModelToRas.SetName('PreModelToRas')
slicer.mrmlScene.AddNode(preModelToRas)

#Set Transform of the transform node

preModelToRasTransform = vtk.vtkTransform()




preModelToRasTransform.PreMultiply()

preModelToRasTransform.Translate(10, 10, 10)
preModelToRasTransform.Update()
preModelToRas.SetAndObserveTransformToParent(preModelToRasTransform)


preModelNode.SetAndObserveTransformNodeID(preModelToRas.GetID())

