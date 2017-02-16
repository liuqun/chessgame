# coding=utf-8
import collections

Vector = collections.namedtuple('Vector', ['dx', 'dy'])

Square = collections.namedtuple('Square', ['x', 'y'])


class Unit(object):
    def __init__(self, owner):
        self.owner = owner  # 所属玩家
        self.has_been_moved = None  # None 表示未知棋子当前状态是否已经走过


class GameArena:
    """模拟竞技场
    """

    class PlayerID(int):
        """直接使用整数表示游戏玩家编号"""
        pass

    class UnitID(int):
        """直接使用整数表示的战斗单位编码"""
        pass

    def __init__(self, width, ranks):
        """初始化游戏竞技场数据

        :param width: x 轴方向上棋盘的宽度(=xmax), 例如国际象棋棋盘为 8 路纵列, 中国象棋棋盘则为 9 路
        :param ranks: 横行数量(=ymax)
        """
        self.__unit_info_list = []  # 按单位的编码顺序存储所有战斗单位的信息(其中并不包括该单位所在位置), 初始状态为空列表, 通过编码查找. 单位死亡后仍然保留记录
        # 二维数组共 width*ranks 个格子, 记录每个空格被哪一个棋子占领, 全部初始化置零表示所有格子均无人占领:
        self.__battlefield = [[self.UnitID(0)] * width for y in range(ranks)]

    @property
    def size(self):
        """长度和宽度格子数

        :return: 战场一横排的格数 x 和一纵列的格数 y
        :rtype : int, int
        """
        ymax = len(self.__battlefield)
        xmax = len(self.__battlefield[0])
        return xmax, ymax

    def new_unit_recruited_by_player(self, player_id, square, unit_type, **unit_kwargs):
        """征募一个虚拟单位进入战场, 返回值表示为其分配的编码

        :param player_id: 玩家编号, 每个单位必须有一个玩家归属
        :param square: 单位的初始位置
        :param unit_type: 单位的类型, 必须继承 class Unit
        :param **unit_kwargs: 变长参数表
        :return: 为新单位分配的编码, 最小值从 1 开始分配
        :rtype : GameArena.UnitID
        """
        unit = unit_type(owner=player_id, **unit_kwargs)
        self.__unit_info_list.append(unit)
        unit_id = self.UnitID(len(self.__unit_info_list))
        unit.has_been_moved = False
        if square:
            x, y = square[0], square[1]
            xmax, ymax = self.size
            if x < 0 or y < 0 or x >= xmax or y >= ymax:
                raise ValueError('invalid square:{}'.format(square))
            self.__battlefield[y][x] = unit_id
            # self.__survivors[unit_id] = Square(x, y)
        return unit_id

    def owner_of_unit(self, unit_id):
        if not self.is_valid_unit_id(unit_id):
            raise ValueError('unit_id:{} not exists'.format(unit_id))
        return self.__unit_info_list[unit_id - 1].owner

    def __place_unit_on_square(self, unit_id, square):
        """放置棋子(即移动或者复活棋子, 但该函数不能将棋子本身从棋盘上拿走)

        如果指定的单位已经死亡则将其复活并放入战场, 强制杀死指定位置上原有的单位无论是否是己方单位
        """
        x, y = square[0], square[1]
        self.__battlefield[y][x] = unit_id
        try:
            # 进行移动前, 先尝试寻找该棋子移动前的位置信息
            square_before_move = self.find_square_from_unit_id(unit_id)
        except ValueError:
            # 这种情况没有“脚印”即不需要擦除
            pass
        else:  # 擦除脚印
            self.__battlefield[square_before_move.y][square_before_move.x] = self.UnitID(0)

    def move_unit_to_somewhere(self, unit_id, square):
        """移动棋子

        :param unit_id: 单位编码
        :param square: 目的地坐标
        """
        if not self.is_valid_unit_id(unit_id):
            raise ValueError('unit_id:{} does not exist'.format(unit_id))
        x, y = square[0], square[1]
        xmax, ymax = self.size
        if x < 0 or y < 0 or x >= xmax or y >= ymax:
            raise ValueError('invalid square:{}'.format(square))
        self.__place_unit_on_square(unit_id, square)
        self.__unit_info_list[unit_id - 1].has_been_moved = True

    def is_valid_unit_id(self, unit_id):
        """unit_id 编码检查, 这里不区分是否已经死亡, 只要单位曾经存在即为有效 ID, unit_id=0 时无效

        :param unit_id: 单位的编码
        :return: False 表示编码无效
        :rtype : bool
        """
        return 1 <= unit_id <= len(self.__unit_info_list)

    def retrieve_valid_moves_of_unit(self, unit_id):
        """查询走法

        :param unit_id: 棋子单位的编码
        :return: 依据棋子自己的走法规则搜索该棋子所有可达位置
        :rtype : tuple
        """
        result = {}
        if not self.is_valid_unit_id(unit_id):
            return result
        square = self.find_square_from_unit_id(unit_id)  # 找不到则会向上传递 ValueError 异常
        unit = self.__unit_info_list[unit_id - 1]
        return unit.retrieve_valid_moves(starting_square=square, snapshot=self.__take_snapshot())

    def find_square_from_unit_id(self, unit_id):
        """搜索特定棋子编码的棋子如果在棋盘上则返回坐标, 否则向上传递一个 ValueError 表示没找到

        :param unit_id:
        :rtype : Square
        """
        if not self.is_valid_unit_id(unit_id):
            raise ValueError('Error: invalid unit_id:{}'.format(unit_id))
        for y in range(len(self.__battlefield)):
            rank = self.__battlefield[y]
            for x in range(len(rank)):
                if unit_id == rank[x]:
                    return Square(x, y)
        raise ValueError('Note: unit_id:{} is not on chessboard'.format(unit_id))

    def is_occupied_square(self, square):
        x, y = square[0], square[1]
        xmax, ymax = self.size
        if x < 0 or y < 0 or x >= xmax or y >= ymax:
            return False
        return self.__battlefield[y][x] > 0

    def __take_snapshot(self):
        """遍历所有格子的信息, 生成一份快照"""
        builder = SnapshotBuilder(self.size)
        for y in range(len(self.__battlefield)):
            rank = self.__battlefield[y]
            for x in range(len(rank)):
                unit_id = rank[x]
                unit = Unit(owner=None)
                if unit_id:
                    unit.owner = self.__unit_info_list[unit_id - 1].owner
                builder.set_node(x, y, unit_id, unit)
        return builder.snapshot


