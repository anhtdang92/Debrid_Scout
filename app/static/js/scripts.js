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

  // ── Close modals on Escape key ──────────────────────────────
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      var rdModal = document.getElementById("rdModal");
      if (rdModal && rdModal.classList.contains("show")) {
        window.closeModal();
      }
    }
  });

  // ── Close modals on outside click ───────────────────────────
  window.addEventListener("click", function (event) {
    const rdModal = document.getElementById("rdModal");
    if (rdModal && rdModal.classList.contains("show") && event.target === rdModal) {
      window.closeModal();
    }
    document.querySelectorAll(".rd-modal").forEach(function (modal) {
      if (modal.classList.contains("show") && event.target === modal) {
        window.closeIndexModal(modal.id);
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
    var rawUrl = btn.getAttribute("data-url");
    var url = (rawUrl && rawUrl !== "null") ? rawUrl : "";
    var id = btn.getAttribute("data-id") || "";

    switch (action) {
      case "download":
        if (url) {
          btn.disabled = true;
          var origHTML = btn.innerHTML;
          btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading...';
          fetch("/torrent/unrestrict_link", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ link: url })
          })
            .then(function (r) {
              if (!r.ok) {
                return r.json().then(function (d) {
                  throw new Error(d.error || "Failed to unrestrict link");
                });
              }
              return r.json();
            })
            .then(function (data) {
              var dlUrl = data.unrestricted_link;
              if (dlUrl && isValidUrl(dlUrl)) {
                window.open(dlUrl, "_blank");
              } else {
                alert("Could not generate a download link. The link may have expired.");
              }
            })
            .catch(function (err) {
              alert("Download error: " + err.message);
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
            .then(function (r) {
              if (!r.ok) {
                return r.json().then(function (d) {
                  throw new Error(d.error || "Failed to unrestrict link");
                });
              }
              return r.json();
            })
            .then(function (data) {
              if (data.unrestricted_link && isValidUrl(data.unrestricted_link)) {
                launchVLC(data.unrestricted_link);
              } else {
                alert("Could not generate a VLC link. The link may have expired.");
              }
            })
            .catch(function (err) { alert("VLC error: " + err.message); })
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
            .then(function (r) {
              if (!r.ok) {
                return r.json().then(function (d) {
                  throw new Error(d.error || "Failed to unrestrict link");
                });
              }
              return r.json();
            })
            .then(function (data) {
              if (data.unrestricted_link && isValidUrl(data.unrestricted_link)) {
                launchHeresphere(data.unrestricted_link);
              } else {
                alert("Could not generate a HereSphere link. The link may have expired.");
              }
            })
            .catch(function (err) { alert("HereSphere error: " + err.message); })
            .finally(function () { btn.innerHTML = hsOrigHTML; btn.disabled = false; });
        }
        break;

      case "copy-hs-url":
        hsPageCopyUrl();
        break;

      case "hs-launch":
        hsPageLaunch(id, "heresphere", btn);
        break;

      case "hs-vlc":
        hsPageLaunch(id, "vlc", btn);
        break;

      case "open-file-modal":
        openFileModal(id);
        break;

      case "close-modal":
        window.closeIndexModal(id);
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
// VLC streaming (client-side via vlc:// protocol + .m3u fallback)
// ──────────────────────────────────────────────────────────────
/**
 * Open a video URL in VLC from the browser.
 *
 * Strategy:
 *  1. Try the vlc:// custom protocol (works when VLC is installed and
 *     registered as a protocol handler — common on Windows/macOS).
 *  2. If the protocol doesn't trigger within a short timeout, fall back
 *     to downloading a .m3u playlist file that the user can open in VLC.
 */
function launchVLC(link) {
  if (!link) {
    alert("No video URL provided for VLC.");
    return;
  }

  // Build the vlc:// URI by replacing the scheme (https:// → vlc://)
  var vlcUri = "vlc://" + link.replace(/^https?:\/\//, "");

  // Try the protocol handler. If VLC is registered, the browser will
  // prompt or open VLC directly. If not, nothing visible happens.
  var protocolFrame = document.createElement("iframe");
  protocolFrame.style.display = "none";
  protocolFrame.src = vlcUri;
  document.body.appendChild(protocolFrame);

  // After a short delay, clean up the iframe and offer the .m3u fallback
  // so the user always has a way to open the file even if vlc:// failed.
  setTimeout(function () {
    document.body.removeChild(protocolFrame);
    downloadM3U(link);
  }, 1500);
}

/**
 * Generate and trigger download of a .m3u playlist file containing the
 * video URL. When opened, the OS will launch the default media player
 * (typically VLC) with the stream.
 */
function downloadM3U(link) {
  var content = "#EXTM3U\n" + link + "\n";
  var blob = new Blob([content], { type: "audio/x-mpegurl" });
  var url = URL.createObjectURL(blob);

  var a = document.createElement("a");
  a.href = url;
  a.download = "stream.m3u";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
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
      if (!response.ok) {
        return response.json().then(function (errData) {
          throw new Error(errData.error || "Server returned " + response.status);
        });
      }
      return response.json();
    })
    .then(function (data) {
      filesList.innerHTML = "";

      if (!Array.isArray(data.files)) {
        filesList.innerHTML = "<li><strong>Error: No files data found.</strong></li>";
        return;
      }

      // Show status banner when torrent isn't fully downloaded
      var status = (data.status || "").toLowerCase();
      var errorStatuses = ["error", "magnet_error", "virus", "dead"];
      if (status && status !== "downloaded") {
        var statusLi = document.createElement("li");
        var statusText = "Status: " + data.status;
        if (data.progress !== undefined && data.progress < 100) {
          statusText += " (" + data.progress + "%)";
        }
        if (errorStatuses.indexOf(status) !== -1) {
          statusLi.style.cssText = "color:#e74c3c;margin-bottom:12px;font-weight:bold;";
          statusLi.textContent = statusText + " — this torrent has failed. Delete it and try again.";
        } else {
          statusLi.style.cssText = "color:#f39c12;margin-bottom:12px;font-weight:bold;";
          statusLi.textContent = statusText + " — links may not be available yet.";
        }
        filesList.appendChild(statusLi);
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

        if (file.link) {
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
        } else {
          var noLink = document.createElement("span");
          noLink.style.color = "#999";
          noLink.textContent = "No link available";
          actions.appendChild(noLink);
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
var collectedResults = [];
var _pendingStreamResults = [];
var _rafScheduled = false;

function startStreamingSearch() {
  // Clear previous saved results
  sessionStorage.removeItem("ds_search_results");
  collectedResults = [];
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
    collectedResults.push(data.torrent);
    _pendingStreamResults.push(data.torrent);
    if (!_rafScheduled) {
      _rafScheduled = true;
      requestAnimationFrame(flushPendingResults);
    }
  }
  else if (data.type === "done") {
    // Flush any remaining batched results before finalizing
    flushPendingResults();
    document.getElementById("progress-status").innerText = "Complete!";
    if (data.total === 0) {
      document.getElementById("progress-detail").innerText =
        "No torrents found. Try different keywords or check your indexer availability.";
    } else {
      document.getElementById("progress-detail").innerText = "Found " + data.total + " torrents.";
    }
    document.getElementById("progress-bar").style.width = "100%";

    document.getElementById("stream-timer").style.display = "flex";
    document.getElementById("stream-elapsed").innerText = data.elapsed;

    // Persist results so they survive page navigation
    var queryInput = document.getElementById("query");
    var limitInput = document.getElementById("limit");
    try {
      sessionStorage.setItem("ds_search_results", JSON.stringify({
        results: collectedResults,
        query: queryInput ? queryInput.value.trim() : "",
        limit: limitInput ? limitInput.value.trim() : "10",
        total: data.total,
        elapsed: data.elapsed
      }));
    } catch (e) {
      console.warn("Could not save search results to sessionStorage:", e);
    }

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

function flushPendingResults() {
  _rafScheduled = false;
  var batch = _pendingStreamResults.splice(0);
  if (!batch.length) return;
  var tbody = document.getElementById("stream-results-body");
  if (!tbody) return;
  var frag = document.createDocumentFragment();
  for (var i = 0; i < batch.length; i++) {
    frag.appendChild(buildStreamResultRow(batch[i]));
  }
  tbody.appendChild(frag);
  var countEl = document.getElementById("stream-total");
  if (countEl) {
    countEl.innerText = tbody.querySelectorAll("tr").length;
  }
}

function buildStreamResultRow(torrent) {
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
    var fileLabel = document.createElement("strong");
    fileLabel.textContent = "File: ";
    fInfo.appendChild(fileLabel);
    fInfo.appendChild(document.createTextNode(f["File Name"].replace(/[._]/g, " ")));
    fInfo.appendChild(document.createElement("br"));
    var sizeLabel = document.createElement("strong");
    sizeLabel.textContent = "Size: ";
    fInfo.appendChild(sizeLabel);
    fInfo.appendChild(document.createTextNode(f["File Size"]));
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
  return tr;
}

function appendStreamResult(torrent) {
  var tbody = document.getElementById("stream-results-body");
  if (!tbody) return;
  tbody.appendChild(buildStreamResultRow(torrent));
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

// ──────────────────────────────────────────────────────────────
// HereSphere Library Page helpers
// ──────────────────────────────────────────────────────────────

function hsPageCopyUrl() {
  var urlEl = document.getElementById("hs-url");
  if (!urlEl) return;
  var text = urlEl.textContent;
  navigator.clipboard.writeText(text).then(function () {
    var copyBtn = document.querySelector('[data-action="copy-hs-url"]');
    if (copyBtn) {
      var orig = copyBtn.innerHTML;
      copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
      setTimeout(function () { copyBtn.innerHTML = orig; }, 1500);
    }
  }).catch(function () {
    window.prompt("Copy this URL:", text);
  });
}

/**
 * Fetch the first video link from a torrent and launch it via HereSphere or VLC.
 * @param {string} torrentId  RD torrent ID
 * @param {string} target     "heresphere" or "vlc"
 * @param {HTMLElement} btn   the button element (for loading state)
 */
function hsPageLaunch(torrentId, target, btn) {
  if (!torrentId) return;
  var origHTML = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';

  fetch("/torrent/torrents/" + encodeURIComponent(torrentId))
    .then(function (r) {
      if (!r.ok) throw new Error("Failed to fetch torrent details");
      return r.json();
    })
    .then(function (data) {
      var files = (data.files || []).filter(function (f) { return f.link; });
      files.sort(function (a, b) {
        var sa = parseFloat(a.size) || 0;
        var sb = parseFloat(b.size) || 0;
        return sb - sa;
      });
      var videoFile = files.find(function (f) {
        return window.videoExtensions && window.videoExtensions.some(function (ext) {
          return f.name.toLowerCase().endsWith(ext);
        });
      });
      var link = videoFile ? videoFile.link : (files.length ? files[0].link : null);
      if (!link) throw new Error("No playable link found in this torrent");

      return fetch("/torrent/unrestrict_link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ link: link })
      });
    })
    .then(function (r) {
      if (!r.ok) {
        return r.json().then(function (d) {
          throw new Error(d.error || "Failed to unrestrict link");
        });
      }
      return r.json();
    })
    .then(function (data) {
      var url = data.unrestricted_link;
      if (!url || !isValidUrl(url)) {
        throw new Error("Could not generate a playable link");
      }
      if (target === "heresphere") {
        // Use the heresphere:// protocol to send the video to the
        // already-running HereSphere instance instead of spawning a new one.
        window.location.href = "heresphere://" + url;
      } else {
        launchVLC(url);
      }
    })
    .catch(function (err) {
      alert("Launch error: " + err.message);
    })
    .finally(function () {
      btn.innerHTML = origHTML;
      btn.disabled = false;
    });
}

// ──────────────────────────────────────────────────────────────
// Restore previous search results on page load
// ──────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", function () {
  var resultsBody = document.getElementById("stream-results-body");
  if (!resultsBody) return; // not on search page

  var saved;
  try {
    saved = JSON.parse(sessionStorage.getItem("ds_search_results"));
  } catch (e) {
    return;
  }
  if (!saved || !saved.results || !saved.results.length) return;

  // Restore query and limit inputs
  var queryInput = document.getElementById("query");
  var limitInput = document.getElementById("limit");
  if (queryInput && saved.query) queryInput.value = saved.query;
  if (limitInput && saved.limit) limitInput.value = saved.limit;

  // Re-render each result
  saved.results.forEach(function (torrent) {
    appendStreamResult(torrent);
  });

  // Show the results table and timer
  var resultsContainer = document.getElementById("stream-results");
  if (resultsContainer) resultsContainer.style.display = "block";

  var timerContainer = document.getElementById("stream-timer");
  if (timerContainer && saved.elapsed) {
    timerContainer.style.display = "flex";
    document.getElementById("stream-total").innerText = saved.total || saved.results.length;
    document.getElementById("stream-elapsed").innerText = saved.elapsed;
  }
});

// Client-side search filter + sort for HereSphere library cards
document.addEventListener("DOMContentLoaded", function () {
  var searchInput = document.getElementById("hs-search");
  var sortSelect = document.getElementById("hs-sort");
  var grid = document.getElementById("hs-grid");
  if (!grid) return;

  var HS_SORT_KEY = "hs-sort-preference";

  // Restore saved sort preference
  if (sortSelect) {
    var saved = localStorage.getItem(HS_SORT_KEY);
    if (saved) sortSelect.value = saved;
  }

  // ── Pagination state ──────────────────────────────────────
  var HS_PAGE_SIZE = 24;
  var currentPage = 1;
  var countEl = document.getElementById("hs-count");
  var noMatch = document.getElementById("hs-no-match");
  var paginationEl = document.getElementById("hs-pagination");

  function getFilteredCards() {
    var term = searchInput ? searchInput.value.toLowerCase().trim() : "";
    var all = Array.prototype.slice.call(grid.querySelectorAll(".hs-card"));
    if (!term) return all;
    return all.filter(function (card) {
      var title = (card.querySelector(".hs-card-title") || {}).textContent || "";
      return title.toLowerCase().indexOf(term) !== -1;
    });
  }

  function applyPagination() {
    var filtered = getFilteredCards();
    var totalPages = Math.max(1, Math.ceil(filtered.length / HS_PAGE_SIZE));
    if (currentPage > totalPages) currentPage = totalPages;
    var start = (currentPage - 1) * HS_PAGE_SIZE;
    var end = start + HS_PAGE_SIZE;

    // Build a set of IDs for the current page
    var pageSet = {};
    for (var i = start; i < end && i < filtered.length; i++) {
      pageSet[filtered[i].getAttribute("data-id")] = true;
    }

    // Show only cards on the current page
    grid.querySelectorAll(".hs-card").forEach(function (card) {
      card.style.display = pageSet[card.getAttribute("data-id")] ? "" : "none";
    });

    if (countEl) {
      countEl.textContent = filtered.length + " video" + (filtered.length !== 1 ? "s" : "");
    }
    if (noMatch) {
      var term = searchInput ? searchInput.value.trim() : "";
      noMatch.style.display = (filtered.length === 0 && term) ? "block" : "none";
    }

    renderPagination(totalPages);
  }

  function renderPagination(totalPages) {
    if (!paginationEl) return;
    paginationEl.innerHTML = "";
    if (totalPages <= 1) return;

    function btn(label, page, active, disabled) {
      var b = document.createElement("button");
      b.className = "hs-page-btn" + (active ? " active" : "");
      b.textContent = label;
      b.disabled = disabled;
      if (!disabled && !active) {
        b.addEventListener("click", function () {
          currentPage = page;
          applyPagination();
          grid.scrollIntoView({ behavior: "smooth", block: "start" });
        });
      }
      return b;
    }

    var frag = document.createDocumentFragment();
    frag.appendChild(btn("\u00AB", 1, false, currentPage === 1));
    frag.appendChild(btn("\u2039", currentPage - 1, false, currentPage === 1));

    var lo = Math.max(1, currentPage - 3);
    var hi = Math.min(totalPages, lo + 6);
    lo = Math.max(1, hi - 6);
    for (var p = lo; p <= hi; p++) {
      frag.appendChild(btn(String(p), p, p === currentPage, false));
    }

    frag.appendChild(btn("\u203A", currentPage + 1, false, currentPage === totalPages));
    frag.appendChild(btn("\u00BB", totalPages, false, currentPage === totalPages));
    paginationEl.appendChild(frag);
  }

  function applyFilter() {
    currentPage = 1;
    applyPagination();
  }

  function applySort() {
    var value = sortSelect ? sortSelect.value : "date-desc";
    var parts = value.split("-");
    var field = parts[0]; // "date", "name", or "size"
    var dir = parts[1];   // "asc" or "desc"

    var cards = Array.prototype.slice.call(grid.querySelectorAll(".hs-card"));
    cards.sort(function (a, b) {
      var aVal, bVal;
      if (field === "name") {
        aVal = a.getAttribute("data-name") || "";
        bVal = b.getAttribute("data-name") || "";
        return dir === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      } else if (field === "size") {
        aVal = parseFloat(a.getAttribute("data-size")) || 0;
        bVal = parseFloat(b.getAttribute("data-size")) || 0;
        return dir === "asc" ? aVal - bVal : bVal - aVal;
      } else {
        aVal = a.getAttribute("data-date") || "";
        bVal = b.getAttribute("data-date") || "";
        return dir === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
    });

    var sortFrag = document.createDocumentFragment();
    cards.forEach(function (card) { sortFrag.appendChild(card); });
    grid.appendChild(sortFrag);
    if (sortSelect) localStorage.setItem(HS_SORT_KEY, value);
    applyPagination();
  }

  // Bind events
  if (searchInput) searchInput.addEventListener("input", applyFilter);
  if (sortSelect) sortSelect.addEventListener("change", applySort);

  // Apply initial sort (triggers pagination)
  applySort();

  // ── Hover-to-preview: shared <video> element ──────────────
  var previewVideo = document.createElement("video");
  previewVideo.className = "hs-preview-video";
  previewVideo.muted = true;
  previewVideo.loop = true;
  previewVideo.playsInline = true;
  previewVideo.preload = "none";

  var hoverTimer = null;
  var activeWrap = null;

  grid.addEventListener("mouseenter", function (e) {
    var wrap = e.target.closest(".hs-thumb-wrap");
    if (!wrap) return;
    var src = wrap.getAttribute("data-preview");
    if (!src) return;

    // Delay slightly so quick mouse-overs don't trigger loads
    clearTimeout(hoverTimer);
    hoverTimer = setTimeout(function () {
      activeWrap = wrap;
      previewVideo.src = src;
      wrap.appendChild(previewVideo);
      previewVideo.play().catch(function () {});
    }, 400);
  }, true);

  grid.addEventListener("mouseleave", function (e) {
    var wrap = e.target.closest(".hs-thumb-wrap");
    if (!wrap) return;
    clearTimeout(hoverTimer);
    if (activeWrap === wrap) {
      previewVideo.pause();
      previewVideo.removeAttribute("src");
      previewVideo.load(); // reset
      if (previewVideo.parentElement) previewVideo.parentElement.removeChild(previewVideo);
      activeWrap = null;
    }
  }, true);
});
