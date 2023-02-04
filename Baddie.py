from direct.showbase import DirectObject
from direct.actor.Actor import Actor
from direct.interval.IntervalGlobal import Sequence,Parallel,Wait,Func
from pandac.PandaModules import CollisionNode, CollisionSphere, BitMask32
from pandac.PandaModules import CollisionHandlerEvent
from pandac.PandaModules import Point3, Vec3
import sound

class Baddie(DirectObject.DirectObject):
    id_count = 0
    targetTiles = []
    adjustedHeading = {0:180,
                       90:90,
                       180:0,
                       270:270}
    headingMap = {  0:[ 0,-1],
                   90:[ 1, 0],
                  180:[ 0, 1],
                  270:[-1, 0]}
    @classmethod
    def resetIds(cls):
        cls.id_count = 0

    def __init__(self,world,parent,
                 startColumn,startRow,startHeading):
        DirectObject.DirectObject.__init__(self)
        self.world = world
        self.parent = parent
        self.id = Baddie.id_count
        Baddie.id_count += 1
        Baddie.targetTiles.append((None,None))
        
        self.np = Actor()
        self.np.loadModel("models/baddie")
        self.np.loadAnims({"walk":"models/baddie-walk",
                           "explode":"models/baddie-explode",
                           "die":"models/baddie-die"})
        self.np.setScale(0.33)
        self.np.reparentTo(parent)

        #Load up Sounds
        self.explodeSound = sound.load("sounds/baddie-explode.wav")
        self.hitSound = sound.load("sounds/baddie-hit.wav")
        self.triggerSound = sound.load("sounds/baddie-trigger.wav")

        #Setup collisions solids
        #BitMasks are set explicitly in reset()
        triggerSolid = CollisionSphere(0,0,0,12)
        self.triggerNodeName = "trigger%d" % self.id
        triggerNode = CollisionNode(self.triggerNodeName)
        triggerNode.addSolid(triggerSolid)
        self.triggerNp = self.np.attachNewNode(triggerNode)
        self.triggerNp.setPos(0,0,1.5)
        self.triggerHandler = CollisionHandlerEvent()
        self.triggerHandler.addInPattern("%fn")
        world.cTrav.addCollider(self.triggerNp, self.triggerHandler)

        explosionSolid = CollisionSphere(0,0,0,29)
        self.explosionSolid = explosionSolid
        self.explosionNodeName = "explosion%d" % self.id
        explosionNode = CollisionNode(self.explosionNodeName)
        explosionNode.addSolid(explosionSolid)
        self.explosionNp = self.np.attachNewNode(explosionNode)
        self.explosionNp.setPos(0,0,1.5)
        self.explosionHandler = CollisionHandlerEvent()
        self.explosionHandler.addInPattern("%fn")
        world.cTrav.addCollider(self.explosionNp,self.explosionHandler)
        self.accept(self.explosionNodeName, self.kill)

        hitSolid = CollisionSphere(0,0,0,1)
        self.hitNodeName = "hit%d" % self.id
        hitNode = CollisionNode(self.hitNodeName)
        hitNode.addSolid(hitSolid)
        self.hitNp = self.np.attachNewNode(hitNode)
        self.hitNp.setPos(0,0,1.5)
        self.hitHandler = CollisionHandlerEvent()
        self.hitHandler.addInPattern("%fn")
        world.cTrav.addCollider(self.hitNp,self.hitHandler)

        self.interval = Wait(0)
        self.targetPos = None
        self.targetH = None
        self.isEnd = False
        self.startInfo = (startColumn,startRow,startHeading)

    def reset(self):
        startColumn, startRow, startH = self.startInfo
        self.np.setPos(self.world.map.getTilePos(startColumn,startRow))
        self.np.setH(Baddie.adjustedHeading[startH])
        self.setTarget(startColumn,startRow,startH)

        self.triggerNp.node().setIntoCollideMask(BitMask32(0x0))
        self.triggerNp.node().setFromCollideMask(BitMask32(0x2))
        self.accept(self.triggerNodeName, self.trigger)
        self.explosionNp.node().setIntoCollideMask(BitMask32(0x0))
        self.explosionNp.node().setFromCollideMask(BitMask32(0x0))
        self.hitNp.node().setIntoCollideMask(BitMask32(0x4))
        self.hitNp.node().setFromCollideMask(BitMask32(0x2))
        self.accept(self.hitNodeName, self.die)
        
        self.isEnd = False

        self.np.reparentTo(self.parent)
        self.np.loop("walk")
        
        self.think()
        self.refreshInterval()

    def isTargetOk(self,col_index,row_index):
        try:
            if self.world.map.getTileWall(col_index,row_index) != None:
                return False
            elif (col_index,row_index) in Baddie.targetTiles:
                return False
            else:
                return True
        except IndexError:
            return False

    def setTarget(self,col_index,row_index,heading):
        self.targetPos = self.world.map.getTilePos(col_index,row_index)
        Baddie.targetTiles[self.id] = (col_index,row_index)
        self.targetH = heading

    def getTargetPos(self):
        return self.targetPos

    def getTargetH(self):
        return self.targetH

    def getTargetTile(self):
        return Baddie.targetTiles[self.id]

    def think(self):
        #Base Baddie doesn't do much thinking.
        pass

    def refreshInterval(self):
        self.interval.pause()

        if self.np.getPos() != self.getTargetPos():
            targetH = self.getIntervalH(self.getTargetPos())
        else:
            targetH = self.np.getH()
            
        self.interval = Sequence(Parallel(self.np.hprInterval(0.25,Vec3(targetH,0,0)),
                                          self.np.posInterval(1.0,self.getTargetPos())),
                                 Func(self.think),
                                 Func(self.refreshInterval))
        self.interval.start()

    def getIntervalH(self,targetPos):
        currentH = self.np.getH()
        self.np.lookAt(targetPos)
        targetH = (180+self.np.getH())%360
        turnAngle = currentH-targetH
        if abs(turnAngle) > 180:
            if turnAngle > 0:
                currentH = currentH-360
            else:
                currentH = currentH+360
        self.np.setH(currentH)
        return targetH

    def explode(self):
        self.triggerNp.node().setFromCollideMask(BitMask32(0x0))
        self.interval.pause()
        self.np.play("explode",fromFrame=12)
        self.interval = Parallel(Sequence(Wait(8.0/24.0),Func(self.activateExplosion)),
                                 Sequence(Wait(36.0/24.0),Func(self.setDead)))
        self.interval.start()

    def trigger(self,entry):
        self.triggerNp.node().setFromCollideMask(BitMask32(0x0))
        self.interval.pause()
        
        targetH = self.getIntervalH(entry.getIntoNodePath())
        
        self.np.play("explode")
        self.triggerSound.play()
        self.interval = Parallel(self.np.hprInterval(0.25,Vec3(targetH,0,0)),
                                 Sequence(Wait(20.0/24.0),Func(self.activateExplosion)),
                                 Sequence(Wait(48.0/24.0),Func(self.setDead)))
        self.interval.start()

    def kill(self,entry):
        name = entry.getIntoNode().getName()
        if name == "truck":
            self.world.setLoser()
        elif name[:3] == "hit":
            id = int(name[3:])
            self.world.baddies[id].explode()
        self.isVictor = True

    def die(self,entry):
        self.triggerNp.node().setFromCollideMask(BitMask32(0x0))
        self.explosionNp.node().setFromCollideMask(BitMask32(0x0))
        self.hitNp.node().setFromCollideMask(BitMask32(0x0))
        self.interval.pause()
        self.np.play("die")
        self.hitSound.play()
        self.interval = Sequence(Wait(4.0/24.0),Func(self.setDead))
        self.interval.start()

    def activateExplosion(self):
        self.explosionNp.node().setFromCollideMask(BitMask32(0x2|0x4))
        self.hitNp.node().setFromCollideMask(BitMask32(0x0))
        self.hitNp.node().setIntoCollideMask(BitMask32(0x0))
        self.explodeSound.play()

    def setDead(self):
        Baddie.targetTiles[self.id] = (None,None)
        if not self.isEnd:
            self.np.detachNode()

    def setEnd(self,force=False):
        if force or self.triggerNp.node().getFromCollideMask().getWord():
            self.np.stop()
            self.interval.pause()
        self.isEnd = True
        self.ignore(self.triggerNodeName)
        self.ignore(self.hitNodeName)

