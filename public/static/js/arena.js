/*
 * Rone Arena: site-wide behaviour shared by every page.
 *   - theme toggle (system / light / dark, remembered per browser)
 *   - mobile navigation drawer
 *   - player session: JWT cache, navbar state, sign-in / sign-out modals
 *   - donate modal and copy-to-clipboard buttons
 * Exposes window.ArenaWebAuth for page scripts (the playground).
 */
(() => {
	const AUTH_KEY = "arena_user_auth";
	const USER_INFO_KEY = "arena_user_info";
	const THEME_KEY = "arena_theme";
	const AUTH_TTL_MS = 24 * 60 * 60 * 1000;
	const FALLBACK_AVATAR =
		"data:image/svg+xml;utf8," +
		encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><rect width="40" height="40" fill="#8a8f9a"/><circle cx="20" cy="16" r="7" fill="#fff" opacity=".85"/><path d="M6 38a14 14 0 0 1 28 0" fill="#fff" opacity=".85"/></svg>');

	const $ = (id) => document.getElementById(id);

	const storage = {
		get(key) {
			try {
				return localStorage.getItem(key);
			} catch {
				return null;
			}
		},
		set(key, value) {
			try {
				localStorage.setItem(key, value);
			} catch {
				/* storage unavailable */
			}
		},
		remove(key) {
			try {
				localStorage.removeItem(key);
			} catch {
				/* storage unavailable */
			}
		},
	};

	// One-time migration from the pre-rebrand storage keys so signed-in
	// visitors are not logged out by the rename. Safe to delete later.
	for (const [legacyKey, currentKey] of [["mlbb_user_auth", AUTH_KEY], ["mlbb_user_info", USER_INFO_KEY]]) {
		const legacyValue = storage.get(legacyKey);
		if (legacyValue !== null && storage.get(currentKey) === null) {
			storage.set(currentKey, legacyValue);
		}
		if (legacyValue !== null) {
			storage.remove(legacyKey);
		}
	}

	function parseJson(value) {
		try {
			return JSON.parse(value);
		} catch {
			return null;
		}
	}

	async function copyText(value) {
		const text = String(value || "");
		if (!text) {
			return false;
		}
		try {
			if (navigator.clipboard && window.isSecureContext) {
				await navigator.clipboard.writeText(text);
				return true;
			}
		} catch {
			/* fall back below */
		}
		const temp = document.createElement("textarea");
		temp.value = text;
		temp.style.position = "fixed";
		temp.style.left = "-9999px";
		document.body.appendChild(temp);
		temp.select();
		const success = document.execCommand("copy");
		temp.remove();
		return success;
	}

	/** Swap a button's label briefly (e.g. "Copied"), then restore it. */
	function flashLabel(button, text, ms = 1400) {
		const label = button.querySelector("[data-label]") || button;
		if (!label.dataset.original) {
			label.dataset.original = label.textContent;
		}
		label.textContent = text;
		clearTimeout(label.__flashTimer);
		label.__flashTimer = setTimeout(() => {
			label.textContent = label.dataset.original;
		}, ms);
	}

	// ------------------------------------------------------------------ theme

	function currentTheme() {
		const explicit = document.documentElement.dataset.theme;
		if (explicit === "light" || explicit === "dark") {
			return explicit;
		}
		return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
	}

	// The masthead switch (tablet and up) and the drawer entry (phones).
	document.querySelectorAll("[data-theme-toggle]").forEach((toggle) => {
		toggle.addEventListener("click", () => {
			const next = currentTheme() === "dark" ? "light" : "dark";
			document.documentElement.dataset.theme = next;
			storage.set(THEME_KEY, next);
		});
	});

	// ------------------------------------------------------------ nav drawer

	const navToggle = $("nav-toggle");
	const navDrawer = $("nav-drawer");
	navToggle?.addEventListener("click", () => {
		const open = navDrawer?.classList.toggle("hidden") === false;
		navToggle.setAttribute("aria-expanded", String(open));
		navToggle.textContent = open ? "Close" : "Menu";
	});

	// ------------------------------------------------------- article contents

	// Marks the section being read in every contents list, and folds the
	// inline list again after a jump so the text is not pushed down.
	const tocLinks = Array.from(document.querySelectorAll("[data-toc-link]"));
	if (tocLinks.length && "IntersectionObserver" in window) {
		const sections = [...new Set(tocLinks.map((link) => link.hash.slice(1)))]
			.map((id) => document.getElementById(id))
			.filter(Boolean);
		const mark = (id) => {
			tocLinks.forEach((link) => {
				if (link.hash === `#${id}`) link.setAttribute("aria-current", "true");
				else link.removeAttribute("aria-current");
			});
		};
		const observer = new IntersectionObserver(
			(entries) => {
				const visible = entries.filter((entry) => entry.isIntersecting);
				if (visible.length) mark(visible[0].target.id);
			},
			{ rootMargin: "-20% 0px -70% 0px" },
		);
		sections.forEach((section) => observer.observe(section));
		tocLinks.forEach((link) =>
			link.addEventListener("click", () => {
				link.closest("details")?.removeAttribute("open");
			}),
		);
	}

	// ---------------------------------------------------------------- session

	function clearStoredSession() {
		storage.remove(AUTH_KEY);
		storage.remove(USER_INFO_KEY);
	}

	function readAuth() {
		const parsed = parseJson(storage.get(AUTH_KEY));
		if (!parsed) {
			if (storage.get(AUTH_KEY) !== null) {
				clearStoredSession();
			}
			return null;
		}
		if (typeof parsed.jwt !== "string" || typeof parsed.expiresAt !== "number" || Date.now() > parsed.expiresAt) {
			clearStoredSession();
			return null;
		}
		return parsed;
	}

	function readUserInfo(auth) {
		if (!auth) {
			return null;
		}
		const parsed = parseJson(storage.get(USER_INFO_KEY));
		if (!parsed || parsed.expiresAt !== auth.expiresAt || !parsed.data || typeof parsed.data !== "object") {
			storage.remove(USER_INFO_KEY);
			return null;
		}
		return parsed.data;
	}

	function renderNavbarState() {
		const status = $("jwt-status");
		const signInButton = $("user-signin-button");
		const trigger = $("user-menu-trigger");
		const panel = $("user-menu-panel");
		const avatar = $("user-avatar");
		const name = $("user-name");
		const country = $("user-country-inline");
		const roleZone = $("user-role-zone");
		if (!status) {
			return;
		}

		const auth = readAuth();
		if (!auth) {
			status.lastChild.textContent = "Not Signed In";
			signInButton?.classList.remove("hidden");
			trigger?.classList.add("hidden");
			panel?.classList.add("hidden");
			if (roleZone) roleZone.textContent = "-";
			return;
		}

		const remaining = auth.expiresAt - Date.now();
		const hours = Math.floor(remaining / (1000 * 60 * 60));
		const minutes = Math.floor((remaining / (1000 * 60)) % 60);
		status.lastChild.textContent = `Signed in, ${hours}h ${minutes}m left on this JWT`;
		signInButton?.classList.add("hidden");
		trigger?.classList.remove("hidden");

		const info = readUserInfo(auth);
		const displayName = typeof info?.name === "string" && info.name.trim() ? info.name.trim() : "Player";
		const regCountry = typeof info?.reg_country === "string" && info.reg_country.trim() ? info.reg_country.trim() : "";
		const roleId = info?.roleId ?? info?.roleid;
		const zoneId = info?.zoneId ?? info?.zoneid;

		if (avatar) {
			avatar.src = typeof info?.avatar === "string" && info.avatar ? info.avatar : FALLBACK_AVATAR;
			avatar.alt = `${displayName} avatar`;
		}
		if (name) name.textContent = displayName;
		if (country) country.textContent = regCountry ? ` (${regCountry})` : "";
		if (roleZone) {
			roleZone.textContent = roleId != null ? `${roleId} (${zoneId ?? "-"})` : "-";
		}
	}

	function writeAuth(jwt) {
		if (typeof jwt !== "string" || !jwt.trim()) {
			return;
		}
		storage.remove(USER_INFO_KEY);
		storage.set(AUTH_KEY, JSON.stringify({ jwt, expiresAt: Date.now() + AUTH_TTL_MS }));
		renderNavbarState();
	}

	function writeUserInfo(userInfo, expiresAt) {
		if (!userInfo || typeof userInfo !== "object" || typeof expiresAt !== "number") {
			return;
		}
		storage.set(USER_INFO_KEY, JSON.stringify({ data: userInfo, expiresAt }));
		renderNavbarState();
	}

	function clearAuth() {
		clearStoredSession();
		renderNavbarState();
	}

	async function fetchAndCacheUserInfo() {
		const auth = readAuth();
		if (!auth) {
			return;
		}
		try {
			const response = await fetch("/api/user/info", {
				headers: { accept: "application/json", Authorization: `Bearer ${auth.jwt}` },
			});
			if (!response.ok) {
				return;
			}
			const parsed = parseJson(await response.text());
			if (parsed?.data && typeof parsed.data === "object") {
				writeUserInfo(parsed.data, auth.expiresAt);
			}
		} catch {
			// Keep the session even if profile hydration fails.
		}
	}

	window.ArenaWebAuth = { readAuth, readUserInfo, writeAuth, writeUserInfo, clearAuth, renderNavbarState, copyText, flashLabel };

	// ----------------------------------------------------------------- modals

	const modals = {
		signin: $("signin-modal"),
		signout: $("signout-confirm-modal"),
		donate: $("donate-modal"),
	};

	function openModal(modal, focusTarget) {
		if (!modal) return;
		modal.classList.remove("hidden");
		(focusTarget || modal.querySelector("button, input"))?.focus();
	}

	function closeModal(modal) {
		modal?.classList.add("hidden");
	}

	Object.values(modals).forEach((modal) => {
		modal?.addEventListener("click", (event) => {
			if (event.target === modal) {
				if (modal === modals.signin) closeSignIn();
				else closeModal(modal);
			}
		});
	});

	// Donate
	$("donate-modal-trigger")?.addEventListener("click", () => openModal(modals.donate, $("donate-close")));
	document.querySelectorAll("[data-open-donate]").forEach((button) => {
		button.addEventListener("click", () => openModal(modals.donate, $("donate-close")));
	});
	$("donate-close")?.addEventListener("click", () => closeModal(modals.donate));

	// Sign in
	const roleInput = $("signin-role-id");
	const zoneInput = $("signin-zone-id");
	const vcInput = $("signin-vc");
	const sendVcButton = $("signin-send-vc");
	const loginButton = $("signin-login");
	const loginBlock = $("signin-login-block");
	const statusLine = $("signin-status");

	function setSignInStatus(text, variant = "default") {
		if (!statusLine) return;
		statusLine.dataset.variant = variant;
		statusLine.textContent = text;
	}

	function toPositiveInt(value) {
		const parsed = Number.parseInt(String(value || "").trim(), 10);
		return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
	}

	function signInPayload() {
		const roleId = toPositiveInt(roleInput?.value);
		const zoneId = toPositiveInt(zoneInput?.value);
		return roleId && zoneId ? { role_id: roleId, zone_id: zoneId } : null;
	}

	// Step 2 (enter the code) stays greyed out until a code has been sent.
	function setCodeStepReady(ready) {
		loginBlock?.classList.toggle("is-waiting", !ready);
		if (vcInput) vcInput.disabled = !ready;
		if (loginButton) loginButton.disabled = !ready;
	}

	function openSignIn() {
		if (!modals.signin) {
			window.location.href = "/web/user/auth/send-vc";
			return;
		}
		setCodeStepReady(false);
		setSignInStatus("Fill Role ID and Zone ID, then click Send VC.");
		openModal(modals.signin, roleInput);
	}

	function closeSignIn() {
		closeModal(modals.signin);
		setCodeStepReady(false);
		if (vcInput) vcInput.value = "";
		setSignInStatus("");
	}

	async function postJson(url, body) {
		const response = await fetch(url, {
			method: "POST",
			headers: { accept: "application/json", "content-type": "application/json" },
			body: JSON.stringify(body),
		});
		const parsed = parseJson(await response.text());
		const code = typeof parsed?.code === "number" ? parsed.code : response.status;
		const message = parsed?.msg || parsed?.message || "No message";
		return { response, parsed, code, message };
	}

	$("user-signin-button")?.addEventListener("click", openSignIn);
	$("signin-cancel")?.addEventListener("click", closeSignIn);

	sendVcButton?.addEventListener("click", async () => {
		const payload = signInPayload();
		if (!payload) {
			setSignInStatus("Role ID and Zone ID must be valid numbers.", "warn");
			return;
		}
		sendVcButton.disabled = true;
		sendVcButton.textContent = "Sending...";
		try {
			const { response, code, message } = await postJson("/api/user/auth/send-vc", payload);
			if (!response.ok || code !== 0) {
				setSignInStatus(`Send VC failed (code: ${code}) - ${message}`, "error");
				return;
			}
			setCodeStepReady(true);
			setSignInStatus("Code sent. Check your in-game mail for the verification code.", "info");
			vcInput?.focus();
		} catch {
			setSignInStatus("Failed to send VC. Please try again.", "error");
		} finally {
			sendVcButton.disabled = false;
			sendVcButton.textContent = "Send VC";
		}
	});

	loginButton?.addEventListener("click", async () => {
		const payload = signInPayload();
		const vc = toPositiveInt(vcInput?.value);
		if (!payload || !vc) {
			setSignInStatus("Role ID, Zone ID, and VC are required for login.", "warn");
			return;
		}
		loginButton.disabled = true;
		loginButton.textContent = "Signing in...";
		try {
			const { response, parsed, code, message } = await postJson("/api/user/auth/login", { ...payload, vc });
			if (!response.ok || code !== 0 || typeof parsed?.data?.jwt !== "string") {
				setSignInStatus(`Sign in failed (code: ${code}) - ${message}`, "error");
				return;
			}
			writeAuth(parsed.data.jwt);
			await fetchAndCacheUserInfo();
			closeSignIn();
		} catch {
			setSignInStatus("Sign in request failed. Please try again.", "error");
		} finally {
			loginButton.disabled = false;
			loginButton.textContent = "Sign In";
		}
	});

	// Sign out
	const signOutConfirm = $("signout-confirm");
	$("signout-cancel")?.addEventListener("click", () => closeModal(modals.signout));
	signOutConfirm?.addEventListener("click", async () => {
		signOutConfirm.disabled = true;
		signOutConfirm.textContent = "Signing out...";
		const auth = readAuth();
		if (auth) {
			try {
				await fetch("/api/user/auth/logout", {
					method: "POST",
					headers: { accept: "application/json", Authorization: `Bearer ${auth.jwt}` },
				});
			} catch {
				// Clear the local session even if the upstream logout fails.
			}
		}
		clearAuth();
		closeModal(modals.signout);
		signOutConfirm.textContent = "Sign Out";
		signOutConfirm.disabled = false;
	});

	// ------------------------------------------------------------- user menu

	const menuTrigger = $("user-menu-trigger");
	const menuPanel = $("user-menu-panel");

	function setMenuOpen(open) {
		menuPanel?.classList.toggle("hidden", !open);
		menuTrigger?.setAttribute("aria-expanded", String(open));
	}

	menuTrigger?.addEventListener("click", (event) => {
		event.stopPropagation();
		setMenuOpen(menuPanel?.classList.contains("hidden"));
	});

	document.addEventListener("click", (event) => {
		if (!menuPanel || menuPanel.classList.contains("hidden")) return;
		if (menuPanel.contains(event.target) || menuTrigger?.contains(event.target)) return;
		setMenuOpen(false);
	});

	$("jwt-auth-action")?.addEventListener("click", () => {
		setMenuOpen(false);
		if (readAuth()) {
			openModal(modals.signout, signOutConfirm);
		} else {
			openSignIn();
		}
	});

	const copyJwt = $("jwt-copy-action");
	copyJwt?.addEventListener("click", async () => {
		const auth = readAuth();
		if (!auth) {
			flashLabel(copyJwt, "No JWT", 3000);
			return;
		}
		flashLabel(copyJwt, (await copyText(auth.jwt)) ? "Copied" : "Copy failed", 3000);
	});

	document.addEventListener("keydown", (event) => {
		if (event.key !== "Escape") return;
		setMenuOpen(false);
		if (modals.signin && !modals.signin.classList.contains("hidden")) closeSignIn();
		closeModal(modals.donate);
		closeModal(modals.signout);
	});

	// ------------------------------------------------------------- copy buttons

	document.querySelectorAll("[data-copy-command]").forEach((button) => {
		button.addEventListener("click", async () => {
			const ok = await copyText(button.getAttribute("data-copy-command"));
			flashLabel(button, ok ? "Copied" : "Copy failed");
		});
	});

	// Copies the text of another element, for blocks too long to repeat in an attribute.
	document.querySelectorAll("[data-copy-from]").forEach((button) => {
		button.addEventListener("click", async () => {
			const source = $(button.getAttribute("data-copy-from"));
			const ok = source ? await copyText(source.textContent) : false;
			flashLabel(button, ok ? "Copied" : "Copy failed");
		});
	});

	renderNavbarState();
})();
