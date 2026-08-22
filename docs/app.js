const API_BASE = "https://xyzrss.feishan0711.workers.dev";

const SITE_BASE = window.location.origin + "/xyzrss";

const form = document.getElementById("rss-form");
const urlInput = document.getElementById("rss-url");
const checkButton = document.getElementById("check-button");

const statusBox = document.getElementById("status");
const previewBox = document.getElementById("preview");

const feedList = document.getElementById("feed-list");
const selectAllButton = document.getElementById("select-all");
const generateOpmlButton = document.getElementById("generate-opml");


let feeds = [];


function setStatus(message, type = "success") {
  statusBox.textContent = message;
  statusBox.className = `status ${type}`;
}


function clearStatus() {
  statusBox.textContent = "";
  statusBox.className = "status hidden";
}


function clearPreview() {
  previewBox.innerHTML = "";
  previewBox.className = "preview hidden";
}


function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}


function fallbackCover() {
  return "data:image/svg+xml;charset=UTF-8," +
    encodeURIComponent(`
      <svg xmlns="http://www.w3.org/2000/svg"
           width="200"
           height="200"
           viewBox="0 0 200 200">
        <rect width="200" height="200" fill="#e5e7eb"/>
        <text x="100"
              y="108"
              text-anchor="middle"
              font-size="70">♫</text>
      </svg>
    `);
}


function normalizeFeed(feed) {
  return {
    id: feed.id,
    title: feed.title || feed.id,
    image: feed.image || fallbackCover(),
    source: feed.source,
    rss: `${SITE_BASE}/${feed.rss}`
  };
}


async function loadFeeds() {
  try {
    const response = await fetch("./feeds.json", {
      cache: "no-store"
    });

    if (!response.ok) {
      throw new Error("Failed to load feeds.json");
    }

    const data = await response.json();

    feeds = (data.feeds || []).map(normalizeFeed);

    renderFeeds();

  } catch (error) {
    feedList.innerHTML = `
      <div class="empty">
        Unable to load the podcast library.
      </div>
    `;

    console.error(error);
  }
}


function renderFeeds() {
  if (!feeds.length) {
    feedList.innerHTML = `
      <div class="empty">
        No podcasts in the library yet.
      </div>
    `;
    return;
  }

  feedList.innerHTML = feeds.map(feed => `
    <div class="feed-item">

      <input
        class="feed-checkbox"
        type="checkbox"
        value="${escapeHtml(feed.id)}"
        aria-label="Select ${escapeHtml(feed.title)}"
      >

      <img
        class="feed-cover"
        src="${escapeHtml(feed.image)}"
        alt=""
        loading="lazy"
        onerror="this.src='${fallbackCover()}'"
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
        >
          Copy
        </button>

        <button
          class="secondary open-button"
          data-url="${escapeHtml(feed.rss)}"
        >
          Open
        </button>

      </div>

    </div>
  `).join("");

  document.querySelectorAll(".copy-button").forEach(button => {
    button.addEventListener("click", async () => {
      await copyText(button.dataset.url);

      const oldText = button.textContent;
      button.textContent = "Copied";

      setTimeout(() => {
        button.textContent = oldText;
      }, 1200);
    });
  });

  document.querySelectorAll(".open-button").forEach(button => {
    button.addEventListener("click", () => {
      window.open(button.dataset.url, "_blank", "noopener");
    });
  });
}


async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const textarea = document.createElement("textarea");

    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();

    document.execCommand("copy");

    textarea.remove();
  }
}


function showPreview(result) {
  const title = escapeHtml(result.title || result.id);
  const image = escapeHtml(result.image || fallbackCover());

  previewBox.innerHTML = `
    <div class="preview-card">

      <img
        class="cover"
        src="${image}"
        alt=""
        onerror="this.src='${fallbackCover()}'"
      >

      <div class="preview-info">

        <div class="preview-title">
          ${title}
        </div>

        <div class="preview-subtitle">
          Xiaoyuzhou · ${escapeHtml(result.id)}
        </div>

      </div>

    </div>

    <div class="preview-actions">

      ${
        result.exists
          ? `
            <button
              id="preview-copy"
              class="secondary"
            >
              Copy RSS URL
            </button>
          `
          : `
            <button
              id="add-button"
            >
              Add to library
            </button>
          `
      }

    </div>
  `;

  previewBox.className = "preview";


  if (result.exists) {

    const copyButton = document.getElementById("preview-copy");

    copyButton.addEventListener("click", async () => {

      await copyText(result.rss);

      copyButton.textContent = "Copied";

      setTimeout(() => {
        copyButton.textContent = "Copy RSS URL";
      }, 1200);

    });

  } else {

    document
      .getElementById("add-button")
      .addEventListener("click", () => addFeed(result));

  }
}


async function validateFeed(url) {

  const endpoint =
    `${API_BASE}/api/validate?url=${encodeURIComponent(url)}`;

  const response = await fetch(endpoint);

  let data;

  try {
    data = await response.json();
  } catch {
    throw new Error("The API returned an invalid response.");
  }

  if (!response.ok) {
    throw new Error(data.error || "Validation failed.");
  }

  return data;
}


