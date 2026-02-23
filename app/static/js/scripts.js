// app/static/js/scripts.js

// ──────────────────────────────────────────────────────────────
// DOMContentLoaded — main initialisation
// ──────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", function () {
  console.log("DOM fully loaded and parsed.");

  // ── Modal helpers (exposed globally for legacy close-button support) ──
  window.closeModal = function () {
    const modal = document.getElementById("rdModal");
    if (modal) {
      modal.style.display = "none";
      modal.classList.remove("show");
    }
  };

  window.closeIndexModal = function (modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.style.display = "none";
      modal.classList.remove("show");
    }
  };

  // Hide all modals on page load
  document.querySelectorAll(".rd-modal").forEach(function (modal) {
    modal.style.display = "none";
  });

  // ── Search form — normal POST with loading overlay ──────────
  // FIX: removed the old fetch() + document.write() approach that
  // destroyed the entire DOM.  We now let the browser POST the form
  // normally and just show a spinner during navigation.
  const searchForm = document.getElementById("search-form");
  const loadingOverlay = document.getElementById("loading");

  if (searchForm && loadingOverlay) {
    searchForm.addEventListener("submit", function () {
      // Show the loading overlay; the browser will navigate away,
      // so we don't need to hide it – the new page load resets it.
      loadingOverlay.style.display = "flex";
      // Do NOT call event.preventDefault() — we want the real POST.
    });
  }

  // Enter-key support (mirrors submit-button click)
  const submitButton = document.getElementById("submit-button");
  if (searchForm && submitButton) {
    searchForm.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
        submitButton.click();
      }
    });
  }

  // ── Close modals on outside click ───────────────────────────
  window.addEventListener("click", function (event) {
    const rdModal = document.getElementById("rdModal");
    if (rdModal && rdModal.classList.contains("show") && event.target === rdModal) {
      closeModal();
    }
    document.querySelectorAll(".rd-modal").forEach(function (modal) {
      if (modal.classList.contains("show") && event.target === modal) {
        closeIndexModal(modal.id);
      }
    });
  });

  // ── Navigation loading overlay ──────────────────────────────
  document.querySelectorAll(".navbar a").forEach(function (link) {
    link.addEventListener("click", function (event) {
      if (loadingOverlay) loadingOverlay.style.display = "flex";
      event.preventDefault();
      var href = this.href;
      setTimeout(function () {
        window.location.href = href;
      }, 300);
    });
  });

  // ── Centralised event delegation for [data-action] buttons ──
  // This replaces ALL inline onclick="" handlers across templates,
  // removing XSS risk from user-controlled data (download links, IDs).
  document.addEventListener("click", function (event) {
    var btn = event.target.closest("[data-action]");
    if (!btn) return;

    var action = btn.getAttribute("data-action");
    var url = btn.getAttribute("data-url") || "";
    var id = btn.getAttribute("data-id") || "";

    switch (action) {
      case "download":
        if (url) {
          // Unrestrict the link on-demand, then open the direct download
          btn.disabled = true;
          var origHTML = btn.innerHTML;
          btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading...';
          fetch("/torrent/unrestrict_link", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ link: url })
          })
            .then(function (r) { return r.json(); })
            .then(function (data) {
              var dlUrl = data.unrestricted_link || url;
              if (dlUrl && isValidUrl(dlUrl)) window.open(dlUrl, "_blank");
            })
            .catch(function () {
              // Fallback: try opening the original URL
              if (isValidUrl(url)) window.open(url, "_blank");
            })
            .finally(function () {
              btn.innerHTML = origHTML;
              btn.disabled = false;
            });
        }
        break;

      case "vlc":
        if (url) {
          btn.disabled = true;
          var vlcOrigHTML = btn.innerHTML;
          btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading...';
          fetch("/torrent/unrestrict_link", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ link: url })
          })
            .then(function (r) { return r.json(); })
            .then(function (data) { launchVLC(data.unrestricted_link || url); })
            .catch(function () { launchVLC(url); })
            .finally(function () { btn.innerHTML = vlcOrigHTML; btn.disabled = false; });
        }
        break;

      case "heresphere":
        if (url) {
          btn.disabled = true;
          var hsOrigHTML = btn.innerHTML;
          btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading...';
          fetch("/torrent/unrestrict_link", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ link: url })
          })
            .then(function (r) { return r.json(); })
            .then(function (data) { launchHeresphere(data.unrestricted_link || url); })
            .catch(function () { launchHeresphere(url); })
            .finally(function () { btn.innerHTML = hsOrigHTML; btn.disabled = false; });
        }
        break;

      case "open-file-modal":
        openFileModal(id);
        break;

      case "close-modal":
        closeIndexModal(id);
        break;

      case "show-files":
        showFiles(id);
        break;

      case "confirm-delete":
        confirmDeletion(id);
        break;

      case "delete-selected":
        deleteSelectedTorrents();
        break;

      case "toggle-select-all":
        // The btn IS the checkbox input itself
        toggleSelectAll(btn);
        break;

      default:
        console.warn("Unknown data-action:", action);
    }
  });
});

