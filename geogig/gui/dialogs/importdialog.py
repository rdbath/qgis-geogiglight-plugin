from qgis.core import *
from qgis.gui import *
from PyQt4 import QtGui
from geogig.tools.layers import *
import os
from geogig.tools.layertracking import addTrackedLayer, isRepoLayer
from geogig.tools.utils import *
from geogig.tools.gpkgsync import addGeoGigTablesAndTriggers
from geogig.geogigwebapi import repository
from geogig.tools.gpkgsync import getUserInfo

class ImportDialog(QtGui.QDialog):

    def __init__(self, parent, repo = None, layer = None):
        super(ImportDialog, self).__init__(parent)
        self.repo = repo
        self.layer = layer
        self.ok = False
        self.initGui()

    def initGui(self):
        self.setWindowTitle('Add layer to GeoGig repository')
        verticalLayout = QtGui.QVBoxLayout()

        if self.repo is None:
            repos = repository.repos
            layerLabel = QtGui.QLabel('Repository')
            verticalLayout.addWidget(layerLabel)
            self.repoCombo = QtGui.QComboBox()
            self.repoCombo.addItems(repos.keys())
            verticalLayout.addWidget(self.repoCombo)
        if self.layer is None:
            layerLabel = QtGui.QLabel('Layer')
            verticalLayout.addWidget(layerLabel)
            self.layerCombo = QtGui.QComboBox()
            layerNames = [layer.name() for layer in getVectorLayers()
                          if layer.source().lower().split("|")[0].split(".")[-1] in["gpkg", "geopkg"]
                          and not isRepoLayer(layer)]
            self.layerCombo.addItems(layerNames)
            verticalLayout.addWidget(self.layerCombo)

        messageLabel = QtGui.QLabel('Message to describe this update')
        verticalLayout.addWidget(messageLabel)

        self.messageBox = QtGui.QPlainTextEdit()
        self.messageBox.textChanged.connect(self.messageHasChanged)
        verticalLayout.addWidget(self.messageBox)

        self.buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Cancel)
        self.importButton = QtGui.QPushButton("Add layer")
        self.importButton.clicked.connect(self.importClicked)
        self.importButton.setEnabled(False)
        self.buttonBox.addButton(self.importButton, QtGui.QDialogButtonBox.ApplyRole)
        self.buttonBox.rejected.connect(self.cancelPressed)
        verticalLayout.addWidget(self.buttonBox)

        self.setLayout(verticalLayout)

        self.resize(400, 200)

    def messageHasChanged(self):
        self.importButton.setEnabled(self.messageBox.toPlainText() != "")


    def importClicked(self):
        if self.repo is None:
            self.repo = repository.repos[self.repoCombo.currentText()]
        if self.layer is None:
            text = self.layerCombo.currentText()
            self.layer = resolveLayer(text)

        addGeoGigTablesAndTriggers(self.layer)
        user, email = getUserInfo()
        if user is None:
            self.close()
            return
        message = self.messageBox.toPlainText()
        self.repo.importgeopkg(self.layer, message, user, email)

        commitid =  self.repo.revparse(self.repo.HEAD)
        addTrackedLayer(self.layer().source, self.repo.url, commitid)
        self.ok = True
        config.iface.messageBar().pushMessage("Layer was correctly added to repository",
                                                  level = QgsMessageBar.INFO, duration = 4)
        self.close()


    def cancelPressed(self):
        self.close()