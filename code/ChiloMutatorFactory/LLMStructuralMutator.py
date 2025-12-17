import time
import random

from .chilo_factory import ChiloFactory
from .crash_library import CrashLibrary


def _get_compact_structural_prompt(sql: str, target_dbms: str, dbms_version: str, crash_examples: str = "") -> str:
    """
    精简版结构化变异提示词 (基于SOFT论文优化)
    
    核心发现：87.4%的SQL函数漏洞由边界值参数处理不当引起
    - 边界字面量 (29.5%): 直接使用极值
    - 边界类型转换 (23.3%): 隐式/显式类型转换  
    - 边界嵌套函数 (34.6%): 函数返回极值结果
    """
    crash_section = ""
    if crash_examples:
        crash_section = f"""
---

## 🔥 CRASH-INDUCING PATTERNS (Real Bugs!)

These SQL patterns have triggered crashes in {target_dbms}. Use similar techniques:

{crash_examples}

**Apply these crash patterns** when enriching the SQL.

"""

    prompt = f"""
You are a DBMS fuzzing expert. Perform **STRUCTURAL MUTATION** on the input SQL to maximize crash probability in {target_dbms} v{dbms_version}.

**Key Insight**: Research shows 87.4% of SQL bugs come from boundary value handling.
{crash_section}---

## Goal

Enrich the SQL by adding 5-15 new statements. Focus on **CRASH-INDUCING PATTERNS**:

---

## 10 Boundary Value Patterns (87.4% of Bugs!)

### Category 1: Boundary Literals (29.5%)
```sql
-- Use extreme values directly
SELECT ABS(9223372036854775807);                    -- MAX_INT
SELECT LENGTH(REPEAT('a', 1000000));                -- Extreme length
SELECT json_extract('{{}}', '$.a');                 -- Empty JSON
SELECT SUBSTR('', 1, 1);                            -- Empty string
```

### Category 2: Type Casting Boundaries (23.3%)
```sql
-- Explicit cast to trigger conversion bugs
SELECT CAST(99999999999999999999 AS INTEGER);       -- Overflow
SELECT CAST('abc' AS REAL);                         -- Invalid conversion
SELECT ABS(CAST(x AS DECIMAL(38,18)));              -- High precision
```

### Category 3: Nested Function Boundaries (34.6%)
```sql
-- Functions returning boundary values as arguments
SELECT json_parse(REPEAT('[', 100000));             -- Stack overflow
SELECT ABS(POWER(2, 63));                           -- MAX_INT from function
SELECT SUBSTR(RANDOMBLOB(1000000), 1, 10);          -- Huge blob
```

### Pattern 1.3 - Insert Repeated Digits
```sql
SELECT json_extract('{{"a":19999999999999999999}}', '$.a');  -- Overflow in JSON
```

### Pattern 1.4 - Malformed Formats
```sql
SELECT json_valid('{{"a":1}}}}}}');                 -- Unbalanced braces
```

---

## Mutation Strategies (Apply 4-6)

| Strategy | Crash-Focused Techniques |
|----------|--------------------------|
| **Subqueries** | Nested 3+ levels, correlated with boundary values |
| **Window Functions** | `ROWS BETWEEN 9223372036854775807 PRECEDING AND ...` |
| **CTEs** | Recursive with `POWER(2, 63)`, deep recursion |
| **Aggregates** | `GROUP_CONCAT` with huge output, `SUM(MAX_INT)` |
| **Type Operations** | `CAST` chains, implicit conversion via UNION |
| **String Functions** | `REPEAT`, `PRINTF('%.*f', MAX_INT, 1.0)` |
| **JSON/XML** | Empty objects, deeply nested, malformed |
| **DML with Boundaries** | `INSERT` extreme values, `UPDATE` with overflow |

---

## Table Usage Rules

1. **Existing tables**: Prefer tables already in the original SQL
2. **New tables allowed**: You MAY create new tables, but MUST:
   - First `CREATE TABLE` with schema
   - Then `INSERT INTO` test data before using
   - Example:
     ```sql
     CREATE TABLE aux(id INTEGER, val TEXT);
     INSERT INTO aux VALUES(1,'a'),(9223372036854775807,'overflow');
     SELECT * FROM aux WHERE id > POWER(2, 62);
     ```
3. **Self-contained**: Every referenced table must exist

---

## Constraints

1. **Keep original SQL** - Include all original statements first
2. **Valid syntax** - Must be valid {target_dbms} v{dbms_version}
3. **5-15 new statements** - Focus on quality over quantity
4. **No comments** in output SQL
5. **Use boundary values** - Prioritize crash-inducing patterns

---

## Input SQL

```sql
{sql}
```

## Output

Return enriched SQL:
```sql
(original + new boundary-value focused statements)
```
"""
    return prompt


