/*
 * Every API call the site's scripts make goes through ArenaApi.request(url, init).
 *
 * The same app runs on two public hosts (data-api-hosts). The reader picks one with the base
 * URL switch (FastAPI Cloud by default, remembered in localStorage); every call is sent there,
 * whichever host the script built its URL for. When that fails in a way another host could
 * fix (network error, timeout, 5xx, 429, or an HTML error page instead of JSON) it repeats the
 * same call on the other host, then keeps using it for a few minutes so a broken host is not
 * retried on every click. Other 4xx answers (bad input, no sign-in) are real answers and are
 * returned as they are. Without data-api-hosts (DEBUG) calls go to data-api-base only.
 *
 * This must run in the browser: when the Worker is down (Cloudflare error 1102, an outage)
 * there is no server code left to forward the request.
 */
(() => {
	const script = document.currentScript;
	const origin = window.location.origin;
	const trim = (base) => String(base || "").replace(/\/+$/, "");
	const local = trim(script?.dataset.apiBase || `${origin}/api`);
	const STICKY_MS = 5 * 60 * 1000;
	const TIMEOUT_MS = 15000;
	const STORE_KEY = "arena_api_backup_until";
	const HOST_KEY = "arena_api_host";

	// [{ key, label, base }], the preferred host first.
	let hosts = [];
	try {
		hosts = JSON.parse(script?.dataset.apiHosts || "[]").map(([key, label, base]) => ({ key, label, base: trim(base) }));
	} catch {
		hosts = [];
	}

	let chosen = null;
	let primary = local;
	let backup = "";

	function choose(key) {
		chosen = hosts.find((host) => host.key === key) || hosts[0] || null;
		primary = chosen ? chosen.base : local;
		backup = chosen ? hosts.find((host) => host !== chosen)?.base || "" : "";
	}

	function readHost() {
		try {
			return localStorage.getItem(HOST_KEY);
		} catch {
			return null;
		}
	}

	/** Switch every later call to another host and tell the page (the "arena:api-host" event). */
	function setHost(key) {
		choose(key);
		writeUntil(0);
		try {
			if (chosen) localStorage.setItem(HOST_KEY, chosen.key);
		} catch {
			/* storage unavailable */
		}
		window.dispatchEvent(new CustomEvent("arena:api-host", { detail: { key: chosen?.key || null, base: primary } }));
	}

	choose(readHost());

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

	// Where a call goes on each host: the part after the API base is the same on all of them.
	function tailOf(url) {
		for (const base of [primary, backup, local, `${origin}/api`, ...hosts.map((host) => host.base)]) {
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
		const tail = tailOf(target);
		const primaryUrl = tail === null ? target : primary + tail;
		if (tail === null || !backup) {
			return { response: await fetch(primaryUrl, init), host: new URL(primaryUrl).host, fellBack: false };
		}
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

	window.ArenaApi = {
		request,
		setHost,
		hosts,
		get hostKey() {
			return chosen?.key || null;
		},
		get primary() {
			return primary;
		},
		get backup() {
			return backup;
		},
	};
})();
