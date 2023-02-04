from direct.showbase.Loader import Loader
from pandac.PandaModules import Point3
from pandac.PandaModules import CollisionNode,CollisionPolygon, CollisionSphere, BitMask32
from pandac.PandaModules import TransparencyAttrib
from Baddie import Baddie,RightTurnBaddie,LeftTurnBaddie,BouncingBaddie,StationaryBaddie
from Truck import Truck

mapSymbols = \
{"^":["models/building_side1",   90, -1, 1, 1, 1,  0, 0, 0, 0 ],
 "%":["models/building_side2",    0, -1, 1, 1, 1,  0, 0, 0, 0 ],
 "[":["models/building_side1",  180,  0, 0, 0 ,0, -1,-1,-1, 1 ],
 "{":["models/building_side2",   90,  0, 0, 0, 0, -1,-1,-1, 1 ],
 "_":["models/building_side1",  270, -1, 1,-1,-1,  0, 0, 0, 0 ],
 "=":["models/building_side2",  180, -1, 1,-1,-1,  0, 0, 0, 0 ],
 "]":["models/building_side1",    0,  0, 0, 0, 0,  1, 1,-1, 1 ],
 "}":["models/building_side2",  270,  0, 0, 0, 0,  1, 1,-1, 1 ],
 "+":["models/building_corner",  90, -1, 1, 1, 1, -1,-1, 1,-1 ],
 "|":["models/building_corner", 180, -1, 1,-1,-1, -1,-1,-1, 1 ],
 "#":["models/building_corner", 270, -1, 1,-1,-1,  1, 1,-1, 1 ],
 "-":["models/building_corner",   0, -1, 1, 1, 1,  1, 1,-1, 1 ],
 "*":["models/building_roof",     0,  0, 0, 0, 0, 0, 0, 0, 0 ],     
 ">":["models/road",             90,  0, 0, 0, 0, 0, 0, 0, 0 ],
 "<":["models/road",            270,  0, 0, 0, 0, 0, 0, 0, 0 ],
 "/":["models/road",              0,  0, 0, 0, 0, 0, 0, 0, 0 ],
 "\\":["models/road",           180,  0, 0, 0, 0, 0, 0, 0, 0 ],
 }

baddieSymbols = \
{"s":StationaryBaddie,
 "r":RightTurnBaddie,
 "l":LeftTurnBaddie,
 "b":BouncingBaddie}

