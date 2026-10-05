SELECT regexp_extract(line_item_iam_principal, '[^/]+$') AS user_name,
       round(sum(line_item_unblended_cost), 2)          AS cost_usd,
       sum(line_item_usage_amount * CASE pricing_unit
             WHEN '1M tokens' THEN 1000000
             WHEN '1K tokens' THEN 1000
             ELSE 1 END)                                AS tokens,
       count(DISTINCT line_item_resource_id)            AS models
FROM cur.cur2
WHERE billing_period = date_format(current_date, '%Y-%m')
  AND line_item_iam_principal IS NOT NULL
  AND line_item_iam_principal <> ''
  AND line_item_line_item_type = 'Usage'
GROUP BY 1
ORDER BY cost_usd DESC;
