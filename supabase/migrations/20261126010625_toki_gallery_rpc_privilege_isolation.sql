-- Move privileged gallery operations into the non-exposed private schema.
-- Public RPC entry points are SECURITY INVOKER wrappers.
CREATE OR REPLACE FUNCTION private.toki_get_client_gallery(p_token text)
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
  RETURN COALESCE(v_result,pg_catalog.json_build_object('ok',false,'message','Gallery not found or access has been revoked.'));
END;
$function$;

CREATE OR REPLACE FUNCTION private.toki_submit_client_selection(p_token text,p_selections jsonb)
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

REVOKE ALL ON FUNCTION private.toki_get_client_gallery(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION private.toki_submit_client_selection(text,jsonb) FROM PUBLIC;
GRANT USAGE ON SCHEMA private TO anon,authenticated;
GRANT EXECUTE ON FUNCTION private.toki_get_client_gallery(text) TO anon,authenticated;
GRANT EXECUTE ON FUNCTION private.toki_submit_client_selection(text,jsonb) TO anon,authenticated;

CREATE OR REPLACE FUNCTION public.toki_get_client_gallery(p_token text)
RETURNS json LANGUAGE sql SECURITY INVOKER SET search_path = ''
AS $function$ SELECT private.toki_get_client_gallery(p_token); $function$;
CREATE OR REPLACE FUNCTION public.toki_submit_client_selection(p_token text,p_selections jsonb)
RETURNS json LANGUAGE sql SECURITY INVOKER SET search_path = ''
AS $function$ SELECT private.toki_submit_client_selection(p_token,p_selections); $function$;

REVOKE ALL ON FUNCTION public.toki_get_client_gallery(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.toki_submit_client_selection(text,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.toki_get_client_gallery(text) TO anon,authenticated;
GRANT EXECUTE ON FUNCTION public.toki_submit_client_selection(text,jsonb) TO anon,authenticated;
ALTER FUNCTION private.is_portfolio_admin() SET search_path = '';
