
"""
用于调用LLM对SQL种子进行解析.
"""
import os
import time
import queue
from collections import deque

from .chilo_factory import ChiloFactory

def _get_constant_prompt(ori_sql, target_dbms, dbms_version):
    prompt = f"""
Instruction: You are a **DBMS fuzzing expert**. Your task is to identify and annotate all **mutable components** in the given SQL test case.

---

### Target DBMS
{target_dbms} version {dbms_version}

---

### Annotation Types

You must identify and annotate the following 4 types of mutable components:

#### 1. CONSTANT - Literal Values
Any literal constant in the SQL: numbers, strings, dates, blobs, NULL, etc.

Examples:
- Numbers: `42`, `-1`, `3.14`, `9223372036854775807`
- Strings: `'hello'`, `"world"`
- NULL: `NULL`
- Blobs: `x'1234'`

Annotation format:
```
[CONSTANT, number:X, type:<inferred_type>, ori:<original_value>]
```

#### 2. OPERATOR - Operators
Any operator that can be replaced with similar operators.

Examples:
- Arithmetic: `+`, `-`, `*`, `/`, `%`
- Comparison: `>`, `<`, `>=`, `<=`, `=`, `!=`, `<>`
- Logical: `AND`, `OR`
- Bitwise: `&`, `|`, `<<`, `>>`

Annotation format:
```
[OPERATOR, number:X, category:<arithmetic|comparison|logical|bitwise>, ori:<original_operator>]
```

#### 3. FUNCTION - Function Names
Built-in function names that can be replaced with similar functions.

Examples:
- Aggregate: `SUM`, `AVG`, `COUNT`, `MAX`, `MIN`
- Scalar: `ABS`, `ROUND`, `UPPER`, `LOWER`, `LENGTH`
- Date: `datetime`, `date`, `julianday`

Annotation format:
```
[FUNCTION, number:X, category:<aggregate|scalar_numeric|scalar_string|datetime>, ori:<original_function>]
```

**Important**: Only annotate the function NAME, not the parentheses or arguments.
Example: `SUM(x)` → `[FUNCTION, number:1, category:aggregate, ori:SUM](x)`

#### 4. KEYWORD - Mutable Keywords
Keywords that can be changed to alter SQL behavior, but NOT core SQL structure keywords.

**Mutable keywords** (should be annotated):
- Constraint keywords: `NOT NULL`, `UNIQUE`, `PRIMARY KEY`, `FOREIGN KEY`
- Conflict resolution: `OR REPLACE`, `OR IGNORE`, `OR FAIL`, `OR ABORT`, `OR ROLLBACK`
- Modifiers: `DISTINCT`, `ALL`
- Temporality: `TEMPORARY`, `TEMP`
- Existence checks: `IF EXISTS`, `IF NOT EXISTS`
- Join types: `INNER`, `LEFT`, `RIGHT`, `CROSS`, `OUTER`
- Order: `ASC`, `DESC`
- Transaction types: `DEFERRED`, `IMMEDIATE`, `EXCLUSIVE`
- Trigger timing: `BEFORE`, `AFTER`, `INSTEAD OF`
- Foreign key actions: `CASCADE`, `SET NULL`, `RESTRICT`, `NO ACTION`
- Collation: `COLLATE BINARY`, `COLLATE NOCASE`, `COLLATE RTRIM`

**Immutable keywords** (DO NOT annotate):
- Core structure: `SELECT`, `FROM`, `WHERE`, `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `DROP`, `ALTER`, `TABLE`, `INDEX`, `VIEW`, `TRIGGER`
- Data definition: `INT`, `INTEGER`, `REAL`, `TEXT`, `BLOB` (treat as immutable for simplicity)
- Control flow: `BEGIN`, `END`, `IF`, `THEN`, `ELSE`

Annotation format:
```
[KEYWORD, number:X, context:<brief_context>, ori:<original_keyword_phrase>]
```

Example contexts:
- `context:constraint` - for NOT NULL, UNIQUE
- `context:conflict` - for OR REPLACE, OR IGNORE
- `context:modifier` - for DISTINCT, ALL
- `context:join` - for INNER, LEFT
- `context:order` - for ASC, DESC

---

### Annotation Rules

1. **Numbering**: Start from 1, increment sequentially, no duplicates.

2. **Do NOT annotate**:
   - Table names, column names, aliases
   - Core SQL keywords (SELECT, FROM, WHERE, etc.)
   - Schema identifiers
   - Parentheses, commas, semicolons

3. **Executability**: The annotated SQL must remain syntactically valid after replacing masks with their original values.

4. **Consecutive keywords**: If multiple mutable keywords appear together, annotate them as ONE mask.
   Example: `NOT NULL` → `[KEYWORD, number:1, context:constraint, ori:NOT NULL]`
   Example: `IF NOT EXISTS` → `[KEYWORD, number:2, context:existence_check, ori:IF NOT EXISTS]`

5. **Output format**: Wrap the result in:
   ```sql
   (annotated SQL)
   ```

---

### Examples

**Input 1:**
```sql
CREATE TABLE t (x INTEGER PRIMARY KEY, y TEXT NOT NULL);
INSERT INTO t VALUES (10, 'hello');
SELECT SUM(x) FROM t WHERE x > 5 ORDER BY y DESC;
```

**Output 1:**
```sql
CREATE TABLE t (
    x INTEGER [KEYWORD, number:1, context:constraint, ori:PRIMARY KEY], 
    y TEXT [KEYWORD, number:2, context:constraint, ori:NOT NULL]
);
INSERT INTO t VALUES (
    [CONSTANT, number:3, type:integer, ori:10], 
    [CONSTANT, number:4, type:string, ori:hello]
);
SELECT [FUNCTION, number:5, category:aggregate, ori:SUM](x) 
FROM t 
WHERE x [OPERATOR, number:6, category:comparison, ori:>] [CONSTANT, number:7, type:integer, ori:5] 
ORDER BY y [KEYWORD, number:8, context:order, ori:DESC];
```

**Input 2:**
```sql
INSERT OR REPLACE INTO t VALUES (1);
SELECT AVG(a + b) FROM t WHERE c != 10;
```

**Output 2:**
```sql
INSERT [KEYWORD, number:1, context:conflict, ori:OR REPLACE] INTO t VALUES ([CONSTANT, number:2, type:integer, ori:1]);
SELECT [FUNCTION, number:3, category:aggregate, ori:AVG](
    a [OPERATOR, number:4, category:arithmetic, ori:+] b
) 
FROM t 
WHERE c [OPERATOR, number:5, category:comparison, ori:!=] [CONSTANT, number:6, type:integer, ori:10];
```

---

### Now Annotate

Please annotate the following SQL for fuzzing {target_dbms} version {dbms_version}:

```sql
{ori_sql}
```

**Remember**: 
- Annotate CONSTANT, OPERATOR, FUNCTION, KEYWORD
- Do NOT provide alternative values
- Ensure the result is syntactically valid
"""
    return prompt

