const REPOSITORY =
  "https://github.com/x-claire-lin/xyzrss";

const EDIT_FEEDS_URL =
  `${REPOSITORY}/edit/main/feeds.txt`;

const SITE_BASE =
  window.location.origin +
  window.location.pathname.replace(/\/$/, "");

const form =
  document.getElementById("rss-form");

const urlInput =
  document.getElementById("rss-url");

const checkButton =
  document.getElementById("check-button");

const statusBox =
  document.getElementById("status");

const previewBox =
  document.getElementById("preview");

const feedList =
  document.getElementById("feed-list");

const selectAllButton =
  document.getElementById("select-all");

const generateOpmlButton =
  document.getElementById("generate-opml");

const editFeedsLink =
  document.getElementById("edit-feeds-link");


let feeds = [];


editFeedsLink.href = EDIT_FEEDS_URL;


function setStatus(
  message,
  type = "success"
) {
  statusBox.textContent = message;
  statusBox.className =
    `status ${type}`;
}


function clearStatus() {
  statusBox.textContent = "";
  statusBox.className =
    "status hidden";
}


function clearPreview() {
  previewBox.innerHTML = "";
  previewBox.className =
    "preview hidden";
}


function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}


function escapeXml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}


function fallbackCover() {
  return (
    "data:image/svg+xml;charset=UTF-8," +
    encodeURIComponent(`
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="200"
        height="200"
        viewBox="0 0 200 200"
      >
        <rect
          width="200"
          height="200"
          fill="#e5e7eb"
        />

        <text
          x="100"
          y="108"
          text-anchor="middle"
          font-size="70"
        >
          ♫
        </text>
      </svg>
    `)
  );
}


function normalizeFeed(feed) {
  return {
    id: feed.id,
    title: feed.title || feed.id,
    image: feed.image || fallbackCover(),
    source:
      feed.source ||
      `https://feed.xyzfm.space/${feed.id}`,
    rss:
      `${SITE_BASE}/${feed.id}.xml`
  };
}


async function loadFeedsFromJson() {
  const response =
    await fetch(
      "./feeds.json",
      {
        cache: "no-store"
      }
    );

  if (!response.ok) {
    throw new Error(
      "feeds.json unavailable"
    );
  }

  const data =
    await response.json();

  return (data.feeds || [])
    .map(normalizeFeed);
}


async function loadFeedsFromTxt() {
  const response =
    await fetch(
      "./../feeds.txt",
      {
        cache: "no-store"
      }
    );

  if (!response.ok) {
    throw new Error(
      "feeds.txt unavailable"
    );
  }

  const text =
    await response.text();

  const result = [];

  for (
    const line of text.split(/\r?\n/)
  ) {
    const trimmed =
      line.trim();

    if (!trimmed) {
      continue;
    }

    if (trimmed.startsWith("#")) {
      continue;
    }

    const parts =
      trimmed.split("#");

    const id =
      parts[0].trim();

    const title =
      parts
        .slice(1)
        .join("#")
        .trim();

    if (
      !/^[A-Za-z0-9_-]+$/.test(id)
    ) {
      continue;
    }

    result.push(
      normalizeFeed({
        id,
        title
      })
    );
  }

  return result;
}


async function loadFeeds() {

  try {

    try {
      feeds =
        await loadFeedsFromJson();
    } catch {
      feeds =
        await loadFeedsFromTxt();
    }

    renderFeeds();

  } catch (error) {

    console.error(error);

    feedList.innerHTML = `
      <div class="empty">
        无法加载播客列表。
        <br>
        请确认 GitHub Pages 已启用。
      </div>
    `;
  }
}


