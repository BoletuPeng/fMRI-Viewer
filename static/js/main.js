/* static/js/main.js */
/* eslint-env browser */

const thumbStrip = document.getElementById("thumb-strip");
const previewImg = document.getElementById("preview-img");
const metaBodyLeft = document.getElementById("meta-body-left");
const metaBodyRight = document.getElementById("meta-body-right");

let currentThumb = null; // track selected thumbnail div
let currentLanguage = "english"; // default language

// ─── Settings Modal ─────────────────────────────────────────────────────────
const settingsBtn = document.getElementById("settings-btn");
const settingsModal = document.getElementById("settings-modal");
const settingsCancel = document.getElementById("settings-cancel");
const settingsSave = document.getElementById("settings-save");
const languageSelect = document.getElementById("language-select");

// Show settings modal
settingsBtn.addEventListener("click", () => {
  settingsModal.classList.remove("hidden");
  const modalContent = settingsModal.querySelector(".modal-content");
  modalContent.classList.add("modal-enter");
  
  requestAnimationFrame(() => {
    modalContent.classList.remove("modal-enter");
    modalContent.classList.add("modal-enter-active");
  });
  
  // Load current language
  languageSelect.value = currentLanguage;
});

// Hide settings modal
function hideSettingsModal() {
  const modalContent = settingsModal.querySelector(".modal-content");
  modalContent.classList.remove("modal-enter-active");
  modalContent.classList.add("modal-exit-active");
  
  setTimeout(() => {
    settingsModal.classList.add("hidden");
    modalContent.classList.remove("modal-exit-active");
  }, 150);
}

settingsCancel.addEventListener("click", hideSettingsModal);

// Click outside modal to close
settingsModal.addEventListener("click", (e) => {
  if (e.target === settingsModal) {
    hideSettingsModal();
  }
});

// Save settings
settingsSave.addEventListener("click", async () => {
  const newLanguage = languageSelect.value;
  
  if (newLanguage !== currentLanguage) {
    // Change language
    const response = await fetch(`/api/language/${newLanguage}`, { method: "POST" });
    if (response.ok) {
      currentLanguage = newLanguage;
      await updateUILanguage();
      // Refresh current metadata if a file is selected
      if (currentThumb) {
        const filename = currentThumb.querySelector("img").title;
        await loadMetadata(filename);
      }
    }
  }
  
  hideSettingsModal();
});

// ─── Language Support ───────────────────────────────────────────────────────
async function updateUILanguage() {
  try {
    const response = await fetch("/api/translations");
    const translations = await response.json();
    
    // Update UI elements
    document.getElementById("app-title").textContent = translations.UI_APP_TITLE;
    document.getElementById("import-file-label").textContent = translations.UI_IMPORT_FILE;
    document.getElementById("import-folder-label").textContent = translations.UI_IMPORT_FOLDER;
    document.getElementById("settings-label").textContent = translations.UI_SETTINGS;
    
    // Table headers
    document.getElementById("attr-header-left").textContent = translations.UI_ATTRIBUTE;
    document.getElementById("value-header-left").textContent = translations.UI_VALUE;
    document.getElementById("attr-header-right").textContent = translations.UI_ATTRIBUTE;
    document.getElementById("value-header-right").textContent = translations.UI_VALUE;
    
    // Settings modal
    document.getElementById("settings-title").textContent = translations.UI_SETTINGS_TITLE;
    document.getElementById("option1-label").textContent = translations.UI_OPTION1;
    document.getElementById("option2-label").textContent = translations.UI_OPTION2;
    document.getElementById("language-label").textContent = translations.UI_LANGUAGE;
    document.getElementById("cancel-label").textContent = translations.UI_CANCEL;
    document.getElementById("save-label").textContent = translations.UI_SAVE;
    
  } catch (error) {
    console.error("Error updating UI language:", error);
  }
}

// ─── Helper: load list & populate thumbnails ───────────────────────────────
async function refreshThumbnails() {
  try {
    console.log("Refreshing thumbnails...");
    const response = await fetch("/api/cache/list");
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const files = await response.json();
    console.log("Files found:", files);
    
    thumbStrip.innerHTML = "";
    files.forEach(name => addThumbnail(name));
    
    // 如果有文件，自动选择第一个
    if (files.length > 0 && thumbStrip.firstChild) {
      thumbStrip.firstChild.click();
    }
  } catch (error) {
    console.error("Error refreshing thumbnails:", error);
  }
}

