/* eslint-env browser */

const thumbStrip = document.getElementById("thumb-strip");
const previewImg = document.getElementById("preview-img");
const metaBody   = document.getElementById("meta-body");

let currentThumb = null; // track selected thumbnail div

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
function showContextMenu(x, y, onRemove) {
  const menu = document.createElement("div");
  menu.className = "absolute z-50 bg-[#1f272e] text-white text-sm rounded shadow-lg";
  menu.style.top = `${y}px`;
  menu.style.left = `${x}px`;
  const btn = document.createElement("div");
  btn.textContent = "Remove";
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
    metaBody.innerHTML = "";
    currentThumb = null;
  }
}

// ─── Metadata ---------------------------------------------------------------
async function loadMetadata(name) {
  try {
    const response = await fetch(`/api/cache/metadata/${encodeURIComponent(name)}`);
    const meta = await response.json();
    metaBody.innerHTML = "";
    Object.entries(meta).forEach(([k,v]) => {
      const row = document.createElement("tr");
      row.innerHTML = `<td class="px-4 py-2 text-[#9daebe]">${k}</td><td class="px-4 py-2 text-white">${v}</td>`;
      metaBody.appendChild(row);
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
// 确保DOM完全加载后再初始化
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', refreshThumbnails);
} else {
  refreshThumbnails();
}