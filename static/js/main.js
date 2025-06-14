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
const filterSettingsBtn = document.getElementById("filter-settings-btn");

// ─── Filter Modal ───────────────────────────────────────────────────────────
const filterModal = document.getElementById("filter-modal");
const filterContent = document.getElementById("filter-content");
const filterCancel = document.getElementById("filter-cancel");
const filterOk = document.getElementById("filter-ok");
const selectAllBtn = document.getElementById("select-all-btn");
const deselectAllBtn = document.getElementById("deselect-all-btn");

let filterStructure = {};
let tempFilterSettings = { categories: {}, fields: {} };
let expandedCategories = new Set(); // Track which categories are expanded

// ─── Modal Helper Functions ─────────────────────────────────────────────────
function showModal(modal) {
  modal.classList.remove("hidden");
  const modalContent = modal.querySelector(".modal-content");
  modalContent.classList.add("modal-enter");
  
  requestAnimationFrame(() => {
    modalContent.classList.remove("modal-enter");
    modalContent.classList.add("modal-enter-active");
  });
}

function hideModal(modal) {
  const modalContent = modal.querySelector(".modal-content");
  modalContent.classList.remove("modal-enter-active");
  modalContent.classList.add("modal-exit-active");
  
  setTimeout(() => {
    modal.classList.add("hidden");
    modalContent.classList.remove("modal-exit-active");
  }, 150);
}

// ─── Settings Modal Handlers ────────────────────────────────────────────────
settingsBtn.addEventListener("click", () => {
  showModal(settingsModal);
  languageSelect.value = currentLanguage;
});

settingsCancel.addEventListener("click", () => hideModal(settingsModal));

settingsModal.addEventListener("click", (e) => {
  if (e.target === settingsModal) {
    hideModal(settingsModal);
  }
});

settingsSave.addEventListener("click", async () => {
  const newLanguage = languageSelect.value;
  
  if (newLanguage !== currentLanguage) {
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
  
  hideModal(settingsModal);
});

// ─── Filter Settings Button ─────────────────────────────────────────────────
filterSettingsBtn.addEventListener("click", async () => {
  hideModal(settingsModal);
  await loadFilterSettings();
  showModal(filterModal);
});

// ─── Filter Modal Handlers ──────────────────────────────────────────────────
filterCancel.addEventListener("click", () => hideModal(filterModal));

filterModal.addEventListener("click", (e) => {
  if (e.target === filterModal) {
    hideModal(filterModal);
  }
});

filterOk.addEventListener("click", async () => {
  // Save filter settings
  await fetch("/api/filter/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(tempFilterSettings)
  });
  
  hideModal(filterModal);
  
  // Refresh current metadata if a file is selected
  if (currentThumb) {
    const filename = currentThumb.querySelector("img").title;
    await loadMetadata(filename);
  }
});

selectAllBtn.addEventListener("click", () => {
  // Set all categories and fields to visible
  Object.keys(filterStructure).forEach(category => {
    tempFilterSettings.categories[category] = true;
    filterStructure[category].fields.forEach(field => {
      tempFilterSettings.fields[field.index] = true;
    });
  });
  renderFilterContent();
});

deselectAllBtn.addEventListener("click", () => {
  // Set all categories and fields to hidden
  Object.keys(filterStructure).forEach(category => {
    tempFilterSettings.categories[category] = false;
    filterStructure[category].fields.forEach(field => {
      tempFilterSettings.fields[field.index] = false;
    });
  });
  renderFilterContent();
});

// ─── Filter Settings Functions ──────────────────────────────────────────────
async function loadFilterSettings() {
  try {
    // Load structure
    const structureResponse = await fetch("/api/filter/structure");
    filterStructure = await structureResponse.json();
    
    // Load current settings
    const settingsResponse = await fetch("/api/filter/settings");
    const currentSettings = await settingsResponse.json();
    
    // Initialize temp settings
    tempFilterSettings = {
      categories: { ...currentSettings.categories },
      fields: { ...currentSettings.fields }
    };
    
    // Clear expanded categories when opening modal
    expandedCategories.clear();
    
    // Ensure all fields have a setting
    Object.values(filterStructure).forEach(categoryData => {
      categoryData.fields.forEach(field => {
        if (!(field.index in tempFilterSettings.fields)) {
          tempFilterSettings.fields[field.index] = true;
        }
      });
    });
    
    renderFilterContent();
  } catch (error) {
    console.error("Error loading filter settings:", error);
  }
}