class Snapshot:
    def __init__(self, nodes):
        self.__nodes = nodes

    @property
    def xmax(self):
        return len(self.__nodes[0])

    @property
    def ymax(self):
        return len(self.__nodes)

    def get_node(self, x, y):
        if 0 <= x < self.xmax and 0 <= y < self.ymax:
            return self.__nodes[y][x]
        # 否则上报一个 ValueError 异常:
        raise ValueError('Error: 坐标越界: get_node(x={},y={})'.format(x, y))


class SnapshotBuilder:
    def __init__(self, size):
        xmax, ymax = size[0], size[1]
        self.__nodes = [[self.Node() for x in range(xmax)] for y in range(ymax)]

    class Node:
        def __init__(self):
            self.unit_id = 0
            self.owner = None

    @property
    def snapshot(self):
        return Snapshot(self.__nodes)

    def set_node(self, x, y, unit_id, unit_info):
        if 0 <= x < len(self.__nodes[0]) and 0 <= y < len(self.__nodes):
            self.__nodes[y][x].unit_id = unit_id
            self.__nodes[y][x].owner = unit_info.owner
        else:
            raise ValueError('Error: 坐标越界: get_node(x={},y={})'.format(x, y))


class PawnUnit(Unit):
    def __init__(self, owner, pawn_charge_direction):
        """国际象棋的兵

        :param owner: 所属玩家
        :param pawn_charge_direction: 指定兵的冲锋方向, DirectionVector 矢量, 一般情况下应设置白方为 Vector(0, 1), 黑方为 Vector(0, -1)
        """
        super(PawnUnit, self).__init__(owner)
        self.pawn_charge_direction = \
            Vector(pawn_charge_direction[0], pawn_charge_direction[1])
        self.has_been_moved = False  # 是否被移动过(兵第一次移动时可以进行冲锋走两格,之后只能沿棋盘纵列每步走一格)

    def retrieve_valid_moves(self, starting_square, snapshot):
        """兵只直走和斜吃两种情况(吃过路兵功能未实现, 需要另外单独处理)

        :param starting_square: 兵当前位置
        :param snapshot: 作战双方棋子的位置的一个快照
        :rtype : tuple
        """
        result = []

        # 先分析直走
        dx, dy = self.pawn_charge_direction
        x, y = starting_square.x + dx, starting_square.y + dy
        max_steps = 1
        if not self.has_been_moved:
            max_steps = 2
        step = 1
        squares = []
        while step <= max_steps:
            step += 1
            if y < 0 or y >= snapshot.ymax:
                break  # 此时已经跑到棋盘外面了
            other_unit_id = snapshot.get_node(x, y).unit_id
            if not other_unit_id:
                squares.append(Square(x, y))
                y += dy
        result += squares

        # 再分析斜吃
        dy = self.pawn_charge_direction.dy
        squares = []
        for x, y in self.retrieve_squares_within_shooting_range(starting_square, snapshot):
            node = snapshot.get_node(x, y)
            if not node.unit_id:
                # 斜线方向上没有棋子时兵不能斜吃斜走, 但是吃过路兵除外
                continue  # FIXME: 此处信息不足, 暂时无法判断能否吃过路兵
            elif node.owner == self.owner:
                continue  # 兵不能斜吃己方棋子
            squares.append(Square(x, y))
        result += squares
        return tuple(result)

    def retrieve_squares_within_shooting_range(self, starting_square, snapshot):
        """分析兵可以攻击的两格火力点(射程), 不需要区分目标格子上是否为己方的棋子

        :param starting_square: 兵当前位置
        :param snapshot: 作战双方棋子的位置的一个快照
        :rtype : tuple
        """
        result = []
        dy = self.pawn_charge_direction.dy
        for dx in {-1, 1}:
            x, y = starting_square.x + dx, starting_square.y + dy
            if x < 0 or x >= snapshot.xmax or y < 0 or y >= snapshot.ymax:
                continue  # 此时已经跑到棋盘外面了
            result.append(Square(x, y))
        return tuple(result)