def _get_structural_prompt(sql, target_dbms, dbms_version):
    prompt = f"""
You are an expert **SQL fuzzing and coverage engineer**. Your task is to perform **STRUCTURAL MUTATION** on the given SQL test case to maximize code coverage in {target_dbms} v{dbms_version}.

🎯 **PRIMARY OBJECTIVE**: Enrich the SQL test case by adding diverse SQL structures, functions, and statements to explore MORE code paths in the DBMS.

---

## 📋 STRUCTURAL MUTATION STRATEGIES

Apply **3-5** of the following strategies to enrich the input SQL:

### 1. ADD NEW SQL STATEMENTS
Append new statements that interact with existing tables/data:
```sql
-- Create new auxiliary structures
CREATE INDEX IF NOT EXISTS idx_col ON existing_table(column);
CREATE VIEW IF NOT EXISTS v1 AS SELECT * FROM existing_table;
CREATE TRIGGER IF NOT EXISTS trg1 AFTER INSERT ON t BEGIN SELECT 1; END;

-- Add new queries with different patterns
SELECT * FROM existing_table WHERE column IN (SELECT column FROM t2);
SELECT * FROM existing_table GROUP BY column HAVING COUNT(*) > 0;
SELECT * FROM existing_table ORDER BY column LIMIT 10 OFFSET 5;
```

### 2. ADD BUILT-IN FUNCTIONS
Introduce various {target_dbms} built-in functions:

**Aggregate Functions**:
- SUM(), AVG(), COUNT(), MAX(), MIN(), TOTAL(), GROUP_CONCAT()

**Scalar Functions**:
- ABS(), COALESCE(), IFNULL(), NULLIF(), IIF(), TYPEOF(), QUOTE()
- LENGTH(), UPPER(), LOWER(), TRIM(), LTRIM(), RTRIM(), SUBSTR(), REPLACE(), INSTR()
- HEX(), UNHEX(), ZEROBLOB(), RANDOMBLOB(), RANDOM(), UNICODE(), CHAR()
- ROUND(), PRINTF(), LIKELIHOOD(), LIKELY(), UNLIKELY()

**Date/Time Functions**:
- date(), time(), datetime(), julianday(), strftime(), unixepoch()

**Window Functions**:
- ROW_NUMBER(), RANK(), DENSE_RANK(), NTILE(), LAG(), LEAD()
- FIRST_VALUE(), LAST_VALUE(), NTH_VALUE()
- SUM/AVG/COUNT OVER (PARTITION BY ... ORDER BY ...)

Example:
```sql
SELECT 
    column,
    ROW_NUMBER() OVER (ORDER BY column) as rn,
    LAG(column, 1) OVER (ORDER BY column) as prev_val,
    SUM(column) OVER (PARTITION BY category) as category_sum
FROM existing_table;
```

### 3. ADD SUBQUERIES
Introduce subqueries in various positions:
```sql
-- Scalar subquery
SELECT (SELECT MAX(id) FROM t) as max_id, * FROM existing_table;

-- EXISTS/NOT EXISTS
SELECT * FROM t1 WHERE EXISTS (SELECT 1 FROM t2 WHERE t2.id = t1.id);

-- IN/NOT IN
SELECT * FROM t1 WHERE column IN (SELECT column FROM t2);

-- FROM clause subquery
SELECT * FROM (SELECT *, ROWID FROM existing_table) AS sub WHERE sub.ROWID > 0;

-- Correlated subquery
SELECT *, (SELECT COUNT(*) FROM t2 WHERE t2.fk = t1.pk) as ref_count FROM t1;
```

### 4. ADD COMMON TABLE EXPRESSIONS (CTE)
Introduce WITH clauses:
```sql
WITH 
    cte1 AS (SELECT * FROM existing_table WHERE column > 0),
    cte2 AS (SELECT column, COUNT(*) as cnt FROM cte1 GROUP BY column)
SELECT * FROM cte1 JOIN cte2 ON cte1.column = cte2.column;

-- Recursive CTE (moderate recursion, 10-100 iterations)
WITH RECURSIVE cnt(x) AS (
    SELECT 1
    UNION ALL
    SELECT x+1 FROM cnt WHERE x < 50
)
SELECT * FROM cnt;
```

### 5. ADD JOIN VARIATIONS
Introduce different join types:
```sql
SELECT * FROM t1 INNER JOIN t2 ON t1.id = t2.fk;
SELECT * FROM t1 LEFT JOIN t2 ON t1.id = t2.fk;
SELECT * FROM t1 CROSS JOIN t2;
SELECT * FROM t1 NATURAL JOIN t2;
SELECT * FROM t1, t2 WHERE t1.id = t2.fk;  -- implicit join
```

### 6. ADD CASE/IIF EXPRESSIONS
Introduce conditional expressions:
```sql
SELECT 
    CASE 
        WHEN column > 100 THEN 'high'
        WHEN column > 50 THEN 'medium'
        ELSE 'low'
    END as category,
    IIF(column IS NULL, 0, column) as safe_value
FROM existing_table;
```

### 7. ADD TYPE CONVERSIONS
Introduce CAST expressions:
```sql
SELECT 
    CAST(column AS TEXT) as text_val,
    CAST(column AS REAL) as real_val,
    CAST(column AS INTEGER) as int_val,
    CAST(column AS BLOB) as blob_val
FROM existing_table;
```

### 8. ADD COMPOUND QUERIES
Introduce UNION/INTERSECT/EXCEPT:
```sql
SELECT column FROM t1
UNION ALL
SELECT column FROM t2
EXCEPT
SELECT column FROM t3;
```

### 9. ADD AGGREGATE WITH GROUPING
Introduce GROUP BY with various features:
```sql
SELECT 
    category,
    COUNT(*) as cnt,
    SUM(value) as total,
    AVG(value) as avg_val,
    GROUP_CONCAT(name, ', ') as names
FROM existing_table
GROUP BY category
HAVING COUNT(*) > 1
ORDER BY total DESC;
```

### 10. ADD INSERT/UPDATE/DELETE VARIATIONS
Introduce data modification statements:
```sql
INSERT INTO t SELECT * FROM t WHERE 0;  -- no-op insert with subquery
INSERT OR REPLACE INTO t VALUES (...);
INSERT OR IGNORE INTO t VALUES (...);
UPDATE t SET column = column + 1 WHERE column > 0;
UPDATE t SET column = (SELECT MAX(column) FROM t) WHERE ROWID = 1;
DELETE FROM t WHERE column IN (SELECT column FROM t2);
```

### 11. ADD VIRTUAL TABLES (if applicable)
Introduce special table types:
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS ft USING fts5(content);
INSERT INTO ft VALUES ('test content');
SELECT * FROM ft WHERE ft MATCH 'test';
```

### 12. ADD EXPRESSION COMPLEXITY
Combine operators and functions:
```sql
SELECT 
    ABS(column1 - column2) * 100.0 / NULLIF(column1, 0) as pct_diff,
    COALESCE(column1, column2, 0) as merged_value,
    SUBSTR(text_col, 1, INSTR(text_col, ' ') - 1) as first_word,
    PRINTF('%08d', column) as formatted
FROM existing_table;
```

---

## ⚠️ CONSTRAINTS

1. **Keep existing SQL**: Include the original SQL statements (may modify slightly)
2. **Syntactic validity**: All SQL must be valid for {target_dbms} v{dbms_version}
3. **Reasonable size**: Add 5-15 new statements, total output should be manageable
4. **Use existing tables**: Reference tables created in the original SQL
5. **Moderate values**: Use reasonable numeric values (avoid extreme overflow values)
6. **Pure SQL output**: No comments, no explanations in the code block

---

## 📥 INPUT TEST CASE

Enrich this SQL with diverse structures:

```sql
{sql}
```

---

## 📤 OUTPUT FORMAT

Return the enriched SQL wrapped as:

```sql
(original SQL + new diverse statements here)
```

**Remember**: 
- Keep the original SQL's table structures
- Add diverse functions, subqueries, joins, CTEs
- Goal is CODE COVERAGE, not just crashes
- Make the test case RICHER and explore more DBMS code paths
"""
    return prompt