function renderFeeds() {

  if (!feeds.length) {

    feedList.innerHTML = `
      <div class="empty">
        目前还没有播客。
      </div>
    `;

    return;
  }


  feedList.innerHTML =
    feeds
      .map(feed => `

        <div class="feed-item">

          <input
            class="feed-checkbox"
            type="checkbox"
            value="${escapeHtml(feed.id)}"
            aria-label="选择 ${escapeHtml(feed.title)}"
          >


          <img
            class="feed-cover"
            src="${escapeHtml(feed.image)}"
            alt=""
            loading="lazy"
            onerror="this.src='${fallbackCover()}';"
          >


          <div class="feed-info">

            <div class="feed-title">
              ${escapeHtml(feed.title)}
            </div>

            <div class="feed-id">
              ${escapeHtml(feed.id)}
            </div>

          </div>


          <div class="feed-buttons">

            <button
              class="secondary copy-button"
              data-url="${escapeHtml(feed.rss)}"
              type="button"
            >
              复制
            </button>


            <button
              class="secondary open-button"
              data-url="${escapeHtml(feed.rss)}"
              type="button"
            >
              打开
            </button>

          </div>

        </div>

      `)
      .join("");


  document
    .querySelectorAll(".copy-button")
    .forEach(button => {

      button.addEventListener(
        "click",
        async () => {

          await copyText(
            button.dataset.url
          );

          const oldText =
            button.textContent;

          button.textContent =
            "已复制";

          setTimeout(() => {
            button.textContent =
              oldText;
          }, 1200);

        }
      );

    });


  document
    .querySelectorAll(".open-button")
    .forEach(button => {

      button.addEventListener(
        "click",
        () => {

          window.open(
            button.dataset.url,
            "_blank",
            "noopener"
          );

        }
      );

    });
}


async function copyText(text) {

  try {

    await navigator
      .clipboard
      .writeText(text);

  } catch {

    const textarea =
      document.createElement(
        "textarea"
      );

    textarea.value = text;

    document.body.appendChild(
      textarea
    );

    textarea.select();

    document.execCommand(
      "copy"
    );

    textarea.remove();
  }
}


function parseFeedUrl(url) {

  let parsed;

  try {
    parsed = new URL(url);
  } catch {
    return null;
  }


  if (
    parsed.protocol !== "https:"
  ) {
    return null;
  }


  const hostname =
    parsed.hostname.toLowerCase();


  if (
    hostname !== "feed.xyzfm.space"
  ) {
    return null;
  }


  const parts =
    parsed.pathname
      .split("/")
      .filter(Boolean);


  if (parts.length !== 1) {
    return null;
  }


  const feedId =
    parts[0];


  if (
    !/^[A-Za-z0-9_-]+$/.test(feedId)
  ) {
    return null;
  }


  return feedId;
}


function findExistingFeed(feedId) {

  return feeds.find(
    feed => feed.id === feedId
  );
}


function showAddInstructions(
  feedId
) {

  const existing =
    findExistingFeed(feedId);


  const sourceUrl =
    `https://feed.xyzfm.space/${feedId}`;


  if (existing) {

    previewBox.innerHTML = `

      <div class="preview-card">

        <div class="preview-info">

          <div class="preview-title">
            ${escapeHtml(existing.title)}
          </div>

          <div class="preview-subtitle">
            已经在播客库中
          </div>

        </div>

      </div>


      <div class="preview-actions">

        <button
          id="existing-copy"
          class="secondary"
          type="button"
        >
          复制 RSS URL
        </button>


        <button
          id="existing-open"
          type="button"
        >
          打开 RSS
        </button>

      </div>

    `;

    previewBox.className =
      "preview";


    document
      .getElementById("existing-copy")
      .addEventListener(
        "click",
        async () => {

          await copyText(
            existing.rss
          );

          setStatus(
            "RSS URL 已复制。",
            "success"
          );
        }
      );


    document
      .getElementById("existing-open")
      .addEventListener(
        "click",
        () => {

          window.open(
            existing.rss,
            "_blank",
            "noopener"
          );

        }
      );

    return;
  }


  previewBox.innerHTML = `

    <div class="preview-card">

      <div class="preview-info">

        <div class="preview-title">
          Feed ID：${escapeHtml(feedId)}
        </div>

        <div class="preview-subtitle">
          小宇宙 RSS 已识别
        </div>

      </div>

    </div>


    <div class="add-instruction">

      <p>
        把下面这一行加入
        <code>feeds.txt</code>：
      </p>


      <div class="code-box">
        ${escapeHtml(feedId)} # 节目名称
      </div>


      <p class="muted">
        把“节目名称”替换成实际播客名称。
        提交后 GitHub Actions 会自动生成兼容 RSS。
      </p>

    </div>


    <div class="preview-actions">

      <button
        id="copy-config"
        type="button"
      >
        复制配置行
      </button>


      <button
        id="edit-github"
        class="secondary"
        type="button"
      >
        打开 GitHub 编辑
      </button>

    </div>

  `;

  previewBox.className =
    "preview";


  const config =
    `${feedId} # 节目名称`;


  document
    .getElementById("copy-config")
    .addEventListener(
      "click",
      async () => {

        await copyText(config);

        setStatus(
          "配置行已复制。",
          "success"
        );

      }
    );


  document
    .getElementById("edit-github")
    .addEventListener(
      "click",
      () => {

        window.open(
          EDIT_FEEDS_URL,
          "_blank",
          "noopener"
        );

      }
    );
}