class StraightMovingAndAttackingUnit(Unit):
    """沿直线行进并攻击敌人的棋子，包括車、象、后、王(王只能走1格)

    注意:
    中国象棋的炮只能隔子吃而不能直线吃, 所以该走法规则是不能支持中国象棋炮的
    中国象棋的象和马有有蹩腿规则, 也需要单独判定
    """

    def __init__(self, owner):
        super(StraightMovingAndAttackingUnit, self).__init__(owner)
        self.directions = []  # 用一组 Vector 矢量描述棋子可以朝哪些方向走
        self.limited_move_range = 0  # 用负数或 0 代表不限制棋子最大移动格数, 用正整数 N 代表棋子最大移动距离(倍数 N). 王和马只能按移动矢量的一倍距离进行移动(倍数 N=1)

    def retrieve_valid_moves(self, starting_square, snapshot):
        """计算走法沿直线走和吃子的棋子可以到达哪些格子

        :param starting_square: 当前位置
        :param snapshot: 作战双方棋子的位置的一个快照
        :rtype : tuple
        """
        squares = []
        for x, y in self.retrieve_squares_within_shooting_range(starting_square, snapshot):
            node = snapshot.get_node(x, y)
            # 可以占领空格或攻击敌人所在的格子, 但不能攻击己方棋子所在的格子:
            if not node.unit_id or node.owner != self.owner:
                squares.append(Square(x, y))
        return tuple(squares)

    def retrieve_squares_within_shooting_range(self, starting_square, snapshot):
        """计算沿直线走和吃子的棋子可以的所有火力点(当前火力射程范围), 不需要区分目标格子上是敌方还是己方的棋子

        :param starting_square: 当前位置
        :param snapshot: 作战双方棋子的位置的一个快照
        :rtype : tuple
        """
        result = []
        for dx, dy in self.directions:  # 每个方向单独处理
            squares = []
            step_count = 1
            x, y = starting_square[0] + dx, starting_square[1] + dy
            # 若不限制棋子移动格数则一直循环, 直到碰到其他棋子或者棋盘边界:
            while step_count <= self.limited_move_range if self.limited_move_range > 0 else True:
                step_count += 1
                if x < 0 or x >= snapshot.xmax or y < 0 or y >= snapshot.ymax:
                    # 此时已经跑到棋盘外面了, 结束 while 循环
                    break
                node = snapshot.get_node(x, y)
                if node.unit_id > 0:
                    # 存在敌人时, 火力线被敌人阻挡, 火力覆盖不到后面的位置了
                    # 存在己方棋子时, 火力线则被己方阻挡, 结果同上
                    squares.append(Square(x, y))
                    break  # 结束 while 循环
                squares.append(Square(x, y))
                x, y = x + dx, y + dy
            result += squares
        return tuple(result)


