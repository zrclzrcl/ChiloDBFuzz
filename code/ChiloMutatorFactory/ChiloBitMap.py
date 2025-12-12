#用于存储全局bitmap的类
import array

class BitMap:
    """
    高效的位图实现，使用 array 模块减少内存开销。
    
    内存优化说明：
    - Python list 中每个 int 约 28 字节
    - array('Q') 每个元素仅 8 字节
    - array('L') 每个元素仅 4 字节
    - array('B') 每个元素仅 1 字节
    
    对于 mapsize=65536:
    - 原 list 方案: 3 * 65536 * 28 ≈ 5.5 MB
    - 优化后: 65536*8 + 65536*4 + 65536*1 ≈ 0.85 MB
    """
    
    def __init__(self, mapsize):
        #维护一个全局的BitMap
        self.map_size = mapsize
        # 使用 array 替代 list 以节省内存
        # 'Q' = unsigned long long (8 bytes), 支持大数值累加
        # 'L' = unsigned long (4 bytes), 足够存储测试用例命中次数
        # 'B' = unsigned char (1 byte), 只需存储 0/1
        self._sum_bitmap = array.array('Q', [0] * self.map_size)    # 总命中次数
        self._cumulative_bitmap = array.array('L', [0] * self.map_size)    # 测试用例命中次数
        self._bool_bitmap = array.array('B', [0] * self.map_size)    # 是否命中过（0/1）
        self.hit_count = 0    # _bool_bitmap中为1的边数量
        # 最近一次读取的原始位图快照
        self._last_snapshot = None


    def add_bitmap(self, bitmap):
        """
        添加一个位图：
        - _sum_bitmap[i] += bitmap[i]
        - 若 bitmap[i] > 0 则 _cumulative_bitmap[i] += 1 （一次测试用例对该槽位的命中次数计为1次）
        - 若 bitmap[i] > 0 且 _bool_bitmap[i] == 0，则将其置为1，并计入新边
        返回：本次位图带来的新增边数量（0->1的数量）
        """
        if bitmap is None or len(bitmap) != self.map_size:
            raise ValueError("Bitmap size mismatch")

        new_edges = 0
        # 保证类型为可索引的字节序列
        data = bitmap if isinstance(bitmap, (bytes, bytearray)) else bytes(bitmap)

        for i in range(self.map_size):
            val = data[i]
            if val > 0:
                # 总命中次数叠加（int不封顶）
                self._sum_bitmap[i] += int(val)

                # 测试用例命中次数（本次命中过则+1）
                self._cumulative_bitmap[i] += 1

                # 是否命中过：0 -> 1 视为新边
                if self._bool_bitmap[i] == 0:
                    self._bool_bitmap[i] = 1
                    new_edges += 1
                    self.hit_count += 1

        # 记录快照
        self._last_snapshot = bytes(data)
        return new_edges

    def get_sum_bitmap(self):
        """返回总命中次数位图（list[int]）"""
        return list(self._sum_bitmap)

    def get_cumulative_bitmap(self):
        """返回测试用例命中次数位图（list[int]）"""
        return list(self._cumulative_bitmap)

    def get_bool_bitmap(self):
        """返回是否命中的0/1位图（list[int]）"""
        return list(self._bool_bitmap)