form.addEventListener(
  "submit",
  event => {

    event.preventDefault();

    clearStatus();
    clearPreview();

    const url =
      urlInput.value.trim();


    if (!url) {

      setStatus(
        "请输入 RSS URL。",
        "warning"
      );

      return;
    }


    const feedId =
      parseFeedUrl(url);


    if (!feedId) {

      setStatus(
        "这不是有效的小宇宙 RSS 地址。格式应类似：https://feed.xyzfm.space/xxxxxxxxxxxx",
        "error"
      );

      return;
    }


    showAddInstructions(
      feedId
    );


    setStatus(
      "已识别小宇宙 RSS。",
      "success"
    );

  }
);


selectAllButton.addEventListener(
  "click",
  () => {

    const checkboxes =
      document.querySelectorAll(
        ".feed-checkbox"
      );


    if (!checkboxes.length) {
      return;
    }


    const allChecked =
      [...checkboxes]
        .every(
          checkbox =>
            checkbox.checked
        );


    checkboxes.forEach(
      checkbox => {
        checkbox.checked =
          !allChecked;
      }
    );


    selectAllButton.textContent =
      allChecked
        ? "全选"
        : "取消全选";
  }
);


generateOpmlButton.addEventListener(
  "click",
  () => {

    const selectedIds =
      [
        ...document.querySelectorAll(
          ".feed-checkbox:checked"
        )
      ]
        .map(
          checkbox =>
            checkbox.value
        );


    if (!selectedIds.length) {

      setStatus(
        "请至少选择一个播客。",
        "warning"
      );

      return;
    }


    const selectedFeeds =
      feeds.filter(
        feed =>
          selectedIds.includes(
            feed.id
          )
      );


    const outlines =
      selectedFeeds
        .map(feed => {

          const title =
            escapeXml(
              feed.title
            );

          const rss =
            escapeXml(
              feed.rss
            );


          return `
    <outline
      text="${title}"
      title="${title}"
      type="rss"
      xmlUrl="${rss}"
    />`;

        })
        .join("\n");


    const xml =
`<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head>
    <title>小宇宙 Podcasts</title>
  </head>
  <body>
${outlines}
  </body>
</opml>
`;


    const blob =
      new Blob(
        [xml],
        {
          type:
            "application/xml;charset=utf-8"
        }
      );


    const url =
      URL.createObjectURL(
        blob
      );


    const link =
      document.createElement(
        "a"
      );

    link.href = url;

    link.download =
      "xiaoyuzhou-podcasts.opml";


    document.body.appendChild(
      link
    );

    link.click();

    link.remove();

    URL.revokeObjectURL(
      url
    );


    setStatus(
      `已生成 ${selectedFeeds.length} 个播客的 OPML。`,
      "success"
    );

  }
);


loadFeeds();
