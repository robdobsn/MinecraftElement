# Rhino3D Python Script to create a Minecraft Block of an Element using laser cutting
# Rob Dobson 2014
import rhinoscriptsyntax as rs
import Rhino
import System
import scriptcontext

# Settings 
clearBeforeDrawing = True
numPix = 16                 # pixels along each side of minecraft block
widthOfLaserCutMm = 0.15    # width of laser cut - this will take some experimentation to get just right
                            # each piece cut out will be smaller than designed because each cut the laser
                            # makes has a width
pixMm = 5                   # size of each pixel (they are square)
numSides = 4                # number of sides to each face
cutSpacingMm = 2            # spacing between pieces when laid out for cutting
elementCoreColour = "O"     # Colour of the core of the block
elementTopColour = "R"      # Colour of the top face of the block
numFaces = 5                # Faces are indexed 0..3 for the 4 vertical sides and 4 for the top face
sheetsOrigin = ( 200,0,0 )  # To move perspex sheet location away from origin
sheetSize = (680, 600 )     # Size of perspex sheet that fits in my laser cutter (mm)

# The definition of the element
# Each character represents a colour of a pixel
# All faces are based on this definition - it is mirrored for alternate faces
# around the sides to ensure continuity of colour
# The top face is further processed to ensure colours of edge pixels (which are
# shared with the side faces) are consistent
elementDefinition = [   "RROOYYOYXYORRRRR",
                        "RROOROYXYOORRRRR",
                        "OROOROYXYOOROROO",
                        "OOORROYXXYOROOOO",
                        "OROORROYXYORROYX",
                        "OOOORRROOORROOYX",
                        "OYXYOORRRRROROYX",
                        "OYXOORROOROOOOXY",
                        "OYXYORRROYXYOYXY",
                        "ROYYOORROYXYOYOO",
                        "OYXYORRROYYOOOOO",
                        "YXXYOORRROROOYOY",
                        "YXYORRROOORRROOY",
                        "OOORRORRRRRRROOO",
                        "RRRROOORROOORRRR",
                        "RRROOOROYOORRRRR" ]

def InitLayer(layerName, colour):
    if layerName in rs.LayerNames():
        rs.DeleteLayer(layerName)
    rs.AddLayer(layerName, colour)
    
def GetPixColour(elementDef, levelNum, faceIdx, pix):
    faceIdx = faceIdx if faceIdx < numSides else 0
    pixIdx = pix if (faceIdx == 0 or faceIdx == 2 or faceIdx == 4) else numPix - pix - 1
    pixColour = elementDef[numPix-levelNum-1][pixIdx]
    return pixColour
    
def GetPixOrigin(origin, vectors, iPix, jPix):
    pixOrigin = rs.VectorAdd(origin, rs.VectorScale(vectors[0], pixMm * iPix))
    pixOrigin = rs.VectorAdd(pixOrigin, rs.VectorScale(vectors[2], pixMm * jPix))
    return pixOrigin
    
def AssignToLayer(geom, colourChar, forVisualisation = False):
    layerName = "Cut" + colourChar
    if forVisualisation:
        layerName = "Visual" + colourChar
    if layerName in rs.LayerNames():
        if geom is not None:
            rs.ObjectLayer(geom, layerName)

# Utility function to add vectors using a direction string "F" = Forward,
# "B" = Back, "I" = In, "O" = Out and "M" is a modifier to say move instead
# of draw a line (e.g. "MI" = Move In)
def AddVecs(p1, vecStr, unitVecs, lines, sideLen, sideWidth):
    vecOpMove = False
    for vecCh in vecStr:
        if vecCh == "M":
            vecOpMove = True
            continue
        elif vecCh == "F":
            vecDir = unitVecs[0]
            vecLen = sideLen
        elif vecCh == "B":
            vecDir = unitVecs[1]
            vecLen = sideLen
        elif vecCh == "I":
            vecDir = unitVecs[2]
            vecLen = sideWidth
        else:
            vecDir = unitVecs[3]
            vecLen = sideWidth
        p2 = rs.VectorAdd(p1, rs.VectorScale(vecDir, vecLen))
        if not vecOpMove:
            lines.append(rs.AddLine(p1, p2))
        p1 = p2
        vecOpMove = False
    return p1

# We may need to patch up the colours of the top face to ensure that the colours around
# the edge of the top face match up with the edges that they coincide with    
def CreateTopFaceColours(elementDef):
    # Create a copy of the element definition
    topColours = [row[:] for row in elementDef]
    # Go round fixing up the colours of the edge pieces based on the colour of the side adjacent
    topColours[0] = elementDef[0][::-1]
    topColours[numPix-1] = elementDef[0]
    for y in range(1, numPix-1):
        topColours[y] = elementDef[0][numPix-y-1] + elementDef[y][1:numPix-1] + elementDef[0][y]
    return topColours
    
