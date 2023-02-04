#!/usr/bin/env python3
import direct.directbase.DirectStart
from direct.actor import Actor
from direct.showbase import DirectObject
from direct.interval.IntervalGlobal import *
from pandac.PandaModules import Point3, Vec3
from direct.task import Task
from direct.gui.OnscreenImage import OnscreenImage
from direct.gui.OnscreenText import OnscreenText 
from pandac.PandaModules import NodePath
from pandac.PandaModules import CollisionTraverser
from pandac.PandaModules import CollisionHandlerQueue, CollisionHandlerPusher, CollisionHandlerEvent
from pandac.PandaModules import Camera,BitMask32, CollisionSphere, CollisionNode, CollisionSegment, CollisionPolygon, TransparencyAttrib
from pandac.PandaModules import TransparencyAttrib
import sys
import os
from Map import Map
import sound

class World(DirectObject.DirectObject):
	#Symbol tables used to decode map files.
	#Format: symbol: [model path, heading, collision mask]

	
	def __init__(self,mapName=None):
		base.disableMouse()		
		self.level = 0

		self.accept("q",self.quit)

		#Items used during game play
		self.cTrav = None
		self.truck = None
		self.baddies = []
		self.mapNp = None
		self.map = Map(self)
		self.isWaitForInput = False

		self.splashImage = None
		self.splashText = None
		self.winnerSound = sound.load("sounds/winner.wav")
		self.loserSound = sound.load("sounds/loser.wav")

		self.centerCamera = base.camera
		self.leftCamera = render.attachNewNode(Camera("camera"))
		self.leftCamera.node().setScene(render)
		self.rightCamera = render.attachNewNode(Camera("camera"))
		self.rightCamera.node().setScene(render)

		self.leftDisplayRegion = base.win.makeDisplayRegion(0,0.33,0,0.33)
		self.leftDisplayRegion.setClearColorActive(1)
		self.leftDisplayRegion.setClearDepthActive(1)
		self.leftDisplayRegion.setCamera(self.leftCamera)
		self.leftFrame = None
		
		self.rightDisplayRegion = base.win.makeDisplayRegion(0.66,1,0,0.33)
		self.rightDisplayRegion.setClearColorActive(1)
		self.rightDisplayRegion.setClearDepthActive(1)
		self.rightDisplayRegion.setCamera(self.rightCamera)
		self.rightFrame = None

		#cameraMounts is empty now, but when
		#a map is loaded this will be filled with,
		#in order, the forward view, overhead view, and rear view
		#camera mounts on the truck.  The camera order
		#in cameraPositions will then determine which
		#mount which camera is mounted to.
		self.cameraMounts = []
		self.cameraPositions = [self.leftCamera, self.centerCamera, self.rightCamera]

		if mapName == None:
			self.showOpening()
		else:
			try:
				self.level = int(mapName)-1
			except ValueError:
				self.loadNextLevel(mapName)
			else:
				self.loadNextLevel()

	def showOpening(self,index=0):
		if index == 3:
			self.acceptOnce("space",self.loadNextLevel)
			self.loadNextLevel()
		else:
			self.showImage("images/opening%d.png" % index)
			self.acceptOnce("space",self.showOpening,[index+1])

	def loadNextLevel(self,mapName=None):
		self.ignore("c")
		self.ignore("space")
		self.isWaitForInput = False
		self.clearImage()
		self.clearText()
		
		#Now load the next map.
		if mapName == None:
			self.level += 1
			mapPath = "levels/%d.txt" % int(self.level)
		else:
			mapPath = "levels/%s.txt" % str(mapName)
			
		if self.mapNp != None:
			self.mapNp.detachNode()
		if not os.path.exists(mapPath):
			self.clearFrames()
			self.showGameOver()
		else:
			self.mapNp = render.attachNewNode("Map Level %d" % self.level)
			self.cTrav = CollisionTraverser()
			base.cTrav = self.cTrav
			#self.cTrav.showCollisions(render)
			self.truck, self.baddies = self.map.load(self.mapNp,mapPath)
			self.truck.reset()
			[baddie.reset() for baddie in self.baddies]
			
			self.cameraMounts = [(self.truck.cameraForwardMount,self.truck.cameraForwardTarget),
								(self.truck.cameraOverheadMount,self.truck.cameraOverheadTarget),
								(self.truck.cameraRearMount,self.truck.cameraRearTarget)]
			self.resetCameras()

			self.winnerSound.stop()
			self.showFrames()
			self.showText(self.map.getName())
			self.accept("c",self.rotateCameras)

	def resetLevel(self):
		self.ignore("space")
		self.isWaitForInput = False
		self.truck.reset()
		for baddie in self.baddies:
			baddie.reset()
		self.resetCameras()
		self.clearImage()
		self.showText(self.map.getName())
		self.loserSound.stop()
		self.accept("c",self.rotateCameras)

	def showText(self,text):
		self.clearText()
		self.splashText = OnscreenText(text,
									pos=(0,-0.90,0),
									fg=(255,255,1,1))

	def clearText(self):
		if self.splashText != None:
			self.splashText.destroy()
			self.splashText = None

	def showImage(self,path):
		self.clearImage()
		self.splashImage = OnscreenImage(path,
										 parent=render2d)
		self.splashImage.setTransparency(TransparencyAttrib.MAlpha)

	def clearImage(self):
		if self.splashImage != None:
			self.splashImage.destroy()
			self.splashImage = None		

	def showFrames(self):
		if self.leftFrame == None:
			self.leftFrame = OnscreenImage("images/leftframe.png",
										pos = (-0.67,0,-0.67),
										scale=0.35,
										parent=render2d)
			self.leftFrame.setTransparency(TransparencyAttrib.MAlpha)
		if self.rightFrame == None:
			self.rightFrame = OnscreenImage("images/rightframe.png",
											pos = (0.65,0,-0.67),
											scale=0.35,
											parent=render2d)
			self.rightFrame.setTransparency(TransparencyAttrib.MAlpha)

	def clearFrames(self):
		if self.leftFrame != None:
			self.leftFrame.destroy()
			self.leftFrame = None
		if self.rightFrame != None:
			self.rightFrame.destroy()
			self.rightFrame = None
		
	def resetCameras(self):
		for i in range(len(self.cameraMounts)):
			cam = self.cameraPositions[i]
			mount, target = self.cameraMounts[i]
			cam.reparentTo(mount)
			cam.lookAt(target)

	def rotateCameras(self):
		tmp = self.cameraPositions[0]
		for i in range(len(self.cameraPositions)-1):
			self.cameraPositions[i] = self.cameraPositions[i+1]
		self.cameraPositions[-1] = tmp
		self.resetCameras()
		
	def quit(self):
		sys.exit(0)

	def setLoser(self):
		if not self.isWaitForInput:
			self.truck.explode()
			[baddie.setEnd() for baddie in self.baddies]
			self.loserSound.play()
			self.clearText()
			self.showImage("images/loser.png")
			self.ignore("c")
			self.acceptOnce("space",self.resetLevel)
			self.isWaitForInput = True

	def setWinner(self):
		if not self.isWaitForInput:
			[baddie.setEnd(force=True) for baddie in self.baddies]
			self.clearText()
			self.showImage("images/winner.png")
			self.winnerSound.play()
			for baddie in self.baddies:
				baddie.setEnd()
			self.acceptOnce("space",self.loadNextLevel)
			self.isWaitForInput = True

	def showGameOver(self):
		self.leftDisplayRegion.setClearColorActive(0)
		self.leftDisplayRegion.setClearDepthActive(0)		
		self.rightDisplayRegion.setClearColorActive(0)
		self.rightDisplayRegion.setClearDepthActive(0)
		
		backDrop = loader.loadModel("models/backdrop")
		backDrop.setScale(20)
		backDrop.reparentTo(render)
		backDrop.setHpr(Vec3(0,90,0))
		backDrop.setPos(Point3(0,10,0))
		
		actor = Actor.Actor()
		actor.loadModel("models/baddie")
		actor.loadAnims({"walk":"models/baddie-walk",
						 "explode":"models/baddie-explode"})
		actor.setScale(0.4)
		actor.reparentTo(render)
		actor.setPos(Point3(6,0,0))
		actor.setHpr(Vec3(270,0,0))

		self.clearText()
		self.showImage("images/gameover.png")

		self.centerCamera.reparentTo(render)
		self.centerCamera.setPos(Point3(-5,-10,3))
		self.centerCamera.lookAt(Point3(0,0,0))

		def walk():
			self.winnerSound.play()
			actor.setScale(0.4)
			actor.loop("walk")
		def cheer():
			actor.play("explode",fromFrame=0,toFrame=19)
		def explode1():
			self.loserSound.play()
			actor.play("explode",fromFrame=19,toFrame=23)
		def explode2():
			actor.setScale(0.25)
			actor.play("explode",fromFrame=24)
		def hprReset():
			actor.setH(90)
			  
		interval = Sequence(Func(walk),
							actor.posInterval(4,Point3(-2,0,0)),
							Func(cheer),
							Wait(19.0/24.0),
							actor.hprInterval(2,Vec3(990,0,0)),
							Func(explode1),
							Wait(5.0/24.0),
							Func(explode2),
							Wait(2.0))
		interval.loop()

def main():
	if len(sys.argv) > 1:
		mapName = sys.argv[1]
	else:
		mapName = None
	world = World(mapName)
	run()

if __name__ == "__main__":
	main()