class RookUnit(StraightMovingAndAttackingUnit):
    # TODO: 王車易位功能暂未实现, 需要在王的走法部分补充代码单独进行处理
    """車(国际象棋与中国象棋通用)"""

    def __init__(self, owner):
        super(RookUnit, self).__init__(owner)
        self.directions = [Vector(1, 0), Vector(0, 1), Vector(-1, 0), Vector(0, -1)]  # 車可以前后左右四个方向(纵向、横向)移动, 不限格数
        self.limited_move_range = 0  # 0 for no limit

    def retrieve_valid_moves(self, starting_square, snapshot):
        """車的走法(国际象棋与中国象棋完全相同)

        :param starting_square: 当前位置
        :param snapshot: 作战双方棋子的位置的一个快照
        :rtype : tuple
        """
        return super(RookUnit, self).retrieve_valid_moves(starting_square, snapshot)


class BishopUnit(StraightMovingAndAttackingUnit):
    """国际象棋象的走法: 斜走 and 不限格数"""

    def __init__(self, owner):
        super(BishopUnit, self).__init__(owner)
        self.directions = [Vector(1, 1), Vector(-1, 1), Vector(-1, -1), Vector(1, -1)]  # 象可以朝四个斜方向移动, 不限格数
        self.limited_move_range = 0  # 0 for no limit


class QueenUnit(StraightMovingAndAttackingUnit):
    """国际象棋后的走法: 直走或斜走, 并且均不限格数"""

    def __init__(self, owner):
        super(QueenUnit, self).__init__(owner)
        self.directions = \
            [Vector(1, 0), Vector(1, 1), Vector(0, 1), Vector(-1, 1),
             Vector(-1, 0), Vector(-1, -1), Vector(0, -1), Vector(1, -1)]
        self.limited_move_range = 0  # 0 for no limit


def do_self_test():
    """以下为模块自测试代码

    """
    import sys
    log = sys.stdout
    log.write('Module:{}\n'.format(__name__))
    arena = GameArena(width=8, ranks=8)
    white = GameArena.PlayerID(1)
    black = GameArena.PlayerID(2)
    white_pawns = []
    black_pawns = []
    for x in range(8):
        unit_id = arena.new_unit_recruited_by_player(
            player_id=white,
            square=Square(x, 1),
            unit_type=PawnUnit,
            pawn_charge_direction=Vector(0, 1)
        )
        white_pawns.append(unit_id)
        unit_id = arena.new_unit_recruited_by_player(
            player_id=black,
            square=Square(x, 6),
            unit_type=PawnUnit,
            pawn_charge_direction=Vector(0, -1))
        black_pawns.append(unit_id)
    m = arena.retrieve_valid_moves_of_unit(white_pawns[0])
    print(m)
    selected_destination = m[1]
    arena.move_unit_to_somewhere(white_pawns[0], selected_destination)
    white_rook = arena.new_unit_recruited_by_player(white, Square(0, 0), RookUnit)
    m = arena.retrieve_valid_moves_of_unit(white_rook)
    print(m)


if '__main__' == __name__:
    do_self_test()
    pass
