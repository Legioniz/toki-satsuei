-- Protect the booking audit trail from application-role tampering.
ALTER TABLE public.admin_activity FORCE ROW LEVEL SECURITY;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
  ON public.admin_activity FROM PUBLIC, anon, authenticated, service_role;

GRANT SELECT ON public.admin_activity TO authenticated;

CREATE OR REPLACE FUNCTION private.prevent_admin_activity_mutation()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $function$
BEGIN
  RAISE EXCEPTION 'admin_activity is append-only; updates and deletions are prohibited'
    USING ERRCODE = '55000';
END;
$function$;

REVOKE ALL ON FUNCTION private.prevent_admin_activity_mutation() FROM PUBLIC, anon, authenticated, service_role;

DROP TRIGGER IF EXISTS admin_activity_append_only ON public.admin_activity;
CREATE TRIGGER admin_activity_append_only
BEFORE UPDATE OR DELETE ON public.admin_activity
FOR EACH ROW EXECUTE FUNCTION private.prevent_admin_activity_mutation();
