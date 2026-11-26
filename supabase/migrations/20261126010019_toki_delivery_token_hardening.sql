-- TOKI private delivery: store only SHA-256 hashes of high-entropy access keys.
ALTER TABLE public.toki_booking_requests
  ADD COLUMN IF NOT EXISTS reservation_fee_paid boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS reservation_fee_paid_at timestamptz,
  ADD COLUMN IF NOT EXISTS balance_paid boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS balance_paid_at timestamptz,
  ADD COLUMN IF NOT EXISTS delivery_status text NOT NULL DEFAULT 'pending',
  ADD COLUMN IF NOT EXISTS delivery_folder_url text,
  ADD COLUMN IF NOT EXISTS delivery_token_hash text,
  ADD COLUMN IF NOT EXISTS delivery_expires_at timestamptz,
  ADD COLUMN IF NOT EXISTS client_selected_photos jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS client_selection_submitted_at timestamptz;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.toki_booking_requests'::regclass AND conname='toki_booking_delivery_status_check') THEN
    ALTER TABLE public.toki_booking_requests ADD CONSTRAINT toki_booking_delivery_status_check CHECK(delivery_status IN('pending','editing','ready','delivered','revoked','expired')) NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.toki_booking_requests'::regclass AND conname='toki_booking_token_hash_format_check') THEN
    ALTER TABLE public.toki_booking_requests ADD CONSTRAINT toki_booking_token_hash_format_check CHECK(delivery_token_hash IS NULL OR delivery_token_hash ~ '^[0-9a-f]{64}$') NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.toki_booking_requests'::regclass AND conname='toki_booking_token_expiry_pair_check') THEN
    ALTER TABLE public.toki_booking_requests ADD CONSTRAINT toki_booking_token_expiry_pair_check CHECK((delivery_token_hash IS NULL AND delivery_expires_at IS NULL) OR (delivery_token_hash IS NOT NULL AND delivery_expires_at IS NOT NULL)) NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.toki_booking_requests'::regclass AND conname='toki_booking_photos_array_check') THEN
    ALTER TABLE public.toki_booking_requests ADD CONSTRAINT toki_booking_photos_array_check CHECK(jsonb_typeof(client_selected_photos)='array') NOT VALID;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.toki_booking_requests'::regclass AND conname='toki_booking_ready_delivery_requires_url_check') THEN
    ALTER TABLE public.toki_booking_requests ADD CONSTRAINT toki_booking_ready_delivery_requires_url_check CHECK(delivery_status NOT IN('ready','delivered') OR (delivery_folder_url IS NOT NULL AND delivery_token_hash IS NOT NULL AND delivery_expires_at IS NOT NULL)) NOT VALID;
  END IF;
END $$;
ALTER TABLE public.toki_booking_requests VALIDATE CONSTRAINT toki_booking_delivery_status_check;
ALTER TABLE public.toki_booking_requests VALIDATE CONSTRAINT toki_booking_token_hash_format_check;
ALTER TABLE public.toki_booking_requests VALIDATE CONSTRAINT toki_booking_token_expiry_pair_check;
ALTER TABLE public.toki_booking_requests VALIDATE CONSTRAINT toki_booking_photos_array_check;
ALTER TABLE public.toki_booking_requests VALIDATE CONSTRAINT toki_booking_ready_delivery_requires_url_check;
CREATE UNIQUE INDEX IF NOT EXISTS toki_booking_delivery_token_hash_key ON public.toki_booking_requests(delivery_token_hash) WHERE delivery_token_hash IS NOT NULL;
CREATE INDEX IF NOT EXISTS toki_booking_delivery_expiry_idx ON public.toki_booking_requests(delivery_expires_at) WHERE delivery_token_hash IS NOT NULL;

ALTER TABLE public.submission_rate_limits DROP CONSTRAINT IF EXISTS submission_rate_limits_scope_allowlist_check;
ALTER TABLE public.submission_rate_limits ADD CONSTRAINT submission_rate_limits_scope_allowlist_check
CHECK(scope IN('inquiry','comment','page_view','toki_booking','toki_calendar','toki_booking_contact','toki_gallery_global','toki_gallery_token'));

