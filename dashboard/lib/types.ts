export type Session = {
  id: string;
  cowrie_session: string | null;
  source_ip: string;
  country: string | null;
  asn: string | null;
  started_at: string;
  ended_at: string | null;
  protocol: string | null;
  usernames_tried: string[] | null;
  passwords_tried: string[] | null;
  commands_tried: string[] | null;
  abuseipdb_score: number | null;
  vt_malicious_count: number | null;
  mitre_techniques: string[] | null;
  ai_summary: string | null;
  ai_notability_score: number | null;
  created_at: string;
};
