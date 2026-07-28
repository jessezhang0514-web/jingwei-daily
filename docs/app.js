const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );

const safeUrl = (value) => {
  try {
    const url = new URL(value);
    return /^https?:$/.test(url.protocol) ? url.href : "";
  } catch {
    return "";
  }
};

function storyMarkup(story, index) {
  const url = safeUrl(story.sourceUrl);
  return `
    <article class="card ${index === 0 ? "lead" : ""}">
      <div class="story-index">
        <span>${String(story.rank || index + 1).padStart(2, "0")}</span>
        <small>${esc(story.category)}</small>
      </div>
      <div class="body">
        <div class="source">
          <span>${esc(story.source)}</span>
          <span>${esc(story.eventTime)}</span>
        </div>
        <h3><a href="${url}" target="_blank" rel="noreferrer">${esc(story.title)}</a></h3>
        <p>${esc(story.summary)}</p>
        <div class="why"><strong>为什么重要</strong>${esc(story.whyImportant)}</div>
        <div class="foot"><a href="${url}" target="_blank" rel="noreferrer">阅读原文 ↗</a></div>
      </div>
    </article>`;
}

function render(digests) {
  const all = (Array.isArray(digests) ? digests : [])
    .slice()
    .sort((a, b) => String(b.date).localeCompare(String(a.date)));
  const requestedDate = new URLSearchParams(location.search).get("date");
  const digest = all.find((item) => item.date === requestedDate) || all[0];
  if (!digest) return;

  const stories = (digest.articles || [])
    .slice()
    .sort((a, b) => Number(a.rank) - Number(b.rank));

  document.title = `${digest.date} · 经纬日报`;
  document.querySelector("#title").textContent =
    digest.title || "今日全球科技与经济要闻";
  document.querySelector("#date").textContent = digest.date;
  document.querySelector("#count").textContent = `${stories.length} 则新闻`;
  document.querySelector("#updated").textContent =
    `更新于 ${digest.generatedAt || digest.date}`;

  const themes = (digest.mainThemes || []).slice(0, 3);
  document.querySelector("#themegrid").innerHTML = themes
    .map(
      (theme, index) =>
        `<article class="theme"><span>0${index + 1}</span><p>${esc(theme)}</p></article>`,
    )
    .join("");

  document.querySelector("#news").innerHTML =
    `<div class="grid">${stories.map(storyMarkup).join("")}</div>`;

  document.querySelector("#archive").innerHTML = all
    .slice(0, 365)
    .map(
      (item) =>
        `<a class="${item.date === digest.date ? "active" : ""}" href="?date=${encodeURIComponent(item.date)}"><time>${esc(item.date)}</time><span>查看 →</span></a>`,
    )
    .join("");

  document.querySelector("#watch").innerHTML =
    `<ol>${(digest.watchNext || [])
      .slice(0, 5)
      .map((item) => `<li>${esc(item)}</li>`)
      .join("")}</ol>`;
}

fetch("./data/digests.json", { cache: "no-store" })
  .then((response) => (response.ok ? response.json() : []))
  .then(render)
  .catch(() => {});
