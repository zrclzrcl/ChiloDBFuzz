-- Nested function patterns (Pattern 3.1, 3.2, 3.3)
-- Pattern 3.1: REPEAT to construct extreme lengths
SELECT JSON(REPEAT('[', 1000) || '1' || REPEAT(']', 1000));
SELECT XML(REPEAT('<a>', 1000) || 'x' || REPEAT('</a>', 1000));
SELECT REGEXP_REPLACE('test', REPEAT('(', 100) || '.' || REPEAT(')', 100), 'x');

-- Pattern 3.2: Wrap argument with another function
SELECT ABS(ABS(ABS(ABS(ABS(-9223372036854775808)))));
SELECT LENGTH(UPPER(LOWER(UPPER(REPEAT('a', 10000)))));
SELECT COALESCE(NULLIF(IFNULL(NULL, NULL), NULL), 0);

-- Pattern 3.3: Replace argument with function return value
SELECT SUBSTR(REPEAT('a', 1000000), POWER(2, 20), POWER(2, 20));
SELECT INSTR(REPEAT('ab', 1000000), REPEAT('b', 1000));
SELECT REPLACE(REPEAT('a', 100000), 'a', REPEAT('b', 100));
