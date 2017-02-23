#!/usr/bin/env python27
# -*-encoding:utf8;-*-
from __future__ import print_function

import sys
import math
import panda3d.core
import direct.showbase.ShowBase
import direct.gui.OnscreenText
import direct.task.Task
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
        self.__chessboard = self.__defaultChessboard()
        squares = self.__chessboard['squares']  # 后面会通过变量 squares[i] 访问 64 个棋盘方格

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
            pieces_sorted_by_square[i] = piece_holder
            # Arena 中的对应点位建立相同的棋子:
            point = (i % 8, i // 8)
            pid = self.arena.new_unit_recruited_by_player(white_player, point, white_unit_type_list[name])
            pieces_sorted_by_id[pid] = pieces_sorted_by_square[i]
            piece_id_sorted_by_square[i] = pid
        for i, name in zip(range(64 - 16, 64), ['pawn'] * 8 + name_order):
            # 实例化棋子的 3D 模型(初始定位到棋盘方格模型的上方)
            piece_holder = squares[i].attachNewNode("pieceInstanceHolder")
            piece_holder.setColor(colors['BLACK'])
            piece_holder.setH(180)  # 转头180°让黑棋的马(或象)与白棋的马面对面
            black_piece_model[name].instanceTo(piece_holder)
            pieces_sorted_by_square[i] = piece_holder
            # Arena 中的对应点位建立相同的棋子:
            point = (i % 8, i // 8)
            pid = self.arena.new_unit_recruited_by_player(black_player, point, black_unit_type_list[name])
            pieces_sorted_by_id[pid] = pieces_sorted_by_square[i]
            piece_id_sorted_by_square[i] = pid

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
        self.__finger = self.render.attachNewNode("fingerTouching")  # 后面用于设定用户手指正在触摸的棋盘位置
        # 注册回调函数
        self.taskMgr.add(self.mouseTask, 'MouseTask')
        self.accept('escape', sys.exit)  # 键盘 Esc 键
        self.accept("mouse1", self.onMouse1Pressed)  # left-click grabs a piece
        self.accept("mouse1-up", self.onMouse1Released)  # releasing places it
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
        if self.__dragging:
            p = self.render.getRelativePoint(self.camera, self.__pickerRay.getOrigin())
            v = self.render.getRelativeVector(self.camera, self.__pickerRay.getDirection())
            h = 0.5
            t = (h - p.getZ()) / v.getZ()
            x = p.getX() + v.getX() * t
            y = p.getY() + v.getY() * t
            # 将摄像机与鼠标指针两点连线, 再延长, 直线与棋盘平面上方高度 z=H 的水平面相交
            # 需要计算出交点的绝对坐标(x, y, h), 因为此时握住棋子的手指正处于在这个坐标
            self.__finger.setPos(x, y, h)
            # 【备注】
            # 已知直线的起点为 P=(X0,Y0,Z0), 方向矢量为 V=(u,v,w), 水平面方程为 z=H
            # 求直线与水平面的交点:
            # 直线方程组
            #     x = X0 + u*t
            #     y = Y0 + v*t
            #     z = Z0 + w*t
            # 与 z=h 联立, 消除变量 t 后
            # x = X1+u*t = X1+u*(h-Z1)/w
            # y = Y1+v*t = Y1+v*(h-Z1)/w
            # z = H

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
            self.__dragging = False
            return

        # When we are pointing to the chessboard:
        if not self.__dragging:
            if self.__hasPieceOnSquare(self.__pointingTo - 1):  # See Case A
                self.__dragging = self.__pointingTo
                i = self.__dragging - 1
                self.__pieceOnSquare[i].reparentTo(self.__finger)  # 抓起一个棋子i
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
                    k = self.__dragging - 1
                    self.__pieceOnSquare[k].reparentTo(self.__chessboard['squares'][k])  # 先把棋子k重新定位到原来的格子
                    self.__dragging = self.__pointingTo
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
        self.__dragging = False
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
            return

        # Finally, now
        #   1: We are pointing to the chessboard
        # and
        #   2: We has been dragging something
        # but
        #   3: We just release mouse1 while pointing to the same square for a second time!
        # So we don't need to do anything here. See Case C
        return

    def __isLegalMove(self, fr, to):
        """

        :param fr: 取值范围0<=fr<64
        :param to: 取值范围0<=to<64
        """
        pid = self.__pidOnSquare[fr]
        if not pid:
            return False
        valid_moves = self.arena.retrieve_valid_moves_of_unit(pid)
        destination = gamearena.Square(x=to%8, y=to//8)
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
        self.__pidOnSquare[to] = pid1
        self.__pidOnSquare[fr] = 0  # 清除 piece_id1 之前的痕迹
        if pid2:
            # 把被吃掉的棋子送往墓地
            self.__sendToGraveyard(pid2)

        # 必须同步移动 Arena 中的棋子
        destination = gamearena.Square(x=to%8, y=to//8)
        self.arena.move_unit_to_somewhere(pid1, destination)

    def __sendToGraveyard(self, pid):
        piece = self.__pieces[pid]
        grave_index = pid - 1
        grave = self.__graveyard['graves'][grave_index]
        piece.reparentTo(grave)

    def __defaultGraveyard(self):
        """整个墓区
        for id in range(32) 的 32 个棋子各自预留一小块墓地, 每个棋子墓穴位置固定
        """
        # 8*8 棋盘理论上最多允许存在 64 枚棋子, 实际一套标准国际象棋为 32 枚棋子.
        # 另外 16 个小兵生变时只是更改棋子的外观, 不会增加额外的棋子.
        max_pieces = 32
        max_graves = max_pieces
        graves = []
        graveyard = self.render.attachNewNode("graveyard")
        for i in range(max_graves):
            grave = graveyard.attachNewNode("grave")
            grave.reparentTo(graveyard)
            x = -4.5 if i < 16 else 4.5  # 右手边左手边分开两块墓地
            y = 0.4 * ((i % 16) - 7.5)
            grave.setPos(x, y, 0)
            grave.setScale(0.75)
            graves.append(grave)
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
        """A handy little function for getting the proper position for a given square1"""
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
