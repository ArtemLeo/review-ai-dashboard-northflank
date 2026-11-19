/**
 * Country whose flag stands for each language, by ISO 639-1 code.
 *
 * A language is not a country, so every entry names the country where the
 * language is official or most widely spoken.  The deprecated codes some
 * models still answer with (iw, in, ji, jw, mo, sh) are listed as well.
 * Constructed languages such as Esperanto have no country and get the globe.
 */
const LANGUAGE_TO_COUNTRY: Record<string, string> = {
  aa: "DJ",
  ab: "GE",
  ae: "IR",
  af: "ZA",
  ak: "GH",
  am: "ET",
  an: "ES",
  ar: "SA",
  as: "IN",
  av: "RU",
  ay: "BO",
  az: "AZ",
  ba: "RU",
  be: "BY",
  bg: "BG",
  bh: "IN",
  bi: "VU",
  bm: "ML",
  bn: "BD",
  bo: "CN",
  br: "FR",
  bs: "BA",
  ca: "AD",
  ce: "RU",
  ch: "GU",
  co: "FR",
  cr: "CA",
  cs: "CZ",
  cu: "RU",
  cv: "RU",
  cy: "GB",
  da: "DK",
  de: "DE",
  dv: "MV",
  dz: "BT",
  ee: "GH",
  el: "GR",
  en: "US",
  es: "ES",
  et: "EE",
  eu: "ES",
  fa: "IR",
  ff: "SN",
  fi: "FI",
  fj: "FJ",
  fo: "FO",
  fr: "FR",
  fy: "NL",
  ga: "IE",
  gd: "GB",
  gl: "ES",
  gn: "PY",
  gu: "IN",
  gv: "IM",
  ha: "NG",
  he: "IL",
  hi: "IN",
  ho: "PG",
  hr: "HR",
  ht: "HT",
  hu: "HU",
  hy: "AM",
  hz: "NA",
  id: "ID",
  ig: "NG",
  ii: "CN",
  ik: "US",
  in: "ID",
  is: "IS",
  it: "IT",
  iu: "CA",
  iw: "IL",
  ja: "JP",
  ji: "IL",
  jv: "ID",
  jw: "ID",
  ka: "GE",
  kg: "CD",
  ki: "KE",
  kj: "NA",
  kk: "KZ",
  kl: "GL",
  km: "KH",
  kn: "IN",
  ko: "KR",
  kr: "NG",
  ks: "IN",
  ku: "IQ",
  kv: "RU",
  kw: "GB",
  ky: "KG",
  la: "VA",
  lb: "LU",
  lg: "UG",
  li: "NL",
  ln: "CD",
  lo: "LA",
  lt: "LT",
  lu: "CD",
  lv: "LV",
  mg: "MG",
  mh: "MH",
  mi: "NZ",
  mk: "MK",
  ml: "IN",
  mn: "MN",
  mo: "MD",
  mr: "IN",
  ms: "MY",
  mt: "MT",
  my: "MM",
  na: "NR",
  nb: "NO",
  nd: "ZW",
  ne: "NP",
  ng: "NA",
  nl: "NL",
  nn: "NO",
  no: "NO",
  nr: "ZA",
  nv: "US",
  ny: "MW",
  oc: "FR",
  oj: "CA",
  om: "ET",
  or: "IN",
  os: "RU",
  pa: "IN",
  pi: "LK",
  pl: "PL",
  ps: "AF",
  pt: "PT",
  qu: "PE",
  rm: "CH",
  rn: "BI",
  ro: "RO",
  ru: "RU",
  rw: "RW",
  sa: "IN",
  sc: "IT",
  sd: "PK",
  se: "NO",
  sg: "CF",
  sh: "BA",
  si: "LK",
  sk: "SK",
  sl: "SI",
  sm: "WS",
  sn: "ZW",
  so: "SO",
  sq: "AL",
  sr: "RS",
  ss: "SZ",
  st: "LS",
  su: "ID",
  sv: "SE",
  sw: "TZ",
  ta: "IN",
  te: "IN",
  tg: "TJ",
  th: "TH",
  ti: "ER",
  tk: "TM",
  tl: "PH",
  tn: "BW",
  to: "TO",
  tr: "TR",
  ts: "ZA",
  tt: "RU",
  tw: "GH",
  ty: "PF",
  ug: "CN",
  uk: "UA",
  ur: "PK",
  uz: "UZ",
  ve: "ZA",
  vi: "VN",
  wa: "BE",
  wo: "SN",
  xh: "ZA",
  yi: "IL",
  yo: "NG",
  za: "CN",
  zh: "CN",
  zu: "ZA",
};

/** Shown for a missing, unknown or constructed language. */
const NO_FLAG = "🌐";

/** The first regional indicator symbol, the flag letter "A". */
const REGIONAL_INDICATOR_A = 0x1f1e6;

/** Turns an ISO 3166-1 alpha-2 country code into its flag emoji. */
function countryFlag(countryCode: string): string {
  const letters = [...countryCode.toUpperCase()];
  return String.fromCodePoint(
    ...letters.map((letter) => REGIONAL_INDICATOR_A + letter.charCodeAt(0) - "A".charCodeAt(0))
  );
}

/**
 * Get the country flag emoji for a language code such as `uk`, `en-US` or
 * `zh-Hans`.
 *
 * A two-letter region subtag names the country directly, so `en-US` shows the
 * US flag and `pt-BR` the Brazilian one; otherwise the language's own country
 * is used.
 * @param languageCode - Language code as detected by the AI.
 * @returns Flag emoji as a string. Returns '🌐' for a missing, unknown or
 *   constructed language.
 */
export function getLanguageFlag(languageCode: string | null): string {
  if (!languageCode) return NO_FLAG;

  const [language = "", region = ""] = languageCode.trim().toLowerCase().split("-");
  if (/^[a-z]{2}$/.test(region)) {
    // "UK" is no ISO country code; the United Kingdom is "GB".
    return countryFlag(region === "uk" ? "gb" : region);
  }

  const country = LANGUAGE_TO_COUNTRY[language];
  return country ? countryFlag(country) : NO_FLAG;
}
