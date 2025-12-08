"""
用于保存生成的变异器的类
其中包括三个类

1. 变异器池
2. 一个变异器
3. 一个任务队列
"""
import random
import math
from typing import List


#先定义变异器

class ChiloMutator:
    def __init__(self, file_path, seed_id, mutator_id, mutator_index, mask_count=0, similarity=0.0):
        """
        初始化一个变异器池,其中具有一些属性
        """
        self.seed_id = seed_id
        self.mutator_id = mutator_id
        self.mutator_index = mutator_index
        self.mask_count = mask_count # 掩码数量 (用于 Ci 计算)
        self.similarity = similarity # 重复率 (用于 Ci 计算, 0表示完全不重复, 1表示完全重复)
        self.file_name = f"{file_path}{seed_id}_{mutator_id}.py"
        self.is_error = False   #是否在最终的FUZZ出现了错误
        self.last_error_count = 0   #如果出现了最终FUZZ错误则加1...不过好像没啥用

        # 汤普森采样相关属性
        self.alpha = 1.0    # 成功次数 + 1 (先验)
        self.beta = 1.0     # 失败次数 + 1 (先验)
        self.success_count = 0  # 成功次数
        self.failure_count = 0  # 失败次数
        self.total_new_edges = 0 # 历史贡献的总新边数量 (用于 Bi 计算)

    def update_stats(self, is_success, new_edges):
        """
        更新变异器的统计信息
        :param is_success: 本次采样是否成功（覆盖了新边）
        :param new_edges: 本次采样发现的新边数量
        """
        if is_success:
            self.success_count += 1
            self.alpha += 1
        else:
            self.failure_count += 1
            self.beta += 1
        self.total_new_edges += new_edges

class ChiloMutatorPool:
    def __init__(self, file_path):
        """
        初始化一个变异器池，用于保存所有变异器
        """
        self.mutator_list:List[ChiloMutator] = []
        self.next_mutator_index = 0
        self.file_path = file_path
        self.total_select_count = 0 # 变异器池总选择次数 (用于 Bi 计算)

    def add_mutator(self, seed_id, mutator_id, mask_count=0, similarity=0.0):
        self.mutator_list.append(ChiloMutator(self.file_path, seed_id, mutator_id, self.next_mutator_index, mask_count, similarity))
        self.next_mutator_index += 1
        return self.next_mutator_index - 1



    def random_select_mutator(self):
        """
        从变异器池中随机选择一个
        :return: 返回的变异器对象
        """
        if self.next_mutator_index == 0:    #说明还没有变异器呢，要稍微等一会
            return None
        else:
            num = random.randint(0, self.next_mutator_index - 1)
            return self.mutator_list[num]

    def thompson_select_mutator(self):
        """
        使用汤普森采样算法(结合历史因子Bi)从变异器池中选择一个变异器
        :return: (变异器对象, 采样得分)
        """
        if self.next_mutator_index == 0:
            return None, 0.0
        
        best_mutator = None
        best_score = -1.0
        best_Ai = 0.0
        best_Bi = 0.0
        best_Ci = 0.0
        
        N = self.next_mutator_index # 变异器总数
        t = self.total_select_count # 总选择次数
        
        # 计算所有变异器的平均掩码数量 (在循环外计算一次即可)
        avg_mask_count = sum(m.mask_count for m in self.mutator_list) / len(self.mutator_list)
        
        for mutator in self.mutator_list:
            # 1. 基础汤普森采样 (Ai)
            sample_val = random.betavariate(mutator.alpha, mutator.beta)
            
            # 2. 计算历史因子 (Bi)
            # Bi = log(t/N + 1) * log((ne + 1)/(su + fa + 1) + 1)
            # 含义：时间压力 × 效率（每次选择能发现多少新边）
            # 效率高的变异器 Bi 大，效率低的 Bi 小
            su = mutator.success_count
            fa = mutator.failure_count
            ne = mutator.total_new_edges
            
            time_pressure = math.log(t / N + 1)
            efficiency = math.log((ne + 1) / (su + fa + 1) + 1)
            
            Bi = time_pressure * efficiency
            
            # 3. 计算潜力因子 (Ci)
            # Ci = log((mask_i * (1 - sim_i)) / avg_mask + 1)
            # 分子: mask_count * (1 - similarity) = 掩码数 × 多样性
            numerator_ci = mutator.mask_count * (1 - mutator.similarity)
            # 分母: 平均掩码数量 (归一化)
            denominator_ci = avg_mask_count if avg_mask_count > 1e-9 else 1.0
            
            Ci = math.log(numerator_ci / denominator_ci + 1)
            
            # 4. 组合分数
            # S = Ai * (1 + Bi) * (1 + Ci)
            score = sample_val * (1 + Bi) * (1 + Ci)
            
            if score > best_score:
                best_score = score
                best_mutator = mutator
                best_Ai = sample_val
                best_Bi = Bi
                best_Ci = Ci
                
        return best_mutator, best_score, best_Ai, best_Bi, best_Ci
                