function renderFilterContent() {
  filterContent.innerHTML = "";
  
  Object.entries(filterStructure).forEach(([category, data]) => {
    // Create category container
    const categoryDiv = document.createElement("div");
    categoryDiv.className = "border border-[#3d4d5c] rounded-lg overflow-hidden";
    
    // Category header
    const headerDiv = document.createElement("div");
    headerDiv.className = "flex items-center gap-2 px-4 py-3 bg-[#2b3640] cursor-pointer hover:bg-[#3d4d5c] transition-colors";
    
    // Expand icon
    const expandIcon = document.createElement("svg");
    expandIcon.className = "expand-icon w-4 h-4 text-[#9daebe]";
    expandIcon.innerHTML = '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>';
    
    // Category checkbox
    const categoryCheckbox = document.createElement("input");
    categoryCheckbox.type = "checkbox";
    categoryCheckbox.className = "rounded bg-[#2b3640] border-[#3d4d5c] text-[#4f9cff] focus:ring-[#4f9cff] focus:ring-offset-0";
    
    // Update checkbox state
    const categoryState = getCategoryState(category, data.fields);
    if (categoryState === "checked") {
      categoryCheckbox.checked = true;
      categoryCheckbox.classList.remove("checkbox-indeterminate");
    } else if (categoryState === "indeterminate") {
      categoryCheckbox.checked = true;
      categoryCheckbox.classList.add("checkbox-indeterminate");
    } else {
      categoryCheckbox.checked = false;
      categoryCheckbox.classList.remove("checkbox-indeterminate");
    }
    
    // Category label
    const categoryLabel = document.createElement("span");
    categoryLabel.className = "text-white font-medium flex-1";
    categoryLabel.textContent = data.name;
    
    headerDiv.appendChild(expandIcon);
    headerDiv.appendChild(categoryCheckbox);
    headerDiv.appendChild(categoryLabel);
    
    // Fields container
    const fieldsDiv = document.createElement("div");
    fieldsDiv.className = "bg-[#141a1f] divide-y divide-[#3d4d5c]";
    
    // Check if category should be expanded
    if (expandedCategories.has(category)) {
      fieldsDiv.classList.remove("hidden");
      expandIcon.classList.add("expanded");
    } else {
      fieldsDiv.classList.add("hidden");
    }
    
    // Add fields
    data.fields.forEach(field => {
      const fieldDiv = document.createElement("div");
      fieldDiv.className = "flex items-center gap-2 px-10 py-2 hover:bg-[#1f272e] transition-colors";
      
      const fieldCheckbox = document.createElement("input");
      fieldCheckbox.type = "checkbox";
      fieldCheckbox.className = "rounded bg-[#2b3640] border-[#3d4d5c] text-[#4f9cff] focus:ring-[#4f9cff] focus:ring-offset-0";
      fieldCheckbox.checked = tempFilterSettings.fields[field.index] !== false;
      
      const fieldLabel = document.createElement("span");
      fieldLabel.className = "text-[#9daebe] text-sm";
      fieldLabel.textContent = field.name;
      
      fieldDiv.appendChild(fieldCheckbox);
      fieldDiv.appendChild(fieldLabel);
      fieldsDiv.appendChild(fieldDiv);
      
      // Field checkbox handler
      fieldCheckbox.addEventListener("change", () => {
        tempFilterSettings.fields[field.index] = fieldCheckbox.checked;
        updateCategoryCheckbox(category, data.fields);
      });
    });
    
    categoryDiv.appendChild(headerDiv);
    categoryDiv.appendChild(fieldsDiv);
    filterContent.appendChild(categoryDiv);
    
    // Toggle expand/collapse - only when clicking on header but not checkbox
    headerDiv.addEventListener("click", (e) => {
      // Check if the click target is the checkbox or its label
      if (e.target === categoryCheckbox || categoryCheckbox.contains(e.target)) {
        return;
      }
      
      const isExpanded = !fieldsDiv.classList.contains("hidden");
      fieldsDiv.classList.toggle("hidden");
      expandIcon.classList.toggle("expanded", !isExpanded);
      
      // Update expanded state tracking
      if (!isExpanded) {
        expandedCategories.add(category);
      } else {
        expandedCategories.delete(category);
      }
    });
    
    // Category checkbox handler - prevent event bubbling
    categoryCheckbox.addEventListener("click", (e) => {
      e.stopPropagation();
    });
    
    categoryCheckbox.addEventListener("change", (e) => {
      e.stopPropagation();
      
      const newState = categoryCheckbox.checked;
      tempFilterSettings.categories[category] = newState;
      
      // Update all fields in this category
      data.fields.forEach(field => {
        tempFilterSettings.fields[field.index] = newState;
      });
      
      // Re-render to update field checkboxes
      renderFilterContent();
    });
  });
}

function getCategoryState(category, fields) {
  const visibleCount = fields.filter(f => tempFilterSettings.fields[f.index] !== false).length;
  
  if (visibleCount === 0) return "unchecked";
  if (visibleCount === fields.length) return "checked";
  return "indeterminate";
}

function updateCategoryCheckbox(category, fields) {
  // Re-render to update the category checkbox state
  renderFilterContent();
}

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
    document.getElementById("filter-settings-label").textContent = translations.UI_FILTER_SETTINGS || "Filter Settings";
    document.getElementById("language-label").textContent = translations.UI_LANGUAGE;
    document.getElementById("cancel-label").textContent = translations.UI_CANCEL;
    document.getElementById("save-label").textContent = translations.UI_SAVE;
    
    // Filter modal
    document.getElementById("filter-title").textContent = translations.UI_FILTER_SETTINGS || "Filter Settings";
    document.getElementById("select-all-label").textContent = translations.UI_SELECT_ALL || "Select All";
    document.getElementById("deselect-all-label").textContent = translations.UI_DESELECT_ALL || "Deselect All";
    document.getElementById("filter-cancel-label").textContent = translations.UI_CANCEL;
    document.getElementById("filter-ok-label").textContent = translations.UI_OK || "OK";
    
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