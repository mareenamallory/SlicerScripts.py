import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import numpy
import math


#
# mareenaModule
#

class mareenaModule(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "mareenaModule"  # TODO make this more human readable by adding spaces
        self.parent.categories = ["Examples"]
        self.parent.dependencies = []
        self.parent.contributors = ["John Doe (AnyWare Corp.)"]  # replace with "Firstname Lastname (Organization)"
        self.parent.helpText = """
    This is an example of scripted loadable module bundled in an extension.
    It performs a simple thresholding on the input volume and optionally captures a screenshot.
    """
        self.parent.acknowledgementText = """
    This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc.
    and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
"""  # replace with organization, grant and thanks.


#
# mareenaModuleWidget
#

class mareenaModuleWidget(ScriptedLoadableModuleWidget):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)

        # Instantiate and connect widgets ...

        #
        # Parameters Area
        #
        parametersCollapsibleButton = ctk.ctkCollapsibleButton()
        parametersCollapsibleButton.text = "Parameters"
        self.layout.addWidget(parametersCollapsibleButton)

        # Layout within the dummy collapsible button
        parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

        self.emSelector = slicer.qMRMLNodeComboBox()
        self.emSelector.nodeTypes = ['vtkMRMLLinearTransformNode']
        self.emSelector.setMRMLScene(slicer.mrmlScene)
        parametersFormLayout.addRow("EM tool tip transform: ",self.emSelector)

        self.opticalSelector = slicer.qMRMLNodeComboBox()
        self.opticalSelector.nodeTypes = ['vtkMRMLLinearTransformNode']
        self.opticalSelector.setMRMLScene(slicer.mrmlScene)
        parametersFormLayout.addRow("Optical tool tip transform: ",self.opticalSelector)


        #
        # Apply Button
        #
        self.applyButton = qt.QPushButton("Apply")
        self.applyButton.toolTip = "Run the algorithm."
        self.applyButton.enabled = False
        parametersFormLayout.addRow(self.applyButton)

        # connections
        self.applyButton.connect('clicked(bool)', self.onApplyButton)

        self.emSelector.connect("currentNodeCHanged(vtkMRMLNode*)", self.onSelect)
        self.opticalSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)


        # Add vertical spacer
        self.layout.addStretch(1)

        # Refresh Apply button state
        self.onSelect()

    def cleanup(self):
        pass

    def onSelect(self):
        self.applyButton.enabled = self.emSelector.currentNode() and self.opticalSelector.currentNode()

    def onApplyButton(self):
        emTipTransform = self.emSelector.currentNode()
        if emTipTransform == None:
            return
        opTipTransform = self.opticalSelector.currentNode()
        if opTipTransform == None:
            return

        emTipTransform.AddObserver(slicer.vtkMRMLTransformNode.TransformModifiedEvent, self.onTransformedModified)

        opTipTransform.AddObserver(slicer.vtkMRMLTransformNode.TransformModifiedEvent, self.onTransformedModified)

    def onTransformedModified(self, caller, event):
        print 'transforms modified'
        emTipTransform = self.emSelector.currentNode()
        if emTipTransform == None:
            return
        opTipTransform = self.opticalSelector.currentNode()
        if opTipTransform == None:
            return

        emTip_EmTip = [0,0,0,1]
        opTip_OpTip = [0,0,0,1]

        emTipToRasMatrix = vtk.vtkMatrix4x4()
        emTipTransform.GetMatrixTransformToWorld(emTipToRasMatrix)
        emTip_Ras = numpy.array(emTipToRasMatrix.MultiplyFloatPoint(emTip_EmTip))

        opTipTORasMatrix = vtk.vtkMatrix4x4()
        opTipTransform.GetMatrixTransformToWorld(opTipTORasMatrix)
        opTip_Ras = numpy.array(opTipTORasMatrix.MultiplyFloatPoint(opTip_OpTip))

        distance = numpy.linalg.norm(emTip_Ras - opTip_Ras)
        print distance

#
# mareenaModuleLogic
#

class mareenaModuleLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def averageTransformedDistance(self, pointsA, pointsB, aToBMatrix):
        average = 0.0
        numSoFar = 0
        numPts = pointsA.GetNumberOfPoints()

        for i in range(numPts):
            numSoFar = numSoFar + 1

            a = pointsA.GetPoint(i)
            pointA_Ref = numpy.array(a)
            pointA_Ref = numpy.append(pointA_Ref, 1)
            pointA_Ras = aToBMatrix.MultiplyFloatPoint(pointA_Ref)

            b = pointsB.GetPoint(i)
            pointB_Ras = numpy.array(b)
            pointB_Ras = numpy.append(pointB_Ras, 1)

            distance = numpy.linalg.norm(pointA_Ras - pointB_Ras)
            average = average + (distance - average) / numSoFar

        return average

    def rigidRegistration(self, alphaPoints, betaPoints, alphatToBetaMatrix):

        # Create transform node for registration
        landmarkTransform = vtk.vtkLandmarkTransform()
        landmarkTransform.SetSourceLandmarks(alphaPoints)
        landmarkTransform.SetTargetLandmarks(betaPoints)
        landmarkTransform.SetModeToRigidBody()
        landmarkTransform.Update()

        landmarkTransform.GetMatrix(alphatToBetaMatrix)

    def hasImageData(self, volumeNode):
        """This is an example logic method that
        returns true if the passed in volume
        node has valid image data
        """
        if not volumeNode:
            logging.debug('hasImageData failed: no volume node')
            return False
        if volumeNode.GetImageData() is None:
            logging.debug('hasImageData failed: no image data in volume node')
            return False
        return True

    def isValidInputOutputData(self, inputVolumeNode, outputVolumeNode):
        """Validates if the output is not the same as input
        """
        if not inputVolumeNode:
            logging.debug('isValidInputOutputData failed: no input volume node defined')
            return False
        if not outputVolumeNode:
            logging.debug('isValidInputOutputData failed: no output volume node defined')
            return False
        if inputVolumeNode.GetID() == outputVolumeNode.GetID():
            logging.debug(
                'isValidInputOutputData failed: input and output volume is the same. Create a new volume for output to avoid this error.')
            return False
        return True

    def takeScreenshot(self, name, description, type=-1):
        # show the message even if not taking a screen shot
        slicer.util.delayDisplay(
            'Take screenshot: ' + description + '.\nResult is available in the Annotations module.', 3000)

        lm = slicer.app.layoutManager()
        # switch on the type to get the requested window
        widget = 0
        if type == slicer.qMRMLScreenShotDialog.FullLayout:
            # full layout
            widget = lm.viewport()
        elif type == slicer.qMRMLScreenShotDialog.ThreeD:
            # just the 3D window
            widget = lm.threeDWidget(0).threeDView()
        elif type == slicer.qMRMLScreenShotDialog.Red:
            # red slice window
            widget = lm.sliceWidget("Red")
        elif type == slicer.qMRMLScreenShotDialog.Yellow:
            # yellow slice window
            widget = lm.sliceWidget("Yellow")
        elif type == slicer.qMRMLScreenShotDialog.Green:
            # green slice window
            widget = lm.sliceWidget("Green")
        else:
            # default to using the full window
            widget = slicer.util.mainWindow()
            # reset the type so that the node is set correctly
            type = slicer.qMRMLScreenShotDialog.FullLayout

        # grab and convert to vtk image data
        qpixMap = qt.QPixmap().grabWidget(widget)
        qimage = qpixMap.toImage()
        imageData = vtk.vtkImageData()
        slicer.qMRMLUtils().qImageToVtkImageData(qimage, imageData)

        annotationLogic = slicer.modules.annotations.logic()
        annotationLogic.CreateSnapShot(name, description, type, 1, imageData)

    def run(self, inputVolume, outputVolume, imageThreshold, enableScreenshots=0):
        """
        Run the actual algorithm
        """

        if not self.isValidInputOutputData(inputVolume, outputVolume):
            slicer.util.errorDisplay('Input volume is the same as output volume. Choose a different output volume.')
            return False

        logging.info('Processing started')

        # Compute the thresholded output volume using the Threshold Scalar Volume CLI module
        cliParams = {'InputVolume': inputVolume.GetID(), 'OutputVolume': outputVolume.GetID(),
                     'ThresholdValue': imageThreshold, 'ThresholdType': 'Above'}
        cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True)

        # Capture screenshot
        if enableScreenshots:
            self.takeScreenshot('mareenaModuleTest-Start', 'MyScreenshot', -1)

        logging.info('Processing completed')

        return True

    def generatePoints(self, numPoints, Scale, Sigma):

        rasFids = slicer.util.getNode('RasPoints')

        if rasFids == None:
            rasFids = slicer.vtkMRMLMarkupsFiducialNode()
            rasFids.SetName('RasPoints')
            slicer.mrmlScene.AddNode(rasFids)

        rasFids.RemoveAllMarkups()
        refFids = slicer.util.getNode('ReferencePoints')

        if refFids == None:
            refFids = slicer.vtkMRMLMarkupsFiducialNode()
            refFids.SetName('ReferencePoints')
            slicer.mrmlScene.AddNode(refFids)

        refFids.RemoveAllMarkups()
        refFids.GetDisplayNode().SetSelectedColor(1, 1, 0)

        # Creating two fiducial lists
        fromNormCoord = numpy.random.rand(numPoints, 3)
        noise = numpy.random.normal(0.0, Sigma, numPoints * 3)

        for i in range(numPoints):
            x = (fromNormCoord[i, 0] - 0.5) * Scale
            y = (fromNormCoord[i, 1] - 0.5) * Scale
            z = (fromNormCoord[i, 2] - 0.5) * Scale

            rasFids.AddFiducial(x, y, z)
            xx = x + noise[i * 3]
            yy = y + noise[i * 3 + 1]
            zz = z + noise[i * 3 + 2]
            refFids.AddFiducial(xx, yy, zz)

    def fiducialsToPoints(self, fiducials, points):
        n = fiducials.GetNumberOfFiducials()

        for i in range(n):
            p = [0, 0, 0]
            fiducials.GetNthFiducialPosition(i, p)
            points.InsertNextPoint(p[0], p[1], p[2])

class mareenaModuleTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
        """
        slicer.mrmlScene.Clear(0)

    def runTest(self):
        """Run as few or as many tests as needed here.
        """
        self.setUp()
        self.test_mareenaModule1()

    def generatePoints(self, numPoints, Scale, Sigma):

        rasFids = slicer.util.getNode('RasPoints')

        if rasFids == None:
            rasFids = slicer.vtkMRMLMarkupsFiducialNode()
            rasFids.SetName('RasPoints')
            slicer.mrmlScene.AddNode(rasFids)

        rasFids.RemoveAllMarkups()
        refFids = slicer.util.getNode('RefPoints')

        if refFids == None:
            refFids = slicer.vtkMRMLMarkupsFiducialNode()
            refFids.SetName('RefPoints')
            slicer.mrmlScene.AddNode(refFids)

        refFids.RemoveAllMarkups()
        refFids.GetDisplayNode().SetSelectedColor(1, 1, 0)

        fromNormCoord = numpy.random.rand(numPoints, 3)
        noise = numpy.random.normal(0.0, Sigma, numPoints * 3)

        for i in range(numPoints):
            x = (fromNormCoord[i, 0] - 0.5) * Scale
            y = (fromNormCoord[i, 1] - 0.5) * Scale
            z = (fromNormCoord[i, 2] - 0.5) * Scale

            rasFids.AddFiducial(x, y, z)
            xx = x + noise[i * 3]
            yy = y + noise[i * 3 + 1]
            zz = z + noise[i * 3 + 2]
            refFids.AddFiducial(xx, yy, zz)

    def fiducialsToPoints(self, fiducials, points):
        n = fiducials.GetNumberOfFiducials()

        for i in range(n):
            p = [0, 0, 0]
            fiducials.GetNthFiducialPosition(i, p)
            points.InsertNextPoint(p[0], p[1], p[2])


    def createChart(self, nVals, TREVals):

        numSamples = 10

        # Switch to layout 24 that contains a chart view to initiate
        # construction of the widget and chart view node
        lns = slicer.mrmlScene.GetNodesByClass('vtkMRMLLayoutNode')
        lns.InitTraversal()
        ln = lns.GetNextItemAsObject()
        ln.SetViewArrangement(24)

        # Get the Chart View Node
        cvns = slicer.mrmlScene.GetNodesByClass('vtkMRMLChartViewNode')
        cvns.InitTraversal()
        cvn = cvns.GetNextItemAsObject()

        # Create an Array Node and add some data
        dn = slicer.mrmlScene.AddNode(slicer.vtkMRMLDoubleArrayNode())
        a = dn.GetArray()
        a.SetNumberOfTuples(numSamples)

        for i in range(numSamples):
            a.SetComponent(i, 0, nVals[i])
            a.SetComponent(i, 1, TREVals[i])
            a.SetComponent(i, 2, 0)

        # Create a Chart Node.
        cn = slicer.mrmlScene.AddNode(slicer.vtkMRMLChartNode())

        # Add the Array Nodes to the Chart. The first argument is a string used for the legend and to refer to the Array when setting properties.
        cn.AddArray('TRE to Number of Points', dn.GetID())

        # Set a few properties on the Chart. The first argument is a string identifying which Array to assign the property.
        # 'default' is used to assign a property to the Chart itself (as opposed to an Array Node).
        cn.SetProperty('default', 'title', 'TRE as a Function of Number of Points')
        cn.SetProperty('default', 'xAxisLabel', 'Points')
        cn.SetProperty('default', 'yAxisLabel', 'TRE')

        # Tell the Chart View which Chart to display
        cvn.SetChartNodeID(cn.GetID())


    def test_mareenaModule1(self):

        # Create coordinate models using CreateModels module
        createModelsLogic = slicer.modules.createmodels.logic()

        rasModelNode = createModelsLogic.CreateCoordinate(20, 2)
        rasModelNode.SetName('RasModel')

        refModelNode = createModelsLogic.CreateCoordinate(20, 2)
        refModelNode.SetName('RefModel')

        # Change the color of models
        rasModelNode.GetDisplayNode().SetColor(1, 0, 0)
        refModelNode.GetDisplayNode().SetColor(0, 1, 0)

        # Create transform node for registration
        refToRas = slicer.vtkMRMLLinearTransformNode()
        refToRas.SetName('RefToRas')
        slicer.mrmlScene.AddNode(refToRas)

        refModelNode.SetAndObserveTransformNodeID(refToRas.GetID())

        rasPoints = vtk.vtkPoints()
        refPoints = vtk.vtkPoints()

        logic = mareenaModuleLogic()

        TREVals = []
        nVals = range(10,70,5)

        for i in range(10):

            numPts = 10 + i * 5
            sigma = 3.0
            scale = 100.0

            nVals.append(numPts)

            self.generatePoints(numPts, scale, sigma)
            rasFids = slicer.util.getNode('RasPoints')
            refFids = slicer.util.getNode('RefPoints')

            self.fiducialsToPoints(rasFids, rasPoints)
            self.fiducialsToPoints(refFids, refPoints)

            refToRasMatrix = vtk.vtkMatrix4x4()
            logic.rigidRegistration(refPoints, rasPoints, refToRasMatrix)

            det = refToRasMatrix.Determinant()
            if det < 1e-8:
                logging.error('All points in one line')
                continue

            refToRas.SetMatrixTransformToParent(refToRasMatrix)
            avgDistance = logic.averageTransformedDistance(refPoints, rasPoints, refToRasMatrix)

            print "Average distance: " + str(avgDistance)

            targetPoint_Ras = numpy.array([0, 0, 0, 1])
            targetPoint_Ref = refToRasMatrix.MultiplyFloatPoint(targetPoint_Ras)
            targetPoint_Ref = numpy.array(targetPoint_Ref)

            TRE = numpy.linalg.norm(targetPoint_Ras - targetPoint_Ref)

            TREVals.append(TRE)

            print "TRE: " + str(TRE)

        # Creating a chart

        self.createChart(nVals, TREVals)