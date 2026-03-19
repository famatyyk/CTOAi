const IDEA_STORAGE_KEY = "ctoa_idea_parking_v1";
const ADMIN_STATE_KEY = "ctoa_admin_state_v1";
const ADMIN_PASS_KEY = "ctoa_admin_password_v1";
const ADMIN_SESSION_KEY = "ctoa_admin_session_v1";
const ADMIN_USERNAME = "molek";
const RUNE_GLYPH_POOL = ["✶", "✦", "✹", "✷", "✧", "✵", "⚡", "✺", "❋", "✴"];

function createIdeaId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function encodeSecret(input) {
  return btoa(unescape(encodeURIComponent(input)));
}

function loadJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) {
      return fallback;
    }
    const data = JSON.parse(raw);
    return data ?? fallback;
  } catch {
    return fallback;
  }
}

function saveJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function loadIdeas() {
  const parsed = loadJson(IDEA_STORAGE_KEY, []);
  return Array.isArray(parsed) ? parsed : [];
}

function saveIdeas(ideas) {
  saveJson(IDEA_STORAGE_KEY, ideas);
}

function formatDate(isoString) {
  const d = new Date(isoString);
  return d.toLocaleString("pl-PL", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function updateIdeaCount() {
  const n = loadIdeas().length;
  const listCounter = document.getElementById("idea-count");
  if (listCounter) {
    listCounter.textContent = n === 0 ? "Brak zaparkowanych pomyslow" : `Zaparkowane: ${n}`;
  }
  const parkingMenu = document.querySelector('.menu-item[data-section="parking"]');
  if (parkingMenu) {
    parkingMenu.textContent = `📜 Parking Pomyslow [${n}]`;
  }
}

function downloadJsonFile(filename, data) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function renderIdeas() {
  const list = document.getElementById("idea-list");
  if (!list) {
    return;
  }

  const ideas = loadIdeas();
  list.innerHTML = "";

  if (!ideas.length) {
    const empty = document.createElement("li");
    empty.className = "idea-item";
    empty.innerHTML = "<p>Brak zaparkowanych pomyslow. Dodaj pierwszy wpis.</p>";
    list.appendChild(empty);
    updateIdeaCount();
    return;
  }

  ideas.forEach((idea) => {
    const li = document.createElement("li");
    li.className = "idea-item";

    const body = document.createElement("div");
    const text = document.createElement("p");
    text.textContent = idea.text;

    const meta = document.createElement("div");
    meta.className = "idea-meta";
    meta.textContent = `Dodano: ${formatDate(idea.createdAt)}`;

    body.appendChild(text);
    body.appendChild(meta);

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.className = "idea-remove";
    removeButton.textContent = "Usun";
    removeButton.addEventListener("click", () => {
      const next = loadIdeas().filter((entry) => entry.id !== idea.id);
      saveIdeas(next);
      renderIdeas();
    });

    li.appendChild(body);
    li.appendChild(removeButton);
    list.appendChild(li);
  });

  updateIdeaCount();
}

function setupIdeaForm() {
  const form = document.getElementById("idea-form");
  const input = document.getElementById("idea-input");
  const clearAll = document.getElementById("clear-all");

  if (!form || !input || !clearAll) {
    return;
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const value = input.value.trim();
    if (!value) {
      return;
    }

    const ideas = loadIdeas();
    ideas.unshift({
      id: createIdeaId(),
      text: value,
      createdAt: new Date().toISOString(),
    });

    saveIdeas(ideas);
    input.value = "";
    renderIdeas();
  });

  clearAll.addEventListener("click", () => {
    if (!confirm("Na pewno usunac wszystkie zaparkowane pomysly?")) {
      return;
    }
    saveIdeas([]);
    renderIdeas();
  });
}

function getDefaultAdminState() {
  return {
    stealthMode: true,
    showPrices: false,
    heroNote: "",
  };
}

function loadAdminState() {
  const state = loadJson(ADMIN_STATE_KEY, getDefaultAdminState());
  return { ...getDefaultAdminState(), ...state };
}

function saveAdminState(state) {
  saveJson(ADMIN_STATE_KEY, state);
}

function getAdminPassword() {
  return localStorage.getItem(ADMIN_PASS_KEY) || "";
}

function isAdminLoggedIn() {
  return sessionStorage.getItem(ADMIN_SESSION_KEY) === "1";
}

function setAdminLoggedIn(value) {
  if (value) {
    sessionStorage.setItem(ADMIN_SESSION_KEY, "1");
  } else {
    sessionStorage.removeItem(ADMIN_SESSION_KEY);
  }
}

function applyAdminState(state) {
  const drawer = document.getElementById("admin-drawer");
  const banner = document.getElementById("admin-banner");
  const stealthToggle = document.getElementById("stealth-toggle");
  const pricesToggle = document.getElementById("prices-toggle");
  const heroNote = document.getElementById("hero-note");
  const homeText = document.querySelector(".home-text");

  if (!drawer || !banner || !stealthToggle || !pricesToggle || !heroNote || !homeText) {
    return;
  }

  stealthToggle.checked = state.stealthMode;
  pricesToggle.checked = state.showPrices;
  heroNote.value = state.heroNote;

  drawer.hidden = !isAdminLoggedIn();
  if (!isAdminLoggedIn()) {
    drawer.classList.remove("open");
  }
  banner.hidden = !isAdminLoggedIn();

  document.querySelectorAll(".price-tag").forEach((el) => {
    const price = el.getAttribute("data-price") || "";
    el.textContent = state.showPrices ? `Cena: ${price}` : "Cena: ukryta do premiery";
  });

  if (state.heroNote.trim()) {
    homeText.textContent = state.heroNote.trim();
  } else if (state.stealthMode) {
    homeText.textContent = "Najedz na nazwe sekcji po lewej. Po prawej wysunie sie aktualny zestaw kart. Zabierasz kursor i scena wraca do widoku glownego.";
  } else {
    homeText.textContent = "Najedz na nazwe sekcji po lewej. Po prawej wysunie sie aktualny zestaw kart. Tryb otwartego onboardingu jest aktywny.";
  }
}

function setupAdminDrawerHover() {
  const trigger = document.getElementById("open-auth");
  const drawer = document.getElementById("admin-drawer");
  if (!trigger || !drawer) {
    return;
  }

  let hideTimer = null;

  const openDrawer = () => {
    if (!isAdminLoggedIn() || drawer.hidden) {
      return;
    }
    if (hideTimer) {
      clearTimeout(hideTimer);
      hideTimer = null;
    }
    drawer.classList.add("open");
  };

  const closeDrawer = () => {
    if (!isAdminLoggedIn()) {
      return;
    }
    if (hideTimer) {
      clearTimeout(hideTimer);
    }
    hideTimer = setTimeout(() => {
      drawer.classList.remove("open");
      hideTimer = null;
    }, 120);
  };

  trigger.addEventListener("mouseenter", openDrawer);
  drawer.addEventListener("mouseenter", openDrawer);
  trigger.addEventListener("mouseleave", closeDrawer);
  drawer.addEventListener("mouseleave", closeDrawer);

  trigger.addEventListener("focus", openDrawer);
  drawer.addEventListener("focusin", openDrawer);
  drawer.addEventListener("focusout", (e) => {
    if (!drawer.contains(e.relatedTarget)) {
      closeDrawer();
    }
  });
}

function showAuthModal(visible) {
  const modal = document.getElementById("auth-modal");
  if (!modal) {
    return;
  }
  if (visible) {
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    const user = document.getElementById("auth-user");
    if (user) {
      user.focus();
    }
  } else {
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
  }
}

function setupAdminAuth() {
  const open = document.getElementById("open-auth");
  const close = document.getElementById("auth-close");
  const submit = document.getElementById("auth-submit");
  const status = document.getElementById("auth-status");
  const hint = document.getElementById("auth-hint");

  const saveButton = document.getElementById("save-admin");
  const exportButton = document.getElementById("export-admin");
  const resetButton = document.getElementById("reset-admin");
  const logoutButton = document.getElementById("logout-admin");
  const adminStatus = document.getElementById("admin-status");

  const stealthToggle = document.getElementById("stealth-toggle");
  const pricesToggle = document.getElementById("prices-toggle");
  const heroNote = document.getElementById("hero-note");

  open.addEventListener("click", () => {
    if (isAdminLoggedIn()) {
      const drawer = document.getElementById("admin-drawer");
      if (drawer) {
        drawer.classList.toggle("open");
      }
      return;
    }
    const hasPassword = Boolean(getAdminPassword());
    hint.textContent = hasPassword
      ? "Zaloguj sie jako administrator."
      : "Pierwsze logowanie. Ustaw haslo dla konta molek.";
    status.textContent = "";
    showAuthModal(true);
  });

  close.addEventListener("click", () => showAuthModal(false));

  document.getElementById("auth-modal").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) {
      showAuthModal(false);
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      showAuthModal(false);
    }
  });

  submit.addEventListener("click", () => {
    const user = (document.getElementById("auth-user").value || "").trim().toLowerCase();
    const pass = document.getElementById("auth-pass").value || "";

    if (user !== ADMIN_USERNAME) {
      status.textContent = "Nieprawidlowy login.";
      return;
    }

    const storedPassword = getAdminPassword();
    if (!storedPassword) {
      if (pass.length < 8) {
        status.textContent = "Ustaw haslo min. 8 znakow.";
        return;
      }
      localStorage.setItem(ADMIN_PASS_KEY, encodeSecret(pass));
      setAdminLoggedIn(true);
      showAuthModal(false);
      applyAdminState(loadAdminState());
      adminStatus.textContent = "Pierwsze logowanie zakonczone.";
      return;
    }

    if (encodeSecret(pass) !== storedPassword) {
      status.textContent = "Nieprawidlowe haslo.";
      return;
    }

    setAdminLoggedIn(true);
    showAuthModal(false);
    applyAdminState(loadAdminState());
    adminStatus.textContent = "Zalogowano.";
  });

  saveButton.addEventListener("click", () => {
    if (!isAdminLoggedIn()) {
      adminStatus.textContent = "Brak sesji admina.";
      return;
    }

    const next = {
      stealthMode: stealthToggle.checked,
      showPrices: pricesToggle.checked,
      heroNote: heroNote.value.trim(),
    };

    saveAdminState(next);
    applyAdminState(next);
    adminStatus.textContent = "Ustawienia zapisane.";
  });

  exportButton.addEventListener("click", () => {
    if (!isAdminLoggedIn()) {
      adminStatus.textContent = "Brak sesji admina.";
      return;
    }

    const payload = {
      exportedAt: new Date().toISOString(),
      adminState: loadAdminState(),
      ideaCount: loadIdeas().length,
    };
    downloadJsonFile("ctoa-admin-config.json", payload);
    adminStatus.textContent = "Wyeksportowano JSON.";
  });

  resetButton.addEventListener("click", () => {
    if (!isAdminLoggedIn()) {
      adminStatus.textContent = "Brak sesji admina.";
      return;
    }
    if (!confirm("To wyczysci caly localStorage dla tej domeny. Kontynuowac?")) {
      return;
    }

    localStorage.clear();
    setAdminLoggedIn(false);
    saveAdminState(getDefaultAdminState());
    saveIdeas([]);
    renderIdeas();
    applyAdminState(loadAdminState());
    adminStatus.textContent = "Wyczyszczono localStorage i wylogowano.";
  });

  logoutButton.addEventListener("click", () => {
    setAdminLoggedIn(false);
    applyAdminState(loadAdminState());
    adminStatus.textContent = "Wylogowano.";
  });
}