// ──────────────────────────────────────────────────────────────
// Video extensions (loaded once on startup)
// ──────────────────────────────────────────────────────────────
window.videoExtensions = [];

function loadVideoExtensions() {
  fetch("/static/video_extensions.json")
    .then(function (response) {
      if (!response.ok) throw new Error("Failed to load video extensions");
      return response.json();
    })
    .then(function (data) {
      window.videoExtensions = data.video_extensions;
    })
    .catch(function (error) {
      console.error("Error loading video extensions:", error);
    });
}
document.addEventListener("DOMContentLoaded", loadVideoExtensions);

// ──────────────────────────────────────────────────────────────
// Modal helpers
// ──────────────────────────────────────────────────────────────
function openFileModal(index) {
  var modal = document.getElementById("modal-" + index);
  if (modal) {
    modal.style.display = "flex";
    modal.classList.add("show");
  }
}

// ──────────────────────────────────────────────────────────────
// VLC streaming
// ──────────────────────────────────────────────────────────────
/**
 * Launch VLC via server-side subprocess (vlc:// protocol is unreliable on Windows).
 */
function launchVLC(link) {
  if (!link) {
    alert("No video URL provided for VLC.");
    return;
  }

  fetch("/torrent/launch_vlc", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": document.querySelector('input[name="csrf_token"]')
        ? document.querySelector('input[name="csrf_token"]').value
        : ""
    },
    body: JSON.stringify({ video_url: link }),
  })
    .then(function (response) {
      if (!response.ok) {
        return response.json().then(function (data) {
          throw new Error(data.error || "Failed to launch VLC on the server.");
        });
      }
      console.log("VLC launched successfully on the server.");
    })
    .catch(function (error) {
      alert("Error launching VLC: " + error.message);
    });
}

/**
 * Unrestrict a link via the server, then open in VLC.
 */
function streamInVLC(originalLink) {
  fetch("/torrent/unrestrict_link", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ link: originalLink }),
  })
    .then(function (response) {
      if (!response.ok) {
        return response.json().then(function (data) {
          throw new Error(data.error || "Failed to fetch unrestricted link.");
        });
      }
      return response.json();
    })
    .then(function (data) {
      if (data.unrestricted_link) {
        launchVLC(data.unrestricted_link);
      } else {
        alert("Failed to get unrestricted link for streaming.");
      }
    })
    .catch(function (error) {
      alert("Error preparing to stream in VLC: " + error.message);
    });
}

// ──────────────────────────────────────────────────────────────
// HereSphere
// ──────────────────────────────────────────────────────────────
/**
 * Launch HereSphere via server-side subprocess (legacy functionality).
 * HereSphere does not automatically register the heresphere:// protocol on Windows.
 */
