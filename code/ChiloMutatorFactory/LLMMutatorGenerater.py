"""
这个函数用于对已经解析结束的SQL，使用LLM
生成对应的变异器
"""
import time
from .chilo_factory import ChiloFactory


def _get_compact_mutator_prompt(parsed_sql: str, target_dbms, dbms_version):
    """
    精简版变异器生成提示词 (基于SOFT论文优化)
    
    核心发现：87.4%的SQL函数漏洞由边界值参数处理不当引起
    - 边界字面量 (29.5%): 直接使用极值
    - 边界类型转换 (23.3%): 隐式/显式类型转换
    - 边界嵌套函数 (34.6%): 函数返回极值结果
    """
    prompt = f"""
You are a DBMS fuzzing expert. Generate a Python mutation module that produces crash-inducing SQL mutations.

**Key Insight**: Research shows 87.4% of SQL function bugs are triggered by boundary value arguments.

## Task Overview

**Input**: A SQL template with 6 types of mutation masks (marked as `[TYPE, number:N, ...]`)
**Output**: A Python module with a `mutate()` function that replaces all masks with actual values
**Goal**: Each `mutate()` call produces a different, crash-inducing SQL statement using boundary value patterns

---

## 10 Boundary Value Patterns (CRITICAL for Bug Finding)

### Category 1: Boundary Literals (29.5% of bugs)

| Data Type | Boundary Values |
|-----------|-----------------|
| Integer | 0, 1, -1, ±2147483647, ±9223372036854775807 |
| Float | 0.0, ±1e308, ±0.9999999999999999999 |
| String | '', NULL, 'a'*10000, '{{}}'(empty JSON), '[]' |
| Special | x'' (empty blob), RANDOMBLOB(1000000) |

**Pattern 1.3 - Insert Repeated Digits**: `'{{"a":10}}' → '{{"a":19999999999999999999}}'`
**Pattern 1.4 - Repeat Characters**: `'{{"a":1}}' → '{{"a":1}}}}}}}}'` (malformed)

### Category 2: Boundary Type Castings (23.3% of bugs)

**Pattern 2.1**: `f(x) → f(CAST(x AS DECIMAL(38,18)))` - Explicit cast
**Pattern 2.3**: `SUBSTR(123, 1, 2)` - Type confusion (int where string expected)

### Category 3: Boundary Nested Functions (34.6% of bugs)

**Pattern 3.1**: `f(REPEAT('[', 1000000))` - Extreme length via REPEAT
**Pattern 3.2**: `ABS(POWER(2, 63))` - Function returning boundary value

---

## The 6 Mask Types and Mutation Strategies

### 1. CONSTANT - `[CONSTANT, number:N, type:<type>, ori:<value>]`

**Integer mutations** (apply boundary patterns):
- Boundary: 0, 1, -1, 2147483647, -2147483648, 9223372036854775807
- AFL interesting: [-128, 127, 255, 256, 32767, 65535]
- Bit-flip: `ori ^ (1<<random.randint(0,63))`
- Delta: `ori + random.choice([1,-1,128,-128,32767,-32768])`

**String mutations**:
- Boundary: '', NULL, CHAR(0), CHAR(255)
- Long: 'a'*10000, REPEAT('x', 1000000)
- Malformed JSON/XML: '{{', '}}', '[[', ']]'
- Pattern 1.3: Insert '9999999999' into numeric strings

**Float mutations**:
- Boundary: 0.0, 1e308, -1e308, 0.9999999999999999999
- Special: inf, -inf, nan (if supported)

### 2. OPERATOR - `[OPERATOR, number:N, category:<cat>, ori:<op>]`
Same-category substitution: +↔-↔*↔/↔%, =↔!=↔<>↔<↔>

### 3. FUNCTION - `[FUNCTION, number:N, category:<cat>, argc:<n>, ori:<func>]`
Replace with same-argc function. **Apply Pattern 3.2**: Consider functions that return boundary values.
- argc=1: ABS, LENGTH, UPPER, TYPEOF, HEX, SUM, COUNT, MAX, MIN
- argc=2: SUBSTR, INSTR, NULLIF, IFNULL, COALESCE
- argc=3: SUBSTR, REPLACE, IIF

### 4. KEYWORD - `[KEYWORD, number:N, context:<ctx>, ori:<kw>]`
| context | candidates |
|---------|------------|
| constraint | NOT NULL, UNIQUE, PRIMARY KEY, CHECK(1), "" |
| conflict | OR REPLACE, OR IGNORE, OR FAIL, OR ABORT, "" |
| modifier | DISTINCT, ALL, "" |
| join | INNER, LEFT, LEFT OUTER, CROSS, NATURAL |
| order | ASC, DESC |

### 5. FRAME - `[FRAME, number:N, ori:<frame>]` (HIGH CRASH POTENTIAL)
- Overflow: `ROWS BETWEEN 9223372036854775807 PRECEDING AND 9223372036854775807 FOLLOWING`
- Negative: `ROWS BETWEEN -1 PRECEDING AND 1 FOLLOWING`
- Zero: `ROWS BETWEEN 0 PRECEDING AND 0 FOLLOWING`

### 6. CAST_TYPE - `[CAST_TYPE, number:N, ori:<type>]` (HIGH CRASH POTENTIAL)
- Standard: INTEGER, REAL, TEXT, BLOB, NUMERIC
- Extreme precision: DECIMAL(1000,500), DECIMAL(38,18)
- Edge: BOOLEAN, UNSIGNED BIG INT

---

## Required Python Module Structure

```python
import random
import re

SQL_TEMPLATE = \"\"\"<paste input SQL with all masks>\"\"\"

# Boundary values from research (87.4% of bugs)
BOUNDARY_INT = [0, 1, -1, 2147483647, -2147483648, 9223372036854775807, -9223372036854775808]
BOUNDARY_FLOAT = [0.0, 1e308, -1e308, 0.9999999999999999999]
AFL_INTERESTING = [-128, 127, 255, 256, 32767, 65535, 65536, 2147483647]

MASK_INFO = {{
    1: {{'pattern': r'\\[CONSTANT, number:1, [^\\]]+\\]', 'type': 'CONSTANT', 
        'value_type': 'int', 'ori': <original>, 'candidates': BOUNDARY_INT}},
    # ... one entry per mask
}}

def mutate() -> str:
    \"\"\"Generate crash-inducing SQL using boundary value patterns.\"\"\"
    result = SQL_TEMPLATE
    for mask_id, info in MASK_INFO.items():
        # Apply mutation with 95% probability
        if random.random() < 0.95:
            new_value = _mutate_by_type(info)
        else:
            new_value = info['ori']
        formatted = _format_value(new_value, info)
        result = re.sub(info['pattern'], formatted, result, count=1)
    return result
```

---

## Mutation Strategy Weights (for CONSTANT type)

1. **Boundary values** (30%): Direct use of boundary constants
2. **Delta mutation** (20%): `ori + random.choice([1,-1,128,-128,32767])`
3. **Bit-flip** (15%): `ori ^ (1 << random.randint(0, 63))`
4. **AFL interesting** (15%): From predefined interesting value list
5. **Pattern 1.3** (10%): Insert '9999999999' for string types
6. **Range random** (10%): `random.randint(-2**63, 2**63-1)`

---

## Output Requirements

1. **Complete replacement**: No `[CONSTANT, ...]` masks remain in output
2. **Valid SQL syntax**: Properly quoted strings, unquoted NULL/numbers
3. **High diversity**: Different output each `mutate()` call
4. **Standard library only**: random, re, string - no external deps
5. **No side effects**: No print, no file I/O

---

## Target DBMS: {target_dbms} v{dbms_version}

## Input SQL Template

```sql
{parsed_sql}
```

## Output

Provide ONLY the complete Python module:
```python
<your implementation>
```
"""
    return prompt


