// app/static/js/scripts.js

// Ensure all modals are hidden on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded and parsed.");

    /**
     * Close the RD Modal specifically.
     */
    window.closeModal = function() {
        console.log("closeModal function called");
        const modal = document.getElementById('rdModal');
        if (modal) {
            modal.style.display = "none";
            modal.classList.remove('show');
            console.log("Modal closed");
        } else {
            console.error("Modal element not found in the DOM when attempting to close.");
        }
    };

    /**
     * Close any modal by its ID.
     * @param {string} modalId - The ID of the modal to close.
     */
    window.closeIndexModal = function(modalId) {
        console.log(`closeIndexModal function called for modal ID: ${modalId}`);
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = "none";
            modal.classList.remove('show');
            console.log(`Modal with ID ${modalId} closed.`);
        } else {
            console.error(`Modal element with ID ${modalId} not found in the DOM when attempting to close.`);
        }
    };

    // Hide all RD modals on load
    const rdModals = document.querySelectorAll(".rd-modal");
    rdModals.forEach((modal, index) => {
        modal.style.display = "none";
        console.log(`RD modal ${index + 1} is hidden on load.`);
    });

    // Loading overlay for form submission
    const searchForm = document.getElementById("search-form");
    const loadingOverlay = document.getElementById("loading");

    if (searchForm) {
        searchForm.addEventListener("submit", function(event) {
            event.preventDefault(); // Prevent default submission for custom handling
            loadingOverlay.style.display = 'flex'; // Show loading overlay

            const formData = new FormData(searchForm);
            const query = formData.get("query");
            const limit = formData.get("limit");

            fetch("/", {
                method: "POST",
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({ query, limit })
            })
            .then(response => {
                if (!response.ok) {
                    return response.text().then(text => {
                        throw new Error(text || 'Network response was not ok');
                    });
                }
                return response.text(); // Expecting HTML response for document.write
            })
            .then(data => {
                document.open();
                document.write(data);
                document.close();
            })
            .catch(error => {
                console.error("Error:", error);
                alert("An error occurred: " + error.message);
            })
            .finally(() => {
                loadingOverlay.style.display = 'none'; // Hide loading overlay
            });
        });
    }

    // Enable form submission with Enter key, if search form exists
    const submitButton = document.getElementById("submit-button");
    if (searchForm && submitButton) {
        searchForm.addEventListener("keydown", function(event) {
            if (event.key === "Enter") {
                event.preventDefault();
                submitButton.click();
            }
        });
    }

    // Set up close button event listeners for RD Modal
    const closeButton = document.querySelector('.rd-close');
    if (closeButton) {
        closeButton.addEventListener('click', closeModal);
    }

    // Set up close button event listeners for Index Modals
    const indexCloseButtons = document.querySelectorAll('.rd-close[data-modal-id]');
    indexCloseButtons.forEach(button => {
        const modalId = button.getAttribute('data-modal-id');
        if (modalId) {
            button.addEventListener('click', function() {
                closeIndexModal(modalId);
            });
        }
    });

    // Close modals when clicking outside of them
    window.addEventListener('click', function(event) {
        // Close RD Modal
        const rdModal = document.getElementById('rdModal');
        if (rdModal && rdModal.classList.contains('show') && event.target === rdModal) {
            closeModal();
            console.log("Clicked outside rdModal. Modal should close.");
        }

        // Close Index Modals
        rdModals.forEach(modal => {
            if (modal.classList.contains('show') && event.target === modal) {
                const modalId = modal.id;
                closeIndexModal(modalId);
                console.log(`Clicked outside ${modalId}. Modal should close.`);
            }
        });
    });
});

window.videoExtensions = [];

/**
 * Function to load video extensions from a JSON file.
 */
function loadVideoExtensions() {
    fetch('/static/video_extensions.json')
    .then(response => {
        if (!response.ok) throw new Error("Failed to load video extensions");
        return response.json();
    })
    .then(data => {
        window.videoExtensions = data.video_extensions;
        console.log("Video extensions loaded:", window.videoExtensions);
    })
    .catch(error => console.error("Error loading video extensions:", error));
}

