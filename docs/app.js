// News and archives are static; keep compatibility with old shared links.
const oldDate = new URLSearchParams(location.search).get("date");
if (/^\d{4}-\d{2}-\d{2}$/.test(oldDate || "") && !location.pathname.includes("/archive/")) {
  location.replace(`./archive/${oldDate}.html`);
}