# The core cutting curve is the one for each level of the block which cuts the core material so that
# what is left on the side faces of the block are gaps where different coloured pixels or shapes are 
# inserted
def CreateCoreCuttingGeom(levelOrigin, coreColour, elementDef, levelNum, outGeom):
    p1 = levelOrigin
    lines = []
    prevCut = False
    for side in range(0,numSides):
        for pix in range(1,numPix):
            pixColour = GetPixColour(elementDef, levelNum, side, pix)
            thisCut = (coreColour != pixColour)
            # Handle the corner
            if pix == numPix - 1:
                nextPixColour = GetPixColour(elementDef, levelNum, side+1, 1)
                nextCut = (coreColour != nextPixColour)
                case = 1 if nextCut else 0
                case += 2 if thisCut else 0
                case += 4 if prevCut else 0
                if case == 0:
                    p1 = AddVecs(p1, "FI", dirnVecs[side], lines, pixMm, pixMm)
                elif case == 1:
                    p1 = AddVecs(p1, "FIB", dirnVecs[side], lines, pixMm, pixMm)
                elif case == 2:
                    p1 = AddVecs(p1, "IF", dirnVecs[side], lines, pixMm, pixMm)
                elif case == 3:
                    p1 = AddVecs(p1, "I", dirnVecs[side], lines, pixMm, pixMm)
                elif case == 4:
                    p1 = AddVecs(p1, "OFI", dirnVecs[side], lines, pixMm, pixMm)
                elif case == 5:
                    p1 = AddVecs(p1, "OFIB", dirnVecs[side], lines, pixMm, pixMm)
                elif case == 6:
                    p1 = AddVecs(p1, "F", dirnVecs[side], lines, pixMm, pixMm)
                prevCut = nextCut
            else:
                if thisCut == prevCut:
                    p1 = AddVecs(p1, "F", dirnVecs[side], lines, pixMm, pixMm)
                elif thisCut:
                    if side == 0 and pix == 1:
                        p1 = AddVecs(p1, "MIF", dirnVecs[side], lines, pixMm, pixMm)
                    else:
                        p1 = AddVecs(p1, "IF", dirnVecs[side], lines, pixMm, pixMm)
                else:
                    p1 = AddVecs(p1, "OF", dirnVecs[side], lines, pixMm, pixMm)
                prevCut = thisCut
    if len(lines) > 0:
        # Create cutting curve
        baseLine = rs.JoinCurves(lines, True)
        # Don't add to cutting geometry for top layer - because it is cut differently
        if levelNum != numPix - 1:
            if not coreColour in outGeom:
                outGeom[coreColour] = []
            outGeom[coreColour].append(baseLine)
        AssignToLayer(baseLine, coreColour)
        # Visualise
        p2 = rs.VectorAdd(levelOrigin, rs.VectorScale(zvector,pixMm))
        for curve in baseLine:
            baseSurf = rs.ExtrudeCurveStraight(curve, levelOrigin, p2)
            AssignToLayer(baseSurf, coreColour, True)

# Draw the block's core (all levels)
def DrawBlockCore(origin, elementDef, elementCoreColour, zincrement, coreCutGeom):
    for levelIdx in range(0,numPix):
        coreCutGeom.append({})
        levelOrigin = rs.VectorAdd(origin, rs.VectorScale(zincrement, levelIdx*pixMm))
        CreateCoreCuttingGeom(rs.VectorAdd(levelOrigin, rs.VectorScale(xvector,pixMm)), elementCoreColour, elementDef, levelIdx, coreCutGeom[levelIdx])
                
