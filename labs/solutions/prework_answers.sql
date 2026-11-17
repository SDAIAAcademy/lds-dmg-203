-- Q1
SELECT city_code, count(*) FROM centres GROUP BY 1;
-- Q2
SELECT centre_type, count(*) FROM centres GROUP BY 1;
-- Q3
SELECT channel, count(*) FROM applications WHERE submitted_at >= DATE '2026-01-01' GROUP BY 1;
-- Q4
SELECT office_city, round(avg(score), 1) FROM inspections GROUP BY 1;
-- Q5
SELECT count(*) FROM licences WHERE status = 'RENEWED';
-- Q6
SELECT c.centre_type, count(*) FROM licences l JOIN centres c USING (centre_id) GROUP BY 1;
-- Q7
SELECT year(inspection_date), count(*) FROM inspections GROUP BY 1;
-- Q8
SELECT inspector_id, count(*) n FROM inspections GROUP BY 1 ORDER BY n DESC, inspector_id LIMIT 5;
-- Q9
SELECT district_code, count(*) FROM centres GROUP BY 1 HAVING count(*) > 30;
-- Q10
SELECT c.city_code, count(*), round(avg(a.decision_date - a.submitted_at), 1)
FROM applications a JOIN centres c USING (centre_id)
WHERE a.decision = 'APPROVED' AND a.submitted_at >= DATE '2026-01-01' GROUP BY 1;
