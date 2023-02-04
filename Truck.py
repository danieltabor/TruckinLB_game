from direct.showbase import DirectObject
from direct.actor.Actor import Actor
from direct.interval.IntervalGlobal import Sequence,Parallel,Wait,Func,LerpFunc,SoundInterval
from pandac.PandaModules import CollisionNode, CollisionSegment, CollisionPolygon, BitMask32
from pandac.PandaModules import CollisionHandlerEvent
from pandac.PandaModules import Point3, Vec3
import sound

import math
import time

class Truck(DirectObject.DirectObject):
	adjustedHeading = {   0:270,
						 90:180,
						180: 90,
						270:  0}
	def __init__(self,world,parent,
				 startColumn,startRow,startHeading):
		DirectObject.DirectObject.__init__(self)
		self.world = world
		self.parent = parent

		#Create the truck node path		
		self.np = Actor()
		self.np.loadModel("models/truck")
		self.np.loadAnims({"forward":"models/truck-forward",
							   "idle":"models/truck-idle"})
		self.np.reparentTo(parent)

		#Load Sounds
		self.idleSound = sound.load("sounds/truck-idle.wav")
		self.idleSound.setLoop(True)
		self.forwardSound = sound.load("sounds/truck-forward.wav")
		self.forwardSound.setLoop(True)

		#Use baddie actor to simulat the truck exploding
		#if/when the time comes
		self.explosion = Actor()
		self.explosion.loadModel("models/baddie")
		self.explosion.loadAnims({"explode":"models/baddie-explode"})
		self.explosion.setScale(0.33)

		#Create Nodes to which cameras can be attached.
		#And create corresponding nodes for the camera to lookat
		#while there.
		self.cameraForwardMount = self.np.attachNewNode("cameraForwardMount")
		self.cameraForwardTarget = self.np.attachNewNode("cameraForwardTarget")
		self.cameraRearMount = self.np.attachNewNode("cameraRearMount")
		self.cameraRearTarget = self.np.attachNewNode("cameraRearTarget")
		self.cameraOverheadMount = self.np.attachNewNode("cameraOverheadMount")
		self.cameraOverheadTarget = self.np

		#Create collision solids
		#I'll use segments that go around the truck as "from" solids
		#and a polygon that is encompased by those same corners as
		#an "into" solid.  From solids will be used to detect collisions
		#with walls and the goal, while Intp solids will be used by the
		#bad guys to detect the truck.
		truckCorners = ((-5.1,  1,-5.1, -1),
						(-5.1, -1,   1, -1),
						(   1, -1,   1,  1),
						(   1,  1,-5.1,  1))
		
		solidFromNode = CollisionNode("truck")
		for x1,y1,x2,y2 in truckCorners:
			segment = CollisionSegment(x1,y1,0.5,x2,y2,0.5)
			solidFromNode.addSolid(segment)
		solidFromNode.setFromCollideMask(BitMask32(0x1))
		solidFromNode.setIntoCollideMask(BitMask32(0x0))
		self.fromNp = self.np.attachNewNode(solidFromNode)

		solidIntoNode = CollisionNode("truck")
		polyPoints = [(x,y,0.5) for x,y,j,k in truckCorners]
		polySolid = CollisionPolygon( Point3(*polyPoints[0]),
									  Point3(*polyPoints[1]),
									  Point3(*polyPoints[2]),
									  Point3(*polyPoints[3]))
		solidIntoNode.addSolid(polySolid)
		solidIntoNode.setFromCollideMask(BitMask32(0x0))
		solidIntoNode.setIntoCollideMask(BitMask32(0x2))
		self.intoNp = self.np.attachNewNode(solidIntoNode)

		#Create a handler for collisions
		self.cHandler = CollisionHandlerEvent()
		self.cHandler.addInPattern("%fn")
		self.accept("truck", self.collision)
		world.cTrav.addCollider(self.fromNp, self.cHandler)

		#Record startup info for reset to use
		self.startInfo = (startColumn,startRow,startHeading)

		self.keyMap = {"left":False,"right":False,"up":False,"down":False}
		self.accept("arrow_left",self.setKey,["left",True])
		self.accept("arrow_left-up",self.setKey,["left",False])
		self.accept("arrow_right",self.setKey,["right",True])
		self.accept("arrow_right-up",self.setKey,["right",False])
		self.accept("arrow_up",self.setKey,["up",True])
		self.accept("arrow_up-up",self.setKey,["up",False])
		self.accept("arrow_down",self.setKey,["down",True])
		self.accept("arrow_down-up",self.setKey,["down",False])

		#Variables used to determine different aspects
		#of movement.
		self.lastGoodPos = None
		self.lastGoodH = None
		self.isMoving = False
		self.np.loop("idle")
		self.walls = []
		self.interval = Sequence(Func(self.updateWalls),
								 LerpFunc(self.move,fromData=0.0,toData=1.0,duration=1) )
		self.moveSpeed=7
		self.rotSpeed=75
		self.moveDir = 0
		self.rotDir = 0
		self.prevMoveT = 0

		self.resetTime = 0

	def reset(self):
		startColumn, startRow, startHeading = self.startInfo

		self.explosion.detachNode()

		self.interval.pause()
		self.np.setPos(self.world.map.getTilePos(startColumn,startRow))
		self.lastGoodPos = self.np.getPos()
		self.np.setH(Truck.adjustedHeading[startHeading])
		self.lastGoodH = self.np.getH()
		self.prevMoveT = 0
		self.resetCameras()
		self.updateWalls()
		
		self.isMoving = False
		self.np.loop("idle")
		self.idleSound.play()

		self.interval.loop()

	def resetCameras(self):
		self.cameraForwardMount.setPos(8,0,4)
		self.cameraForwardTarget.setPos(-8,0,0.5)
		self.cameraRearMount.setPos(-10,0,4)
		self.cameraRearTarget.setPos(10,0,0.5)
		self.cameraOverheadMount.setPos(0,0,75)
		self.cameraOverheadMount.setR(90)

	def setKey(self,key,value):
		keyMap = self.keyMap
		keyMap[key] = value
		self.moveDir = 0
		self.rotDir = 0
		if keyMap["up"]:
			self.moveDir += 1
		if keyMap["down"]:
			self.moveDir -= 1
		if keyMap["right"]:
			self.rotDir -= 1
		if keyMap["left"]:
			self.rotDir += 1		  

	def move(self,t):
		if t < self.prevMoveT: elapse = (1.0 - self.prevMoveT) + t
		else: elapse = t - self.prevMoveT
		self.prevMoveT = t
		
		self.lastGoodPos = self.np.getPos()
		self.lastGoodH = self.np.getH()

		if not self.moveDir and self.isMoving:
			self.isMoving = False
			self.np.loop("idle")
			self.forwardSound.stop()
			self.idleSound.play()
		if self.moveDir and not self.isMoving:
			self.isMoving = True
			self.np.loop("forward")
			self.forwardSound.play()
			self.idleSound.stop()

		if self.moveDir:
			self.np.setH(self.np.getH()+self.rotSpeed*elapse*self.rotDir*self.moveDir)
			forward  = self.np.getNetTransform().getMat().getRow3(0)*-1
			forward.setZ(0)
			forward.normalize()
			self.np.setPos(self.np.getPos() + forward*(self.moveSpeed*elapse*self.moveDir))

		#This is so the overhead camera doesn't
		#swing around and make people sick.
		self.cameraOverheadMount.setH(-self.np.getH()+90)

	def updateWalls(self):
		walls = self.walls
		[wall.setCollideMask(BitMask32(0x0)) for wall in walls]
		c, r = self.world.map.getTile(self.np.getPos())
		walls = self.world.map.getWalls(c-3,c+3,r-3,r+3)
		[wall.setIntoCollideMask(BitMask32(0x1)) for wall in walls]
		self.walls = walls

	def collision(self,entry):
		if entry.getIntoNode().getName() == "goal":
			self.setEnd()
			self.world.setWinner()
		else:
			self.interval.pause()
			self.np.setPos(self.lastGoodPos)
			self.np.setH(self.lastGoodH)
			self.interval.resume()

	def explode(self):
		self.explosion.reparentTo(self.np)
		collection = self.np.findAllMatches("**/camera")
		self.cameraForwardMount.setPos(0,0,25)
		self.cameraRearMount.setPos(0,0,25)
		[collection[i].lookAt(self.np) for i in range(collection.getNumPaths())] 
		self.explosion.play("explode",fromFrame=24)
		self.setEnd()

	def setEnd(self):
		self.interval.pause()
		self.np.stop()
		self.forwardSound.stop()
		self.idleSound.stop()