// Call this function when the page loads
document.addEventListener("DOMContentLoaded", loadVideoExtensions);

/**
 * Function to open a specific RD file modal.
 * @param {number} index - The index of the modal to open.
 */
function openFileModal(index) {
    console.log(`openFileModal called for index: ${index}`);
    const modal = document.getElementById("modal-" + index);
    if (modal) {
        modal.style.display = "flex";
        modal.classList.add('show');
        console.log(`RD modal modal-${index} is now displayed.`);
    } else {
        console.error(`RD modal with id modal-${index} not found.`);
    }
}

/**
 * Function to launch VLC without confirmation modal.
 * @param {string} link - The download link to stream in VLC.
 */
function launchVLC(link) {
    if (!link || !isValidUrl(link)) {
        alert('Invalid link provided for VLC.');
        return;
    }

    console.log(`launchVLC called with link: ${link}`);
    fetch('/torrent/stream_vlc', {  // Updated endpoint with /torrent prefix
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ link: link }),
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.message || 'Failed to launch VLC.');
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.status !== 'success') {
            alert('Failed to launch VLC. Please try again later.');
            console.error('Error launching VLC:', data.message);
        }
    })
    .catch(error => {
        console.error("Error launching VLC: ", error);
        alert('An unexpected error occurred while launching VLC: ' + error.message);
    });
}

/**
 * Function to stream in VLC with an unrestricted link.
 * @param {string} originalLink - The original download link to unrestrict.
 */
function streamInVLC(originalLink) {
    fetch('/torrent/unrestrict_link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ link: originalLink }),
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Failed to fetch unrestricted link.');
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.unrestricted_link) {
            launchVLC(data.unrestricted_link);
        } else {
            alert('Failed to get unrestricted link for streaming.');
        }
    })
    .catch(error => {
        console.error('Error fetching unrestricted link:', error);
        alert('An error occurred while preparing to stream in VLC: ' + error.message);
    });
}

/**
 * Function to handle errors gracefully.
 * @param {string} message - The error message to display.
 */
function handleError(message) {
    alert(message);
    console.error(message);
}

/**
 * Function to show files from a specific torrent.
 * @param {string} torrentId - The ID of the torrent.
 */
function showFiles(torrentId) {
    const filesList = document.getElementById('files-list');
    filesList.innerHTML = '<li>Loading files...</li>'; // Show loading message
    console.log("Fetching files for torrent ID:", torrentId);

    fetch(`/torrent/torrents/${encodeURIComponent(torrentId)}`) // Updated endpoint
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log("Data received from server for torrent ID:", torrentId, data);
            filesList.innerHTML = '';

            if (Array.isArray(data.files)) {
                const validFiles = data.files.filter(file => file.size !== "0.00 GB");
                if (validFiles.length > 0) {
                    validFiles.forEach(file => {
                        const isVideo = window.videoExtensions.some(ext => file.name.toLowerCase().endsWith(ext));
                        const listItem = document.createElement('li');
                        listItem.innerHTML = `
                            <strong>${file.name}</strong> (${file.size}):
                            <button class="button" onclick="getUnrestrictedLink('${file.link}')">Download</button>
                            ${isVideo ? `<button class="button" onclick="streamInVLC('${file.link}')">Stream in VLC</button>` : ''}
                        `;
                        filesList.appendChild(listItem);
                    });
                } else {
                    filesList.innerHTML = '<li><strong>No valid files available for this torrent.</strong></li>';
                }
            } else {
                filesList.innerHTML = '<li><strong>Error: No files data found.</strong></li>';
            }

            const modalTitle = document.getElementById('modal-files-title');
            if (modalTitle) {
                modalTitle.innerText = data.filename || "Unknown Torrent";
            }

            const modal = document.getElementById('rdModal');
            if (modal) {
                modal.style.display = "flex";
                modal.classList.add('show');
            }
        })
        .catch(error => {
            filesList.innerHTML = '<li><strong>Error loading files. Please try again.</strong></li>';
            console.error('Error fetching torrent files:', error);
        });
}

