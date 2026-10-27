(function () {
    function lazyLoadContentImages() {
        document.querySelectorAll(".detail-content img").forEach(function (img) {
            if (!img.hasAttribute("loading")) img.setAttribute("loading", "lazy");
            if (!img.hasAttribute("decoding")) img.setAttribute("decoding", "async");
        });
    }

    function trackScrollDepth(root) {
        if (typeof gtag !== "function") return;
        var pageType = root.dataset.scrollTrack;
        var pageId = root.dataset.scrollTrackId || "";
        var thresholds = [25, 50, 75, 100];
        var fired = {};

        function currentDepth() {
            var doc = document.documentElement;
            var scrollTop = window.scrollY || doc.scrollTop || 0;
            var viewport = window.innerHeight || doc.clientHeight || 0;
            var scrollable = doc.scrollHeight - viewport;
            if (scrollable <= 0) return 100;
            return Math.min(100, Math.round((scrollTop / scrollable) * 100));
        }

        function onScroll() {
            var depth = currentDepth();
            thresholds.forEach(function (t) {
                if (depth >= t && !fired[t]) {
                    fired[t] = true;
                    gtag("event", "scroll_depth", {
                        event_category: "engagement",
                        event_label: pageType + ":" + pageId,
                        value: t,
                    });
                }
            });
            if (fired[100]) window.removeEventListener("scroll", onScroll);
        }

        window.addEventListener("scroll", onScroll, { passive: true });
        onScroll();
    }

    document.addEventListener("DOMContentLoaded", function () {
        lazyLoadContentImages();
        var root = document.querySelector("[data-scroll-track]");
        if (root) trackScrollDepth(root);
    });
})();