function launchHeresphere(videoUrl) {
  if (!videoUrl) {
    alert("No video URL provided for HereSphere.");
    return;
  }

  fetch("/heresphere/launch_heresphere", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      // Include CSRF token if it exists just in case (though heresphere_bp is exempted)
      "X-CSRFToken": document.querySelector('input[name="csrf_token"]')
        ? document.querySelector('input[name="csrf_token"]').value
        : ""
    },
    body: JSON.stringify({ video_url: videoUrl }),
  })
    .then(function (response) {
      if (!response.ok) {
        return response.json().then(function (data) {
          throw new Error(data.error || "Failed to launch HereSphere on the server.");
        });
      }
      console.log("HereSphere launched successfully on the server.");
    })
    .catch(function (error) {
      alert("Error launching HereSphere: " + error.message);
    });
}

// ──────────────────────────────────────────────────────────────
// Show files in RD Manager modal (XSS-safe DOM construction)
// ──────────────────────────────────────────────────────────────
function showFiles(torrentId) {
  var filesList = document.getElementById("files-list");
  filesList.innerHTML = "";
  var li = document.createElement("li");
  li.textContent = "Loading files...";
  filesList.appendChild(li);

  // Find the button that triggered this and set it to a loading state
  var btn = document.querySelector('button[data-action="show-files"][data-id="' + torrentId + '"]');
  var originalHTML = "";
  if (btn) {
    originalHTML = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading...';
    btn.disabled = true;
  }

  fetch("/torrent/torrents/" + encodeURIComponent(torrentId))
    .then(function (response) {
      if (!response.ok) throw new Error("Network response was not ok");
      return response.json();
    })
    .then(function (data) {
      filesList.innerHTML = "";

      if (!Array.isArray(data.files)) {
        filesList.innerHTML = "<li><strong>Error: No files data found.</strong></li>";
        return;
      }

      var validFiles = data.files.filter(function (f) { return f.size !== "0.00 GB"; });
      if (validFiles.length === 0) {
        filesList.innerHTML = "<li><strong>No valid files available for this torrent.</strong></li>";
        return;
      }

      validFiles.forEach(function (file) {
        var isVideo = window.videoExtensions.some(function (ext) {
          return file.name.toLowerCase().endsWith(ext);
        });

        var listItem = document.createElement("li");
        var fileInfo = document.createElement("div");
        fileInfo.className = "file-info";

        // File name + size (safe text)
        var fileName = document.createElement("div");
        fileName.className = "file-name";
        var strong = document.createElement("strong");
        strong.textContent = file.name;
        fileName.appendChild(strong);
        fileName.appendChild(document.createTextNode(" (" + file.size + ")"));
        fileInfo.appendChild(fileName);

        // Action buttons
        var actions = document.createElement("div");
        actions.className = "file-actions";

        // Download button
        var dlBtn = document.createElement("button");
        dlBtn.className = "button";
        dlBtn.setAttribute("data-action", "download");
        dlBtn.setAttribute("data-url", file.link);
        dlBtn.innerHTML = '<i class="fa-solid fa-download"></i> Download';
        actions.appendChild(dlBtn);

        if (isVideo) {
          // VLC button
          var vlcBtn = document.createElement("button");
          vlcBtn.className = "button";
          vlcBtn.setAttribute("data-action", "vlc");
          vlcBtn.setAttribute("data-url", file.link);
          vlcBtn.innerHTML = '<i class="fa-solid fa-play"></i> VLC';
          vlcBtn.style.marginLeft = "10px";
          actions.appendChild(vlcBtn);

          // HereSphere button
          var hsBtn = document.createElement("button");
          hsBtn.className = "button";
          hsBtn.setAttribute("data-action", "heresphere");
          hsBtn.setAttribute("data-url", file.link);
          hsBtn.innerHTML = '<i class="fa-solid fa-vr-cardboard"></i> HereSphere';
          hsBtn.style.marginLeft = "10px";
          actions.appendChild(hsBtn);
        }

        fileInfo.appendChild(actions);
        listItem.appendChild(fileInfo);
        filesList.appendChild(listItem);
      });

      var modalTitle = document.getElementById("modal-files-title");
      if (modalTitle) modalTitle.textContent = data.filename || "Unknown Torrent";

      var modal = document.getElementById("rdModal");
      if (modal) {
        modal.style.display = "flex";
        modal.classList.add("show");
      }
    })
    .catch(function (error) {
      filesList.innerHTML = "<li><strong>Error loading files. Please try again.</strong></li>";
      console.error("Error fetching torrent files:", error);
    })
    .finally(function () {
      // Restore the button state
      if (btn) {
        btn.innerHTML = originalHTML;
        btn.disabled = false;
      }
    });
}

