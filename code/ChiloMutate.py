import time

from ChiloMutatorFactory import chilo_factory as cf
import threading
from ChiloMutatorFactory import LLMParser,LLMMutatorGenerater,LLMStructuralMutator,mutator_fixer


chilo_factory: cf.ChiloFactory | None = None
fuzz_count_number = 0
fuzz_number = 0
last_bitmap_save = time.time()
is_chilo_fuzzed = False     #避免每次运行都postrun 只chilo的postrun就行了
left_fuzz_count = 0

def init(seed):
    """
    fuzz的初始化函数，用于初始化整个变异器的状态等等。注意该函数在整个Fuzz过程中只运行一次。
    在这里将会读取配置文件，确定被测对象等等...
    :param seed: 由AFL++传来的一个随机种子，这里其实可以忽略seed的存在
    :return: 返回0，表示初始化成功
    """

    global chilo_factory
    chilo_factory = cf.ChiloFactory()   #首先初始化整个工厂（读配置文件）
    chilo_factory.main_logger.info("Chilo工厂初始化成功！")
    
    # 计算总线程数
    total_threads = (chilo_factory.parser_thread_count + 
                    chilo_factory.mutator_generator_thread_count + 
                    chilo_factory.structural_mutator_thread_count + 
                    chilo_factory.fixer_thread_count)
    chilo_factory.main_logger.info(f"Chilo工厂准备启动{total_threads}个子线程")
    
    # 启动多个Parser线程
    chilo_factory.main_logger.info(f"Chilo工厂启动解析器中~（共{chilo_factory.parser_thread_count}个线程）")
    parser_threads = []
    for i in range(chilo_factory.parser_thread_count):
        parser_t = threading.Thread(target=LLMParser.chilo_parser, args=(chilo_factory,))
        parser_t.start()
        parser_threads.append(parser_t)
        chilo_factory.main_logger.info(f"解析器[线程{i}]启动成功")
    
    # 启动多个Mutator Generator线程
    chilo_factory.main_logger.info(f"Chilo工厂启动变异器生成器中~（共{chilo_factory.mutator_generator_thread_count}个线程）")
    generator_threads = []
    for i in range(chilo_factory.mutator_generator_thread_count):
        generator_t = threading.Thread(target=LLMMutatorGenerater.chilo_mutator_generator, args=(chilo_factory,))
        generator_t.start()
        generator_threads.append(generator_t)
        chilo_factory.main_logger.info(f"变异器生成器[线程{i}]启动成功")
    
    # 启动多个Structural Mutator线程
    chilo_factory.main_logger.info(f"Chilo工厂启动结构化变异器中~（共{chilo_factory.structural_mutator_thread_count}个线程）")
    structural_threads = []
    for i in range(chilo_factory.structural_mutator_thread_count):
        structural_t = threading.Thread(target=LLMStructuralMutator.structural_mutator, args=(chilo_factory,))
        structural_t.start()
        structural_threads.append(structural_t)
        chilo_factory.main_logger.info(f"结构化变异器[线程{i}]启动成功")
    
    # 启动多个Fixer线程
    chilo_factory.main_logger.info(f"Chilo工厂启动变异器修复器中~（共{chilo_factory.fixer_thread_count}个线程）")
    fixer_threads = []
    for i in range(chilo_factory.fixer_thread_count):
        fixer_t = threading.Thread(target=mutator_fixer.fix_mutator, args=(chilo_factory, i))
        fixer_t.start()
        fixer_threads.append(fixer_t)
        chilo_factory.main_logger.info(f"变异器修复器[线程{i}]启动成功")
    
    chilo_factory.main_logger.info("初始化完成，结束初始化~")


    return 0

