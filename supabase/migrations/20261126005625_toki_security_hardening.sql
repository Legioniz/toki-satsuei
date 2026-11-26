-- TOKI security hardening: fixed database-side quotas, bounded rate-limit storage,
-- forced RLS, and privacy-preserving booking audit history.
CREATE INDEX IF NOT EXISTS submission_rate_limits_expires_at_idx ON public.submission_rate_limits (expires_at);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.submission_rate_limits'::regclass AND conname='submission_rate_limits_bucket_hash_format_check') THEN
    ALTER TABLE public.submission_rate_limits ADD CONSTRAINT submission_rate_limits_bucket_hash_format_check CHECK (bucket_hash ~ '^[0-9a-f]{64}$') NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.submission_rate_limits'::regclass AND conname='submission_rate_limits_scope_allowlist_check') THEN
    ALTER TABLE public.submission_rate_limits ADD CONSTRAINT submission_rate_limits_scope_allowlist_check CHECK (scope IN ('inquiry','comment','page_view','toki_booking','toki_calendar','toki_booking_contact')) NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.submission_rate_limits'::regclass AND conname='submission_rate_limits_hit_count_positive_check') THEN
    ALTER TABLE public.submission_rate_limits ADD CONSTRAINT submission_rate_limits_hit_count_positive_check CHECK (hit_count > 0) NOT VALID;
  END IF;
END $$;
ALTER TABLE public.submission_rate_limits VALIDATE CONSTRAINT submission_rate_limits_bucket_hash_format_check;
ALTER TABLE public.submission_rate_limits VALIDATE CONSTRAINT submission_rate_limits_scope_allowlist_check;
ALTER TABLE public.submission_rate_limits VALIDATE CONSTRAINT submission_rate_limits_hit_count_positive_check;
ALTER TABLE public.submission_rate_limits FORCE ROW LEVEL SECURITY;
ALTER TABLE public.toki_booking_requests FORCE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public.consume_portfolio_quota(p_bucket_hash text,p_scope text,p_limit integer DEFAULT 5)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $function$
DECLARE
  v_now timestamptz := pg_catalog.clock_timestamp();
  v_window timestamptz;
  v_scope_ceiling integer;
  v_count integer;
BEGIN
  IF p_bucket_hash IS NULL OR p_bucket_hash !~ '^[0-9a-f]{64}$' THEN
    RAISE EXCEPTION 'Invalid quota bucket hash' USING ERRCODE = '22023';
  END IF;
  v_scope_ceiling := CASE p_scope
    WHEN 'inquiry' THEN 4 WHEN 'comment' THEN 6 WHEN 'page_view' THEN 60
    WHEN 'toki_booking' THEN 4 WHEN 'toki_calendar' THEN 30
    WHEN 'toki_booking_contact' THEN 2 ELSE NULL END;
  IF v_scope_ceiling IS NULL THEN RAISE EXCEPTION 'Invalid quota scope' USING ERRCODE = '22023'; END IF;
  IF p_limit IS NULL OR p_limit < 1 OR p_limit > v_scope_ceiling THEN
    RAISE EXCEPTION 'Requested quota exceeds the scope ceiling' USING ERRCODE = '22023';
  END IF;
  v_window := pg_catalog.to_timestamp(pg_catalog.floor(extract(epoch FROM v_now) / 600) * 600);
  IF mod(extract(minute FROM v_now)::integer,10)=0 AND extract(second FROM v_now)<5 THEN
    DELETE FROM public.submission_rate_limits WHERE expires_at < v_now;
  END IF;
  INSERT INTO public.submission_rate_limits(bucket_hash,scope,window_start,hit_count,expires_at)
  VALUES(p_bucket_hash,p_scope,v_window,1,v_now+interval '2 days')
  ON CONFLICT(bucket_hash,scope,window_start)
  DO UPDATE SET hit_count=CASE WHEN public.submission_rate_limits.hit_count<2147483647
    THEN public.submission_rate_limits.hit_count+1 ELSE public.submission_rate_limits.hit_count END,
    expires_at=EXCLUDED.expires_at
  RETURNING hit_count INTO v_count;
  RETURN v_count <= p_limit;
END;
$function$;
REVOKE ALL ON FUNCTION public.consume_portfolio_quota(text,text,integer) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.consume_portfolio_quota(text,text,integer) TO service_role;

CREATE OR REPLACE FUNCTION private.log_portfolio_admin_update_delete()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $function$
DECLARE v_id uuid; v_summary text; v_changed_fields text;
BEGIN
  IF TG_OP='DELETE' THEN v_id:=OLD.id; v_summary:='Administrator deleted a record.';
  ELSIF TG_OP='INSERT' THEN v_id:=NEW.id; v_summary:='New booking request submitted.';
  ELSE
    v_id:=NEW.id;
    SELECT pg_catalog.string_agg(field_name,', ' ORDER BY field_name) INTO v_changed_fields
    FROM (
      SELECT COALESCE(new_values.key,old_values.key) AS field_name
      FROM pg_catalog.jsonb_each(pg_catalog.to_jsonb(NEW)) AS new_values
      FULL JOIN pg_catalog.jsonb_each(pg_catalog.to_jsonb(OLD)) AS old_values USING(key)
      WHERE new_values.value IS DISTINCT FROM old_values.value
        AND COALESCE(new_values.key,old_values.key)<>'updated_at'
    ) AS changed;
    v_summary:='Administrator updated a record. Changed fields: '||pg_catalog.left(COALESCE(v_changed_fields,'none'),450);
  END IF;
  INSERT INTO public.admin_activity(actor_id,action,record_type,record_id,summary)
  VALUES((SELECT auth.uid()),pg_catalog.lower(TG_OP),TG_TABLE_NAME,v_id,v_summary);
  IF TG_OP='DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END;
$function$;
DROP TRIGGER IF EXISTS toki_booking_requests_admin_audit ON public.toki_booking_requests;
CREATE TRIGGER toki_booking_requests_admin_audit AFTER INSERT OR UPDATE OR DELETE
ON public.toki_booking_requests FOR EACH ROW EXECUTE FUNCTION private.log_portfolio_admin_update_delete();
CREATE INDEX IF NOT EXISTS admin_activity_record_history_idx ON public.admin_activity(record_type,record_id,created_at DESC);
CREATE INDEX IF NOT EXISTS admin_activity_created_at_idx ON public.admin_activity(created_at DESC);
