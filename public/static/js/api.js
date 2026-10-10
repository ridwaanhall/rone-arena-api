/*
 * Every API call the site's scripts make goes through ArenaApi.request(url, init).
 *
 * It sends the call to this host first. When that fails in a way another host could fix
 * (network error, timeout, 5xx, 429, or an HTML error page instead of JSON) it repeats the
 * same call on the backup host, then keeps using the backup for a few minutes so a broken
 * host is not retried on every click. Other 4xx answers (bad input, no sign-in) are real
 * answers and are returned as they are.
 *
 * This must run in the browser: when the Worker is down (Cloudflare error 1102, an outage)
 * there is no server code left to forward the request.
 */
(() => {
	const script = document.currentScript;
	const origin = window.location.origin;
	const primary = (script?.dataset.apiBase || `${origin}/api`).replace(/\/+$/, "");
	const backup = (script?.dataset.fallbackBase || "").replace(/\/+$/, "");
	const STICKY_MS = 5 * 60 * 1000;
	const TIMEOUT_MS = 15000;
	const STORE_KEY = "arena_api_backup_until";

	function readUntil() {
		try {
			return Number(sessionStorage.getItem(STORE_KEY)) || 0;
		} catch {
			return 0;
		}
	}

	function writeUntil(value) {
		try {
			if (value) sessionStorage.setItem(STORE_KEY, String(value));
			else sessionStorage.removeItem(STORE_KEY);
		} catch {
			/* storage unavailable */
		}
	}

	// Where a call goes on each host: the part after the API base is the same on both.
	function tailOf(url) {
		for (const base of [primary, backup, `${origin}/api`]) {
			if (base && url.startsWith(`${base}/`)) return url.slice(base.length);
		}
		return null;
	}

	async function attempt(url, init) {
		const controller = new AbortController();
		const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
		try {
			const response = await fetch(url, { ...init, signal: controller.signal });
			// A JSON API never answers 2xx/4xx with a web page; a CDN error page does.
			const type = response.headers.get("content-type") || "";
			const brokenPage = response.status >= 500 || response.status === 429 || (type.includes("text/html") && !response.ok);
			return { response, failed: brokenPage };
		} catch (error) {
			return { error, failed: true };
		} finally {
			clearTimeout(timer);
		}
	}

	/** Same as fetch(url, init); resolves to { response, host, fellBack }. Throws only when every host failed. */
	async function request(url, init = {}) {
		const target = url.startsWith("/") ? origin + url : String(url);
		const tail = backup ? tailOf(target) : null;
		if (tail === null) {
			return { response: await fetch(target, init), host: new URL(target).host, fellBack: false };
		}
		const primaryUrl = primary + tail;
		const backupUrl = backup + tail;
		const done = (result, address, fellBack) => ({ response: result.response, host: new URL(address).host, fellBack });

		if (Date.now() < readUntil()) {
			const sticky = await attempt(backupUrl, init);
			if (!sticky.failed) return done(sticky, backupUrl, true);
			writeUntil(0);
		}
		const first = await attempt(primaryUrl, init);
		if (!first.failed) return done(first, primaryUrl, false);

		const second = await attempt(backupUrl, init);
		if (!second.failed) {
			writeUntil(Date.now() + STICKY_MS);
			return done(second, backupUrl, true);
		}
		// Both failed: show what the host the reader chose said.
		if (first.response) return done(first, primaryUrl, false);
		if (second.response) return done(second, backupUrl, true);
		throw first.error || second.error;
	}

	window.ArenaApi = { request, primary, backup };
})();
