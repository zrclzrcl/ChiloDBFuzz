"""
Crash案例库管理模块

两个来源：
1. AFL crashes目录 - 动态读取fuzzing过程中触发的真实crash
2. CVE案例文件夹 - 预置的已知漏洞SQL案例

每次结构化变异时，从两个来源中随机选取2-3个案例指导LLM生成
"""

import os
import random
import glob
from typing import List, Tuple
from pathlib import Path


class CrashLibrary:
    """
    Crash案例库
    
    来源1: AFL crashes目录 (动态)
      - 路径: {afl_output}/default/crashes/
      - 实时读取fuzzing触发的crash
    
    来源2: CVE案例文件夹 (静态)
      - 路径: 配置的cve_cases_path
      - 预置的已知漏洞SQL案例，每个文件一个案例
    """
    
    def __init__(self, afl_output_dir: str, cve_cases_path: str, target_dbms: str):
        """
        初始化crash案例库
        :param afl_output_dir: AFL输出目录 (如 ../../afl_output/)
        :param cve_cases_path: CVE案例文件夹路径 (如 ../../cve_cases/)
        :param target_dbms: 目标数据库类型
        """
        self.afl_output_dir = afl_output_dir
        self.cve_cases_path = cve_cases_path
        self.target_dbms = target_dbms.lower()
        
        # AFL crashes目录路径 (AFL++默认结构)
        self.afl_crashes_dir = os.path.join(afl_output_dir, "default", "crashes")
        
        # 确保CVE案例目录存在
        self._ensure_cve_dir()
    
    def _ensure_cve_dir(self):
        """确保CVE案例目录存在，如果不存在则创建并放入默认案例"""
        if not os.path.exists(self.cve_cases_path):
            os.makedirs(self.cve_cases_path, exist_ok=True)
            self._create_default_cve_cases()
    
    def _create_default_cve_cases(self):
        """创建默认的CVE案例文件"""
        default_cases = {
            # SQLite CVE和已知crash模式
            "cve_window_overflow.sql": {
                "content": "SELECT SUM(x) OVER (ORDER BY y ROWS BETWEEN 9223372036854775807 PRECEDING AND 1 FOLLOWING) FROM t;",
                "comment": "-- CVE-like: Window frame integer overflow"
            },
            "cve_recursive_cte.sql": {
                "content": "WITH RECURSIVE r(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM r WHERE x < 10000000) SELECT * FROM r;",
                "comment": "-- CVE-like: Recursive CTE stack overflow"
            },
            "cve_nested_subquery.sql": {
                "content": "SELECT * FROM t1 WHERE x IN (SELECT x FROM t1 WHERE y IN (SELECT y FROM t1 WHERE z IN (SELECT z FROM t1)));",
                "comment": "-- CVE-like: Deep nested subquery"
            },
            "cve_printf_overflow.sql": {
                "content": "SELECT printf('%.*f', 2147483647, 1.0);",
                "comment": "-- CVE-2015-3416: printf precision overflow"
            },
            "cve_fts_match.sql": {
                "content": "CREATE VIRTUAL TABLE ft USING fts3(content); SELECT * FROM ft WHERE content MATCH '\"a b c d e f g h i j k l m n o p q r s t u v w x y z\"*';",
                "comment": "-- CVE-like: FTS3 complex MATCH pattern"
            },
            "cve_group_concat.sql": {
                "content": "SELECT GROUP_CONCAT(DISTINCT x, CHAR(0)) FROM t GROUP BY y HAVING LENGTH(GROUP_CONCAT(x)) > 1000000;",
                "comment": "-- CVE-like: GROUP_CONCAT memory exhaustion"
            },
            "cve_cast_overflow.sql": {
                "content": "SELECT CAST(99999999999999999999999999999999999999999999999999 AS INTEGER);",
                "comment": "-- CVE-like: Integer cast overflow"
            },
            "cve_zeroblob.sql": {
                "content": "SELECT ZEROBLOB(2147483647);",
                "comment": "-- CVE-like: ZEROBLOB memory exhaustion"
            },
            "cve_json_path.sql": {
                "content": "SELECT json_extract('{\"a\":1}', '$.' || RANDOMBLOB(10000));",
                "comment": "-- CVE-like: JSON path with binary data"
            },
            "cve_alter_default.sql": {
                "content": "ALTER TABLE t ADD COLUMN c DEFAULT (SELECT MAX(x) FROM t WHERE x > (SELECT AVG(y) FROM t));",
                "comment": "-- CVE-like: ALTER with complex DEFAULT subquery"
            },
            "cve_trigger_recursion.sql": {
                "content": "CREATE TRIGGER tr1 AFTER INSERT ON t BEGIN INSERT INTO t VALUES(NEW.x + 1); END;",
                "comment": "-- CVE-like: Trigger infinite recursion"
            },
            "cve_view_recursion.sql": {
                "content": "CREATE VIEW v1 AS SELECT * FROM v1;",
                "comment": "-- CVE-like: Self-referencing view"
            }
        }
        
        for filename, data in default_cases.items():
            filepath = os.path.join(self.cve_cases_path, filename)
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"{data['comment']}\n{data['content']}\n")
            except Exception as e:
                print(f"[CrashLibrary] 创建默认案例 {filename} 失败: {e}")
    
    def get_afl_crashes(self) -> List[Tuple[str, str]]:
        """
        从AFL crashes目录读取crash案例
        :return: [(crash内容, 来源描述), ...]
        """
        crashes = []
        
        if not os.path.exists(self.afl_crashes_dir):
            return crashes
        
        try:
            # 读取crashes目录下的所有文件（排除README.txt）
            crash_files = [f for f in os.listdir(self.afl_crashes_dir) 
                          if os.path.isfile(os.path.join(self.afl_crashes_dir, f))
                          and not f.startswith('README')]
            
            for crash_file in crash_files:
                filepath = os.path.join(self.afl_crashes_dir, crash_file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().strip()
                        if content:  # 只添加非空内容
                            crashes.append((content, f"AFL crash: {crash_file}"))
                except Exception as e:
                    continue  # 跳过无法读取的文件
        except Exception as e:
            print(f"[CrashLibrary] 读取AFL crashes目录失败: {e}")
        
        return crashes
    
    def get_cve_cases(self) -> List[Tuple[str, str]]:
        """
        从CVE案例文件夹读取案例
        :return: [(案例内容, 来源描述), ...]
        """
        cases = []
        
        if not os.path.exists(self.cve_cases_path):
            return cases
        
        try:
            # 读取所有.sql文件
            sql_files = glob.glob(os.path.join(self.cve_cases_path, "*.sql"))
            
            for sql_file in sql_files:
                try:
                    with open(sql_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            # 提取文件名作为描述
                            filename = os.path.basename(sql_file)
                            # 提取注释作为描述（如果有）
                            lines = content.split('\n')
                            description = filename
                            sql_content = content
                            
                            if lines[0].startswith('--'):
                                description = lines[0][2:].strip()
                                sql_content = '\n'.join(lines[1:]).strip()
                            
                            if sql_content:
                                cases.append((sql_content, f"CVE: {description}"))
                except Exception as e:
                    continue
        except Exception as e:
            print(f"[CrashLibrary] 读取CVE案例目录失败: {e}")
        
        return cases
    
    def get_all_cases(self) -> List[Tuple[str, str]]:
        """
        获取所有crash案例（AFL + CVE）
        :return: [(案例内容, 来源描述), ...]
        """
        all_cases = []
        all_cases.extend(self.get_afl_crashes())
        all_cases.extend(self.get_cve_cases())
        return all_cases
    
    def get_random_cases(self, count: int = 3) -> List[Tuple[str, str]]:
        """
        随机获取指定数量的crash案例
        优先从AFL crashes中选取（真实触发的更有价值），再补充CVE案例
        :param count: 需要的案例数量
        :return: [(案例内容, 来源描述), ...]
        """
        afl_crashes = self.get_afl_crashes()
        cve_cases = self.get_cve_cases()
        
        selected = []
        
        # 优先选取AFL crashes（最多选一半）
        if afl_crashes:
            afl_count = min(len(afl_crashes), (count + 1) // 2)  # 最多一半来自AFL
            selected.extend(random.sample(afl_crashes, afl_count))
        
        # 剩余数量从CVE案例中选取
        remaining = count - len(selected)
        if remaining > 0 and cve_cases:
            cve_count = min(len(cve_cases), remaining)
            selected.extend(random.sample(cve_cases, cve_count))
        
        # 如果还不够，继续从AFL中选取
        remaining = count - len(selected)
        if remaining > 0 and afl_crashes:
            available = [c for c in afl_crashes if c not in selected]
            if available:
                selected.extend(random.sample(available, min(len(available), remaining)))
        
        return selected
    
    def format_cases_for_prompt(self, cases: List[Tuple[str, str]] = None, count: int = 3) -> str:
        """
        将案例格式化为提示词中可用的字符串
        :param cases: 案例列表，如果为None则随机选择
        :param count: 随机选择的数量
        :return: 格式化的字符串
        """
        if cases is None:
            cases = self.get_random_cases(count)
        
        if not cases:
            return ""
        
        result = []
        for i, (sql, source) in enumerate(cases, 1):
            result.append(f"### Example {i}: {source}")
            # 截断过长的SQL
            display_sql = sql if len(sql) <= 500 else sql[:500] + "\n... (truncated)"
            result.append(f"```sql\n{display_sql}\n```\n")
        
        return "\n".join(result)
    
    def get_case_count(self) -> Tuple[int, int]:
        """
        获取案例数量
        :return: (AFL crashes数量, CVE案例数量)
        """
        return len(self.get_afl_crashes()), len(self.get_cve_cases())
    
    def get_total_count(self) -> int:
        """获取总案例数量"""
        afl, cve = self.get_case_count()
        return afl + cve