function setupMenuPanels() {
  const root = document.getElementById("realm-root");
  const stage = document.querySelector(".realm-stage");
  const home = document.getElementById("home-view");
  const menuItems = Array.from(document.querySelectorAll(".menu-item"));
  const panels = Array.from(document.querySelectorAll(".section-panel"));

  if (!root || !stage || !home || !menuItems.length || !panels.length) {
    return;
  }

  let currentSection = null;
  let sectionSwitchCount = 0;
  const switchTimestamps = [];

  const runePresets = {
    oferty: {
      apparition: [
        { name: "Ghost Smoke Effect", glyph: "✶", c1: "214, 189, 255", c2: "151, 176, 255" },
        { name: "Avatar Effect", glyph: "✦", c1: "255, 219, 130", c2: "117, 221, 255" },
      ],
      status: [
        { name: "Death Effect", glyph: "✹", c1: "240, 166, 106", c2: "255, 96, 96" },
        { name: "Explosion Effect", glyph: "✷", c1: "255, 179, 110", c2: "255, 122, 96" },
      ],
    },
    projekty: {
      apparition: [
        { name: "Blue Ghost Effect", glyph: "✧", c1: "135, 202, 255", c2: "95, 235, 255" },
        { name: "Ferumbras Effect", glyph: "✵", c1: "194, 168, 255", c2: "121, 181, 255" },
      ],
      status: [
        { name: "Blue Electricity Effect", glyph: "⚡", c1: "120, 190, 255", c2: "74, 224, 255" },
        { name: "Thunderstorm Effect", glyph: "✺", c1: "151, 196, 255", c2: "96, 230, 255" },
      ],
    },
    parking: {
      apparition: [
        { name: "Vanishing Fae Effect", glyph: "❋", c1: "173, 255, 190", c2: "108, 232, 156" },
        { name: "Fae Effect 1", glyph: "✧", c1: "141, 236, 168", c2: "204, 255, 124" },
      ],
      status: [
        { name: "Green Sparkles Effect", glyph: "✺", c1: "113, 231, 156", c2: "204, 255, 124" },
        { name: "Poison Effect", glyph: "✶", c1: "138, 230, 119", c2: "223, 255, 132" },
      ],
    },
    kontakt: {
      apparition: [
        { name: "Assassin Effect", glyph: "✴", c1: "255, 184, 140", c2: "255, 122, 107" },
        { name: "Ghostly Scratch Effect", glyph: "✵", c1: "224, 166, 255", c2: "161, 186, 255" },
      ],
      status: [
        { name: "Red Sparkles Effect", glyph: "✹", c1: "255, 161, 107", c2: "255, 102, 102" },
        { name: "Poof Effect", glyph: "✷", c1: "245, 181, 126", c2: "255, 133, 116" },
      ],
    },
  };

  const randomRange = (min, max) => Math.random() * (max - min) + min;
  const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
  const parseRgb = (value) => value.split(",").map((part) => Number(part.trim()) || 0);
  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
  const boostRgb = (value, factor) => {
    const [r, g, b] = parseRgb(value);
    return [
      clamp(Math.round(r * factor), 0, 255),
      clamp(Math.round(g * factor), 0, 255),
      clamp(Math.round(b * factor), 0, 255),
    ].join(", ");
  };

  const triggerCameraShake = (strength = 1) => {
    stage.style.setProperty("--shake-x", `${randomRange(1.8, 2.6).toFixed(2) * strength}px`);
    stage.style.setProperty("--shake-y", `${randomRange(1.4, 2.2).toFixed(2) * strength}px`);
    stage.classList.remove("shake");
    void stage.offsetWidth;
    stage.classList.add("shake");
  };

  const spawnLegendaryRing = (xPercent, yPercent, c1, c2, power) => {
    const ring = document.createElement("span");
    ring.className = "rune-legend-ring";
    ring.style.setProperty("--legend-x", xPercent);
    ring.style.setProperty("--legend-y", yPercent);
    ring.style.setProperty("--legend-c1", c1);
    ring.style.setProperty("--legend-c2", c2);
    ring.style.setProperty("--legend-scale", `${(6.9 * power).toFixed(2)}`);
    stage.appendChild(ring);
    ring.addEventListener("animationend", () => ring.remove(), { once: true });
  };

  const spawnRuneTrail = (xPercent, yPercent, c1, c2) => {
    const particles = 8;
    for (let i = 0; i < particles; i++) {
      const dot = document.createElement("span");
      dot.className = "rune-trail";
      dot.style.setProperty("--trail-x", xPercent);
      dot.style.setProperty("--trail-y", yPercent);
      dot.style.setProperty("--trail-c1", c1);
      dot.style.setProperty("--trail-c2", c2);
      dot.style.setProperty("--trail-size", `${randomRange(5, 10).toFixed(1)}px`);
      dot.style.setProperty("--trail-dx", `${randomRange(-42, 42).toFixed(1)}px`);
      dot.style.setProperty("--trail-dy", `${randomRange(-36, 28).toFixed(1)}px`);
      stage.appendChild(dot);
      dot.addEventListener("animationend", () => dot.remove(), { once: true });
    }
  };

  const activate = (sectionId) => {
    const changed = sectionId !== currentSection;

    menuItems.forEach((item) => {
      item.classList.toggle("active", item.dataset.section === sectionId);
    });

    let anyActive = false;
    panels.forEach((panel) => {
      const isMatch = panel.dataset.panel === sectionId;
      panel.classList.toggle("active", isMatch);
      anyActive = anyActive || isMatch;
    });

    home.classList.toggle("active", !anyActive);

    if (changed && sectionId) {
      sectionSwitchCount += 1;
      const now = performance.now();
      switchTimestamps.push(now);
      while (switchTimestamps.length && now - switchTimestamps[0] > 2000) {
        switchTimestamps.shift();
      }

      const isFever = switchTimestamps.length >= 3;
      const isLegendary = sectionSwitchCount % 5 === 0;
      const power = (isFever ? 1.35 : 1) * (isLegendary ? 1.18 : 1);
      const group = runePresets[sectionId] || runePresets.oferty;
      const family = Math.random() < 0.5 ? "apparition" : "status";
      const pool = group[family];
      const palette = pick(pool);
      const glyph = pick(RUNE_GLYPH_POOL);
      const c1 = isLegendary ? boostRgb(palette.c1, 1.18) : palette.c1;
      const c2 = isLegendary ? boostRgb(palette.c2, 1.22) : palette.c2;
      const x = `${randomRange(18, 84).toFixed(2)}%`;
      const y = `${randomRange(16, 82).toFixed(2)}%`;

      stage.style.setProperty("--rune-x", x);
      stage.style.setProperty("--rune-y", y);
      stage.style.setProperty("--rune-c1", c1);
      stage.style.setProperty("--rune-c2", c2);
      stage.style.setProperty("--rune-glyph", `"${glyph}"`);
      stage.style.setProperty("--rune-power", power.toFixed(2));
      stage.style.setProperty("--rune-size", `${Math.round(56 * power)}px`);
      stage.style.setProperty("--rune-burst-scale", `${(6.1 * power).toFixed(2)}`);
      stage.style.setProperty("--rune-glyph-end", `${(1.7 * power).toFixed(2)}`);

      let label = stage.querySelector(".rune-label");
      if (!label) {
        label = document.createElement("div");
        label.className = "rune-label";
        stage.appendChild(label);
      }
      if (isLegendary) {
        label.textContent = `LEGENDARY · ${family.toUpperCase()} · ${palette.name}`;
      } else if (isFever) {
        label.textContent = `FEVER x${power.toFixed(2)} · ${family.toUpperCase()} · ${palette.name}`;
      } else {
        label.textContent = `${family.toUpperCase()} · ${palette.name}`;
      }

      spawnRuneTrail(x, y, c1, c2);
      if (isLegendary) {
        spawnLegendaryRing(x, y, c1, c2, power);
      }
      triggerCameraShake(isLegendary ? 1.3 : 1);

      stage.classList.remove("rune-burst");
      stage.classList.toggle("fever-mode", isFever);
      stage.classList.toggle("legendary-mode", isLegendary);
      void stage.offsetWidth;
      stage.classList.add("rune-burst");
    }

    currentSection = sectionId;
  };

  const reset = () => activate(null);

  menuItems.forEach((item) => {
    const id = item.dataset.section;
    item.addEventListener("mouseenter", () => activate(id));
    item.addEventListener("focus", () => activate(id));
    item.addEventListener("click", () => activate(id));
  });

  root.addEventListener("mouseleave", reset);

  document.addEventListener("keydown", (event) => {
    const activeTag = document.activeElement?.tagName || "";
    if (activeTag === "INPUT" || activeTag === "TEXTAREA") {
      return;
    }

    const currentIndex = menuItems.findIndex((item) => item.dataset.section === currentSection);
    if (event.key === "ArrowDown") {
      event.preventDefault();
      const nextIndex = currentIndex < 0 ? 0 : (currentIndex + 1) % menuItems.length;
      activate(menuItems[nextIndex].dataset.section || null);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      const prevIndex = currentIndex < 0 ? menuItems.length - 1 : (currentIndex - 1 + menuItems.length) % menuItems.length;
      activate(menuItems[prevIndex].dataset.section || null);
      return;
    }

    if (event.key === "Escape") {
      reset();
    }
  });

  reset();
}