# This method draws the cutting outline for each colour on a face of the block
# This is done by tracing out the outline of an area of pixels of a specific colour
# and leaving cutting curves only around the edges of the area
def DrawBlockFaces(origin, faceColours, coreColour, outputGeom):
    faceOrigins = [
        origin,
        rs.VectorAdd(rs.VectorAdd(origin, rs.VectorScale(xvector, pixMm * numPix)), rs.VectorScale(yvector, pixMm * numPix)),
        rs.VectorAdd(rs.VectorAdd(origin, rs.VectorScale(xvector, pixMm * numPix)), rs.VectorScale(yvector, pixMm * numPix)),
        origin,
        rs.VectorAdd(origin, rs.VectorScale(zvector, pixMm * numPix))
    ]
    faceVectors = [
        [ zvector, zmvector, xvector, xmvector, yvector, ymvector ],
        [ zvector, zmvector, ymvector, yvector, xmvector, xvector ],
        [ zvector, zmvector, xmvector, xvector, ymvector, yvector ],
        [ zvector, zmvector, yvector, ymvector, xvector, xmvector ],
        [ xvector, xmvector, yvector, ymvector, zmvector, zvector ]
    ]
    for faceIdx in range(len(faceVectors)):
        jPixStart = 0
        jPixEnd = numPix
        iPixStart = 0
        iPixEnd = numPix-1 if faceIdx != 4 else numPix
        if faceIdx == 1 or faceIdx == 3:
            jPixStart = 1
            jPixEnd = numPix-1
        sheetGeom = {}
        for iPix in range(iPixStart,iPixEnd):
            for jPix in range(jPixStart,jPixEnd):
                pixColour = GetPixColour(faceColours[faceIdx], iPix, 0, jPix)
                pixOrigin = GetPixOrigin(faceOrigins[faceIdx], faceVectors[faceIdx], iPix, jPix)
                boundStr = ""
                # Get colours of pix to left, right, above and below
                lColr = "" if iPix <= iPixStart else GetPixColour(faceColours[faceIdx], iPix-1, 0, jPix)
                rColr = "" if iPix >= iPixEnd-1 else GetPixColour(faceColours[faceIdx], iPix+1, 0, jPix)
                dColr = "" if jPix <= jPixStart else GetPixColour(faceColours[faceIdx], iPix, 0, jPix-1)
                uColr = "" if jPix >= jPixEnd-1 else GetPixColour(faceColours[faceIdx], iPix, 0, jPix+1)
                # Handle cut lines at each boundary
                if lColr != pixColour:
                    boundStr += "IMO"
                if rColr != pixColour:
                    boundStr += "MFIMOMB"
                if dColr != pixColour:
                    boundStr += "FMB"
                if uColr != pixColour:
                    boundStr += "MIFMBMO"
                if len(boundStr) > 0:
                    if not pixColour in sheetGeom:
                        sheetGeom[pixColour] = []
                    lines = sheetGeom[pixColour]
                    AddVecs(pixOrigin, boundStr, faceVectors[faceIdx], lines, pixMm, pixMm)
        
        # Form cutting curves
        linesGeom = {}
        for keyColour in sheetGeom:
            if (keyColour != coreColour) or (faceIdx == 4):
                lines = sheetGeom[keyColour]
                if len(lines) > 0:
                    cutLines = rs.JoinCurves(lines, True)
                    resizedLines = []
                    for cutLine in cutLines:
                        resizedLine = rs.OffsetCurve(cutLine, xmvector, widthOfLaserCutMm / 2) 
                        #resizedLine = cutLine
                        resizedLines.append(resizedLine)
                    if not keyColour in linesGeom:
                        linesGeom[keyColour] = []
                    linesGeom[keyColour].append(resizedLines)
                    AssignToLayer(resizedLines, keyColour)
        outputGeom.append(linesGeom)

        # Visualise
        faceGeom = linesGeom
        for keyColour in faceGeom:
            for curve in faceGeom[keyColour]:
                surfGeom = rs.AddPlanarSrf(curve)
                AssignToLayer(surfGeom, keyColour, True)
                for surf in surfGeom:
                    surfNorm = rs.SurfaceNormal(surf, [0,0,0])
                    solidGeom = rs.ExtrudeSurface(surf, rs.AddLine([0,0,0], rs.VectorScale(faceVectors[faceIdx][4], pixMm)), True)
                    AssignToLayer(solidGeom, keyColour, True)

    # Move lines to cutting plane
    for faceIdx in range(len(outputGeom)):
        for keyColour in outputGeom[faceIdx]:
            for curve in outputGeom[faceIdx][keyColour]:
                if faceIdx != 4:
                    rs.RotateObject(curve, GetPixOrigin(faceOrigins[faceIdx], faceVectors[faceIdx], 0, 0), -90, faceVectors[faceIdx][2])
                else:
                    rs.MoveObject(curve, rs.VectorScale(zmvector, pixMm * numPix))

