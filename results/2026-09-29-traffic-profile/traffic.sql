\pset footer off
\echo == per model group
select model_group, count(*) n, sum((status<>'success')::int) not_success, min("startTime")::date first_day, max("startTime")::date last_day, count(distinct api_key) keys
from "LiteLLM_SpendLogs" group by 1 order by 2 desc;
\echo == requests per day, deepseek-v4.1-flash
select "startTime"::date d, count(*) n, sum(prompt_tokens) prompt_tok, sum(completion_tokens) compl_tok, sum((status<>'success')::int) not_success
from "LiteLLM_SpendLogs" where model_group='deepseek-v4.1-flash' group by 1 order by 1;
\echo == token distributions (successful deepseek requests)
with s as (select * from "LiteLLM_SpendLogs" where model_group='deepseek-v4.1-flash' and status='success')
select 'prompt' what, count(*) n, percentile_cont(0.5) within group (order by prompt_tokens)::int p50, percentile_cont(0.9) within group (order by prompt_tokens)::int p90, percentile_cont(0.99) within group (order by prompt_tokens)::int p99, max(prompt_tokens) mx, sum(prompt_tokens) total from s
union all
select 'completion', count(*), percentile_cont(0.5) within group (order by completion_tokens)::int, percentile_cont(0.9) within group (order by completion_tokens)::int, percentile_cont(0.99) within group (order by completion_tokens)::int, max(completion_tokens), sum(completion_tokens) from s;
\echo == prompt length buckets
select case when prompt_tokens<2000 then 'a <2K' when prompt_tokens<8000 then 'b 2-8K' when prompt_tokens<32000 then 'c 8-32K' when prompt_tokens<100000 then 'd 32-100K' else 'e >=100K' end bucket, count(*) n, round(100.0*count(*)/sum(count(*)) over (),1) pct, sum(prompt_tokens) prompt_tok
from "LiteLLM_SpendLogs" where model_group='deepseek-v4.1-flash' and status='success' group by 1 order by 1;
\echo == latency (s): time to first token, total duration
with s as (select extract(epoch from ("completionStartTime"-"startTime")) ttft, extract(epoch from ("endTime"-"startTime")) dur, completion_tokens c from "LiteLLM_SpendLogs" where model_group='deepseek-v4.1-flash' and status='success' and "completionStartTime" is not null)
select count(*) n, round(percentile_cont(0.5) within group (order by ttft)::numeric,2) ttft_p50, round(percentile_cont(0.9) within group (order by ttft)::numeric,2) ttft_p90, round(percentile_cont(0.99) within group (order by ttft)::numeric,2) ttft_p99,
 round(percentile_cont(0.5) within group (order by dur)::numeric,1) dur_p50, round(percentile_cont(0.9) within group (order by dur)::numeric,1) dur_p90,
 round((percentile_cont(0.5) within group (order by c/nullif(dur-ttft,0)))::numeric,1) decode_tok_s_p50 from s;
\echo == concurrency (time-weighted, while at least one request is in flight)
with ev as (
  select "startTime" t, 1 d from "LiteLLM_SpendLogs" where model_group='deepseek-v4.1-flash' and status='success'
  union all select "endTime", -1 from "LiteLLM_SpendLogs" where model_group='deepseek-v4.1-flash' and status='success'),
lv as (select t, sum(d) over (order by t, d rows unbounded preceding) level, lead(t) over (order by t, d) nxt from ev)
select level, round(sum(extract(epoch from (nxt-t)))::numeric/3600,2) hours, round(100.0*sum(extract(epoch from (nxt-t)))/sum(sum(extract(epoch from (nxt-t)))) over (),1) pct_of_busy_time
from lv where level>0 and nxt is not null group by 1 order by 1;
\echo == hour of day, UTC (deepseek requests)
select extract(hour from "startTime")::int h, count(*) n from "LiteLLM_SpendLogs" where model_group='deepseek-v4.1-flash' group by 1 order by 1;
\echo == non-success statuses
select model_group, status, count(*) from "LiteLLM_SpendLogs" where status<>'success' group by 1,2 order by 3 desc limit 10;
