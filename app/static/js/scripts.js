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
        if (url && isValidUrl(url)) window.open(url, "_blank");
        break;

      case "vlc":
        launchVLC(url);
        break;

      case "heresphere":
        launchHeresphere(url);
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
 * Launch VLC via vlc:// protocol URI (client-side, no server subprocess).
 */
function launchVLC(link) {
  if (!link || !isValidUrl(link)) {
    alert("Invalid link provided for VLC.");
    return;
  }
  // Open the link using VLC's registered protocol handler
  window.location.href = "vlc://" + encodeURI(link);
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