class StationaryBaddie(Baddie):
    def __init__(self,world,parent,
                 startColumn,startRow,startHeading):
        Baddie.__init__(self,world,parent,
                        startColumn,startRow,startHeading)
        self.thinkH = None

    def reset(self):
        Baddie.reset(self)
        self.thinkH = self.np.getH()
        
    def think(self):
        if self.thinkH != None:
            startColumn, startRow, startHeading = self.startInfo
            self.np.setH(self.thinkH)
            self.setTarget(startColumn,startRow,startHeading)

class TurningBaddie(Baddie):
    def turn(self,searchOrder):
        currentCol, currentRow = Baddie.targetTiles[self.id]
        currentH = self.getTargetH()
        isStuck = True
    
        for checkH in searchOrder:
            mapping = Baddie.headingMap[checkH]
            if self.isTargetOk(currentCol+mapping[0],currentRow+mapping[1]):
                self.setTarget(currentCol+mapping[0],currentRow+mapping[1],checkH)
                isStuck = False
                break
        if isStuck:
            self.setTarget(currentCol,currentRow,currentH)
        
    def think(self,turnOrder=[]):
        Baddie.think(self)
        self.turn([self.getTargetH()]) 

class RightTurnBaddie(TurningBaddie):
    def think(self):
        currentH = self.getTargetH()
        searchOrder = [ currentH, (currentH+90)%360, (currentH+180)%360, (currentH+270)%360 ]
        self.turn(searchOrder)

class LeftTurnBaddie(TurningBaddie):
    def think(self):
        currentH = self.getTargetH()
        searchOrder = [ currentH, (currentH+270)%360, (currentH+180)%360, (currentH+90)%360 ]
        self.turn(searchOrder)

class BouncingBaddie(TurningBaddie):
    def think(self):
        currentH = self.getTargetH()
        searchOrder = [ currentH, (currentH+180)%360 ]
        self.turn(searchOrder)