def structural_mutator(my_chilo_factory: ChiloFactory):
    """
    实现SQL的结构性变异
    :return: 无返回值
    """
    structural_count = 0
    my_chilo_factory.structural_mutator_logger.info("结构化变异器已启动！")
    
    # 初始化crash案例库（AFL crashes目录 + CVE案例文件夹）
    crash_library = CrashLibrary(
        afl_output_dir=my_chilo_factory.afl_output_dir,
        cve_cases_path=my_chilo_factory.cve_cases_path,
        target_dbms=my_chilo_factory.target_dbms
    )
    afl_count, cve_count = crash_library.get_case_count()
    my_chilo_factory.structural_mutator_logger.info(f"Crash案例库已加载: AFL crashes={afl_count}, CVE案例={cve_count}")
    
    system_prompt = """You are an expert SQL fuzzing and coverage engineer. Your mission is to enrich SQL test cases to maximize code coverage AND trigger crashes in database systems. You have deep knowledge of:
- SQL syntax and semantics across different DBMS
- Built-in functions: aggregate, scalar, window, date/time functions
- Query structures: subqueries, CTEs, JOINs, compound queries
- DDL statements: CREATE TABLE/INDEX/VIEW/TRIGGER
- DML variations: INSERT/UPDATE/DELETE with various clauses
- Known crash patterns: integer overflow, deep recursion, edge cases

Your goal is to make SQL test cases RICHER, more DIVERSE, and more likely to trigger bugs."""
    while True:
        structural_mutate_start_time = time.time()
        structural_count += 1
        all_up_token = 0
        all_down_token = 0
        llm_count = 0
        llm_error_count = 0
        llm_use_time = 0
        my_chilo_factory.structural_mutator_logger.info("结构化变异器等待任务中")
        need_structural_mutate = my_chilo_factory.structural_mutator_list.get()  #拿出一个需要结构化变异的
        target_seed_id = need_structural_mutate["seed_id"]
        my_chilo_factory.structural_mutator_logger.info(f"结构化变异器接收到变异任务，seed_id：{target_seed_id}")
        seed_sql = my_chilo_factory.all_seed_list.seed_list[target_seed_id].seed_sql
        
        # 从crash库随机选取2-3个案例（动态读取，每次都可能获取到新的AFL crash）
        crash_examples = crash_library.format_cases_for_prompt(count=random.randint(2, 3))
        afl_count, cve_count = crash_library.get_case_count()  # 实时更新统计
        
        # 根据配置选择提示词版本
        if my_chilo_factory.use_compact_prompt:
            prompt = _get_compact_structural_prompt(seed_sql, my_chilo_factory.target_dbms, 
                                                    my_chilo_factory.target_dbms_version, crash_examples)
            my_chilo_factory.structural_mutator_logger.info(f"seed_id：{target_seed_id}，使用精简版提示词（AFL crashes={afl_count}, CVE案例={cve_count}）")
        else:
            prompt = _get_structural_prompt(seed_sql, my_chilo_factory.target_dbms, my_chilo_factory.target_dbms_version)
            my_chilo_factory.structural_mutator_logger.info(f"seed_id：{target_seed_id}，使用完整版提示词")
        
        structural_mutate_success = False
        while True:
            structural_mutate_llm_start_time = time.time()
            my_chilo_factory.structural_mutator_logger.info(f"seed_id：{target_seed_id}，准备调用LLM进行结构化变异")
            after_mutate_testcase,up_token, down_token = my_chilo_factory.llm_tool_structural_mutator.chat_llm(prompt, system_prompt)
            all_up_token += up_token
            all_down_token += down_token
            llm_count += 1
            structural_mutate_llm_end_time = time.time()
            llm_use_time += structural_mutate_llm_end_time - structural_mutate_llm_start_time
            my_chilo_factory.structural_mutator_logger.info(f"seed_id：{target_seed_id}，调用LLM结束，用时：{structural_mutate_llm_end_time-structural_mutate_llm_start_time:.2f}s")
            after_mutate_testcase = my_chilo_factory.llm_tool_structural_mutator.get_sql_block_content(after_mutate_testcase)  # 提取内容
            try:
                after_mutate_testcase = after_mutate_testcase[0]
                structural_mutate_success = True
                break
            except:
                #说明生成格式出现错误，需要从新生成
                llm_error_count += 1
                my_chilo_factory.structural_mutator_logger.warning(f"seed_id：{target_seed_id}，LLM生成格式错误（第{llm_error_count}次），正在重新生成")
                # 检查是否超过最大重试次数
                if llm_error_count >= my_chilo_factory.llm_format_error_max_retry:
                    my_chilo_factory.structural_mutator_logger.error(
                        f"seed_id：{target_seed_id}，格式错误次数超过上限{my_chilo_factory.llm_format_error_max_retry}，使用原始SQL")
                    after_mutate_testcase = seed_sql  # 使用原始SQL作为fallback
                    structural_mutate_success = True  # 标记为成功以继续流程
                    break
                continue

        # 只有成功才加入种子池
        if not structural_mutate_success:
            my_chilo_factory.structural_mutator_logger.warning(f"seed_id：{target_seed_id}，结构化变异失败，跳过")
            continue  # 跳过后续处理，继续下一个任务

        my_chilo_factory.structural_mutator_logger.info(f"seed_id：{target_seed_id}，正在加入到种子池中")
        _, new_seed_id = my_chilo_factory.all_seed_list.add_seed_to_list(after_mutate_testcase.encode("utf-8"))
        with open(f"{my_chilo_factory.structural_mutator_path}{structural_count}_{target_seed_id}_{new_seed_id}.txt", "w", encoding="utf-8") as f:
            f.write(after_mutate_testcase)
        my_chilo_factory.structural_mutator_logger.info(f"seed_id：{target_seed_id}，变异后，新的seed_id为：{new_seed_id}，已保存到文件{structural_count}_{target_seed_id}_{new_seed_id}.txt")
        my_chilo_factory.wait_exec_structural_list.put({"seed_id": new_seed_id, "is_from_structural_mutator": True, "mutate_content": after_mutate_testcase})
        my_chilo_factory.structural_mutator_logger.info(f"seed_id：{new_seed_id}，已加入等待执行结构化变异队列")
        my_chilo_factory.structural_mutator_logger.info("-" * 10)
        structural_mutate_end_time = time.time()
        my_chilo_factory.write_structural_mutator_csv(structural_mutate_end_time, target_seed_id, new_seed_id, structural_mutate_end_time-structural_mutate_start_time,
                                                      all_up_token, all_down_token, llm_count, llm_error_count, llm_use_time, my_chilo_factory.structural_mutator_list.qsize())

        