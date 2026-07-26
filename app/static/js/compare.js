/* OK Series compare (max 3, localStorage). Config: window.OK_COMPARE */
(function () {
    const MAX = 3;
    const cfg = window.OK_COMPARE || {};
    const STORAGE_KEY = cfg.storageKey || "ok_compare_ids_v1";

    function getLang() {
        return cfg.lang || "en";
    }

    function getCompareItems() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return [];
            const parsed = JSON.parse(raw);
            return Array.isArray(parsed) ? parsed : [];
        } catch (_) {
            return [];
        }
    }

    function setCompareItems(ids) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
    }

    function compareUrl(ids) {
        const lang = getLang();
        const base = `/compare?lang=${encodeURIComponent(lang)}`;
        if (!ids || !ids.length) return base;
        return `${base}&ids=${encodeURIComponent(ids.join(","))}`;
    }

    function showToast(message) {
        let el = document.getElementById("compare-toast");
        if (!el) {
            el = document.createElement("div");
            el.id = "compare-toast";
            el.className = "compare-toast";
            document.body.appendChild(el);
        }
        el.textContent = message;
        el.classList.add("is-visible");
        clearTimeout(el._hideTimer);
        el._hideTimer = setTimeout(() => el.classList.remove("is-visible"), 2200);
    }

    function syncCompareUI() {
        const ids = getCompareItems();
        const count = ids.length;
        const canCompare = count >= 2;

        document.querySelectorAll("[data-compare-count]").forEach((el) => {
            el.textContent = String(count);
        });

        const bar = document.getElementById("compare-bar");
        if (bar) bar.classList.toggle("is-visible", count > 0);
        document.body.classList.toggle("compare-bar-active", count > 0);

        document.querySelectorAll("[data-compare-open]").forEach((el) => {
            const url = compareUrl(ids);
            if (el.tagName === "A") {
                if (canCompare) {
                    el.href = url;
                    el.classList.remove("is-disabled");
                    el.removeAttribute("aria-disabled");
                } else {
                    el.href = "#";
                    el.classList.add("is-disabled");
                    el.setAttribute("aria-disabled", "true");
                }
            } else if (el.tagName === "BUTTON") {
                el.disabled = !canCompare;
            }
        });

        document.querySelectorAll(".compare-toggle-btn[data-compare-id]").forEach((btn) => {
            const selected = ids.includes(btn.dataset.compareId);
            btn.classList.toggle("is-selected", selected);
            const defaultLabel = btn.dataset.labelDefault || cfg.labelDefault || "+ Compare";
            const selectedLabel = btn.dataset.labelSelected || cfg.labelSelected || "✓ Comparing";
            btn.textContent = selected ? selectedLabel : defaultLabel;
            btn.setAttribute("aria-pressed", selected ? "true" : "false");
        });

        document.querySelectorAll("[data-compare-card]").forEach((card) => {
            card.classList.toggle("in-compare", ids.includes(card.dataset.compareCard));
        });
    }

    function toggleCompareItem(id) {
        if (!id) return;
        const items = getCompareItems();
        const exists = items.includes(id);
        let next;

        if (exists) {
            next = items.filter((v) => v !== id);
            showToast(cfg.toastRemoved || "Removed from compare");
        } else if (items.length >= MAX) {
            showToast(cfg.toastMax || "Max 3 — remove one first");
            return;
        } else {
            next = [...items, id];
            showToast(cfg.toastAdded || "Added to compare ✓");
        }

        setCompareItems(next);
        syncCompareUI();
    }

    function clearCompare() {
        setCompareItems([]);
        syncCompareUI();
        showToast(cfg.toastCleared || "Compare list cleared");
    }

    function bootstrapFromQuery() {
        const params = new URLSearchParams(window.location.search);
        if (window.location.pathname === "/compare") {
            const idsParam = params.get("ids");
            if (idsParam) {
                const ids = idsParam
                    .split(",")
                    .map((value) => value.trim())
                    .filter(Boolean)
                    .slice(0, MAX);
                setCompareItems(ids);
            }
        }
    }

    document.addEventListener("click", (event) => {
        const toggleBtn = event.target.closest(".compare-toggle-btn[data-compare-id]");
        if (toggleBtn) {
            event.preventDefault();
            event.stopPropagation();
            toggleCompareItem(toggleBtn.dataset.compareId);
            return;
        }

        const clearBtn = event.target.closest("[data-compare-clear]");
        if (clearBtn) {
            event.preventDefault();
            clearCompare();
            return;
        }

        const removeBtn = event.target.closest("[data-compare-remove]");
        if (removeBtn) {
            event.preventDefault();
            const id = removeBtn.dataset.compareRemove;
            const next = getCompareItems().filter((value) => value !== id);
            setCompareItems(next);
            window.location.href = compareUrl(next);
            return;
        }

        const openLink = event.target.closest("[data-compare-open].is-disabled");
        if (openLink) {
            event.preventDefault();
        }
    });

    window.OKCompare = {
        getCompareItems,
        toggleCompareItem,
        clearCompare,
        syncCompareUI,
        compareUrl,
    };

    bootstrapFromQuery();
    syncCompareUI();
})();