def  _get_constant_mutator_prompt(parsed_sql:str, target_dbms, dbms_version):
    prompt = f"""
Instruction: You are an **AGGRESSIVE DBMS fuzzing and mutation expert**. The input is a SQL test case with mutation masks. Your task is to generate a Python module that produces **CRASH-INDUCING** mutations.

---

## 🎯 Primary Objective

Generate SQL mutations that:
1. **Maximize crash likelihood** - Target known vulnerability patterns
2. **Explore edge cases** - Use boundary values, type confusion, extreme inputs
3. **High diversity** - Every call to `mutate()` should produce different output

---

## 📋 Input Mask Types

The input SQL contains **6 types** of masks:

### 1. CONSTANT
Format: `[CONSTANT, number:X, type:<type>, ori:<value>]`

**Mutation Strategy**:
- **Boundary values**: 0, 1, -1, MAX_INT (9223372036854775807), MIN_INT (-9223372036854775808)
- **Overflow triggers**: MAX_INT + 1, MIN_INT - 1
- **Type-specific edges**:
  - Integers: 127, 128, 32767, 32768, 2147483647, 2147483648
  - Floats: 0.0, 1e308, -1e308, NaN, Infinity
  - Strings: '', 'a'*10000, special chars (NULL byte, unicode edges)
  - Blobs: x'', x'00', x'FF', randomblob(1000000)
- **Special values**: NULL
- **AFL-style mutations**: bit flip, byte arithmetic, interesting values

### 2. OPERATOR
Format: `[OPERATOR, number:X, category:<category>, ori:<op>]`

**Mutation Strategy**:
- **Same-category substitution**:
  - Arithmetic: +, -, *, /, %
  - Comparison: >, <, >=, <=, =, !=, <>, IS, IS NOT
  - Logical: AND, OR
  - Bitwise: &, |, <<, >>
  - String: ||, LIKE, GLOB, MATCH
- **Cross-category** (10% chance): Try incompatible operators

### 3. FUNCTION
Format: `[FUNCTION, number:X, category:<category>, argc:<arg_count>, ori:<func>]`

**Mutation Strategy** (MUST match argc):
- **argc:1 aggregates**: SUM, AVG, COUNT, MAX, MIN, TOTAL
- **argc:1 scalars**: ABS, UPPER, LOWER, LENGTH, TYPEOF, QUOTE, HEX, ZEROBLOB, RANDOMBLOB
- **argc:2 scalars**: SUBSTR, INSTR, NULLIF, IFNULL, COALESCE, PRINTF
- **argc:3 scalars**: SUBSTR, REPLACE, IIF
- **Cross-category** (5% chance): Try incompatible function (may crash)

**IMPORTANT**: Only substitute with functions that have the SAME argc!

### 4. KEYWORD
Format: `[KEYWORD, number:X, context:<context>, ori:<keyword_phrase>]`

**Mutation Strategy** (context-specific):

| context | Candidates |
|---------|-----------|
| constraint | NOT NULL, UNIQUE, PRIMARY KEY, CHECK(1), <empty> |
| conflict | OR REPLACE, OR IGNORE, OR FAIL, OR ABORT, OR ROLLBACK, <empty> |
| modifier | DISTINCT, ALL, <empty> |
| join | INNER, LEFT, LEFT OUTER, CROSS, NATURAL, <comma> |
| order | ASC, DESC |
| nulls | NULLS FIRST, NULLS LAST, <empty> |
| existence | IF EXISTS, IF NOT EXISTS, <empty> |
| temp | TEMPORARY, TEMP, <empty> |
| transaction | DEFERRED, IMMEDIATE, EXCLUSIVE |
| fk_action | CASCADE, SET NULL, SET DEFAULT, RESTRICT, NO ACTION |

### 5. FRAME (NEW - HIGH CRASH POTENTIAL)
Format: `[FRAME, number:X, ori:<frame_clause>]`

**Mutation Strategy** - Window frame bugs are common crash sources:
- **Standard frames**:
  - `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`
  - `ROWS BETWEEN CURRENT ROW AND UNBOUNDED FOLLOWING`
  - `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`
- **Crash-inducing frames** (target overflow/underflow):
  - `ROWS BETWEEN 9223372036854775807 PRECEDING AND 9223372036854775807 FOLLOWING`
  - `ROWS BETWEEN -1 PRECEDING AND 1 FOLLOWING` (negative!)
  - `ROWS BETWEEN 1 PRECEDING AND -1 FOLLOWING` (invalid range!)
  - `GROUPS BETWEEN 999999999 PRECEDING AND 999999999 FOLLOWING`
  - `RANGE BETWEEN 1e308 PRECEDING AND 1e308 FOLLOWING` (extreme float)
- **Edge cases**:
  - `ROWS 0 PRECEDING` (minimal)
  - `ROWS BETWEEN 0 PRECEDING AND 0 FOLLOWING` (single row)

### 6. CAST_TYPE (NEW - HIGH CRASH POTENTIAL)
Format: `[CAST_TYPE, number:X, ori:<type_name>]`

**Mutation Strategy** - Type conversion bugs are very common:
- **Standard types**: INTEGER, REAL, TEXT, BLOB, NUMERIC
- **Overflow types**: 
  - `UNSIGNED BIG INT` (can overflow)
  - `BIGINT` 
  - `DOUBLE PRECISION`
- **Edge types**:
  - `BOOLEAN` (not all DBs support)
  - `CLOB`, `NCHAR`, `NVARCHAR` (encoding issues)
  - `DECIMAL(1000,500)` (extreme precision)
- **Invalid types** (may crash parser):
  - Empty string (just remove the type)
  - Very long type name: 'A' * 1000

---

## 🧬 DIVERSE MUTATION STRATEGIES (CRITICAL!)

**DO NOT just use `random.choice(candidates)`!** Implement these diverse mutation strategies:

### Strategy 1: Fixed Candidates (20%)
```python
# Boundary values, special values
candidates = [0, 1, -1, MAX_INT, MIN_INT, NULL, ...]
value = random.choice(candidates)
```

### Strategy 2: Random Jump / Delta Mutation (25%)
```python
# Add/subtract random delta from original value
if isinstance(ori_value, int):
    delta = random.choice([1, -1, 10, -10, 100, -100, 1000, -1000, random.randint(-10000, 10000)])
    value = ori_value + delta
elif isinstance(ori_value, float):
    delta = random.uniform(-1000.0, 1000.0)
    value = ori_value * (1 + random.uniform(-0.5, 0.5))  # or percentage change
```

### Strategy 3: Bit Flip Mutation (15%)
```python
# Flip random bits in the value
if isinstance(ori_value, int):
    bit_pos = random.randint(0, 63)
    value = ori_value ^ (1 << bit_pos)
    # Or flip multiple bits
    for _ in range(random.randint(1, 4)):
        value ^= (1 << random.randint(0, 63))
```

### Strategy 4: Byte Arithmetic (15%)
```python
# AFL-style byte arithmetic
byte_deltas = [1, -1, 16, -16, 32, -32, 64, -64, 127, -127, 128, -128, 255, -255, 256, -256]
value = ori_value + random.choice(byte_deltas)
```

### Strategy 5: Range Random (15%)
```python
# Generate completely random value in a range
value = random.randint(-2147483648, 2147483647)  # full 32-bit range
# Or for strings:
length = random.randint(1, 100)
value = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=length))
```

### Strategy 6: Interesting Values (10%)
```python
# AFL's interesting values
interesting_8 = [-128, -1, 0, 1, 16, 32, 64, 100, 127]
interesting_16 = [-32768, -129, 128, 255, 256, 512, 1000, 1024, 4096, 32767]
interesting_32 = [-2147483648, -100663046, -32769, 32768, 65535, 65536, 100663045, 2147483647]
interesting_64 = [-9223372036854775808, -1, 0, 1, 9223372036854775807]
value = random.choice(interesting_8 + interesting_16 + interesting_32 + interesting_64)
```

---

## 📝 Implementation Requirements

### Module Structure

Generate a complete Python module with DIVERSE mutation strategies:

```python
import random
import re
import string

# The original SQL template with masks
SQL_TEMPLATE = \"\"\"(paste the input SQL here with all masks)\"\"\"

# Interesting values for AFL-style mutation
INTERESTING_8 = [-128, -1, 0, 1, 16, 32, 64, 100, 127]
INTERESTING_16 = [-32768, -129, 128, 255, 256, 512, 1000, 1024, 4096, 32767]
INTERESTING_32 = [-2147483648, -100663046, -32769, 32768, 65535, 65536, 100663045, 2147483647]
INTERESTING_64 = [-9223372036854775808, -1, 0, 1, 9223372036854775807]
ALL_INTERESTING = INTERESTING_8 + INTERESTING_16 + INTERESTING_32 + INTERESTING_64

# Define mutation info for each mask
MASK_MUTATIONS = {{
    1: {{
        'pattern': r'\[CONSTANT, number:1, type:[^\]]+, ori:[^\]]+\]',
        'type': 'CONSTANT',
        'value_type': 'int',  # int, float, string, blob
        'ori': 10,  # original value (as proper Python type)
        'candidates': [0, 1, -1, 9223372036854775807, -9223372036854775808, 2147483647]
    }},
    2: {{
        'pattern': r'\[OPERATOR, number:2, category:[^\]]+, ori:[^\]]+\]',
        'type': 'OPERATOR',
        'ori': '+',
        'candidates': ['+', '-', '*', '/', '%']
    }},
    # ... define for ALL masks
}}

def _mutate_int(ori_value: int, candidates: list) -> int:
    \"\"\"Apply diverse mutations to integer values.\"\"\"
    strategy = random.choices(
        ['candidate', 'delta', 'bitflip', 'byte_arith', 'range', 'interesting'],
        weights=[20, 25, 15, 15, 15, 10]
    )[0]
    
    if strategy == 'candidate':
        return random.choice(candidates) if candidates else ori_value
    elif strategy == 'delta':
        # Random jump: add/subtract random delta
        delta = random.choice([1, -1, 10, -10, 100, -100, 1000, -1000])
        if random.random() < 0.3:
            delta = random.randint(-100000, 100000)
        return ori_value + delta
    elif strategy == 'bitflip':
        # Flip 1-4 random bits
        value = ori_value
        for _ in range(random.randint(1, 4)):
            value ^= (1 << random.randint(0, 63))
        return value
    elif strategy == 'byte_arith':
        # AFL-style byte arithmetic
        byte_deltas = [1, -1, 16, -16, 32, -32, 64, -64, 127, -127, 128, -128, 255, -255, 256, -256]
        return ori_value + random.choice(byte_deltas)
    elif strategy == 'range':
        # Full range random
        return random.randint(-2147483648, 2147483647)
    else:  # interesting
        return random.choice(ALL_INTERESTING)

def _mutate_float(ori_value: float, candidates: list) -> float:
    \"\"\"Apply diverse mutations to float values.\"\"\"
    strategy = random.choices(
        ['candidate', 'delta', 'multiply', 'range', 'special'],
        weights=[20, 30, 20, 15, 15]
    )[0]
    
    if strategy == 'candidate':
        return random.choice(candidates) if candidates else ori_value
    elif strategy == 'delta':
        delta = random.uniform(-1000.0, 1000.0)
        return ori_value + delta
    elif strategy == 'multiply':
        factor = random.choice([0.0, 0.5, 2.0, 10.0, 0.1, -1.0, random.uniform(-10, 10)])
        return ori_value * factor
    elif strategy == 'range':
        return random.uniform(-1e10, 1e10)
    else:  # special
        return random.choice([0.0, 1.0, -1.0, 1e308, -1e308, 1e-308, float('inf'), float('-inf')])

def _mutate_string(ori_value: str, candidates: list) -> str:
    \"\"\"Apply diverse mutations to string values.\"\"\"
    strategy = random.choices(
        ['candidate', 'append', 'repeat', 'random', 'special', 'truncate'],
        weights=[20, 20, 15, 20, 15, 10]
    )[0]
    
    if strategy == 'candidate':
        return random.choice(candidates) if candidates else ori_value
    elif strategy == 'append':
        suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(1, 20)))
        return ori_value + suffix
    elif strategy == 'repeat':
        return ori_value * random.randint(2, 10)
    elif strategy == 'random':
        length = random.randint(1, 100)
        return ''.join(random.choices(string.ascii_letters + string.digits + ' ', k=length))
    elif strategy == 'special':
        specials = ["", "NULL", "''", "' OR 1=1--", "\\x00", "a" * 1000, "1", "0"]
        return random.choice(specials)
    else:  # truncate
        if len(ori_value) > 1:
            return ori_value[:random.randint(1, len(ori_value)-1)]
        return ori_value

def mutate() -> str:
    \"\"\"
    Generate one mutated SQL statement with DIVERSE mutation strategies.
    Returns: Complete SQL string with ALL masks replaced by actual values.
    \"\"\"
    result = SQL_TEMPLATE
    
    for mask_num, mask_info in MASK_MUTATIONS.items():
        # 60% chance to mutate, 40% use original
        if random.random() < 0.6:
            if mask_info['type'] == 'CONSTANT':
                ori = mask_info['ori']
                candidates = mask_info.get('candidates', [])
                vtype = mask_info.get('value_type', 'int')
                
                if vtype == 'int':
                    new_value = _mutate_int(int(ori) if isinstance(ori, str) else ori, candidates)
                elif vtype == 'float':
                    new_value = _mutate_float(float(ori) if isinstance(ori, str) else ori, candidates)
                else:  # string
                    new_value = _mutate_string(str(ori), candidates)
            else:
                # For OPERATOR, FUNCTION, KEYWORD, FRAME, CAST_TYPE - use candidates
                new_value = random.choice(mask_info.get('candidates', [mask_info['ori']]))
        else:
            new_value = mask_info['ori']
        
        # Format value for SQL
        formatted = _format_sql_value(new_value, mask_info['type'], mask_info.get('value_type'))
        result = re.sub(mask_info['pattern'], formatted, result)
    
    return result

def _format_sql_value(value, mask_type: str, value_type: str = None) -> str:
    \"\"\"Format value correctly for SQL syntax.\"\"\"
    if mask_type == 'CONSTANT':
        if value is None or (isinstance(value, str) and value.upper() == 'NULL'):
            return 'NULL'
        elif value_type == 'string' or isinstance(value, str):
            # Escape single quotes and wrap
            escaped = str(value).replace("'", "''")
            return f"'{{escaped}}'"
        else:
            return str(value)
    else:
        return str(value)
        # Replace the mask pattern with the actual value
        result = re.sub(mask_info['pattern'], formatted, result)
    
    return result
```

**CRITICAL**: The `mutate()` function MUST:
1. Use `re.sub()` to replace EVERY mask pattern `[TYPE, number:X, ...]` with actual SQL values
2. Return a VALID, EXECUTABLE SQL statement with NO remaining mask brackets
3. Properly quote string values with single quotes
4. Handle NULL without quotes

### Mutation Logic

**For each call to `mutate()`**:

1. **Select masks to mutate**: Randomly choose 30-70% of masks (at least 1)
2. **Choose mutation mode** for selected masks:
   - 40% - Fixed candidates (boundary values, same-category substitutions)
   - 40% - AFL-style binary mutations (for CONSTANT)
   - 20% - Random/creative mutations (cross-category, extreme values)
3. **Replace masks**: 
   - Selected masks → mutated values
   - Unselected masks → original values
4. **Return valid SQL**: Ensure proper quoting for strings, correct syntax

### Code Quality

- Use **only Python standard library** (random, struct, re, etc.)
- **No side effects**: No prints, no file I/O, no network calls
- **No top-level execution**: No `if __name__ == "__main__":`
- **Error handling**: Handle edge cases gracefully
- **Comments**: Explain mutation choices

---

## 🎯 Target: {target_dbms} version {dbms_version}

### DBMS-Specific Considerations

- SQLite supports: `OR IGNORE`, `OR REPLACE`, etc.
- Window functions: ROWS BETWEEN, RANGE BETWEEN
- FTS3/FTS5 virtual tables: MATCH queries
- Built-in functions: randomblob(), zeroblob(), printf()

---

## 📥 Input SQL

```sql
{parsed_sql}
```

---

## 📤 Output Format

Provide the complete Python module inside a code block:

```python
(entire module here)
```

**Do NOT include**:
- Explanations outside the code block
- Example usage or test code
- Comments explaining the task (only implementation comments)

---

## 🚀 Now Generate

Create a Python module that implements aggressive, crash-inducing mutations for the above SQL targeting {target_dbms} version {dbms_version}.

**CRITICAL REQUIREMENTS**:
1. **MUST replace ALL mask patterns** - Use `re.sub()` to replace every `[CONSTANT, ...]`, `[OPERATOR, ...]`, `[FUNCTION, ...]`, `[KEYWORD, ...]` with actual SQL values
2. **Output MUST be executable SQL** - No mask brackets `[...]` should remain in the output
3. **Properly quote strings** - String constants need single quotes, NULL and numbers do not
4. **High diversity** - Different output each time `mutate()` is called

**Remember**:
- Include AFL-style binary mutations (bit flip, interesting values) for CONSTANT
- Target known vulnerability patterns
- Balance fixed candidates (40%), AFL mutations (40%), and random mutations (20%)
"""
    return prompt