def chilo_parser(chilo_factory: ChiloFactory):
    #这里需要单独启动一个线程，用于对SQL进行处理
    chilo_factory.parser_logger.info("解析器启动成功！")
    
    # 初始化本地栈（有界栈，自动淘汰栈底）
    MAX_STACK_SIZE = chilo_factory.parser_stack_max_size
    local_stack = deque(maxlen=MAX_STACK_SIZE)
    # 维护一个无界回流队列，用于承接被栈淘汰的种子
    reflow_queue = deque()
    # 交替来源：True 表示优先从栈取，False 表示优先从回流队列取
    use_stack_next = True
    chilo_factory.parser_logger.info(f"Parser栈初始化完成，最大大小：{MAX_STACK_SIZE}")
    
    while True:
        # === 步骤1: 尝试从wait_parse_list中取出一个种子，压入栈中 ===
        try:
            parse_target = chilo_factory.wait_parse_list.get(timeout=0.1)
            seed_id = parse_target['seed_id']
            
            # 检查栈是否会满（即将淘汰）
            if len(local_stack) >= MAX_STACK_SIZE:
                victim = local_stack[0] if local_stack else None  # 栈底（最老的）
                if victim:
                    evicted_total = chilo_factory.record_parser_eviction()
                    chilo_factory.parser_logger.warning(
                        f"Parser栈已满，淘汰栈底种子{victim['seed_id']} "
                        f"(已淘汰总数:{evicted_total})"
                    )
            
            # 压栈（deque会自动淘汰最老的）
            local_stack.append(parse_target)
            # 如发生淘汰，则将被淘汰的种子回流到无界队列中
            if 'victim' in locals() and victim:
                reflow_queue.append(victim)
                chilo_factory.parser_logger.info(
                    f"Parser: 淘汰种子{victim['seed_id']}已回流到队列 "
                    f"(回流队列大小:{len(reflow_queue)})"
                )
            chilo_factory.parser_logger.info(
                f"Parser: 种子{seed_id}已压栈 (栈大小:{len(local_stack)}/{MAX_STACK_SIZE})"
            )
        except queue.Empty:
            pass  # 没有新种子，继续执行
        
        # === 步骤2: 检查下游队列wait_mutator_generate_list是否已满 ===
        if chilo_factory.wait_mutator_generate_list.full():
            # 下游已满，什么都不做（不解析，省API）
            if local_stack:
                chilo_factory.parser_logger.debug(
                    f"Parser: 下游队列已满，暂停解析 "
                    f"(栈中待处理:{len(local_stack)}, 下游队列:{chilo_factory.wait_mutator_generate_list.qsize()}/{chilo_factory.mutator_generator_queue_max_size})"
                )
            time.sleep(0.1)  # 短暂等待，避免CPU空转
            continue
        
        # === 步骤3: 下游有空位，交替从“栈/回流队列”取出一个种子解析 ===
        source = None
        # 按优先来源选择
        if use_stack_next and local_stack:
            source = 'stack'
        elif (not use_stack_next) and reflow_queue:
            source = 'reflow'
        else:
            # 若优先来源为空，则尝试另一个来源
            if local_stack:
                source = 'stack'
            elif reflow_queue:
                source = 'reflow'
            else:
                # 两个来源都为空，继续下一轮
                continue

        # 实际取出
        if source == 'stack':
            parse_target = local_stack.pop()  # LIFO
        else:
            parse_target = reflow_queue.popleft()  # FIFO
        # 翻转优先来源以实现交替
        use_stack_next = not use_stack_next

        seed_id = parse_target['seed_id']
        chilo_factory.parser_logger.info(
            (f"Parser: 从栈弹出种子{seed_id}进行解析 (栈剩余:{len(local_stack)}, 回流队列:{len(reflow_queue)})"
             if source == 'stack' else
             f"Parser: 从回流队列取出种子{seed_id}进行解析 (栈剩余:{len(local_stack)}, 回流队列:{len(reflow_queue)})")
        )
        
        # === 步骤4: 开始解析流程 ===
        all_start_time = time.time()
        llm_usd_time_all = 0
        up_token_all = 0
        down_token_all = 0
        llm_use_count = 0
        llm_format_error_count = 0
        
        # 判断该目标是否已经被解析过
        if chilo_factory.all_seed_list.seed_list[seed_id].is_parsed:
            # 说明已经被解析过了，直接将这个种子加入待变异队列
            chilo_factory.parser_logger.info(f"seed_id:{seed_id} 已经被解析过，正在放入变异器生成队列")
            chilo_factory.wait_mutator_generate_list.put(parse_target)
            chilo_factory.parser_logger.info(f"seed_id:{seed_id} 放入变异器生成队列成功")
            tmp_seed_is_fuzz_flag_for_csv = 1
        else:
            # 说明还没有被解析过，需要先进行解析...
            chilo_factory.parser_logger.info(f"seed_id:{seed_id} 没有被解析过，进入解析过程")
            need_parse_sql = chilo_factory.all_seed_list.seed_list[seed_id].seed_sql
            while True:
                parse_start_time = time.time()
                chilo_factory.parser_logger.info(f"seed_id:{seed_id} 调用LLM解析开始")
                prompt = _get_constant_prompt(need_parse_sql, chilo_factory.target_dbms, chilo_factory.target_dbms_version)
                parse_msg, up_token, down_token = chilo_factory.llm_tool_parser.chat_llm(prompt)
                up_token_all += up_token
                down_token_all += down_token
                parser_end_time = time.time()
                llm_use_count += 1
                chilo_factory.parser_logger.info(
                    f"seed_id:{seed_id} LLM解析结束，用时：{parser_end_time - parse_start_time:.2f}s")
                llm_usd_time_all += parser_end_time - parse_start_time
                parse_msg = chilo_factory.llm_tool_parser.get_sql_block_content(parse_msg)
                try:
                    parse_msg = parse_msg[0]
                    break
                except:
                    llm_format_error_count += 1
                    chilo_factory.parser_logger.warning(f"seed_id:{seed_id} LLM解析内容提取失败，LLM生成格式错误（第{llm_format_error_count}次），重新解析...")
                    # 检查是否超过最大重试次数
                    if llm_format_error_count >= chilo_factory.llm_format_error_max_retry:
                        chilo_factory.parser_logger.error(f"seed_id:{seed_id} 解析格式错误次数超过上限{chilo_factory.llm_format_error_max_retry}，放弃该种子")
                        parse_msg = need_parse_sql  # 使用原始SQL作为fallback
                        break
            chilo_factory.parser_logger.info(
                f"seed_id:{seed_id} LLM解析内容提取成功")
            save_parsed_sql_path = os.path.join(chilo_factory.parsed_sql_path, f"{seed_id}.txt")
            chilo_factory.parser_logger.info(
                f"seed_id:{seed_id} 解析结果存入文件中")
            with open(save_parsed_sql_path, "w", encoding="utf-8") as f:
                f.write(parse_msg)  #保存到文件中
            chilo_factory.parser_logger.info(
                f"seed_id:{seed_id} 解析结果存入文件成功")
            chilo_factory.all_seed_list.seed_list[seed_id].parser_content = parse_msg
            chilo_factory.all_seed_list.seed_list[seed_id].is_parsed = True
            
            # 计算掩码数量 (Ci 因子)
            mask_count = parse_msg.count('[')
            chilo_factory.all_seed_list.seed_list[seed_id].mask_count = mask_count
            chilo_factory.parser_logger.info(f"seed_id:{seed_id} 掩码数量统计: {mask_count}")
            
            # 然后要将这个加入到待变异中
            chilo_factory.parser_logger.info(
                f"seed_id:{seed_id} 准备加入到变异器待生成队列中")
            chilo_factory.wait_mutator_generate_list.put(parse_target)
            tmp_seed_is_fuzz_flag_for_csv = 0
            chilo_factory.parser_logger.info(f"seed_id:{seed_id} 放入变异器生成队列成功")
            chilo_factory.parser_logger.info(f"-"*10)
        
        # === 步骤5: 记录CSV ===
        left_parser_queue_size = chilo_factory.wait_parse_list.qsize()
        all_end_time = time.time()
        evicted_seed_total = chilo_factory.get_parser_evicted_seed_count()
        chilo_factory.write_parser_csv(all_end_time, seed_id, parse_target['mutate_time'],
                                       tmp_seed_is_fuzz_flag_for_csv, llm_usd_time_all, up_token_all, down_token_all,
                                       llm_use_count, llm_format_error_count, all_end_time-all_start_time,
                                       chilo_factory.all_seed_list.seed_list[seed_id].chose_time,
                                       left_parser_queue_size, evicted_seed_total, mask_count)