-- Boundary values in JSON format (Pattern 1.3 & 1.4)
SELECT JSON('{"a":1999999999999999999999}');
SELECT JSON('{"a":10}}}}}}}}}}}');
SELECT JSON_EXTRACT('{"key": 999999999999999999999}', '$.key');
SELECT JSON_ARRAY(REPEAT('[', 500));
