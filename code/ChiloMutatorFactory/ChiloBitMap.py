#用于存储全局bitmap的类

class BitMap:
    def __init__(self, mapsize):
        #维护一个全局的BitMap
        self.map_size = mapsize
        self._sum_bitmap = [0] * self.map_size    # 总命中次数(记录的是次数总和，int不封顶)
        self._cumulative_bitmap = [0] * self.map_size    # 累计的“测试用例命中次数”（每有一个测试用例命中过该槽位，+1）
        self._bool_bitmap = [0] * self.map_size    # 是否命中过（0/1）
        self.hit_count = 0    # _bool_bitmap中为1的边数量
        # 最近一次读取的原始位图快照


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