/**
 * Function to delete a single torrent with confirmation.
 * @param {string} torrentId - The ID of the torrent to delete.
 */
function deleteTorrent(torrentId) {
    console.log("Attempting to delete torrent with ID:", torrentId); // Log the torrentId

    if (!torrentId || typeof torrentId !== 'string') {
        alert('Invalid torrent ID provided.');
        return;
    }

    if (confirm("Are you sure you want to delete this torrent? This action cannot be undone.")) {
        fetch(`/torrent/delete_torrent/${encodeURIComponent(torrentId)}`, { method: 'DELETE' }) // Updated endpoint
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Error: ${response.status} - ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    alert("Torrent deleted successfully!");
                    location.reload();
                } else {
                    alert("Failed to delete the torrent: " + data.message);
                }
            })
            .catch(error => {
                console.error("Error deleting torrent:", error);
                alert("An error occurred while trying to delete the torrent: " + error.message);
            });
    }
}

/**
 * Function to confirm deletion of a torrent.
 * @param {string} torrentId - The ID of the torrent to delete.
 */
function confirmDeletion(torrentId) {
    const confirmation = confirm("Are you sure you want to delete this torrent?");
    if (confirmation) {
        deleteTorrent(torrentId);
    }
}

/**
 * Function to batch delete multiple torrents.
 */
function deleteSelectedTorrents() {
    const selectedCheckboxes = document.querySelectorAll(".torrent-checkbox:checked");

    if (selectedCheckboxes.length === 0) {
        alert("Please select at least one torrent to delete.");
        return;
    }

    if (confirm(`Are you sure you want to delete the selected ${selectedCheckboxes.length} torrent(s)?`)) {
        const torrentIds = Array.from(selectedCheckboxes).map(checkbox => checkbox.value);

        fetch(`/torrent/delete_torrents`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ torrentIds }),
        })
        .then(response => {
            if (!response.ok) throw new Error('Failed to delete selected torrents');
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                alert("Selected torrents have been deleted successfully.");
            } else if (data.status === 'partial_success') {
                alert("Some torrents could not be deleted.");
                console.log("Partial deletion results:", data.results);
            }
            location.reload();
        })
        .catch(error => console.error("Error deleting selected torrents:", error));
    }
}

/**
 * Function to get an unrestricted download link.
 * @param {string} originalLink - The original download link to unrestrict.
 */
function getUnrestrictedLink(originalLink) {
    fetch('/unrestrict_link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ link: originalLink }),
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Failed to generate unrestricted link.');
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.unrestricted_link) {
            window.location.href = data.unrestricted_link;
        } else {
            alert('Failed to generate unrestricted link.');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while generating the unrestricted link: ' + error.message);
    });
}

/**
 * Function to validate a URL.
 * @param {string} string - The URL string to validate.
 * @returns {boolean} - Returns true if valid, false otherwise.
 */
function isValidUrl(string) {
    try {
        new URL(string);
        return true;
    } catch (_) {
        return false;
    }
}

/**
 * Function to toggle all torrent checkboxes when "Select All" is clicked.
 * @param {HTMLInputElement} selectAllCheckbox - The "Select All" checkbox element.
 */
function toggleSelectAll(selectAllCheckbox) {
    const checkboxes = document.querySelectorAll('.torrent-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
    });
}

/**
 * Navigation Loading Overlay
 * Displays a loading overlay when navigation links are clicked.
 */
document.addEventListener('DOMContentLoaded', function() {
    const navbarLinks = document.querySelectorAll('.navbar a');
    const loadingOverlay = document.getElementById("loading");

    navbarLinks.forEach(link => {
        link.addEventListener("click", function(event) {
            // Display loading overlay
            loadingOverlay.style.display = 'flex';

            // Delay navigation to let loading overlay display
            event.preventDefault();
            const href = this.href;

            setTimeout(() => {
                window.location.href = href;
            }, 300);  // Adjust this delay if needed
        });
    });
});
// Test commit
