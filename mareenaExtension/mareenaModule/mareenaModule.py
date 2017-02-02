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

        #
        # input volume selector
        #
        self.inputSelector = slicer.qMRMLNodeComboBox()
        self.inputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.inputSelector.selectNodeUponCreation = True
        self.inputSelector.addEnabled = False
        self.inputSelector.removeEnabled = False
        self.inputSelector.noneEnabled = False
        self.inputSelector.showHidden = False
        self.inputSelector.showChildNodeTypes = False
        self.inputSelector.setMRMLScene(slicer.mrmlScene)
        self.inputSelector.setToolTip("Pick the input to the algorithm.")
        parametersFormLayout.addRow("Input Volume: ", self.inputSelector)

        #
        # output volume selector
        #
        self.outputSelector = slicer.qMRMLNodeComboBox()
        self.outputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.outputSelector.selectNodeUponCreation = True
        self.outputSelector.addEnabled = True
        self.outputSelector.removeEnabled = True
        self.outputSelector.noneEnabled = True
        self.outputSelector.showHidden = False
        self.outputSelector.showChildNodeTypes = False
        self.outputSelector.setMRMLScene(slicer.mrmlScene)
        self.outputSelector.setToolTip("Pick the output to the algorithm.")
        parametersFormLayout.addRow("Output Volume: ", self.outputSelector)

        #
        # threshold value
        #
        self.imageThresholdSliderWidget = ctk.ctkSliderWidget()
        self.imageThresholdSliderWidget.singleStep = 0.1
        self.imageThresholdSliderWidget.minimum = -100
        self.imageThresholdSliderWidget.maximum = 100
        self.imageThresholdSliderWidget.value = 0.5
        self.imageThresholdSliderWidget.setToolTip(
            "Set threshold value for computing the output image. Voxels that have intensities lower than this value will set to zero.")
        parametersFormLayout.addRow("Image threshold", self.imageThresholdSliderWidget)

        #
        # check box to trigger taking screen shots for later use in tutorials
        #
        self.enableScreenshotsFlagCheckBox = qt.QCheckBox()
        self.enableScreenshotsFlagCheckBox.checked = 0
        self.enableScreenshotsFlagCheckBox.setToolTip(
            "If checked, take screen shots for tutorials. Use Save Data to write them to disk.")
        parametersFormLayout.addRow("Enable Screenshots", self.enableScreenshotsFlagCheckBox)

        #
        # Apply Button
        #
        self.applyButton = qt.QPushButton("Apply")
        self.applyButton.toolTip = "Run the algorithm."
        self.applyButton.enabled = False
        parametersFormLayout.addRow(self.applyButton)

        # connections
        self.applyButton.connect('clicked(bool)', self.onApplyButton)
        self.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
        self.outputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)

        # Add vertical spacer
        self.layout.addStretch(1)

        # Refresh Apply button state
        self.onSelect()

    def cleanup(self):
        pass

    def onSelect(self):
        self.applyButton.enabled = self.inputSelector.currentNode() and self.outputSelector.currentNode()

    def onApplyButton(self):
        logic = mareenaModuleLogic()
        enableScreenshotsFlag = self.enableScreenshotsFlagCheckBox.checked
        imageThreshold = self.imageThresholdSliderWidget.value
        logic.run(self.inputSelector.currentNode(), self.outputSelector.currentNode(), imageThreshold,
                  enableScreenshotsFlag)


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

    def test_mareenaModule1(self):

        #
        # January 20th Homework
        #

        print "Mareena"

        #
        # January 24th Homework
        # This homework is posted in a separate file called transformNode.py



        #
        # January 26th Homework
        #

        N = 10
        Sigma = 5.0
        Scale = 100

        # Creating two fiducial lists
        randCoordinates = numpy.random.rand(10, 3)  # An array of random numbers
        noise = numpy.random.normal(0.0, Sigma, N * 3)

        refFids = slicer.vtkMRMLMarkupsFiducialNode()
        refFids.SetName('Ref Points')
        slicer.mrmlScene.AddNode(refFids)

        rasFids = slicer.vtkMRMLMarkupsFiducialNode()
        rasFids.SetName('Ras Points')
        slicer.mrmlScene.AddNode(rasFids)
        rasFids.GetDisplayNode().SetSelectedColor(1, 1, 0)

        refPoints = vtk.vtkPoints()
        rasPoints = vtk.vtkPoints()

        for i in range(N):

            x = (randCoordinates[i, 0] - 0.5) * Scale
            y = (randCoordinates[i, 1] - 0.5) * Scale
            z = (randCoordinates[i, 2] - 0.5) * Scale
            refFids.AddFiducial(x, y, z)
            refPoints.InsertNextPoint(x, y, z)

            xx = x + noise[i * 3]
            yy = y + noise[i * 3 + 1]
            zz = z + noise[i * 3 + 2]
            rasFids.AddFiducial(xx, yy, zz)
            rasPoints.InsertNextPoint(xx, yy, zz)

        #
        # January 27th Homework
        #

        # Create coordinate models using the CreateModels module

        createModelsLogic = slicer.modules.createmodels.logic()

        RefCoordinateModel = createModelsLogic.CreateCoordinate(20, 3)
        RefCoordinateModel.SetName('RasCoordinateModel')
        RasCoordinateModel = createModelsLogic.CreateCoordinate(10, 3)
        RasCoordinateModel.SetName('ReferenceCoordinateModel')

        # Change the color of models

        RefCoordinateModel.GetDisplayNode().SetColor(0, 0, 1)
        RasCoordinateModel.GetDisplayNode().SetColor(1, 0, 0)

        #
        # January 31st Homework
        #

        # Create transform node for registration

        RefToRas = slicer.vtkMRMLLinearTransformNode()
        RefToRas.SetName('RefToRas')
        slicer.mrmlScene.AddNode(RefToRas)

        landmarkTransform = vtk.vtkLandmarkTransform()
        landmarkTransform.SetSourceLandmarks(refPoints)
        landmarkTransform.SetTargetLandmarks(rasPoints)
        landmarkTransform.SetModeToRigidBody()
        landmarkTransform.Update()

        RefToRasMatrix = vtk.vtkMatrix4x4()
        landmarkTransform.GetMatrix(RefToRasMatrix)

        det = RefToRasMatrix.Determinant()
        if det < 1e-8:
            print 'Unstable registration '

        RefToRas.SetMatrixTransformToParent(RefToRasMatrix)
        RefCoordinateModel.SetAndObserveTransformNodeID(RefToRas.GetID())

        average = 0.0
        numSoFar = 0

        for i in range(N):
            numSoFar = numSoFar + 1

            a = refPoints.GetPoint(i)
            pointA_Ref = numpy.array(a)
            pointA_Ref = numpy.append(pointA_Ref, 1)
            pointA_Ras = RefToRasMatrix.MultiplyFloatPoint(pointA_Ref)

            b = rasPoints.GetPoint(i)
            pointB_Ref = numpy.array(b)
            pointB_Ras = numpy.append(pointB_Ref, 1)

            distance = numpy.linalg.norm(pointA_Ras - pointB_Ras)
            average = average + (distance - average) / numSoFar

        print "Average distance after registration: " + str(average)


        #
        # February 2nd Homework
        #
        
        # Calculate TRE with origin as target
        RasOrigin = numpy.array([0, 0, 0, 1])
        RefOrigin = RefToRasMatrix.MultiplyFloatPoint(RasOrigin)

        TRE = math.sqrt(pow((RasOrigin[0] - RefOrigin[0]), 2) + pow((RasOrigin[1] - RefOrigin[1]), 2) + pow(
            (RasOrigin[2] - RefOrigin[2]), 2))

        print "TRE: " + str(TRE)