function setupDecks() {
  const decks = Array.from(document.querySelectorAll("[data-deck]"));

  decks.forEach((deck) => {
    const cards = Array.from(deck.querySelectorAll(".deck-card"));
    const next = deck.querySelector("[data-next-card]");
    const meta = deck.querySelector("[data-meta]");
    let index = 0;

    if (!cards.length || !next || !meta) {
      return;
    }

    const render = () => {
      cards.forEach((card, i) => card.classList.toggle("active", i === index));
      meta.textContent = `${index + 1} / ${cards.length}`;
    };

    next.addEventListener("click", () => {
      const currentIndex = index;
      const nextIndex = (index + 1) % cards.length;
      const currentCard = cards[currentIndex];
      const nextCard = cards[nextIndex];

      deck.classList.add("turning");
      currentCard.classList.add("turn-out");
      nextCard.classList.add("active");

      setTimeout(() => {
        currentCard.classList.remove("active", "turn-out");
        deck.classList.remove("turning");
      }, 360);

      index = nextIndex;
      deck.classList.remove("flash");
      void deck.offsetWidth;
      deck.classList.add("flash");
      meta.textContent = `${index + 1} / ${cards.length}`;
    });

    deck.addEventListener("animationend", () => {
      deck.classList.remove("flash");
    });

    render();
  });
}

showAuthModal(false);
setupIdeaForm();
renderIdeas();
setupAdminAuth();
setupAdminDrawerHover();
setupMenuPanels();
setupDecks();
applyAdminState(loadAdminState());