def fuzz_count(buf):
    """
    能量调度函数，决定一个种子调用多少次的fuzz()
    注意，在这里调度的时候，还实现了完成对当前种子的TOKEN解析和变异器生成~yooo~~
    :param buf: 当前种子
    :return: 变异次数
    """
    global fuzz_count_number
    global left_fuzz_count
    fuzz_count_number += 1
    #应该采用队列的设计，先放入工厂的队列中，等待加工
    global chilo_factory
    mutate_time = chilo_factory.fuzz_count_time
    chilo_factory.main_logger.info("进入fuzz_count~")
    chilo_factory.main_logger.info("准备将buf中种子加入到待解析队列中~")
    chilo_factory.add_one_seed_to_parse_list(buf, mutate_time)
    chilo_factory.main_logger.info("该种子fuzz_count处理完成")
    # 优先：如果有结构化变异待执行，则直接返回1
    q_struct = chilo_factory.wait_exec_structural_list
    with q_struct.mutex:
        if len(q_struct.queue) > 0:
            chilo_factory.next_fuzz_strategy = 0
            chilo_factory.main_logger.info("有结构化变异待执行，将执行结构化变异，变异次数1")
            left_fuzz_count = 1
            return 1

    # 否则：根据 wait_exec_mutator_list 前缀中连续同一对象实例的个数返回
    q = chilo_factory.wait_exec_mutator_list
    with q.mutex:
        internal = list(q.queue)  # 拷贝当前快照
    if not internal:
        #到这里判断，变异器池是否为空，如果为空，说明是模糊测试刚启动的状态，则默认先用待执行队列，让fuzz mutate_once去等待待执行队列去
        if len(chilo_factory.mutator_pool.mutator_list) > 0:
            #说明并非刚启动，变异器池已经有东西了
            chilo_factory.next_fuzz_strategy = 2
            
            # 汤普森采样选择变异器
            with chilo_factory.mutator_pool_lock:
                mutator, score, Ai, Bi, Ci = chilo_factory.mutator_pool.thompson_select_mutator()
            
            chilo_factory.mutator_pool.total_select_count += 1 # 增加总选择次数
            chilo_factory.current_thompson_mutator = mutator
            chilo_factory.current_thompson_score = score
            chilo_factory.current_Ai = Ai
            chilo_factory.current_Bi = Bi
            chilo_factory.current_Ci = Ci
            chilo_factory.current_batch_new_edges = 0 # 重置当前批次的新边计数
            
            # 能量调度：max(int(score * 10), 5)，且设置上限200
            energy = min(max(int(score * chilo_factory.energy_exchange_rate), chilo_factory.min_energy), chilo_factory.max_energy)
            
            chilo_factory.main_logger.info(f"无待第一次执行的变异器，将执行变异器池选择，变异次数{energy}")
            chilo_factory.main_logger.info(f"汤普森采样选中变异器: {mutator.mutator_id}, 得分: {score}, 能量: {energy}")
            
            #注意，这里就不能再返回mutatetime了，而是在这里确定变异次数和能量调度
            left_fuzz_count = energy
            #这里我在想要不要
            return energy
        else:
            #说明刚启动，需要让mutate_once等一等
            chilo_factory.next_fuzz_strategy = 0
            chilo_factory.main_logger.info("chilo刚启动，再等一等")
            left_fuzz_count = 0
            return 0    #AFL++暂时跳过，等待一下... 
    first_item = internal[0]
    consecutive = 1
    for item in internal[1:]:
        if item is first_item:
            consecutive += 1
        else:
            break
    chilo_factory.next_fuzz_strategy = 1
    chilo_factory.main_logger.info("无结构化，有待第一次执行的变异器，将执行待执行变异器，变异次数{consecutive}")
    left_fuzz_count = consecutive
    return consecutive    #这里就是待执行变异器，需要返回连续的个数

def splice_optout():
    """
    标记函数，当定义了这个函数的时候，则AFL++在非确定性变异阶段不启用随机拼接
    :return: 无返回值
    """
    pass

def fuzz(buf, add_buf, max_size):
    """
    主要的变异API，AFL++在每轮变异中将调用一次这个函数
    在这个函数中，应该完成对于一个种子的变异，并返回变异后的结果
    :param buf: 当前队列中的SEED的内容
    :param add_buf: 被选中拼接的另一个SEED的内容，在此处被忽略了，因为定义了splice_optout函数
    :param max_size: 输出 buffer 最大允许长度，你必须确保返回的变异输入不超过这个长度
    :return: 变异后的结果
    """
    fuzz_start_time = time.time()
    global chilo_factory
    global fuzz_number
    global fuzz_count_number
    global is_chilo_fuzzed
    global left_fuzz_count
    fuzz_number += 1
    is_cut = False
    #思路：
    #其实整个变异的返回值的获取，就是读文件，将文件内容作为返回值即可
    #这里应该启用一次LLM生成的程序，并将程序生成的SQL测试用例作为返回值，这样可以不用记录次数...
    #但这里还有一个问题
    #那就是两种变异并不是每次都用
    #因此在这一次函数的调用中，如何确定本次是结构+TOKEN 还是仅结构呢....这是一个问题
    #不管了，先把TOKEN的写出来吧

    #下一步呢，其实变异阶段有两部分，分别是掩码解析和掩码变异... 到这里已经完成了解析，直接变异就好

    #这里应该只需要做一件事就行，那就是启动LLM生成的变异程序，并获得一个SQL！
    chilo_factory.main_logger.info("进入fuzz阶段~")
    chilo_factory.main_logger.info("准备调用mutator生成")
    mutated_out,is_random, seed_id, mutator_id, is_error_occur, is_from_structural_mutator = chilo_factory.mutate_once()
    chilo_factory.main_logger.info("变异完成")
    # 确保类型正确
    if isinstance(mutated_out, str):
        mutated_out = bytearray(mutated_out, "utf-8", errors="ignore")
        # 检查并截断

    ori_mutate_out_size = len(mutated_out)

    if len(mutated_out) > max_size:
        is_cut = True
        mutated_out = mutated_out[:max_size]
        chilo_factory.main_logger.warning("由于变异结果过长，被迫进行截断")
    real_mutate_out_size = len(mutated_out)
    now_seed_id = chilo_factory.all_seed_list.index_of_seed_buf(buf)

    fuzz_end_time = time.time()
    queue_size = chilo_factory.wait_exec_mutator_list.qsize()
    chilo_factory.write_main_csv(fuzz_end_time, fuzz_count_number, fuzz_number,
                                 is_random, fuzz_end_time - fuzz_start_time, now_seed_id, seed_id, mutator_id,
                                 queue_size, ori_mutate_out_size,
                                 real_mutate_out_size, is_cut, is_error_occur, is_from_structural_mutator,
                                 chilo_factory.current_thompson_score, left_fuzz_count,
                                 chilo_factory.current_Ai, chilo_factory.current_Bi, chilo_factory.current_Ci)
    is_chilo_fuzzed = True
    left_fuzz_count -= 1
    return mutated_out