async function addFeed(result) {

  const addButton = document.getElementById("add-button");

  if (addButton) {
    addButton.disabled = true;
    addButton.textContent = "Adding...";
  }

  setStatus(
    "Adding the podcast and starting the RSS generation job...",
    "success"
  );

  try {

    const response = await fetch(`${API_BASE}/api/add`, {
      method: "POST",

      headers: {
        "Content-Type": "application/json"
      },

      body: JSON.stringify({
        url: result.source
      })
    });


    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Failed to add podcast.");
    }


    setStatus(
      "Podcast added. The compatible RSS feed is being generated. " +
      "It may take a short while before the URL becomes available.",
      "success"
    );


    previewBox.innerHTML = `
      <div class="preview-card">

        <img
          class="cover"
          src="${escapeHtml(result.image || fallbackCover())}"
          alt=""
          onerror="this.src='${fallbackCover()}'"
        >

        <div class="preview-info">

          <div class="preview-title">
            ${escapeHtml(result.title || result.id)}
          </div>

          <div class="preview-subtitle">
            Added to library
          </div>

        </div>

      </div>

      <div class="preview-actions">

        <button
          id="new-rss-copy"
          class="secondary"
        >
          Copy RSS URL
        </button>

        <button
          id="new-rss-open"
          class="secondary"
        >
          Open RSS
        </button>

      </div>
    `;


    const rssUrl =
      `${SITE_BASE}/${result.id}.xml`;


    document
      .getElementById("new-rss-copy")
      .addEventListener("click", async () => {

        await copyText(rssUrl);

        document.getElementById("new-rss-copy").textContent = "Copied";

      });


    document
      .getElementById("new-rss-open")
      .addEventListener("click", () => {

        window.open(rssUrl, "_blank", "noopener");

      });


    // Refresh the library after a short delay.
    setTimeout(loadFeeds, 5000);


  } catch (error) {

    setStatus(error.message, "error");

    if (addButton) {
      addButton.disabled = false;
      addButton.textContent = "Add to library";
    }
  }
}


form.addEventListener("submit", async event => {

  event.preventDefault();

  clearStatus();
  clearPreview();

  const url = urlInput.value.trim();

  if (!url) {
    setStatus("Please enter an RSS URL.", "warning");
    return;
  }


  checkButton.disabled = true;
  checkButton.textContent = "Checking...";


  try {

    const result = await validateFeed(url);


    if (!result.valid) {

      if (result.reason === "not_xiaoyuzhou") {

        setStatus(
          "This is a valid RSS feed, but it is not a Xiaoyuzhou feed.",
          "warning"
        );

      } else if (result.reason === "not_rss") {

        setStatus(
          "This URL does not return a valid RSS feed.",
          "error"
        );

      } else {

        setStatus(
          result.message || "This feed could not be validated.",
          "error"
        );
      }

      return;
    }


    showPreview(result);


    if (result.exists) {

      setStatus(
        "This podcast is already in your library.",
        "success"
      );

    } else {

      setStatus(
        "Valid Xiaoyuzhou RSS. You can add it to the library.",
        "success"
      );

    }

  } catch (error) {

    console.error(error);

    setStatus(
      error.message || "Unable to validate this RSS feed.",
      "error"
    );

  } finally {

    checkButton.disabled = false;
    checkButton.textContent = "Check RSS";

  }

});


selectAllButton.addEventListener("click", () => {

  const checkboxes =
    document.querySelectorAll(".feed-checkbox");

  const allChecked =
    [...checkboxes].every(checkbox => checkbox.checked);

  checkboxes.forEach(checkbox => {
    checkbox.checked = !allChecked;
  });

  selectAllButton.textContent =
    allChecked ? "Select all" : "Clear selection";

});


generateOpmlButton.addEventListener("click", () => {

  const selectedIds =
    [...document.querySelectorAll(".feed-checkbox:checked")]
      .map(checkbox => checkbox.value);


  if (!selectedIds.length) {

    setStatus(
      "Select at least one podcast first.",
      "warning"
    );

    return;
  }


  const selectedFeeds =
    feeds.filter(feed => selectedIds.includes(feed.id));


  const outlines =
    selectedFeeds.map(feed => {

      const title = escapeHtml(feed.title);
      const rss = escapeHtml(feed.rss);

      return `
    <outline
      text="${title}"
      title="${title}"
      type="rss"
      xmlUrl="${rss}"
    />`;

    }).join("\n");


  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head>
    <title>Xiaoyuzhou Podcasts</title>
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
        type: "application/xml;charset=utf-8"
      }
    );


  const url =
    URL.createObjectURL(blob);


  const link =
    document.createElement("a");

  link.href = url;
  link.download = "xiaoyuzhou-podcasts.opml";

  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);


  setStatus(
    `Generated OPML for ${selectedFeeds.length} podcast(s).`,
    "success"
  );

});


loadFeeds();