def chilo_mutator_generator(my_chilo_factory: ChiloFactory):
    my_chilo_factory.mutator_generator_logger.info("变异器生成器启动成功")
    while True:
        # 采用阻塞方式从上游取任务，取消轮询
        generate_target = my_chilo_factory.wait_mutator_generate_list.get()

        all_start_time = time.time()
        all_up_token = 0
        all_down_token = 0
        llm_count = 0
        llm_error_count = 0
        my_chilo_factory.mutator_generator_logger.info("接收变异器生成任务中~")
        my_chilo_factory.mutator_generator_logger.info(f"变异器生成任务接收完毕 任务目标   seed_id：{generate_target['seed_id']}    变异次数：{generate_target['mutate_time']}")
        mutate_time = generate_target['mutate_time']
        parsed_sql = my_chilo_factory.all_seed_list.seed_list[generate_target['seed_id']].parser_content   #拿出对应的已经解析过的内容
        
        # 根据配置选择提示词版本
        if my_chilo_factory.use_compact_prompt:
            prompt = _get_compact_mutator_prompt(parsed_sql, my_chilo_factory.target_dbms, my_chilo_factory.target_dbms_version)
            my_chilo_factory.mutator_generator_logger.info(f"seed_id：{generate_target['seed_id']}  使用精简版提示词（基于SOFT论文边界值模式）")
        else:
            prompt = _get_constant_mutator_prompt(parsed_sql, my_chilo_factory.target_dbms, my_chilo_factory.target_dbms_version)
            my_chilo_factory.mutator_generator_logger.info(f"seed_id：{generate_target['seed_id']}  使用完整版提示词")
        
        mutator_code_success = False
        while True:
            start_time = time.time()
            my_chilo_factory.mutator_generator_logger.info(
                f"seed_id：{generate_target['seed_id']}  准备调用LLM，生成变异器")
            mutator_code, up_token, down_token = my_chilo_factory.llm_tool_mutator_generator.chat_llm(prompt)    #调用LLM
            end_time = time.time()
            all_up_token += up_token
            all_down_token += down_token
            llm_count += 1
            my_chilo_factory.mutator_generator_logger.info(
                f"seed_id：{generate_target['seed_id']}  生成变异器调用结束，用时：{end_time - start_time:.2f}s")
            mutator_code = my_chilo_factory.llm_tool_mutator_generator.get_python_block_content(mutator_code)  #获取python代码
            try:
                mutator_code = mutator_code[0]
                mutator_code_success = True
                break
            except:
                #证明输出格式错误
                llm_error_count += 1
                my_chilo_factory.mutator_generator_logger.warning(
                    f"seed_id：{generate_target['seed_id']}  LLM生成变异器时格式错误（第{llm_error_count}次）！准备再次生成")
                # 检查是否超过最大重试次数
                if llm_error_count >= my_chilo_factory.llm_format_error_max_retry:
                    my_chilo_factory.mutator_generator_logger.error(
                        f"seed_id：{generate_target['seed_id']}  格式错误次数超过上限{my_chilo_factory.llm_format_error_max_retry}，跳过该种子")
                    # 跳过这个任务，继续处理下一个
                    break

        # 只有成功提取代码才放入修复队列
        if mutator_code_success:
            my_chilo_factory.mutator_generator_logger.info(
                f"seed_id：{generate_target['seed_id']}  LLM生成变异器代码提取成功，准备放入待修复队列")
            # 使用阻塞 put，将任务放入下游修复队列
            my_chilo_factory.fix_mutator_list.put({"seed_id" : generate_target['seed_id'], "mutate_time" : mutate_time, "mutator_code": mutator_code})
            my_chilo_factory.mutator_generator_logger.info(
                f"seed_id：{generate_target['seed_id']}  变异器放入修复队列成功")
        else:
            my_chilo_factory.mutator_generator_logger.warning(
                f"seed_id：{generate_target['seed_id']}  生成变异器失败，已跳过该种子")
        my_chilo_factory.mutator_generator_logger.info("-"*10)
        all_end_time = time.time()
        my_chilo_factory.write_mutator_generator_csv(all_end_time, generate_target['seed_id'], all_end_time-all_start_time,
                                                     end_time-start_time, all_up_token, all_down_token, llm_count,
                                                     llm_error_count, my_chilo_factory.fix_mutator_list.qsize())