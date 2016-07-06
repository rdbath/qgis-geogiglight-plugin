#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import os
from geogig.geogigwebapi.repository import Repository
import shutil
from geogig.tools.utils import tempFilename, loadLayerNoCrsDialog
from qgis.core import *
from geogig.tools.gpkgsync import getCommitId
from geogig.gui.dialogs.conflictdialog import ConflictDialog

REPOS_SERVER_URL = "http://localhost:8182/"
REPOS_FOLDER = "d:\\repo" #fill this with your repos folder

def _createTestRepo(name, modifiesRepo = False):
    i = len(os.listdir(REPOS_FOLDER))
    if modifiesRepo:
        folderName = "%i_%s" % (i, name)
    else:
        folderName = "original_%s" % name
    destPath = os.path.join(REPOS_FOLDER, folderName)
    if not os.path.exists(destPath):
        orgPath = os.path.join(os.path.dirname(__file__), "data", "repos", name)
        shutil.copytree(orgPath, destPath)
    repo = Repository(REPOS_SERVER_URL + "repos/%s/" % folderName)
    return repo

def _layer(name):
    path = os.path.join(os.path.dirname(__file__), "data", "layers", name + ".gpkg")
    return loadLayerNoCrsDialog(path, name, "ogr")

class WebApiTests(unittest.TestCase):

    def setUp(self):
        pass

    def testLog(self):
        repo = _createTestRepo("simple")
        log = repo.log()
        self.assertEqual(3, len(log))
        self.assertEqual("third", log[0].message)

    def testLogInEmptyRepo(self):
        repo = _createTestRepo("empty")
        log = repo.log()
        self.assertEqual(0, len(log))

    def testLogInEmptyBranch(self):
        repo = _createTestRepo("empty")
        log = repo.log(until="master")
        self.assertEqual(0, len(log))

    def testLogWithPath(self):
        repo = _createTestRepo("simple")
        log = repo.log(path = "points/fid--678854f5_155b574742f_-8000")
        self.assertEqual(2, len(log))
        self.assertEqual("third", log[0].message)
        self.assertEqual("first", log[1].message)

    def testLogMultipleParents(self):
        repo = _createTestRepo("withmerge")
        log = repo.log()
        self.assertEqual(2, len(log[0].parents))

    def testBlame(self):
        repo = _createTestRepo("simple")
        blame = repo.blame("points/fid--678854f5_155b574742f_-8000")
        print blame

    def testDownload(self):
        repo = _createTestRepo("simple")
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points")
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        self.assertTrue(layer.isValid())

    def testDownloadNonHead(self):
        repo = _createTestRepo("simple")
        log = repo.log()
        self.assertEqual(3, len(log))
        commitid = log[-1].commitid
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points", ref = commitid)
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        self.assertTrue(layer.isValid())
        features = list(layer.getFeatures())
        self.assertEqual(1, len(features))

    def testDescription(self):
        repo = _createTestRepo("simple")
        self.assertTrue("<p>LAST VERSION: <b>third" in repo.fullDescription())

    def testDescriptionInEmptyRepo(self):
        repo = _createTestRepo("empty")
        self.assertTrue("<p>LAST VERSION: <b></b></p>" in repo.fullDescription())

    def testFeature(self):
        repo = _createTestRepo("simple")
        expected = {'geometry': 'POINT (20.532220860123836 83.62989408803831)', 'n': 1}
        feature = repo.feature("points/fid--678854f5_155b574742f_-8000", repo.HEAD)
        self.assertEqual(expected, feature)

    def testFeatureDiff(self):
        pass

    def testTrees(self):
        repo = _createTestRepo("severallayers")
        self.assertEquals(["points", "lines"], repo.trees())

    def testTreesNonHead(self):
        repo = _createTestRepo("severallayers")
        log = repo.log()
        self.assertEqual(4, len(log))
        commitid = log[-1].commitid
        self.assertEquals(["points"], repo.trees(commit = commitid))

    def testRemoveTree(self):
        repo = _createTestRepo("simple", True)
        self.assertEquals(["points"], repo.trees())
        repo.removetree("points")
        self.assertEquals([], repo.trees())

    def testTags(self):
        repo = _createTestRepo("simple")
        tags = repo.tags()
        log = repo.log()
        self.assertEqual({"mytag": log[0].commitid}, tags)

    def testNoTags(self):
        repo = _createTestRepo("empty")
        tags = repo.tags()
        self.assertEqual({}, tags)

    def testCreateTag(self):
        repo = _createTestRepo("simple", True)
        repo.createtag(self.HEAD, "anothertag")
        tags = repo.tags()
        log = repo.log()
        self.assertEqual({"mytag": log[0].commitid, "anothertag": log[0].commitid}, tags)

    def testRemoveTags(self):
        repo = _createTestRepo("simple", True)
        tags = repo.tags()
        self.assertEquals(1, len(tags))
        repo.deletetag(tags.keys()[0])
        tags = repo.tags()
        self.assertEquals(0, len(tags))

    def testDiff(self):
        repo = _createTestRepo("simple")
        log = repo.log()
        self.assertEqual(3, len(log))
        diff = repo.diff(log[-1].commitid, log[0].commitid)
        self.assertEqual(2, len(diff))
        self.assertEqual({"points/fid--678854f5_155b574742f_-8000", "points/fid--678854f5_155b574742f_-7ffd"},
                         {d.path for d in diff})

    def testDiffWithPath(self):
        repo = _createTestRepo("simple")
        log = repo.log()
        self.assertEqual(3, len(log))
        expected = None #TODO
        diff = repo.diff(log[-1].commitid, log[0].commitid, "points/fid--678854f5_155b574742f_-8000")
        self.assertTrue(1, len(diff))
        print diff[0].featurediff
        self.assertEqual(expected, diff)

    def testExportDiff(self):
        repo = _createTestRepo("simple")
        filename = tempFilename("gpkg")
        repo.exportdiff("points", "HEAD", "HEAD~1", filename)
        self.assertTrue(os.path.exists(filename))
        #Check exported gpkg is correct

    def testRevParse(self):
        repo = _createTestRepo("simple")
        head = repo.log()[0].commitid
        self.assertEqual(head, repo.revparse(repo.HEAD))

    def testLastUpdated(self):
        pass

    def testBranches(self):
        repo = _createTestRepo("simple")
        self.assertEquals(["master", "mybranch"], repo.branches())

    def testBranchesInEmptyRepo(self):
        repo = _createTestRepo("empty")
        self.assertEquals(["master"], repo.branches())

    def testCreateBranch(self):
        repo = _createTestRepo("simple", True)
        self.assertEquals(["master", "mybranch"], repo.branches())
        repo.createbranch(repo.HEAD, "anotherbranch")
        self.assertEquals({"master", "mybranch", "anotherbranch"}, set(repo.branches()))
        self.assertEqual(repo.revparse(repo.HEAD), repo.revparse("anotherbranch"))

    def testRemoveBranch(self):
        repo = _createTestRepo("simple", True)
        self.assertEquals(["master", "mybranch"], repo.branches())
        repo.deletebranch("mybranch")
        self.assertEquals(["master"], repo.branches())

    def testFirstImport(self):
        repo = _createTestRepo("empty", True)
        layer = _layer("points")
        repo.importgeopkg(layer, "master", "message", "me", "me@mysite.com", False)
        log = repo.log()
        self.assertEqual(1, len(log))
        self.assertEqual("message", log[0].message)
        self.assertEqual(["points"], repo.trees())

    def testNonAsciiImport(self):
        repo = _createTestRepo("empty", True)
        layer = _layer("points")
        msg = "Покупая птицу, смотри, нет ли у нее зубов. Если есть зубы, то это не птица"
        repo.importgeopkg(layer, "master", msg, "Даниил Хармс", "daniil@kharms.com", False)
        log = repo.log()
        self.assertEqual(1, len(log))
        self.assertEqual(msg, log[0].message)
        self.assertEqual(["points"], repo.trees())

    def testImportInterchangeFormat(self):
        repo = _createTestRepo("simple", True)
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points")
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        self.assertTrue(layer.isValid())
        features = list(layer.getFeatures())
        self.assertEqual(2, len(features))
        with edit(layer):
            layer.deleteFeatures([features[0].id()])
        features = list(layer.getFeatures())
        self.assertEqual(1, len(features))
        repo.importgeopkg(layer, "master", "message", "me", "me@mysite.com", True)
        log = repo.log()
        self.assertEqual("message", log[0].message)
        self.assertEqual(["points"], repo.trees())
        filename2 = tempFilename("gpkg")
        repo.checkoutlayer(filename2, "points")
        layer2 = loadLayerNoCrsDialog(filename, "points2", "ogr")
        self.assertTrue(layer2.isValid())
        features2 = list(layer2.getFeatures())
        self.assertEqual(1, len(features2))


    def testConflictsWithDeleteAndModify(self):
        repo = _createTestRepo("simple", True)
        log = repo.log()
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points", ref = log[0].commitid)
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        filename2 = tempFilename("gpkg")
        repo.checkoutlayer(filename2, "points", ref = log[0].commitid)
        layer2 = loadLayerNoCrsDialog(filename2, "points", "ogr")
        features = list(layer.getFeatures())
        with edit(layer):
            layer.changeAttributeValue(features[0].id(), 1, 1000)
            layer.changeAttributeValue(features[1].id(), 1, 2000)
        _, _, conflicts, _ = repo.importgeopkg(layer, "master", "message", "me", "me@mysite.com", True)
        self.assertEqual(0, len(conflicts))
        features2 = list(layer2.getFeatures())
        with edit(layer2):
            layer2.deleteFeatures([features2[0].id()])
            layer2.deleteFeatures([features2[1].id()])
        _, _, conflicts, _ = repo.importgeopkg(layer2, "master", "another message", "me", "me@mysite.com", True)
        self.assertEqual(2, len(conflicts))
        self.assertEqual("points/fid--678854f5_155b574742f_-8000", conflicts[0].path)
        self.assertEqual("74c26fa429b847bc7559f4105975bc2d7b2ef80c", conflicts[0].origin)
        self.assertEqual(None, conflicts[0].local)
        self.assertEqual("points/fid--678854f5_155b574742f_-7ffd", conflicts[1].path)

    def testConflicts(self):
        repo = _createTestRepo("simple", True)
        log = repo.log()
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points", ref = log[0].commitid)
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        filename2 = tempFilename("gpkg")
        repo.checkoutlayer(filename2, "points", ref = log[0].commitid)
        layer2 = loadLayerNoCrsDialog(filename2, "points", "ogr")
        features = list(layer.getFeatures())
        with edit(layer):
            layer.changeAttributeValue(features[0].id(), 1, 1000)
            layer.changeAttributeValue(features[1].id(), 1, 2000)
        _, _, conflicts, _ = repo.importgeopkg(layer, "master", "message", "me", "me@mysite.com", True)
        self.assertEqual(0, len(conflicts))
        features2 = list(layer2.getFeatures())
        with edit(layer2):
            layer2.changeAttributeValue(features2[0].id(), 1, 1001)
            layer2.changeAttributeValue(features2[1].id(), 1, 2001)
        _, _, conflicts, _ = repo.importgeopkg(layer2, "master", "another message", "me", "me@mysite.com", True)
        self.assertEqual(2, len(conflicts))
        self.assertEqual("points/fid--678854f5_155b574742f_-8000", conflicts[0].path)
        self.assertEqual("74c26fa429b847bc7559f4105975bc2d7b2ef80c", conflicts[0].origin)
        self.assertEqual({'the_geom': 'Point (20.53222086012383585 83.62989408803831282)', 'fid': 2, 'n': 1001}, conflicts[0].local)
        self.assertEqual("points/fid--678854f5_155b574742f_-7ffd", conflicts[1].path)



    def testLayerCommitId(self):
        repo = _createTestRepo("simple", True)
        log = repo.log()
        filename = tempFilename("gpkg")
        repo.checkoutlayer(filename, "points", ref = log[1].commitid)
        layer = loadLayerNoCrsDialog(filename, "points", "ogr")
        self.assertTrue(log[1].commitid, getCommitId(layer))


def webapiSuite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(WebApiTests, 'test'))
    return suite