// ──────────────────────────────────────────────────────────────
// Torrent deletion
// ──────────────────────────────────────────────────────────────
function deleteTorrent(torrentId) {
  if (!torrentId || typeof torrentId !== "string") {
    alert("Invalid torrent ID provided.");
    return;
  }

  // Find the button and set loading state
  var btn = document.querySelector('button[data-action="confirm-delete"][data-id="' + torrentId + '"]');
  var originalHTML = "";
  if (btn) {
    originalHTML = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Deleting...';
    btn.disabled = true;
  }

  fetch("/torrent/delete_torrent/" + encodeURIComponent(torrentId), {
    method: "DELETE",
  })
    .then(function (response) {
      if (!response.ok) throw new Error("Error: " + response.status);
      return response.json();
    })
    .then(function (data) {
      if (data.status === "success") {
        alert("Torrent deleted successfully!");
        location.reload();
      } else {
        alert("Failed to delete the torrent: " + data.message);
      }
    })
    .catch(function (error) {
      alert("Error deleting torrent: " + error.message);
    })
    .finally(function () {
      if (btn) {
        btn.innerHTML = originalHTML;
        btn.disabled = false;
      }
    });
}

function confirmDeletion(torrentId) {
  if (confirm("Are you sure you want to delete this torrent? This action cannot be undone.")) {
    deleteTorrent(torrentId);
  }
}

function deleteSelectedTorrents() {
  var selectedCheckboxes = document.querySelectorAll(".torrent-checkbox:checked");

  if (selectedCheckboxes.length === 0) {
    alert("Please select at least one torrent to delete.");
    return;
  }

  if (!confirm("Are you sure you want to delete the selected " + selectedCheckboxes.length + " torrent(s)?")) {
    return;
  }

  var btn = document.querySelector('button[data-action="delete-selected"]');
  var originalHTML = "";
  if (btn) {
    originalHTML = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Deleting...';
    btn.disabled = true;
  }

  var torrentIds = Array.from(selectedCheckboxes).map(function (cb) { return cb.value; });

  fetch("/torrent/delete_torrents", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ torrentIds: torrentIds }),
  })
    .then(function (response) {
      if (!response.ok) throw new Error("Failed to delete selected torrents");
      return response.json();
    })
    .then(function (data) {
      if (data.status === "success") {
        alert("Selected torrents have been deleted successfully.");
      } else if (data.status === "partial_success") {
        alert("Some torrents could not be deleted.");
      }
      location.reload();
    })
    .catch(function (error) {
      console.error("Error deleting selected torrents:", error);
    })
    .finally(function () {
      if (btn) {
        btn.innerHTML = originalHTML;
        btn.disabled = false;
      }
    });
}

// ──────────────────────────────────────────────────────────────
// Unrestrict link (fixed URL: /torrent/unrestrict_link)
// ──────────────────────────────────────────────────────────────
function getUnrestrictedLink(originalLink) {
  fetch("/torrent/unrestrict_link", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ link: originalLink }),
  })
    .then(function (response) {
      if (!response.ok) {
        return response.json().then(function (data) {
          throw new Error(data.error || "Failed to generate unrestricted link.");
        });
      }
      return response.json();
    })
    .then(function (data) {
      if (data.unrestricted_link) {
        window.location.href = data.unrestricted_link;
      } else {
        alert("Failed to generate unrestricted link.");
      }
    })
    .catch(function (error) {
      alert("Error generating unrestricted link: " + error.message);
    });
}

// ──────────────────────────────────────────────────────────────
// Utilities
// ──────────────────────────────────────────────────────────────
function isValidUrl(string) {
  try {
    new URL(string);
    return true;
  } catch (_) {
    return false;
  }
}