def post_run():
    """
    在每次变异后，读取覆盖率信息
    :return: 无返回值
    """
    global chilo_factory
    global last_bitmap_save
    global fuzz_count_number
    global is_chilo_fuzzed

    if fuzz_count_number == 0:
        #dry run阶段，跳过postrun
        pass
    elif not is_chilo_fuzzed:
        #chilo_fuzzed为False 说明刚刚的fuzz run都不是chilo的，应该跳过
        pass
    else:
        #读取刚刚的fuzz的测试用例的边覆盖位图情况
        now_bitmap = chilo_factory.coverage_reader.get_coverage_bitmap()    #当前的bitmap
        new_edges = chilo_factory.bitmap.add_bitmap(now_bitmap)
        chilo_factory.main_logger.info(f"新增边数量：{new_edges}")

        # 汤普森采样反馈逻辑
        if chilo_factory.next_fuzz_strategy == 2 and chilo_factory.current_thompson_mutator:
            # 累加当前批次的新边数
            chilo_factory.current_batch_new_edges += new_edges
            
            # 如果是本轮最后一次变异，则进行结算
            # left_fuzz_count 在 fuzz() 函数结束前已经减 1
            # 因此当 post_run 运行时，如果 left_fuzz_count 为 0，说明刚刚结束的是最后一次 fuzz
            if left_fuzz_count == 0:
                is_success = chilo_factory.current_batch_new_edges > 0
                chilo_factory.current_thompson_mutator.update_stats(is_success, chilo_factory.current_batch_new_edges)
                chilo_factory.main_logger.info(f"汤普森采样批次结束. 变异器: {chilo_factory.current_thompson_mutator.mutator_id}, 本批次总新边: {chilo_factory.current_batch_new_edges}, 结果: {'成功' if is_success else '失败'}")

        if time.time() - last_bitmap_save > 5:
            chilo_factory.write_bitmap()
            last_bitmap_save = time.time()
        is_chilo_fuzzed = False
    

#当AFL++停止或结束的时候调用该函数，进行清理
def deinit():  # optional for Python
    chilo_factory.main_logger.info("FUZZ结束！祝您早日找到CVE！！")
    pass
# def describe(max_description_length):
#     """
#     为变异生成一个描述，可选的部分，不启用也ok
#     :param max_description_length:
#     :return:
#     """
#     return "description_of_current_mutation"

# def post_process(buf):
#     """
#     在变异后的测试用例即将发送给被测DBMS前，将调用这个函数
#     这个函数的目的应该是对测试用例进行补充，例如ZIP格式需要加入特殊的头信息等等
#     对于DBMS而言，应该不需要，因此该方法会被注释
#     :param buf:
#     :return:
#     """
#     return out_buf

#下面三个函数都是修剪相关的函数，即得到最小化输入，在DBMS模糊测试中不需要，因此被注释
# def init_trim(buf):
#     return cnt
#
# def trim():
#     return out_buf
#
# def post_trim(success):
#     return next_index


#下面两个函数都是自定义havoc变异及其概率，在启动AFL_CUSTOM_MUTATOR_ONLY=1时，该函数将不起作用，因此被注释
# def havoc_mutation(buf, max_size):
#     return mutated_out
#
# def havoc_mutation_probability():
#     return probability # int in [0, 100]

#下面的函数是种子选择的函数，
# def queue_get(filename):
#     return True

# #下面是用于发送测试用例的函数，在本次设计中采用wrapper设计，不需要该函数
# def fuzz_send(buf):
#     pass

# # 有新的种子加入测试用例后会调用这个函数，可以对种子进行处理，但本方法不需要该函数
# def queue_new_entry(filename_new_queue, filename_orig_queue):
#
#     return False

# #返回一个字符串，用于描述变异方法的，不需要
# def introspection():
#     return string