function addThumbnail(name) {
  const img = document.createElement("img");
  const encodedName = encodeURIComponent(name);
  img.src = `/api/cache/preview/${encodedName}`;
  img.className = "h-20 w-20 object-cover rounded cursor-pointer select-none";
  img.title = name;
  
  // 添加加载错误处理
  img.onerror = function() {
    console.error(`Failed to load thumbnail for ${name}`);
    this.src = "/static/images/placeholder.png";
  };
  
  img.onload = function() {
    console.log(`Successfully loaded thumbnail for ${name}`);
  };

  const wrapper = document.createElement("div");
  wrapper.className = "relative flex-shrink-0"; // 添加 flex-shrink-0 防止压缩
  wrapper.appendChild(img);
  thumbStrip.appendChild(wrapper);

  wrapper.addEventListener("click", () => {
    console.log(`Thumbnail clicked: ${name}`);
    
    // highlight selected
    if (currentThumb) currentThumb.classList.remove("thumb-selected");
    wrapper.classList.add("thumb-selected");
    currentThumb = wrapper;

    // set preview & metadata
    previewImg.src = `/api/cache/preview/${encodedName}`;
    previewImg.onerror = function() {
      console.error(`Failed to load preview for ${name}`);
    };
    loadMetadata(name);
  });

  // context-menu remove
  wrapper.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    showContextMenu(e.pageX, e.pageY, () => removeFile(name, wrapper));
  });
}

// ─── Context menu -----------------------------------------------------------
async function showContextMenu(x, y, onRemove) {
  // Get remove translation
  const response = await fetch("/api/translations");
  const translations = await response.json();
  
  const menu = document.createElement("div");
  menu.className = "absolute z-50 bg-[#1f272e] text-white text-sm rounded shadow-lg";
  menu.style.top = `${y}px`;
  menu.style.left = `${x}px`;
  const btn = document.createElement("div");
  btn.textContent = translations.UI_REMOVE || "Remove";
  btn.className = "px-4 py-2 hover:bg-[#2b3640] cursor-pointer";
  btn.addEventListener("click", () => { onRemove(); menu.remove(); });
  menu.appendChild(btn);
  document.body.appendChild(menu);
  const off = () => { menu.remove(); document.removeEventListener("click", off); };
  setTimeout(() => document.addEventListener("click", off), 0);
}

// ─── Remove file ------------------------------------------------------------
async function removeFile(name, wrapper) {
  await fetch(`/api/cache/delete/${encodeURIComponent(name)}`, { method: "DELETE" });
  wrapper.remove();
  if (currentThumb === wrapper) {
    previewImg.src = "/static/images/placeholder.png";
    metaBodyLeft.innerHTML = "";
    metaBodyRight.innerHTML = "";
    currentThumb = null;
  }
}

// ─── Metadata ---------------------------------------------------------------
async function loadMetadata(name) {
  try {
    const response = await fetch(`/api/cache/metadata/${encodeURIComponent(name)}`);
    const metaList = await response.json();
    metaBodyLeft.innerHTML = "";
    metaBodyRight.innerHTML = "";
    
    // metaList is now an ordered array: [{"name": "属性", "value": "值"}, ...]
    const midPoint = Math.ceil(metaList.length / 2);
    
    // Fill left column
    metaList.slice(0, midPoint).forEach(item => {
      const row = document.createElement("tr");
      row.innerHTML = `<td class="px-4 py-2 text-[#9daebe]">${item.name}</td><td class="px-4 py-2 text-white">${item.value}</td>`;
      metaBodyLeft.appendChild(row);
    });
    
    // Fill right column
    metaList.slice(midPoint).forEach(item => {
      const row = document.createElement("tr");
      row.innerHTML = `<td class="px-4 py-2 text-[#9daebe]">${item.name}</td><td class="px-4 py-2 text-white">${item.value}</td>`;
      metaBodyRight.appendChild(row);
    });
  } catch (error) {
    console.error("Error loading metadata:", error);
  }
}


// ─── Import handlers --------------------------------------------------------
function handleImport(inputEl) {
  const files = Array.from(inputEl.files || []);
  if (!files.length) return;
  const body = new FormData();
  files.forEach(f => body.append("files[]", f));
  fetch("/api/import", { method: "POST", body })
    .then(() => refreshThumbnails())
    .catch(error => console.error("Import error:", error));
  inputEl.value = ""; // reset so selecting same again triggers change
}

document.getElementById("file-input").addEventListener("change", e => handleImport(e.target));
document.getElementById("folder-input").addEventListener("change", e => handleImport(e.target));

// ─── Wheel → horizontal scroll in thumbStrip --------------------------------
const thumbStripWrapper = document.getElementById("thumb-strip-wrapper");
thumbStripWrapper.addEventListener("wheel", (e) => {
  e.preventDefault();
  thumbStrip.scrollLeft += e.deltaY;
});

// ─── Init -------------------------------------------------------------------
async function initialize() {
  // Load current language settings
  try {
    const response = await fetch("/api/language");
    const data = await response.json();
    currentLanguage = data.current;
    
    // Update UI language
    await updateUILanguage();
  } catch (error) {
    console.error("Error loading language settings:", error);
  }
  
  // Load thumbnails
  await refreshThumbnails();
}

// 确保DOM完全加载后再初始化
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initialize);
} else {
  initialize();
}