# Layout cutting curve
def LayoutCuttingCurve(curveList, key, sheetOrigins, sheetCurPos, sheetSize):
    if not key in sheetCurPos:
        sheetCurPos[key] = [ 0, 0, 0 ]
    curX = sheetCurPos[key][0]
    curY = sheetCurPos[key][1]
    maxPartHeight = sheetCurPos[key][2]
    sheetOrigin = sheetOrigins[key]
    for curve in curveList:
        bounds = rs.BoundingBox(curve)
        basePt = bounds[0]
        endPt = bounds[3]
        if abs(bounds[2][0]) > abs(bounds[3][0]):
            endPt = bounds[2]
        if curX+abs(endPt[0])+cutSpacingMm > sheetSize[0]:
            curX = 0
            curY = maxPartHeight+cutSpacingMm
        rs.MoveObject(curve, [  sheetOrigin[0]+curX-basePt[0],
                                sheetOrigin[1]+curY-basePt[1],
                                sheetOrigin[2]+0-basePt[2] ])
        curX = curX + abs(endPt[0]) + cutSpacingMm
        if maxPartHeight < curY + endPt[1]:
            maxPartHeight = curY + endPt[1]
    sheetCurPos[key] = [curX, curY, maxPartHeight]
    
# Organise the cutting curves for all pieces
def OrganiseCuttingLayers(coreCutGeom, cutoutGeom, sheetOrigins, sheetSize):
    # Layout the core cutting curves    
    sheetCurPos = {}
    for levelIdx in range(0, len(coreCutGeom)):
        for key in coreCutGeom[levelIdx]:
            curveList = coreCutGeom[levelIdx][key]
            LayoutCuttingCurve(curveList, key, sheetOrigins, sheetCurPos, sheetSize)
    # Compile information on cutout parts
    cutoutSizes = {}
    for levelIdx in range(0, len(cutoutGeom)):
        for key in cutoutGeom[levelIdx]:
            curveList = cutoutGeom[levelIdx][key]
            LayoutCuttingCurve(curveList, key, sheetOrigins, sheetCurPos, sheetSize)
            

# Main program starts here
rs.EnableRedraw(False)
if clearBeforeDrawing:
    rs.Command("selall")
    rs.Command("delete")
# Vectors and locations
origin = Rhino.Geometry.Point3d(0,0,0)
xvector = Rhino.Geometry.Vector3d(1,0,0)
xmvector = Rhino.Geometry.Vector3d(-1,0,0)
yvector = Rhino.Geometry.Vector3d(0,1,0)
ymvector = Rhino.Geometry.Vector3d(0,-1,0)
zvector = Rhino.Geometry.Vector3d(0,0,1)
zmvector = Rhino.Geometry.Vector3d(0,0,-1)
dirnVecs = [ 
        [ xvector, xmvector, yvector, ymvector ],
        [ yvector, ymvector, xmvector, xvector ],
        [ xmvector, xvector, ymvector, yvector ],
        [ ymvector, yvector, xvector, xmvector ]
        ]
# Layer management in Rhino
InitLayer("VisualR", (255,0,0))
InitLayer("VisualO", (255,119,0))
InitLayer("VisualY", (200,200,0))
InitLayer("VisualX", (255,255,0))
InitLayer("CutR", (255,0,0))
InitLayer("CutO", (255,119,0))
InitLayer("CutY", (200,200,0))
InitLayer("CutX", (255,255,0))
# Sheet layout
sheetOrigins = {}
sheetOrigins['R'] = [ sheetsOrigin[0], sheetsOrigin[1], sheetsOrigin[2] ]
sheetOrigins['O'] = [ sheetsOrigin[0]+sheetSize[0]+cutSpacingMm, sheetsOrigin[1], sheetsOrigin[2] ] 
sheetOrigins['Y'] = [ sheetsOrigin[0]+(sheetSize[0]+cutSpacingMm)*2, sheetsOrigin[1], sheetsOrigin[2] ]
sheetOrigins['X'] = [ sheetsOrigin[0]+(sheetSize[0]+cutSpacingMm)*3, sheetsOrigin[1], sheetsOrigin[2] ]
# Define the block faces
faceColours = [
    elementDefinition,
    elementDefinition,
    elementDefinition,
    elementDefinition,
    CreateTopFaceColours(elementDefinition)
]
# Start the process of creating the block - draw the core layers
coreCutGeom = []
DrawBlockCore(origin, elementDefinition, elementCoreColour, zvector, coreCutGeom)
# Create the geometry for each face
faceCutGeom = []
topLayerOrigin = rs.VectorAdd(origin, rs.VectorScale(zvector, pixMm * numPix))
DrawBlockFaces(origin, faceColours, elementCoreColour, faceCutGeom)
# Move the cutting curves into positon on the perspex sheets
OrganiseCuttingLayers(coreCutGeom, faceCutGeom, sheetOrigins, sheetSize)
# All done
rs.EnableRedraw(True)