CREATE OR REPLACE FUNCTION public.consume_portfolio_quota(p_bucket_hash text,p_scope text,p_limit integer DEFAULT 5)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $function$
DECLARE
  v_now timestamptz:=pg_catalog.clock_timestamp(); v_window timestamptz; v_scope_ceiling integer; v_count integer;
BEGIN
  IF p_bucket_hash IS NULL OR p_bucket_hash !~ '^[0-9a-f]{64}$' THEN RAISE EXCEPTION 'Invalid quota bucket hash' USING ERRCODE='22023'; END IF;
  v_scope_ceiling:=CASE p_scope
    WHEN 'inquiry' THEN 4 WHEN 'comment' THEN 6 WHEN 'page_view' THEN 60
    WHEN 'toki_booking' THEN 4 WHEN 'toki_calendar' THEN 30 WHEN 'toki_booking_contact' THEN 2
    WHEN 'toki_gallery_global' THEN 120 WHEN 'toki_gallery_token' THEN 10 ELSE NULL END;
  IF v_scope_ceiling IS NULL THEN RAISE EXCEPTION 'Invalid quota scope' USING ERRCODE='22023'; END IF;
  IF p_limit IS NULL OR p_limit<1 OR p_limit>v_scope_ceiling THEN RAISE EXCEPTION 'Requested quota exceeds the scope ceiling' USING ERRCODE='22023'; END IF;
  v_window:=pg_catalog.to_timestamp(pg_catalog.floor(extract(epoch FROM v_now)/600)*600);
  IF mod(extract(minute FROM v_now)::integer,10)=0 AND extract(second FROM v_now)<5 THEN DELETE FROM public.submission_rate_limits WHERE expires_at<v_now; END IF;
  INSERT INTO public.submission_rate_limits(bucket_hash,scope,window_start,hit_count,expires_at)
  VALUES(p_bucket_hash,p_scope,v_window,1,v_now+interval '2 days')
  ON CONFLICT(bucket_hash,scope,window_start) DO UPDATE SET
    hit_count=CASE WHEN public.submission_rate_limits.hit_count<2147483647 THEN public.submission_rate_limits.hit_count+1 ELSE public.submission_rate_limits.hit_count END,
    expires_at=EXCLUDED.expires_at
  RETURNING hit_count INTO v_count;
  RETURN v_count<=p_limit;
END;
$function$;
REVOKE ALL ON FUNCTION public.consume_portfolio_quota(text,text,integer) FROM PUBLIC,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.consume_portfolio_quota(text,text,integer) TO service_role;

CREATE OR REPLACE VIEW public.toki_booking_inbox WITH(security_invoker=true) AS
SELECT id AS booking_id,reference_code,status,created_at AS submitted_at,name AS client_name,contact_method,contact_value,
session_type,preferred_date AS requested_date,alternate_date,preferred_time AS requested_time,
requested_time_of_day_legacy AS legacy_requested_time_of_day,location,participants,notes AS client_notes,privacy_consent,
confirmed_date,confirmed_start_time,confirmed_end_time,admin_notes AS private_admin_notes,updated_at AS last_updated,
booking_terms_version,booking_terms_accepted_at,total_price,reservation_fee,reservation_fee_paid,reservation_fee_paid_at,
balance_paid,balance_paid_at,add_ons,additional_photos,additional_time,delivery_status,delivery_folder_url,
delivery_expires_at,client_selected_photos,client_selection_submitted_at
FROM public.toki_booking_requests;

