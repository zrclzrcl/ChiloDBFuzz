-- CVE-2016-0773: PostgreSQL regex integer overflow
-- Pattern 1.1: Boundary literal value in regex
SELECT 'a' ~ '\x7fffffff';