function toggleSelectAll(selectAllCheckbox) {
  var checkboxes = document.querySelectorAll(".torrent-checkbox");
  checkboxes.forEach(function (cb) {
    cb.checked = selectAllCheckbox.checked;
  });
}

// ──────────────────────────────────────────────────────────────
// Streaming Search Actions
// ──────────────────────────────────────────────────────────────

var currentSearchId = null;

function startStreamingSearch() {
  var queryInput = document.getElementById("query");
  var limitInput = document.getElementById("limit");
  var query = queryInput ? queryInput.value.trim() : "";
  var limit = limitInput ? limitInput.value.trim() : "10";

  if (!query) {
    alert("Please enter a search query.");
    return;
  }

  // UI Reset
  document.getElementById("search-error").style.display = "none";
  document.getElementById("submit-button").style.display = "none";
  document.getElementById("cancel-button").style.display = "inline-block";
  document.getElementById("search-progress").style.display = "block";
  document.getElementById("progress-bar").style.width = "0%";
  document.getElementById("progress-status").innerText = "Starting search...";
  document.getElementById("progress-detail").innerText = "";
  document.getElementById("progress-spinner").style.display = "inline-block";

  // Results UI
  var resultsContainer = document.getElementById("stream-results");
  var resultsBody = document.getElementById("stream-results-body");
  var timerContainer = document.getElementById("stream-timer");
  if (resultsContainer && resultsBody) {
    resultsContainer.style.display = "block";
    resultsBody.innerHTML = "";
    document.getElementById("stream-total").innerText = "0";
    document.getElementById("stream-elapsed").innerText = "0";
    timerContainer.style.display = "none";
  }

  // We use fetch to initiate the POST because standard EventSource only supports GET.
  // To stick to vanilla JS without external polyfills, we can consume the response body as a stream.
  fetch("/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: query, limit: parseInt(limit, 10) })
  })
    .then(function (response) {
      if (!response.ok) throw new Error("Network response was not ok");
      var reader = response.body.getReader();
      var decoder = new TextDecoder("utf-8");
      var buffer = "";

      function processStream() {
        return reader.read().then(function (result) {
          if (result.done) {
            finishStreamingSearch();
            return;
          }
          buffer += decoder.decode(result.value, { stream: true });
          // The SSE format uses \n\n to separate events
          var events = buffer.split("\n\n");
          // Keep the last chunk in the buffer if it doesn't end with \n\n
          buffer = events.pop();

          for (var i = 0; i < events.length; i++) {
            var ev = events[i].trim();
            if (ev.indexOf("data: ") === 0) {
              var dataStr = ev.substring(6);
              try {
                var data = JSON.parse(dataStr);
                handleSearchEvent(data);
              } catch (e) {
                console.error("Failed to parse SSE JSON:", dataStr);
              }
            }
          }
          return processStream();
        });
      }
      return processStream();
    })
    .catch(function (err) {
      console.error("Streaming error:", err);
      document.getElementById("search-error").style.display = "block";
      document.getElementById("search-error-text").innerText = "Search stream failed: " + err.message;
      finishStreamingSearch();
    });
}

function handleSearchEvent(data) {
  if (data.type === "search_id") {
    currentSearchId = data.id;
  }
  else if (data.type === "progress") {
    document.getElementById("progress-status").innerText = data.stage || "Processing...";
    document.getElementById("progress-detail").innerText = data.detail || "";
    if (data.total > 0 && data.current !== undefined) {
      var pct = Math.floor((data.current / data.total) * 100);
      document.getElementById("progress-bar").style.width = pct + "%";
    }
  }
  else if (data.type === "result") {
    appendStreamResult(data.torrent);
  }
  else if (data.type === "done") {
    document.getElementById("progress-status").innerText = "Complete!";
    document.getElementById("progress-detail").innerText = "Found " + data.total + " torrents.";
    document.getElementById("progress-bar").style.width = "100%";

    document.getElementById("stream-timer").style.display = "flex";
    document.getElementById("stream-elapsed").innerText = data.elapsed;
    finishStreamingSearch();
  }
  else if (data.type === "cancelled") {
    document.getElementById("progress-status").innerText = "Cancelled";
    document.getElementById("progress-detail").innerText = "Search was stopped.";
    finishStreamingSearch();
  }
  else if (data.type === "error") {
    document.getElementById("search-error").style.display = "block";
    document.getElementById("search-error-text").innerText = data.message;
    finishStreamingSearch();
  }
}