CREATE OR REPLACE FUNCTION public.toki_get_client_gallery(p_token text)
RETURNS json LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $function$
DECLARE v_result json; v_token_hash text; v_global_hash text:=pg_catalog.encode(extensions.digest('toki-gallery-global-v1','sha256'),'hex');
BEGIN
  IF NOT public.consume_portfolio_quota(v_global_hash,'toki_gallery_global',120) THEN RETURN pg_catalog.json_build_object('ok',false,'code','rate_limited','message','Too many gallery requests. Please retry later.'); END IF;
  IF p_token IS NULL OR p_token !~ '^toki-[0-9a-f]{64}$' THEN RETURN pg_catalog.json_build_object('ok',false,'message','Gallery not found or access has been revoked.'); END IF;
  v_token_hash:=pg_catalog.encode(extensions.digest(p_token,'sha256'),'hex');
  IF NOT public.consume_portfolio_quota(v_token_hash,'toki_gallery_token',10) THEN RETURN pg_catalog.json_build_object('ok',false,'code','rate_limited','message','Too many attempts for this access key. Please retry later.'); END IF;
  SELECT pg_catalog.json_build_object('ok',true,'reference_code',reference_code,'client_name',name,'session_type',session_type,
    'confirmed_date',confirmed_date,'delivery_status',delivery_status,'delivery_folder_url',delivery_folder_url,
    'delivery_expires_at',delivery_expires_at,'client_selected_photos',client_selected_photos,
    'client_selection_submitted_at',client_selection_submitted_at) INTO v_result
  FROM public.toki_booking_requests WHERE delivery_token_hash=v_token_hash AND delivery_status IN('ready','delivered')
    AND delivery_folder_url IS NOT NULL AND delivery_expires_at IS NOT NULL AND pg_catalog.clock_timestamp()<delivery_expires_at;
  IF v_result IS NULL THEN RETURN pg_catalog.json_build_object('ok',false,'message','Gallery not found or access has been revoked.'); END IF;
  RETURN v_result;
END;
$function$;

CREATE OR REPLACE FUNCTION public.toki_submit_client_selection(p_token text,p_selections jsonb)
RETURNS json LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $function$
DECLARE v_token_hash text; v_global_hash text:=pg_catalog.encode(extensions.digest('toki-gallery-global-v1','sha256'),'hex'); v_selection_count integer; v_distinct_count integer;
BEGIN
  IF NOT public.consume_portfolio_quota(v_global_hash,'toki_gallery_global',120) THEN RETURN pg_catalog.json_build_object('ok',false,'code','rate_limited','message','Too many gallery requests. Please retry later.'); END IF;
  IF p_token IS NULL OR p_token !~ '^toki-[0-9a-f]{64}$' THEN RETURN pg_catalog.json_build_object('ok',false,'message','Unable to save selections. The gallery may have expired or been revoked.'); END IF;
  v_token_hash:=pg_catalog.encode(extensions.digest(p_token,'sha256'),'hex');
  IF NOT public.consume_portfolio_quota(v_token_hash,'toki_gallery_token',10) THEN RETURN pg_catalog.json_build_object('ok',false,'code','rate_limited','message','Too many attempts for this access key. Please retry later.'); END IF;
  IF p_selections IS NULL OR pg_catalog.jsonb_typeof(p_selections)<>'array' OR pg_catalog.jsonb_array_length(p_selections)>50 THEN
    RETURN pg_catalog.json_build_object('ok',false,'message','Selections must be a list of up to 50 photo IDs.');
  END IF;
  SELECT count(*),count(DISTINCT selected.value #>> '{}') INTO v_selection_count,v_distinct_count
  FROM pg_catalog.jsonb_array_elements(p_selections) AS selected(value)
  WHERE pg_catalog.jsonb_typeof(selected.value)='string' AND pg_catalog.char_length(selected.value #>> '{}') BETWEEN 1 AND 128;
  IF v_selection_count<>pg_catalog.jsonb_array_length(p_selections) OR v_distinct_count<>v_selection_count THEN
    RETURN pg_catalog.json_build_object('ok',false,'message','The selection list contains invalid or duplicate photo IDs.');
  END IF;
  UPDATE public.toki_booking_requests SET client_selected_photos=p_selections,
    client_selection_submitted_at=pg_catalog.clock_timestamp(),updated_at=pg_catalog.clock_timestamp()
  WHERE delivery_token_hash=v_token_hash AND delivery_status IN('ready','delivered') AND delivery_folder_url IS NOT NULL
    AND delivery_expires_at IS NOT NULL AND pg_catalog.clock_timestamp()<delivery_expires_at;
  IF FOUND THEN RETURN pg_catalog.json_build_object('ok',true,'message','Selections saved successfully.'); END IF;
  RETURN pg_catalog.json_build_object('ok',false,'message','Unable to save selections. The gallery may have expired or been revoked.');
END;
$function$;
REVOKE ALL ON FUNCTION public.toki_get_client_gallery(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.toki_submit_client_selection(text,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.toki_get_client_gallery(text) TO anon,authenticated;
GRANT EXECUTE ON FUNCTION public.toki_submit_client_selection(text,jsonb) TO anon,authenticated;
