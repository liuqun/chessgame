#!/usr/bin/env python27
# -*-encoding:utf8;-*-
from __future__ import print_function

import sys
import math
import panda3d.core
import direct.showbase.ShowBase
import direct.gui.OnscreenText
import direct.task.Task


class MyChessboard(direct.showbase.ShowBase.ShowBase):

    def __init__(self, fStartDirect=True, windowType=None):
        direct.showbase.ShowBase.ShowBase.__init__(self, fStartDirect=fStartDirect, windowType=windowType)
        self.disableMouse()
        # Since we are using collision detection to do picking, we set it up like
        # any other collision detection system with a traverser and a handler
        self.__picker = panda3d.core.CollisionTraverser()
        self.__handler = panda3d.core.CollisionHandlerQueue()
        # Make a collision node for our picker ray
        self.__pickerNode = panda3d.core.CollisionNode('mouseRay')
        # Attach that node to the camera since the ray will need to be positioned relative to it
        self.__pickerNP = self.camera.attachNewNode(self.__pickerNode)
        # Everything to be picked will use bit 1. This way if we were doing other collision we could separate it
        self.__pickerNode.setFromCollideMask(panda3d.core.BitMask32.bit(1))
        # Make our ray and add it to the collision node
        self.__pickerRay = panda3d.core.CollisionRay()
        self.__pickerNode.addSolid(self.__pickerRay)
        # Register the ray as something that can cause collisions
        self.__picker.addCollider(self.__pickerNP, self.__handler)

        self.__labels = self.__defaultLabels()
        self.__chessboard = self.__defaultChessboard()
        self.__pointingTo = 0  # 取值范围: 整数 0 表示当前没有鼠标指针指向的棋盘格子, 整数 1~64 表示鼠标指向 64 个棋盘方格之一
        self.camera.setPos(x=10.0 * math.sin(0), y=-10.0 * math.cos(0), z=10)
        self.camera.setHpr(h=0, p=-45, r=0)
        # 注册回调函数
        self.taskMgr.add(self.mouseTask, 'MouseTask')
        self.accept("mouse1", self.grabPiece)  # left-click grabs a piece
        self.accept("mouse1-up", self.releasePiece)  # releasing places it
        self.accept('escape', sys.exit)  # 键盘 Esc 键

    def __defaultLabels(self):
        labels = [
            direct.gui.OnscreenText.OnscreenText(
                text="Powered by Panda3D",
                parent=self.a2dBottomRight, align=panda3d.core.TextNode.A_right,
                style=1, fg=(1, 1, 1, 1), pos=(-0.1, 0.1), scale=.07)
            ,
            direct.gui.OnscreenText.OnscreenText(
                text="ESC: Quit",
                parent=self.a2dTopLeft, align=panda3d.core.TextNode.ALeft,
                style=1, fg=(1, 1, 1, 1), pos=(0.06, -0.1), scale=.05)
        ]
        return labels

    def mouseTask(self, task):
        """mouseTask deals with the highlighting and dragging based on the mouse"""

        marks = self.__chessboard['marks']
        squareRoot = self.__chessboard['squareRoot']

        # First, clear the current highlight selected square
        if self.__pointingTo:
            i = self.__pointingTo - 1
            # Erase current mark
            marks[i].hide()
            self.__pointingTo = False

        # Check to see if we can access the mouse. We need its coordinates later
        if not self.mouseWatcherNode.hasMouse():
            # 当前某个时刻鼠标不可用
            return direct.task.Task.cont

        # get the mouse position
        mpos = self.mouseWatcherNode.getMouse()

        # Set the position of the ray based on the mouse position
        self.__pickerRay.setFromLens(self.camNode, mpos.getX(), mpos.getY())

        # Do the actual collision pass (Do it only on the squares for efficiency purposes)
        self.__picker.traverse(squareRoot)
        if self.__handler.getNumEntries() > 0:
            # if we have hit something, sort the hits so that the closest is first, and make a mark
            self.__handler.sortEntries()
            i = int(self.__handler.getEntry(0).getIntoNode().getTag('square'))
            marks[i].show()
            self.__pointingTo = i + 1

        return direct.task.Task.cont

    def __defaultChessboard(self):
        squareRoot = self.render.attachNewNode("squareRoot")
        white = (1, 1, 1, 1)
        black = (0.3, 0.3, 0.3, 1)
        colors = {0: white, 1: black}

        # For each square
        squares = []
        for i in range(64):
            row = i // 8
            color = colors[(row + i) % 2]  # “行数”+“列数”之和的奇偶决定棋盘方格颜色
            # Load, parent, color, and position the model (a single square polygon)
            square = self.loader.loadModel("models/square")
            square.setColor(color)
            square.reparentTo(squareRoot)
            square.setPos(MyChessboard.__squarePos(i))
            # Set the model itself to be collideable with the ray. If this model was
            # any more complex than a single polygon, you should set up a collision
            # sphere around it instead. But for single polygons this works fine.
            square.find("**/polygon").node().setIntoCollideMask(panda3d.core.BitMask32.bit(1))
            # Set a tag on the square's node so we can look up what square this is
            # later during the collision pass
            square.find("**/polygon").node().setTag('square', str(i))
            squares.append(square)
        # Create 64 instances of the same mark
        mark = self.loader.loadModel("models/square")
        mark.setScale(1.02)
        mark.setColor(0, 1, 1)
        marks = []
        for i in range(64):
            # Create instance for every square
            holder = squares[i].attachNewNode("markInstanceHolder")
            mark.instanceTo(holder)
            holder.setPos(0, 0, 1E-2)  # put marks on top of the squares
            holder.hide()
            marks.append(holder)
        return {'squares': squares, 'marks': marks, 'squareRoot': squareRoot}

    @staticmethod
    def __squarePos(i):
        """A handy little function for getting the proper position for a given square1"""
        return panda3d.core.LPoint3((i % 8) - 3.5, (i // 8) - 3.5, 0)

    def grabPiece(self):
        pass  # TODO

    def releasePiece(self):
        pass  # TODO


def main():
    base = MyChessboard()
    base.run()


if '__main__' == __name__:
    main()
