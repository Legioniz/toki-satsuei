ALTER TABLE public.toki_booking_requests
  ADD COLUMN booking_terms_accepted_at timestamptz,
  ADD COLUMN booking_terms_version text;

ALTER TABLE public.toki_booking_requests
  ADD CONSTRAINT toki_booking_terms_acceptance_complete
  CHECK (
    (booking_terms_accepted_at IS NULL AND booking_terms_version IS NULL)
    OR (
      booking_terms_accepted_at IS NOT NULL
      AND booking_terms_version IS NOT NULL
      AND char_length(btrim(booking_terms_version)) BETWEEN 1 AND 40
    )
  );

COMMENT ON COLUMN public.toki_booking_requests.booking_terms_accepted_at
  IS 'Server timestamp recorded only after the client explicitly accepts the booking and cancellation terms.';
COMMENT ON COLUMN public.toki_booking_requests.booking_terms_version
  IS 'Version of the booking/payment/cancellation terms accepted by the client.';
