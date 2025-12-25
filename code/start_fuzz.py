import os
import yaml

def main():

    #1. 读取fuzz_config文件
    with open("./fuzz_config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    target_dbms = config["TARGET_DBMS"]     #目标DBMS
    output_dir = config["OUTPUT_DIR"]     #输出目录
    input_dir = config["INPUT_DIR"]     #输入目录
    fuzzer_path = config["FUZZER_PATH"]     #fuzzer路径
    fuzz_time = config["FUZZ_TIME"]     #fuzz的时间（s）
    chilo_mutator_path = config["CHILO_MUTATOR_PATH"]     #CHILO变异器路径
    is_use_chilo = config["IS_USE_CHILO"]     #是否使用CHILO变异器
    is_use_squirrel = config["IS_USE_SQUIRREL"]     #是否使用Squirrel变异器
    squirrel_lib_path = config["SQUIRREL_LIB_PATH"]     #Squirrel变异器库路径
    squirrel_config_path = config["SQUIRREL_CONFIG_PATH"]     #Squirrel变异器配置文件路径
    mapsize = config["MAPSIZE"]     #AFL++的mapsize
    testcase_time_limit = config["TESTCASE_TIME_LIMIT"]     #测试用例的时间限制（s）
    testcase_memory_limit = config["TESTCASE_MEMORY_LIMIT"]     #测试用例的内存限制（MB）

    can_fuzz_dbms_list = ["SQLite", "MySQL"]

    if target_dbms not in can_fuzz_dbms_list:
        raise Exception(f"Unsupported DBMS, plz check fuzz_config.yaml. TARGET_DBMS must in {can_fuzz_dbms_list}")

    #2. 设置系统环境（FOR AFL++）
    os.environ["AFL_CUSTOM_MUTATOR_ONLY"] = "1" #只使用客制化变异器
    os.environ["AFL_DISABLE_TRIM"] = "1"    #禁用剪裁
    os.environ["AFL_FAST_CAL"] = "1"    #禁用初期多次执行种子时的路径校准
    os.environ["AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES"] = "1"    #禁用警告
    os.environ["AFL_MAP_SIZE"] = str(mapsize)
    
    # 配置 ASAN 运行时选项（用于 fuzzing）
    os.environ["ASAN_OPTIONS"] = (
        "detect_leaks=0:"                    # 禁用泄漏检测（避免 fuzzing 误报）
        "symbolize=0:"                       # 禁用符号化（fuzzing 阶段优先性能）
        "abort_on_error=1:"                  # 发现错误立即崩溃（AFL 需要）
        "allocator_may_return_null=1:"       # 允许 malloc 失败返回 NULL
        "handle_segv=1:"                     # 捕获段错误
        "handle_sigbus=1:"                   # 捕获总线错误
        "print_summary=0:"                   # 减少输出噪音
        "detect_odr_violation=0:"            # 禁用 ODR 违规检测
        "verify_asan_link_order=0"           # 跳过链接顺序验证
    )
    
    if is_use_chilo:
        os.environ["PYTHONPATH"] = chilo_mutator_path
        os.environ["AFL_PYTHON_MODULE"] = "ChiloMutate"

    if is_use_squirrel:
        if not os.path.exists(squirrel_config_path):
            print("Invalid path for squirrel config file")
            raise Exception(f"Invalid path for squirrel config file: {squirrel_config_path}")
        
        if not os.path.exists(squirrel_lib_path):
            print("Invalid path for squirrel lib file")
            raise Exception(f"Invalid path for squirrel lib file: {squirrel_lib_path}")

        os.environ["AFL_CUSTOM_MUTATOR_LIBRARY"]= squirrel_lib_path
        os.environ["SQUIRREL_CONFIG"] = squirrel_config_path

    if not is_use_chilo and not is_use_squirrel:
        raise Exception("Please set IS_USE_CHILO or IS_USE_SQUIRREL to True")

    #3. 启动FUZZ
    if target_dbms == "SQLite":
        # 处理内存限制参数（ASAN 需要设置为 none）
        mem_limit_arg = "" if testcase_memory_limit == "none" else f"-m {testcase_memory_limit}"

        time_limit_arg = "" if testcase_time_limit == "none" else f"-t {testcase_time_limit}"
        if fuzz_time < 0:
            cmd = f"{fuzzer_path} -i {input_dir} -o {output_dir} {mem_limit_arg} {time_limit_arg} -- /home/ossfuzz @@"
        else:
            cmd = f"{fuzzer_path} -i {input_dir} -o {output_dir} {mem_limit_arg} {time_limit_arg} -V {fuzz_time}  -- /home/ossfuzz @@"
    elif target_dbms == "MySQL":
        # 处理内存限制参数（ASAN 需要设置为 none）
        mem_limit_arg = "" if testcase_memory_limit == "none" else f"-m {testcase_memory_limit}"

        time_limit_arg = "" if testcase_time_limit == "none" else f"-t {testcase_time_limit}"
        if fuzz_time < 0:
            cmd = f"{fuzzer_path} -i {input_dir} -o {output_dir} {mem_limit_arg} {time_limit_arg} -- /home/Squirrel/build/db_driver"
        else:
            cmd = f"{fuzzer_path} -i {input_dir} -o {output_dir} {mem_limit_arg} {time_limit_arg} -V {fuzz_time}  -- /home/Squirrel/build/db_driver"
    else:
        raise Exception(f"Unsupported DBMS, plz check fuzz_config.yaml. TARGET_DBMS must in {can_fuzz_dbms_list}")

    os.system(cmd)


if __name__ == "__main__":
    main()