class Map:
    def __init__(self,world):
        self.world = world
        self.tileWallMap = []
        self.name = ""

    def getName(self):
        return self.name
        
    def load(self,head,mapPath):
        scale = 2
        fp = open(mapPath,"rb")
        bytes = fp.read()
        fp.close()
        lines = bytes.split("\n")

        try:
            read_text = lines[0]
            read_text = lines[0].strip().split(":")
            self.name = read_text[0]
            num_col = int(read_text[1])
            num_row = int(read_text[2])
            num_baddies = int(read_text[3])
            tileWallMap = [[ None for r in xrange(num_row)] for c in xrange(num_col)]
        except Exception, err:
            raise IOError, "Could not interpret map description line: %s" % repr(lines[0])

        try:
            read_text = lines[1]
            goal_tile = [int(x) for x in read_text.strip().split(":")]
        except Exception, err:
            raise IOError, "Could not interpret goal information: %s" % repr(lines[1])

        try:
            read_text = lines[2]
            read_text = read_text.strip().split(":")
            truckStart  = [int(x) for x in read_text]
            truckPosition = self.getTilePos(truckStart[0],truckStart[1])
            truck = Truck(self.world,head,
                          truckStart[0],truckStart[1],
                          truckStart[2])
        except Exception, err:
            raise IOError, "Could not interpret truch start info: %s" % repr(lines[2])

        Baddie.resetIds()
        baddies = []
        self.baddiesStart = []
        for i in xrange(num_baddies):
            try:
                read_text = lines[3+i]
                baddie_start = read_text.strip().split(":")
                baddie = baddieSymbols[baddie_start[3]](self.world,head,
                                                             int(baddie_start[0]),
                                                             int(baddie_start[1]),
                                                             int(baddie_start[2]) )
                baddies.append(baddie)
            except Exception, err:
                raise IOError, "Could not interpret Baddie info: %s" % repr(read_text)

        lines = lines[3+num_baddies:]
        for row_index in xrange(num_row):
            line = lines[row_index]
            for col_index in xrange(num_col):
                tilePosition = self.getTilePos(col_index,row_index)

                c = line[col_index]
                try:
                    tile_info = mapSymbols[c]
                except KeyError:
                    print "%d:%d %s" % (row_index,col_index,repr(c))
                else:
                    #Load up the model for this tile
                    #and set it to render
                    model_path = tile_info[0]
                    rotation = tile_info[1]
                    tile = loader.loadModelCopy(model_path)
                    tile.setScale(scale)
                    tile.setPos(tilePosition)
                    tile.setH(rotation)
                    tile.reparentTo(head)
                    
                    #Setup collision solids for this tile
                    solid1_info = tile_info[2:6]
                    solid2_info = tile_info[6:10]
                    new_solids = []
                    tile_x = tilePosition.getX()
                    tile_y = tilePosition.getY()
                    
                    if sum(solid1_info) != 0:
                        solid_info = [scale*x for x in solid1_info]
                        new_solid = CollisionPolygon( Point3(tile_x+solid_info[0],tile_y+solid_info[2],0),
                                                      Point3(tile_x+solid_info[1],tile_y+solid_info[2],0),
                                                      Point3(tile_x+solid_info[1],tile_y+solid_info[3],1),
                                                      Point3(tile_x+solid_info[0],tile_y+solid_info[3],1) )
                        new_solids.append(new_solid)
                    if sum(solid2_info) != 0:
                        solid_info = [scale*x for x in solid2_info]
                        new_solid = CollisionPolygon( Point3(tile_x+solid_info[0],tile_y+solid_info[2],0),
                                                      Point3(tile_x+solid_info[1],tile_y+solid_info[2],1),
                                                      Point3(tile_x+solid_info[1],tile_y+solid_info[3],1),
                                                      Point3(tile_x+solid_info[0],tile_y+solid_info[3],0) )
                        new_solids.append(new_solid)
                    if len(new_solids):
                        solidNode = CollisionNode("tile solid %d:%d" % (col_index,row_index))
                        for solid in new_solids:
                            solidNode.addSolid(solid)
                        solidNode.setFromCollideMask(BitMask32(0x0))
                        solidNode.setIntoCollideMask(BitMask32(0x0))
                        head.attachNewNode(solidNode)
                        tileWallMap[col_index][row_index] = solidNode

                    if [col_index,row_index] == goal_tile:
                        goalNp = loader.loadModelCopy("models/goal")
                        goalNp.setTransparency(TransparencyAttrib.MAlpha)
                        goalNp.setColor(0,1,0,0.5)
                        goalNp.setScale(2*scale)
                        goalNp.setPos( Point3(tile_x,tile_y,0) )
                        goalNp.reparentTo(head)
                        goalCollisionNode = CollisionNode("goal")
                        goalCollisionNode.addSolid(CollisionSphere(0,0,0,0.5))
                        goalNp.attachNewNode(goalCollisionNode)
                        goalNp.setCollideMask(BitMask32(0x0))
                        goalCollisionNode.setFromCollideMask(BitMask32(0x0))
                        goalCollisionNode.setIntoCollideMask(BitMask32(0x1))

        mapCenter = Point3(2+4*(num_col/2),-1*(2+4*num_row/2),-0.25)
        sky = loader.loadModel("models/desertsky")
        sky.setPos(mapCenter)
        sky.setScale(0.25)
        sky.reparentTo(head)
        ground = loader.loadModel("models/ground")
        ground.setPos(mapCenter)
        ground.setScale(300)
        ground.reparentTo(head)

        self.tileWallMap = tileWallMap
        return (truck,baddies)

    def getTile(self,position):
        return( int(round((position.getX()-2.0)/4.0)), int(round((-1.0*(position.getY()+2.0))/4.0)) )
    
    def getTilePos(self,col_index,row_index):
        return Point3(2+4*col_index,-1*(2+4*row_index),0)

    def getTileWall(self,col_index,row_index):
        return self.tileWallMap[col_index][row_index]

    def getWalls(self,firstColumn,lastColumn,firstRow,lastRow):
        cols = [firstColumn+x for x in xrange(lastColumn-firstColumn+1)]
        rows = [firstRow+x for x in xrange(lastRow-firstRow+1)]
        walls = []
        for c in cols:
            if c < 0 or c >= len(self.tileWallMap):
                continue
            for r in rows:
                if r < 0 or r >= len(self.tileWallMap[0]):
                    continue
                wall = self.tileWallMap[c][r]
                if wall != None:
                    walls.append(wall)
        return walls    