function appendStreamResult(torrent) {
  var tbody = document.getElementById("stream-results-body");
  if (!tbody) return;

  var tr = document.createElement("tr");

  // Format file name
  var formattedName = torrent["Torrent Name"].replace(/[._]/g, " ");

  // Column 1: Name
  var tdName = document.createElement("td");
  tdName.innerText = formattedName;
  tr.appendChild(tdName);

  // Column 2: Categories
  var tdCats = document.createElement("td");
  (torrent["Categories"] || []).forEach(function (cat) {
    var span = document.createElement("span");
    span.className = "category-tag";
    span.innerText = cat;
    tdCats.appendChild(span);
  });
  tr.appendChild(tdCats);

  // Column 3: Files (simplified for the stream - we list them directly)
  var tdFiles = document.createElement("td");
  var filesDiv = document.createElement("div");
  filesDiv.className = "scrollable-content";
  filesDiv.style.maxHeight = "250px";
  filesDiv.style.minWidth = "300px";

  (torrent["Files"] || []).forEach(function (f) {
    var fCont = document.createElement("div");
    fCont.style.marginBottom = "15px";
    fCont.style.borderBottom = "1px solid #444";
    fCont.style.paddingBottom = "10px";

    var fInfo = document.createElement("div");
    fInfo.innerHTML = "<strong>File:</strong> " + f["File Name"].replace(/[._]/g, " ") +
      "<br><strong>Size:</strong> " + f["File Size"];
    fCont.appendChild(fInfo);

    var acts = document.createElement("div");
    acts.className = "file-actions";
    acts.style.marginTop = "8px";

    var dl = document.createElement("button");
    dl.className = "button";
    dl.setAttribute("data-action", "download");
    dl.setAttribute("data-url", f["Download Link"]);
    dl.innerHTML = '<i class="fa-solid fa-download"></i> Download';
    acts.appendChild(dl);

    var vlc = document.createElement("button");
    vlc.className = "button";
    vlc.setAttribute("data-action", "vlc");
    vlc.setAttribute("data-url", f["Download Link"]);
    vlc.style.marginLeft = "10px";
    vlc.innerHTML = '<i class="fa-solid fa-play"></i> VLC';
    acts.appendChild(vlc);

    var hs = document.createElement("button");
    hs.className = "button";
    hs.setAttribute("data-action", "heresphere");
    hs.setAttribute("data-url", f["Download Link"]);
    hs.style.marginLeft = "10px";
    hs.innerHTML = '<i class="fa-solid fa-vr-cardboard"></i> HereSphere';
    acts.appendChild(hs);

    fCont.appendChild(acts);
    filesDiv.appendChild(fCont);
  });

  tdFiles.appendChild(filesDiv);
  tr.appendChild(tdFiles);
  tbody.appendChild(tr);

  // Update total count
  var countEl = document.getElementById("stream-total");
  if (countEl) {
    countEl.innerText = tbody.querySelectorAll("tr").length;
  }
}

function cancelStreamingSearch() {
  if (currentSearchId) {
    fetch("/cancel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ search_id: currentSearchId })
    }).catch(function (e) { console.error("Cancel failed:", e); });
  }
  document.getElementById("progress-status").innerText = "Cancelling...";
  document.getElementById("cancel-button").disabled = true;
}

function finishStreamingSearch() {
  document.getElementById("submit-button").style.display = "inline-block";
  document.getElementById("cancel-button").style.display = "none";
  document.getElementById("cancel-button").disabled = false;
  document.getElementById("progress-spinner").style.display = "none";
  currentSearchId = null;
}
