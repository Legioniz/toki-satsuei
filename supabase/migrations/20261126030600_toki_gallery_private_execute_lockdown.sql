-- Public RPC wrappers are the intended client entry points.
-- Execute them as postgres, then remove direct client privileges on the
-- SECURITY DEFINER implementations in the non-exposed private schema.
ALTER FUNCTION public.toki_get_client_gallery(text) SECURITY DEFINER;
ALTER FUNCTION public.toki_submit_client_selection(text, jsonb) SECURITY DEFINER;

REVOKE ALL ON FUNCTION private.toki_get_client_gallery(text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION private.toki_submit_client_selection(text, jsonb) FROM PUBLIC, anon, authenticated;

REVOKE ALL ON FUNCTION public.toki_get_client_gallery(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.toki_submit_client_selection(text, jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.toki_get_client_gallery(text) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.toki_submit_client_selection(text, jsonb) TO anon, authenticated;
