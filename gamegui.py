#!/usr/bin/env python27
# -*-encoding:utf8;-*-
from __future__ import print_function

import sys
import math
import panda3d.core
import direct.showbase.ShowBase
import direct.gui.OnscreenText
import direct.task.Task
import direct.interval.LerpInterval
import direct.gui.DirectCheckButton
import gamearena


class IllegalMoveException(Exception):
    pass


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
        self.__chessboardTopCenter = self.render.attachNewNode("chessboardTopCenter")  # 定位棋盘顶面的中心位置
        self.__pieceRoot = self.__chessboardTopCenter.attachNewNode("pieceRoot")  # 虚拟根节点用于归纳棋子对象
        self.__chessboard = self.__defaultChessboard(self.__chessboardTopCenter, self.__pieceRoot)
        squares = self.__chessboard['squares']  # 后面会通过变量 squares[i] 查询 64 个棋盘方格空间位置并挂载全部棋子模型

        # 载入棋子模型
        white_piece_model = self.__selectChessPieceModelSytle('models/default')
        black_piece_model = self.__selectChessPieceModelSytle('models/default')
        name_order = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook']
        colors = {
            'WHITE': (1.000, 1.000, 1.000, 1),  # RGB color for WHITE pieces
            'BLACK': (0.150, 0.150, 0.150, 1),  # RGB color for BLACK pieces
        }

        # 利用 GameArena() 进行沙盘推演，是为了检查每个棋子的走法是否符合国际象棋规则
        self.arena = gamearena.GameArena(8, 8)
        unit_types_without_pawn = [
            ('king', gamearena.KingUnit),
            ('queen', gamearena.QueenUnit),
            ('rook', gamearena.RookUnit),
            ('knight', gamearena.KnightUnit),
            ('bishop', gamearena.BishopUnit),
        ]
        white_unit_type_list = dict(unit_types_without_pawn + [('pawn', gamearena.WhitePawnUnit)])
        black_unit_type_list = dict(unit_types_without_pawn + [('pawn', gamearena.BlackPawnUnit)])
        white_player = gamearena.GameArena.PlayerID(1)
        black_player = gamearena.GameArena.PlayerID(2)

        # 创建模型实例
        # 双方各 16 个棋子: 白棋棋子位于 _square[0]~[15], 黑棋位于 _square[48]~[63]
        pieces_sorted_by_square = [None] * 64
        piece_id_sorted_by_square = [0] * 64
        pieces_sorted_by_id = {}
        for i, name in zip(range(16), name_order + ['pawn'] * 8):
            # 实例化棋子的 3D 模型(初始定位到棋盘方格模型的上方)
            piece_holder = squares[i].attachNewNode("pieceInstanceHolder")
            piece_holder.setColor(colors['WHITE'])
            white_piece_model[name].instanceTo(piece_holder)
            # Arena 中的对应点位建立相同的棋子:
            point = (i % 8, i // 8)
            pid = self.arena.new_unit_recruited_by_player(white_player, point, white_unit_type_list[name])
            piece_id_sorted_by_square[i] = pid
            piece = CustomizedPiece(piece_holder, mask=panda3d.core.BitMask32.bit(1))
            piece.setTag('piece', str(pid))
            pieces_sorted_by_square[i] = piece
            pieces_sorted_by_id[pid] = piece
        for i, name in zip(range(64 - 16, 64), ['pawn'] * 8 + name_order):
            # 实例化棋子的 3D 模型(初始定位到棋盘方格模型的上方)
            piece_holder = squares[i].attachNewNode("pieceInstanceHolder")
            piece_holder.setColor(colors['BLACK'])
            piece_holder.setH(180)  # 转头180°让黑棋的马(或象)与白棋的马面对面
            black_piece_model[name].instanceTo(piece_holder)
            # Arena 中的对应点位建立相同的棋子:
            point = (i % 8, i // 8)
            pid = self.arena.new_unit_recruited_by_player(black_player, point, black_unit_type_list[name])
            piece_id_sorted_by_square[i] = pid
            piece = CustomizedPiece(piece_holder, mask=panda3d.core.BitMask32.bit(1))
            piece.setTag('piece', str(pid))
            pieces_sorted_by_square[i] = piece
            pieces_sorted_by_id[pid] = piece

        # 棋子模型与棋盘方格位置一一对应:
        # Usage: self.__pieceOnSquare[i], 其中: 0<=i<64. i=0 时代表棋盘 a1 格, i=63 时代表棋盘 h8 格
        self.__pieceOnSquare = pieces_sorted_by_square

        # 棋子模型与 Arena.UnitID 整数编号一一对应:
        # Usage: self.__pieces[piece_id]，其中: 1<=piece_id<=棋子总数N, piece_id!=0
        self.__pieces = pieces_sorted_by_id

        # Arena.UnitID 整数编号与棋盘方格位置一一对应:
        # Usage: self.__pidOnSquare[i], 其中: 0<=i<64. i=0 时代表棋盘 a1 格, i=63 时代表棋盘 h8 格
        self.__pidOnSquare = piece_id_sorted_by_square

        self.__graveyard = self.__defaultGraveyard()  # 初始化虚拟墓地空间用于容放被吃掉的棋子
        self.__pointingTo = 0  # 取值范围: 整数 0 表示当前没有鼠标指针指向的棋盘格子, 整数 1~64 表示鼠标指向 64 个棋盘方格之一
        self.__dragging = 0  # 取值范围: 整数 0 表示当前鼠标指针没有拖拽住棋盘格子上的棋子, 整数 1~64 表示正在拖拽, 被拖拽的棋子原位于 64 个棋盘方格之一
        self.__finger = self.__pieceRoot.attachNewNode('fingerTouching')  # 后面用于设定用户手指正在触摸的棋盘位置
        self.__mouse3 = None # 用于鼠标右键
        self.__hsymbol = 1
        # 注册回调函数
        self.taskMgr.add(self.mouseTask, 'MouseTask')
        self.accept('escape', sys.exit)  # 键盘 Esc 键
        self.accept("mouse1", self.onMouse1Pressed)  # left-click grabs a piece
        self.accept("mouse1-up", self.onMouse1Released)  # releasing places it
        self.accept("mouse3", self.onMouse3Pressed)
        self.accept("mouse3-up", self.onMouse3Released)
        # 可调整拍摄角度的摄像头:
        self.axisCameraPitching = self.render.attachNewNode("axisCameraPitching")  # 摄像机环绕原点运动轨道的轴心
        self.axisCameraPitching.setHpr(h=0, p=-45, r=0)  # 初始摄像头的角度是斜向下俯视 p=-45 度(假如 p=-90 度时则代表垂直俯视视角)
        self.camera.reparentTo(self.axisCameraPitching)
        self.camera.setPos(x=0, y=-15.0, z=0)
        self.accept('page_up', self.onKeyboardPageUpPressed)  # 键盘 Page Up / Page Down 调节俯仰角
        self.accept('page_down', self.onKeyboardPageDownPressed)  # 同上
        self.accept('wheel_up', self.onMouseWheelRolledUpwards)  # 鼠标滚轮实现镜头缩放
        self.accept('wheel_down', self.onMouseWheelRolledDownwards)  # 同上

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
            ,
            direct.gui.OnscreenText.OnscreenText(
                text="Mouse wheel: Zoom in/out the camera",
                parent=self.a2dTopLeft, align=panda3d.core.TextNode.ALeft,
                style=1, fg=(1, 1, 1, 1), pos=(0.06, -0.15), scale=.05)
            ,
            direct.gui.OnscreenText.OnscreenText(
                text="PageUp/PageDown: Camera orientation",
                parent=self.a2dTopLeft, align=panda3d.core.TextNode.ALeft,
                style=1, fg=(1, 1, 1, 1), pos=(0.06, -0.2), scale=.05)
        ]
        return labels

    def mouseTask(self, task):
        """mouseTask deals with the highlighting and dragging based on the mouse"""

        marks = self.__chessboard['marks']
        squareRoot = self.__chessboard['squareRoot']

        # First, clear the current highlight selected square
        if self.__pointingTo:
            i = self.__pointingTo - 1
            marks[i].setScale(0.75)
            if not self.__marksAlwaysVisible or not (i in self.__validMarks):
                # Erase current mark
                marks[i].hide()
            if self.__hasPieceOnSquare(i):
                self.__pieceOnSquare[i].hideBounds()
            self.__pointingTo = False

        # Check to see if we can access the mouse. We need its coordinates later
        if not self.mouseWatcherNode.hasMouse():
            # 当前某个时刻鼠标不可用
            return direct.task.Task.cont

        # get the mouse position
        mpos = self.mouseWatcherNode.getMouse()

        # Set the position of the ray based on the mouse position
        self.__pickerRay.setFromLens(self.camNode, mpos.getX(), mpos.getY())

        # 检查鼠标指针指向的棋盘水平面的点的坐标
        p = self.render.getRelativePoint(self.camera, self.__pickerRay.getOrigin())
        v = self.render.getRelativeVector(self.camera, self.__pickerRay.getDirection())
        z = 0
        t = - p.getZ() / v.getZ()  # t = (z - p.getZ()) / v.getZ() 其中 z = 0
        x = p.getX() + v.getX() * t
        y = p.getY() + v.getY() * t
        self.__finger.setPos(x, y, z)
        # 已知射线 pickerRay 的起点 p 和方向矢量 v, 这条射线与水平面 z=0 相交
        # 计算出交点的绝对坐标(x, y, h), 然后让玩家的手指(或手中握着的棋子)指向这个坐标
        # 【解析几何——三维空间交点坐标算法】
        # 已知:
        # 射线起点 P=(X,Y,Z)=(p.getX,p.getY,p.getZ)
        # 方向矢量 v=(U,V,W)=(v.getX,v.getY,v.getZ)
        # 求:射线线与水平面 z=0 的交点
        #
        # 直线(射线)方程组为
        #     x = X + U*t
        #     y = Y + V*t
        #     z = Z + W*t
        # 与 z = 0 联立, 消除变量 t 后, 得
        # x = X+u*t = X+U*(z-Z)/W = X-U*Z/W
        # y = Y+v*t = Y+V*(z-Z)/W = Y-V*Z/W
        # z = 0

        if self.__dragging:
            # 当前拖拽棋子的手指的正下方对应的棋盘格子
            i = self.__dragging - 1
            piece = self.__pieceOnSquare[i]
            piece.picker.traverse(squareRoot)  # 检查棋子正下方的格子编号
            if piece.handler.getNumEntries() > 0:
                # if we have hit something, sort the hits so that the closest is first, and make a mark
                piece.handler.sortEntries()
                entry = piece.handler.getEntry(0)
                tag = 'square'
                value = entry.getIntoNode().getTag(tag)
                i = int(value)
                self.__pointingTo = i + 1
        else:
            # Do the actual collision pass (Do it only on the squares for efficiency purposes)
            self.__picker.traverse(self.__pieceRoot)  # 检查鼠标指向哪个棋子
            if self.__handler.getNumEntries() > 0:
                self.__handler.sortEntries()
                entry = self.__handler.getEntry(0)
                tag = 'piece'
                value = entry.getIntoNode().getTag(tag)
                try:
                    piece_id = int(value)
                except ValueError:
                    pass  # Ignore this case
                else:
                    for i, pid in enumerate(self.__pidOnSquare):
                        if pid == piece_id:
                            self.__pointingTo = i + 1
                            break
            else:
                # Do the actual collision pass with squareRoot
                self.__picker.traverse(squareRoot)
                if self.__handler.getNumEntries() > 0:
                    # if we have hit something, sort the hits so that the closest is first, and make a mark
                    self.__handler.sortEntries()
                    entry = self.__handler.getEntry(0)
                    tag = 'square'
                    value = entry.getIntoNode().getTag(tag)
                    i = int(value)
                    self.__pointingTo = i + 1

        if self.__pointingTo:
            i = self.__pointingTo - 1
            if self.__dragging:
                marks[i].setScale(1.02)
                marks[i].show()
            if self.__hasPieceOnSquare(i):
                if not self.__dragging or (self.__dragging and self.__pointingTo != self.__dragging):
                    self.__pieceOnSquare[i].showBounds()
        if self.__mouse3:
            fold = 50
            h = self.__mouse3[2] + self.__hsymbol*fold*(self.__mouse3[0] - mpos.getX())
            p = self.__mouse3[3] - fold*(self.__mouse3[1] - mpos.getY())
            self.axisCameraPitching.setH(h)
            if p < 0 and p > -90:
                self.axisCameraPitching.setP(p)
            h_symbol =  1 if mpos.getY() <=0 else -1
            if h_symbol!=self.__hsymbol:
                self.__mouse3 = (mpos.getX(),mpos.getY(),self.axisCameraPitching.getH(),self.axisCameraPitching.getP())
                self.__hsymbol = h_symbol
        return direct.task.Task.cont

    def __defaultChessboard(self, chessboardTopCenter, pieceRoot):
        squareRoot = chessboardTopCenter.attachNewNode("squareRoot")

        white = (1, 1, 1, 1)
        black = (0.3, 0.3, 0.3, 1)
        colors = {1: white, 0: black}

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
        # Create 64 instances of the same mark
        self.__marksAlwaysVisible = True  # True 时让屏幕一直显示棋子的所有有效走法, 帮助用户分析
        self.__checkButton = direct.gui.DirectCheckButton.DirectCheckButton(
            pos=(1.0, 0.0, 0.85),
            scale=0.03,
            text_scale=2,
            text='Show Moves',
            borderWidth=(0.5, 0.5),
            pad=(0.5, 1),
            boxPlacement='left',
            boxImage=('models/maps/checkbox_unchecked.png', 'models/maps/checkbox_checked.png', None),
            indicatorValue=self.__marksAlwaysVisible,
            command=self.toggleChessboardMarksBehavior
        )
        self.__validMarks = set()  # 用于记录当前被拖拽中的棋子可以走到哪些方格, 0-63 自然数集合
        mark = self.loader.loadModel("models/square")
        mark.setTransparency(panda3d.core.TransparencyAttrib.MDual)
        marks = []
        for i in range(64):
            pos = MyChessboard.__squarePos(i)
            # Create instance for every square
            holder = chessboardTopCenter.attachNewNode("markInstanceHolder")
            mark.instanceTo(holder)
            pos.setZ(pos.getZ() + 1E-2)  # put these items above of the top of squares
            holder.setPos(pos)
            holder.setColor(MarkColor['UNACCEPTABLE_MOVE'])
            holder.setScale(0.75)
            holder.hide()
            marks.append(holder)
            # Create 64 fake squares(only for collision traversing)
            # 创建只包含空间定位信息的伪棋盘方格, 方便后面用执行碰撞检测时遍历所有棋子模型
            square = pieceRoot.attachNewNode("square")
            square.setPos(pos)
            squares.append(square)  # 现在列表容器中存储的内容只是代表棋盘方格位置的空节点了

        return {'squares': squares, 'marks': marks, 'squareRoot': squareRoot}

    def __hasPieceOnSquare(self, i):
        """检查编号为 i 的方格上当前是否有棋子

        :param i: 格子编号, 有效范围: 0<=i<64
        :rtype : bool
        """
        assert 0 <= i < 64
        return bool(self.__pieceOnSquare[i])

    def onMouse1Pressed(self):
        """鼠标左键被按下时

        Case A: 初始情况没有拖拽其他棋子，此时如果鼠标正指向棋盘上的方格并且方格上有棋子，按下鼠标左键将拖拽该棋子
        Case B: 第二种情况，如果正在拖拽某棋子，再次按住鼠标左键时需要判断是不是要更换选中其他棋子
        Case C: 鼠标左键如果重复第二次单击当前拖拽中的棋子原来所在的格子, 立即放下该棋子(放回被点击的这个格子)
        Case D: 单击的位置是棋盘之外的空白位置，根据是否正在拖拽中分两种情况处理
        """
        if not self.__pointingTo:  # See Case D
            if not self.__dragging:
                return
            # 否则取消当前选中的棋子
            i = self.__dragging - 1
            self.__pieceOnSquare[i].reparentTo(self.__chessboard['squares'][i])  # 把棋子重新定位到原来的格子
            self.__pieceOnSquare[i].setX(0)
            self.__pieceOnSquare[i].setY(0)
            self.__pieceOnSquare[i].stop('hovering')
            self.__pieceOnSquare[i].play('landing')
            self.__dragging = False
            if self.__marksAlwaysVisible:
                marks = self.__chessboard['marks']
                for i in self.__validMarks:
                    marks[i].hide()
            return

        # When we are pointing to the chessboard:
        if not self.__dragging:
            if self.__hasPieceOnSquare(self.__pointingTo - 1):  # See Case A
                self.__dragging = self.__pointingTo
                i = self.__dragging - 1
                squarePos = self.__chessboard['squares'][i].getPos()
                x = squarePos.getX() - self.__finger.getX()
                y = squarePos.getY() - self.__finger.getY()
                self.__pieceOnSquare[i].reparentTo(self.__finger)  # 抓起一个棋子i
                self.__pieceOnSquare[i].setPos(x, y, 0)
                self.__pieceOnSquare[i].play('hovering')
                destinations = mark_indexes_from_coordinates(
                    self.arena.retrieve_valid_moves_of_unit(unit_id=self.__pidOnSquare[i])
                )
                current = {i}
                previous = self.__validMarks
                self.__validMarks = set(destinations) | current
                marks = self.__chessboard['marks']
                marks[i].setColor(MarkColor['STARTING_POINT'])
                for tmp in previous - self.__validMarks:
                    marks[tmp].setColor(MarkColor['UNACCEPTABLE_MOVE'])
                for tmp in destinations:
                    marks[tmp].setColor(MarkColor['ACCEPTABLE_MOVE'])
                if self.__marksAlwaysVisible:
                    for tmp in self.__validMarks:
                        marks[tmp].show()
            return

        # When we are pointing to the chessboard and we know that we are dragging something already:
        if self.__pointingTo != self.__dragging:
            # See Case B
            # 检查能否选中另一个同颜色的棋子, 如果棋子颜色不同则不要更换
            i2 = self.__pointingTo - 1
            if self.__hasPieceOnSquare(i2):
                piece2_id = self.__pidOnSquare[i2]
                owner2 = self.arena.owner_of_unit(piece2_id)
                i1 = self.__dragging - 1
                piece1_id = self.__pidOnSquare[i1]
                owner1 = self.arena.owner_of_unit(piece1_id)
                if owner2 == owner1:  # 棋子颜色相同时, 才可以更换当前选中的棋子
                    k1 = self.__dragging - 1
                    self.__pieceOnSquare[k1].reparentTo(self.__chessboard['squares'][k1])  # 先把棋子 1 重新定位到它原来所在的格子
                    self.__pieceOnSquare[k1].setX(0)
                    self.__pieceOnSquare[k1].setY(0)
                    self.__pieceOnSquare[k1].stop('hovering')
                    self.__pieceOnSquare[k1].play('landing')
                    if self.__marksAlwaysVisible:
                        marks = self.__chessboard['marks']
                        for i in self.__validMarks:
                            marks[i].hide()
                    self.__dragging = self.__pointingTo
                    # 然后选中棋子 2
                    k2 = self.__dragging - 1
                    squarePos = self.__chessboard['squares'][k2].getPos()
                    x = squarePos.getX() - self.__finger.getX()
                    y = squarePos.getY() - self.__finger.getY()
                    self.__pieceOnSquare[k2].setPos(x, y, 0)
                    self.__pieceOnSquare[k2].play('hovering')
                    destinations = mark_indexes_from_coordinates(
                        self.arena.retrieve_valid_moves_of_unit(unit_id=self.__pidOnSquare[k2])
                    )
                    current = {k2}
                    previous = self.__validMarks
                    self.__validMarks = set(destinations) | current
                    marks = self.__chessboard['marks']
                    marks[k2].setColor(MarkColor['STARTING_POINT'])
                    for tmp in previous - self.__validMarks:
                        marks[tmp].setColor(MarkColor['UNACCEPTABLE_MOVE'])
                    for tmp in destinations:
                        marks[tmp].setColor(MarkColor['ACCEPTABLE_MOVE'])
                    if self.__marksAlwaysVisible:
                        for tmp in self.__validMarks:
                            marks[tmp].show()
            j = self.__dragging - 1
            self.__pieceOnSquare[j].reparentTo(self.__finger)  # 再抓起一个棋子j
            return

        # Finally, now
        #   1: We are pointing to the chessboard
        # and
        #   2: We are dragging something
        # but
        #   3: We are pressing the same square for a second time!
        # See Case C
        k = self.__dragging - 1
        self.__pieceOnSquare[k].reparentTo(self.__chessboard['squares'][k])
        self.__pieceOnSquare[k].setX(0)
        self.__pieceOnSquare[k].setY(0)
        self.__pieceOnSquare[k].stop('hovering')
        self.__pieceOnSquare[k].play('landing')
        self.__dragging = False
        if self.__marksAlwaysVisible:
            marks = self.__chessboard['marks']
            for i in self.__validMarks:
                marks[i].hide()
        return

    def onMouse1Released(self):
        """鼠标左键被松开时

        Case A: 试着将当前拖拽的棋子移动到新位置 (再根据棋子移动规则判定能否这么走)
        Case B: 当前没有被拖拽/被选中的棋子
        Case C: 如果这是“重复第二次单击当前拖拽中的棋子格子后又在当前格子松开鼠标左键”，则什么也不做
        Case D: 当前指针位置是棋盘之外的空白位置，松开鼠标左键时不做处理
        """
        if not self.__pointingTo:  # See Case D
            return

        if not self.__dragging:  # See Case B
            return

        # When we are pointing to the chessboard, and we has been dragging a piece:
        if self.__pointingTo != self.__dragging:
            try:  # try to drag this piece to the new place. See Case A
                self.__movePiece(self.__dragging - 1, self.__pointingTo - 1)
            except IllegalMoveException:
                pass
            else:
                self.__dragging = False
                if self.__marksAlwaysVisible:
                    marks = self.__chessboard['marks']
                    for i in self.__validMarks:
                        marks[i].hide()
            return

        # Finally, now
        #   1: We are pointing to the chessboard
        # and
        #   2: We has been dragging something
        # but
        #   3: We just release mouse1 while pointing to the same square for a second time!
        # So we don't need to do anything here. See Case C
        return

    def onMouse3Pressed(self):
        mpos = self.mouseWatcherNode.getMouse()
        # h_symbol is a symbol to decide the direction
        self.hsymbol = 1 if mpos.getY() <=0 else -1
        self.__mouse3 = (mpos.getX(),mpos.getY(),self.axisCameraPitching.getH(),self.axisCameraPitching.getP())

    def onMouse3Released(self):
        self.__mouse3 = None

    def __isLegalMove(self, fr, to):
        """

        :param fr: 取值范围0<=fr<64
        :param to: 取值范围0<=to<64
        """
        pid = self.__pidOnSquare[fr]
        if not pid:
            return False
        valid_moves = self.arena.retrieve_valid_moves_of_unit(pid)
        destination = gamearena.Square(x=to % 8, y=to // 8)
        return destination in valid_moves

    def __movePiece(self, fr, to):
        """

        :param fr: 取值范围0<=fr<64
        :param to: 取值范围0<=to<64
        """
        if to == fr:  # 原地不动
            return
        elif not self.__isLegalMove(fr, to):
            raise IllegalMoveException()

        piece1 = self.__pieceOnSquare[fr]
        piece2 = self.__pieceOnSquare[to]
        self.__pieceOnSquare[to] = piece1
        self.__pieceOnSquare[fr] = None  # 清除 piece1 之前的痕迹
        pid1 = self.__pidOnSquare[fr]
        pid2 = self.__pidOnSquare[to]  # 这里暂假设是棋子1吃棋子2的情况
        piece1 = self.__pieces[pid1]
        square2 = self.__chessboard['squares'][to]
        piece1.reparentTo(square2)
        piece1.setX(0)
        piece1.setY(0)
        piece1.stop('hovering')
        piece1.play('landing')
        self.__pidOnSquare[to] = pid1
        self.__pidOnSquare[fr] = 0  # 清除 piece_id1 之前的痕迹
        if pid2:
            # 把被吃掉的棋子送往墓地
            self.__sendToGraveyard(piece=piece2, gid=pid2)

        # 必须同步移动 Arena 中的棋子
        destination = gamearena.Square(x=to % 8, y=to // 8)
        self.arena.move_unit_to_somewhere(pid1, destination)

    def __sendToGraveyard(self, piece, gid):
        grave = self.__graveyard['graves'][gid]
        piece.reparentTo(grave)
        piece.setX(0)
        piece.setY(0)
        piece.stop('hovering')
        piece.play('landing')
        piece.hideBounds()

    def __defaultGraveyard(self):
        """整个墓区
        for id in range(32) 的 32 个棋子各自预留一小块墓地, 每个棋子墓穴位置固定
        """
        # 8*8 棋盘理论上最多允许存在 64 枚棋子, 实际一套标准国际象棋为 32 枚棋子.
        # 另外 16 个小兵生变时只是更改棋子的外观, 不会增加额外的棋子.
        max_pieces = 32
        max_graves = max_pieces
        graves = {}
        graveyard = self.render.attachNewNode("graveyard")
        for i in range(max_graves):
            grave = graveyard.attachNewNode("grave")
            grave.reparentTo(graveyard)
            x = -4.5 if i < 16 else 4.5  # 右手边左手边分开两块墓地
            y = 0.4 * ((i % 16) - 7.5)
            grave.setPos(x, y, 0)
            grave.setScale(0.75)
            gid = i + 1
            graves[gid] = grave  # 让 graves[] 的下标 gid 从 1 开始
        return {'graves': graves, 'graveyard': graveyard}

    def __selectChessPieceModelSytle(self, path='models/default'):
        """查找载入路径 path 指定风格样式的棋子模型套件"""
        # Models:
        king = self.loader.loadModel("{}/king".format(path))
        queen = self.loader.loadModel("{}/queen".format(path))
        rook = self.loader.loadModel("{}/rook".format(path))
        knight = self.loader.loadModel("{}/knight".format(path))
        bishop = self.loader.loadModel("{}/bishop".format(path))
        pawn = self.loader.loadModel("{}/pawn".format(path))
        # Actors
        king_actor = None
        queen_actor = None
        rook_actor = None
        knight_actor = None
        bishop_actor = None
        pawn_actor = None
        # # TODO: 为棋子添加动画效果
        # # 可以用 self.__have_animations = True 或 False 进行设置
        # if self.__have_animations:
        #     import direct.actor.Actor
        #     king_actor = direct.actor.Actor.Actor("{}/king".format(style), anims=None)
        #     queen_actor = direct.actor.Actor.Actor("{}/queen".format(style), anims=None)
        #     rook_actor = direct.actor.Actor.Actor("{}/rook".format(style), anims=None)
        #     knight_actor = direct.actor.Actor.Actor("{}/knight".format(style), anims=None)
        #     bishop_actor = direct.actor.Actor.Actor("{}/bishop".format(style), anims=None)
        #     pawn_actor = direct.actor.Actor.Actor("{}/pawn".format(style), anims=None)
        return {
            'king': king,
            'queen': queen,
            'rook': rook,
            'knight': knight,
            'bishop': bishop,
            'pawn': pawn,
            'king_actor': king_actor,
            'queen_actor': queen_actor,
            'rook_actor': rook_actor,
            'knight_actor': knight_actor,
            'bishop_actor': bishop_actor,
            'pawn_actor': pawn_actor,
        }

    @staticmethod
    def __squarePos(i):
        """A handy little function for getting the proper position for a given square"""
        return panda3d.core.LPoint3((i % 8) - 3.5, (i // 8) - 3.5, 0)

    def onKeyboardPageUpPressed(self):
        delta = -14.5
        p = self.axisCameraPitching.getP() + delta
        if p + 10.0 < -90.0:  # p=-90 度时摄像机从顶端垂直向正下方俯视, 初始值 p=-45 度时向斜下方俯视
            return
        self.axisCameraPitching.setP(p)

    def onKeyboardPageDownPressed(self):
        delta = 14.5
        p = self.axisCameraPitching.getP() + delta
        if p - 10.0 > 0.0:  # p=0 度时摄像机为水平视角, 0<p<90 则代表从地平面下方向上仰视
            return
        self.axisCameraPitching.setP(p)

    def onMouseWheelRolledUpwards(self):
        scale = 1.04  # Zoom out
        y = self.camera.getY() * scale
        if math.fabs(y) > 25.0:
            return
        self.camera.setY(y)

    def onMouseWheelRolledDownwards(self):
        scale = 0.96  # Zoom in
        y = self.camera.getY() * scale
        if math.fabs(y) < 12.0:
            return
        self.camera.setY(y)

    def __makeMarksAlwaysVisible(self):
        self.__marksAlwaysVisible = True
        if self.__dragging:
            marks = self.__chessboard['marks']
            for i in self.__validMarks:
                marks[i].show()

    def __makeMarksVisibleOnlyWhenSquareIsPointed(self):
        self.__marksAlwaysVisible = False
        marks = self.__chessboard['marks']
        for i in self.__validMarks:
            marks[i].hide()

    def toggleChessboardMarksBehavior(self, isChecked):
        if isChecked:
            self.__makeMarksAlwaysVisible()
        else:
            self.__makeMarksVisibleOnlyWhenSquareIsPointed()


MarkColor = {
    'STARTING_POINT': panda3d.core.LVecBase4f(0.5, 0.5, 0.5, 0.25),
    'ACCEPTABLE_MOVE': panda3d.core.LVecBase4f(0, 1, 1, 0.75),
    'UNACCEPTABLE_MOVE': panda3d.core.LVecBase4f(1, 0, 0, 0.25),
}


def mark_indexes_from_coordinates(coordinates):
    result = []
    for (x, y) in coordinates:
        result.append(x + 8 * y)
    return tuple(result)


class CustomizedPiece(object):
    def __init__(self, node_path, mask):
        self.__np = node_path
        b = node_path.getTightBounds()
        solid = panda3d.core.CollisionBox(b[0], b[1])
        self.__cb = panda3d.core.CollisionNode('pieceCollisionBox')
        self.__cb.addSolid(solid)
        self.__cb.setIntoCollideMask(mask)
        self.__box = node_path.attachNewNode(self.__cb)

        hovering_interval = direct.interval.LerpInterval.LerpFunc(
            self._vertical_oscillating_motion,  # function to call
            duration=0.4,  # duration (in seconds)
            fromData=0,  # starting value (in radians)
            toData=math.pi,  # ending value
            # Additional information to pass to self._osllicat
            extraArgs=[self.__np, 0.25]
        )
        landing_interval = direct.interval.LerpInterval.LerpFunc(
            self._vertical_oscillating_motion,  # function to call
            duration=0.125,  # duration (in seconds)
            fromData=-math.pi,  # starting value (in radians)
            toData=0,  # ending value
            # Additional information to pass to self._osllicat
            extraArgs=[self.__np, 0.25]
        )
        self.__animations = {
            'hovering': hovering_interval,
            'landing': landing_interval,
        }

        self.pickerRay = panda3d.core.CollisionRay()
        self.pickerRay.setOrigin(0.0, 0.0, 0.0)
        self.pickerRay.setDirection(0, 0, -1)
        self.collisionNode = panda3d.core.CollisionNode('pieceCollisionNode')
        self.collisionNode.setFromCollideMask(mask)  # 注意是碰撞源(From)
        self.collisionNode.setIntoCollideMask(panda3d.core.BitMask32.allOff())
        self.collisionNode.addSolid(self.pickerRay)
        self.collisionNP = self.__np.attachNewNode(self.collisionNode)
        self.collisionNP.setPos(0, 0, 0)
        self.picker = panda3d.core.CollisionTraverser()
        self.handler = panda3d.core.CollisionHandlerQueue()
        self.picker.addCollider(self.collisionNP, self.handler)

    @staticmethod
    def _vertical_oscillating_motion(rad, piece, height):
        """垂直方向上震荡往复运动

        :param rad: 弧度值
        :param piece: 棋子对象的 NodePath
        :param height: 运动轨迹顶点高度, 数值上等于振幅的两倍
        """
        wave_amplitude = height * 0.5
        piece.setZ(wave_amplitude * (1.0 - math.cos(rad)))

    def loop(self, animName, restart=True):
        try:
            interval = self.__animations[animName]
        except KeyError:
            pass
        else:
            if restart:
                interval.loop()  # restart from the beginning
            else:
                interval.resume()  # continue from last position

    def play(self, animName, restart=True):
        try:
            interval = self.__animations[animName]
        except KeyError:
            pass
        else:
            if restart:
                interval.start()  # start play from the beginning
            else:
                interval.resume()  # continue from last position

    def stop(self, animName=None):
        if not animName:
            for interval in self.__animations.values():
                interval.finish()
            return
        try:
            interval = self.__animations[animName]
        except KeyError:
            pass
        else:
            interval.finish()

    def pause(self, animName=None):
        intervals = self.__animations.values()
        if not animName:
            for interval in intervals:
                interval.pause()
        if animName in intervals:
            interval = self.__animations[animName]
            interval.pause()

    def setPos(self, *args, **kwargs):
        self.__np.setPos(*args, **kwargs)

    def setX(self, *args, **kwargs):
        self.__np.setX(*args, **kwargs)

    def setY(self, *args, **kwargs):
        self.__np.setY(*args, **kwargs)

    def setZ(self, *args, **kwargs):
        self.__np.setZ(*args, **kwargs)

    def setTag(self, tagName, tagValue):
        self.__cb.setTag(tagName, tagValue)

    def reparentTo(self, *args, **kwargs):
        self.__np.reparentTo(*args, **kwargs)

    def showBounds(self):
        self.__box.show()

    def hideBounds(self):
        self.__box.hide()


def main():
    # 创建背景光源
    ambientLight = panda3d.core.AmbientLight("ambientLight")
    ambientLight.setColor((.8, .8, .8, 1))
    # 创建直射光源
    directionalLight = panda3d.core.DirectionalLight("directionalLight")
    directionalLight.setDirection(panda3d.core.LVector3(0, 45, -45))
    directionalLight.setColor((0.2, 0.2, 0.2, 1))

    base = MyChessboard()
    base.render.setLight(base.render.attachNewNode(ambientLight))  # 设置光源
    base.render.setLight(base.render.attachNewNode(directionalLight))  # 设置光源
    base.run()


if '__main__' == __name__:
    main()
