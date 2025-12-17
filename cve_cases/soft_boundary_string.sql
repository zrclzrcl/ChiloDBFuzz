-- Boundary string values (Pattern 1.1, 1.3, 1.4)
-- Empty and NULL
SELECT LENGTH('');
SELECT LENGTH(NULL);
SELECT SUBSTR('', 1, 1);
SELECT CONCAT(NULL, NULL);

-- Very long strings via REPEAT (Pattern 3.1)
SELECT LENGTH(REPEAT('a', 1000000));
SELECT SUBSTR(REPEAT('x', 100000), 99999);
SELECT UPPER(REPEAT('a', 1000000));

-- Special characters
SELECT 'test' LIKE '%\x00%';
SELECT REPLACE('abc', 'b', REPEAT('x', 10000));
