// TOKI SATSUEI private booking notification relay.
// Store in Apps Script → Project Settings → Script Properties:
// TOKI_WEBHOOK_SECRET, TOKI_NOTIFICATION_EMAIL, TOKI_SENDER_NAME (optional).
// Deploy as a Web App: Execute as Me; access Anyone. Keep URL and secret in
// Supabase Edge Function secrets. Never put credentials in the public website.

const TOKI_PROPS = PropertiesService.getScriptProperties();
function output_(data) {
  return ContentService.createTextOutput(JSON.stringify(data)).setMimeType(ContentService.MimeType.JSON);
}
function text_(value, max) {
  return typeof value === "string" ? value.trim().slice(0, max) : "";
}
function escape_(value) {
  return String(value).replace(/[&<>"']/g, c => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
  })[c]);
}
function secretMatches_(given, expected) {
  if (typeof given !== "string" || !expected) return false;
  let diff = given.length ^ expected.length;
  for (let i = 0; i < Math.max(given.length, expected.length); i++) {
    diff |= (given.charCodeAt(i) || 0) ^ (expected.charCodeAt(i) || 0);
  }
  return diff === 0;
}
function doPost(e) {
  const expected = TOKI_PROPS.getProperty("TOKI_WEBHOOK_SECRET") || "";
  const recipient = TOKI_PROPS.getProperty("TOKI_NOTIFICATION_EMAIL") || "";
  if (!expected || !recipient) return output_({ok:false,error:"not_configured"});

  let input;
  try {
    const raw = e && e.postData && e.postData.contents;
    if (!raw || raw.length > 12000) return output_({ok:false,error:"invalid_request"});
    input = JSON.parse(raw);
  } catch (_) { return output_({ok:false,error:"invalid_json"}); }

  if (!secretMatches_(input.secret, expected) || input.kind !== "toki_booking_notification") {
    return output_({ok:false,error:"unauthorized"});
  }
  const b = input.booking && typeof input.booking === "object" ? input.booking : {};
  const ref = text_(b.reference_code,20), name = text_(b.name,100);
  const method = text_(b.contact_method,20), contact = text_(b.contact_value,254);
  const session = text_(b.session_type,60), date = text_(b.preferred_date,10);
  const alt = text_(b.alternate_date,10), time = text_(b.preferred_time,20);
  const location = text_(b.location,200), notes = text_(b.notes,2000);
  const participants = Number(b.participants);
  const valid = /^TOKI-[A-F0-9]{8}$/.test(ref) && name && contact &&
    ["instagram","facebook","email"].includes(method) && session &&
    /^\\d{4}-\\d{2}-\\d{2}$/.test(date) &&
    (!alt || /^\\d{4}-\\d{2}-\\d{2}$/.test(alt)) &&
    ["Morning","Afternoon","Evening","Flexible"].includes(time) &&
    location.length >= 2 && notes.length >= 10 &&
    Number.isInteger(participants) && participants >= 1 && participants <= 12;
  if (!valid) return output_({ok:false,error:"invalid_booking"});

  const lock = LockService.getScriptLock();
  try {
    lock.waitLock(10000);
    const sent = JSON.parse(TOKI_PROPS.getProperty("TOKI_SENT_REFS") || "[]");
    if (Array.isArray(sent) && sent.includes(ref)) return output_({ok:true,duplicate:true});
    if (MailApp.getRemainingDailyQuota() < 1) return output_({ok:false,error:"daily_quota"});

    const rows = [
      ["Reference",ref],["Name",name],["Contact channel",method],["Contact detail",contact],
      ["Session",session],["Preferred date",date],["Alternative date",alt || "Not supplied"],
      ["Preferred time",time],["Location",location],["Participants",String(participants)],["Notes",notes]
    ];
    const plain = "A new TOKI SATSUEI booking inquiry was saved.\\n\\n" +
      rows.map(r => r[0] + ": " + r[1]).join("\\n") +
      "\\n\\nInquiry only. The date is not reserved until you confirm it.";
    const htmlRows = rows.map(r => "<tr><th align='left' style='padding:8px;border-bottom:1px solid #ddd'>" +
      escape_(r[0]) + "</th><td style='padding:8px;border-bottom:1px solid #ddd'>" +
      escape_(r[1]) + "</td></tr>").join("");
    const html = "<div style='font:14px Arial;color:#222;max-width:680px'>" +
      "<div style='background:#111;color:#fff;padding:22px'><small>TOKI SATSUEI · BOOKING DESK</small>" +
      "<h2>New booking inquiry</h2><p>" + escape_(ref) + "</p></div>" +
      "<table style='width:100%;border-collapse:collapse'>" + htmlRows + "</table>" +
      "<p style='color:#666'>Inquiry only — this does not reserve the date.</p></div>";
    const message = {
      to: recipient,
      subject: "New TOKI SATSUEI booking inquiry · " + ref,
      body: plain,
      htmlBody: html,
      name: TOKI_PROPS.getProperty("TOKI_SENDER_NAME") || "TOKI SATSUEI Booking Desk"
    };
    if (method === "email" && /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(contact)) message.replyTo = contact;
    MailApp.sendEmail(message);

    const next = (Array.isArray(sent) ? sent : []).filter(v => v !== ref);
    next.push(ref);
    TOKI_PROPS.setProperty("TOKI_SENT_REFS", JSON.stringify(next.slice(-150)));
    return output_({ok:true,reference_code:ref});
  } catch (_) {
    return output_({ok:false,error:"send_failed"});
  } finally {
    try { lock.releaseLock(); } catch (_) {}
  }
}
