/*
 * Rone Arena playground: turns every endpoint card into a working request form.
 *   - builds the URL from path/query fields and the JSON body
 *   - sends it to the API base (data-api-base on this script tag)
 *   - renders the response as readable tables, raw JSON, and code snippets
 */
(() => {
	const API_BASE = document.currentScript?.dataset.apiBase || `${window.location.origin}/api`;
	const formValidationTimers = new WeakMap();
	const auth = () => window.ArenaWebAuth || null;

	function parseJson(text) {
		try {
			return JSON.parse(text);
		} catch {
			return null;
		}
	}

	function el(tag, className, text) {
		const node = document.createElement(tag);
		if (className) node.className = className;
		if (text !== undefined) node.textContent = text;
		return node;
	}

	// ------------------------------------------------------------ session sync

	function hasCoreUserInfo(userInfo) {
		return Boolean(
			userInfo &&
				typeof userInfo === "object" &&
				typeof userInfo.avatar === "string" &&
				userInfo.avatar.trim() &&
				typeof userInfo.name === "string" &&
				userInfo.name.trim()
		);
	}

	async function hydrateUserInfoIfMissing() {
		const session = auth()?.readAuth?.();
		if (!session || hasCoreUserInfo(auth().readUserInfo?.(session))) {
			return;
		}
		try {
			const response = await fetch("/api/user/info", {
				headers: { accept: "application/json", Authorization: `Bearer ${session.jwt}` },
			});
			if (!response.ok) return;
			const parsed = parseJson(await response.text());
			if (hasCoreUserInfo(parsed?.data)) {
				auth().writeUserInfo?.(parsed.data, session.expiresAt);
			}
		} catch {
			// Silent background hydration.
		}
	}

	// ---------------------------------------------------------- form reading

	function getValuesFromInput(input) {
		if (input.dataset.paramKind === "checkbox-group") {
			return Array.from(input.querySelectorAll('input[data-param-choice="true"]:checked'))
				.map((checkbox) => checkbox.value)
				.filter(Boolean);
		}
		if (input.tagName === "SELECT") {
			return input.value ? [input.value] : [];
		}
		const rawValue = input.value.trim();
		if (!rawValue) return [];
		if (input.dataset.array === "true") {
			return rawValue.split(",").map((part) => part.trim()).filter(Boolean);
		}
		return [rawValue];
	}

	// ---------------------------------------------------------------- snippets

	function shellQuote(value) {
		return `'${String(value).replaceAll("'", "'\\''")}'`;
	}

	function buildCurl(method, url, headers, requestBody) {
		const lines = [`curl -X ${shellQuote(method)} \\`, `    ${shellQuote(url)} \\`];
		Object.entries(headers).forEach(([key, value]) => {
			lines.push(`    -H ${shellQuote(`${key}: ${value}`)} \\`);
		});
		if (requestBody) {
			lines.push(`    -d ${shellQuote(requestBody)}`);
		} else {
			lines[lines.length - 1] = lines[lines.length - 1].replace(/ \\$/, "");
		}
		return lines.join("\n");
	}

	function emptySnippets() {
		return { curl: "", python: "", javascript: "", go: "", node: "", php: "", java: "", csharp: "" };
	}

	function buildLanguageSnippets(method, url, headers, requestBody) {
		const headerEntries = Object.entries(headers);
		const hasBody = Boolean(requestBody);
		const jsonHeaders = JSON.stringify(headers, null, 4);
		const parsedBody = requestBody ? parseJson(requestBody) : null;
		const pyJsonBody = parsedBody ? JSON.stringify(parsedBody, null, 4) : "None";
		const jsBody = hasBody ? (parsedBody ?? requestBody) : null;
		const goHeaderLines = headerEntries.map(([key, value]) => `    req.Header.Set(${JSON.stringify(key)}, ${JSON.stringify(value)})`).join("\n");
		const phpHeaders = headerEntries.map(([key, value]) => `'${`${key}: ${value}`.replaceAll("'", "\\'")}'`).join(",\n        ");

		return {
			curl: buildCurl(method, url, headers, requestBody),
			python: `import requests\n\nurl = ${JSON.stringify(url)}\nheaders = ${jsonHeaders}\n${hasBody ? `payload = ${pyJsonBody}` : "payload = None"}\n\nresponse = requests.request(${JSON.stringify(method)}, url, headers=headers${hasBody ? ", json=payload" : ""})\nprint(response.json())`,
			javascript: `const response = await fetch(${JSON.stringify(url)}, {\n    method: ${JSON.stringify(method)},\n    headers: ${jsonHeaders},${hasBody ? `\n    body: ${JSON.stringify(requestBody)}` : ""}\n});\n\nconst data = await response.json();\nconsole.log(data);`,
			go: `package main\n\nimport (\n    "fmt"\n    "io"\n    "net/http"\n    "strings"\n)\n\nfunc main() {\n    client := &http.Client{}\n    body := strings.NewReader(${JSON.stringify(requestBody || "")})\n    req, err := http.NewRequest(${JSON.stringify(method)}, ${JSON.stringify(url)}, body)\n    if err != nil {\n        panic(err)\n    }\n\n${goHeaderLines || "    // No headers required"}\n\n    res, err := client.Do(req)\n    if err != nil {\n        panic(err)\n    }\n    defer res.Body.Close()\n\n    raw, _ := io.ReadAll(res.Body)\n    fmt.Println(string(raw))\n}`,
			node: `const axios = require("axios");\n\n(async () => {\n    const response = await axios({\n        method: ${JSON.stringify(method.toLowerCase())},\n        url: ${JSON.stringify(url)},\n        headers: ${jsonHeaders},${hasBody ? `\n        data: ${JSON.stringify(jsBody, null, 4)}` : ""}\n    });\n\n    console.log(response.data);\n})();`,
			php: `<?php\n$ch = curl_init();\n\ncurl_setopt_array($ch, [\n    CURLOPT_URL => ${JSON.stringify(url)},\n    CURLOPT_RETURNTRANSFER => true,\n    CURLOPT_CUSTOMREQUEST => ${JSON.stringify(method)},\n    CURLOPT_HTTPHEADER => [\n        ${phpHeaders}\n    ],${hasBody ? `\n    CURLOPT_POSTFIELDS => ${JSON.stringify(requestBody)},` : ""}\n]);\n\n$response = curl_exec($ch);\ncurl_close($ch);\n\necho $response;`,
			java: `HttpRequest request = HttpRequest.newBuilder()\n    .uri(URI.create(${JSON.stringify(url)}))\n    .method(${JSON.stringify(method)}, ${hasBody ? `HttpRequest.BodyPublishers.ofString(${JSON.stringify(requestBody)})` : "HttpRequest.BodyPublishers.noBody()"})\n${headerEntries.map(([key, value]) => `    .header(${JSON.stringify(key)}, ${JSON.stringify(value)})`).join("\n")}\n    .build();\n\nHttpClient client = HttpClient.newHttpClient();\nHttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());\nSystem.out.println(response.body());`,
			csharp: `using System.Net.Http;\nusing System.Text;\n\nvar client = new HttpClient();\nvar request = new HttpRequestMessage(new HttpMethod(${JSON.stringify(method)}), ${JSON.stringify(url)});\n${headerEntries.map(([key, value]) => `request.Headers.TryAddWithoutValidation(${JSON.stringify(key)}, ${JSON.stringify(value)});`).join("\n")}\n${hasBody ? `request.Content = new StringContent(${JSON.stringify(requestBody)}, Encoding.UTF8, "application/json");\n` : ""}\nvar response = await client.SendAsync(request);\nvar content = await response.Content.ReadAsStringAsync();\nConsole.WriteLine(content);`,
		};
	}

	// ------------------------------------------------------- readable values

	function looksLikeUrl(value) {
		return typeof value === "string" && /^https?:\/\//i.test(value.trim());
	}

	function looksLikeImageUrl(value) {
		return looksLikeUrl(value) && /\.(png|jpe?g|gif|webp|svg|bmp|avif)(\?.*)?$/i.test(value.trim());
	}

	function normalizeSafeColor(value) {
		const trimmed = String(value || "").trim();
		if (/^#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$/.test(trimmed)) {
			return trimmed.startsWith("#") ? trimmed : `#${trimmed}`;
		}
		if (/^(black|white|red|green|blue|yellow|cyan|magenta|gray|grey|orange)$/i.test(trimmed)) {
			return trimmed.toLowerCase();
		}
		return null;
	}

	/** Game text carries <font color> and <br>; keep those, flatten every other tag to text. */
	function sanitizeInlineMarkup(value) {
		const template = document.createElement("template");
		template.innerHTML = value;
		const output = document.createDocumentFragment();

		function appendSanitized(source, target) {
			source.childNodes.forEach((node) => {
				if (node.nodeType === Node.TEXT_NODE) {
					target.appendChild(document.createTextNode(node.textContent || ""));
					return;
				}
				if (node.nodeType !== Node.ELEMENT_NODE) return;
				const tag = node.tagName.toLowerCase();
				if (tag === "br") {
					target.appendChild(document.createElement("br"));
					return;
				}
				if (tag === "font") {
					const span = document.createElement("span");
					const color = normalizeSafeColor(node.getAttribute("color"));
					if (color) span.style.color = color;
					appendSanitized(node, span);
					target.appendChild(span);
					return;
				}
				appendSanitized(node, target);
			});
		}

		appendSanitized(template.content, output);
		return output;
	}

	function createPrimitiveNode(value) {
		if (value === null || value === undefined) {
			return el("span", "rv-null", "null");
		}
		if (typeof value === "boolean") {
			return el("span", `rv-bool rv-bool--${value}`, String(value));
		}
		if (typeof value === "number") {
			return el("span", "rv-num", String(value));
		}
		if (typeof value === "string" && looksLikeUrl(value)) {
			const link = el("a", looksLikeImageUrl(value) ? "" : "rv-link");
			link.href = value;
			link.target = "_blank";
			link.rel = "noreferrer noopener";
			if (looksLikeImageUrl(value)) {
				const preview = el("img", "rv-img");
				preview.src = value;
				preview.alt = "Image preview";
				preview.loading = "lazy";
				link.title = value;
				link.appendChild(preview);
			} else {
				link.textContent = value;
			}
			return link;
		}
		const text = el("span");
		text.appendChild(sanitizeInlineMarkup(String(value)));
		return text;
	}

	function table(rows, headers) {
		const tableNode = el("table", "rt");
		if (headers) {
			const head = el("thead");
			const headRow = el("tr");
			headers.forEach((header) => headRow.appendChild(el("th", "", header)));
			head.appendChild(headRow);
			tableNode.appendChild(head);
		}
		const body = el("tbody");
		rows.forEach((row) => body.appendChild(row));
		tableNode.appendChild(body);
		return tableNode;
	}

	function keyedRow(key, value, mode) {
		const row = el("tr");
		row.appendChild(el("td", "rt-key", key));
		const cell = el("td");
		cell.appendChild(renderReadableValueAsNode(value, mode));
		row.appendChild(cell);
		return row;
	}

	function createObjectTableKeyValue(value) {
		return table(Object.entries(value).map(([key, nested]) => keyedRow(key, nested, "key-value")));
	}

	function createObjectTableHeader(value) {
		const row = el("tr");
		Object.values(value).forEach((nested) => {
			const cell = el("td");
			cell.appendChild(renderReadableValueAsNode(nested, "header"));
			row.appendChild(cell);
		});
		return table([row], Object.keys(value));
	}

	function createArrayTableKeyValue(value) {
		return table(value.map((item, index) => keyedRow(`#${index}`, item, "key-value")));
	}

	function createArrayTableHeader(value) {
		const everyItemObject = value.every((item) => item && typeof item === "object" && !Array.isArray(item));
		if (!everyItemObject) {
			return table(value.map((item, index) => keyedRow(`#${index}`, item, "header")), ["index", "value"]);
		}
		const keys = [];
		value.forEach((item) => Object.keys(item).forEach((key) => keys.includes(key) || keys.push(key)));
		const rows = value.map((item) => {
			const row = el("tr");
			keys.forEach((key) => {
				const cell = el("td");
				cell.appendChild(renderReadableValueAsNode(item[key], "header"));
				row.appendChild(cell);
			});
			return row;
		});
		return table(rows, keys);
	}

	function renderReadableValueAsNode(value, mode = "key-value") {
		if (Array.isArray(value)) {
			if (!value.length) return el("span", "rv-null", "[]");
			return mode === "header" ? createArrayTableHeader(value) : createArrayTableKeyValue(value);
		}
		if (value && typeof value === "object") {
			if (!Object.keys(value).length) return el("span", "rv-null", "{}");
			return mode === "header" ? createObjectTableHeader(value) : createObjectTableKeyValue(value);
		}
		return createPrimitiveNode(value);
	}

	// Kept for readers of the old API: both names build the readable table.
	const createObjectTable = createObjectTableKeyValue;

	// ---------------------------------------------------------- response panel

	function setReadableModeButtonLabel(button, mode) {
		if (button) button.textContent = mode === "header" ? "View: Key As Header" : "View: Key-Value";
	}

	function renderReadableIntoContainer(container, parsedResponse, mode) {
		if (!container) return;
		container.replaceChildren(
			parsedResponse ? renderReadableValueAsNode(parsedResponse, mode) : el("p", "help", "Response is not JSON.")
		);
	}

	function setActiveResponseTab(wrapper, name) {
		wrapper.querySelectorAll("[data-response-tab]").forEach((tab) => {
			const active = tab.dataset.responseTab === name;
			tab.classList.toggle("is-active", active);
			tab.setAttribute("aria-selected", String(active));
		});
		wrapper.querySelectorAll("[data-response-pane]").forEach((pane) => {
			pane.classList.toggle("hidden", pane.dataset.responsePane !== name);
		});
	}

	function setActiveLanguageSnippet(wrapper, languageKey, snippets) {
		const content = wrapper.querySelector("[data-language-content]");
		if (!content || !snippets) return;
		const resolved = snippets[languageKey] ? languageKey : "curl";
		content.textContent = snippets[resolved] || "No snippet: the request did not reach the API.";
		content.dataset.activeLanguage = resolved;
		wrapper.querySelectorAll("[data-lang-tab]").forEach((button) => {
			button.classList.toggle("is-active", button.dataset.langKey === resolved);
		});
	}

	function statusTone(statusText) {
		const match = /HTTP (\d{3})/.exec(String(statusText));
		if (!match) return "error";
		const code = Number(match[1]);
		return code < 300 ? "ok" : code < 500 ? "warn" : "error";
	}

	function setResponse(form, statusText, responseText, snippets, parsedResponse = null) {
		const wrapper = form.querySelector("[data-response-wrapper]");
		if (!wrapper) return;
		const status = wrapper.querySelector("[data-response-status]");
		const readable = wrapper.querySelector("[data-response-readable]");
		const modeToggle = wrapper.querySelector("[data-readable-mode-toggle]");
		const languageContent = wrapper.querySelector("[data-language-content]");

		status.textContent = statusText;
		status.dataset.tone = statusTone(statusText);
		wrapper.querySelector("[data-response-content]").textContent = responseText;

		const resolvedSnippets = snippets && typeof snippets === "object" ? snippets : emptySnippets();
		languageContent.__snippets = resolvedSnippets;
		setActiveLanguageSnippet(wrapper, languageContent.dataset.activeLanguage || "curl", resolvedSnippets);

		const mode = readable.dataset.mode === "header" ? "header" : "key-value";
		readable.dataset.mode = mode;
		readable.__parsedResponse = parsedResponse;
		setReadableModeButtonLabel(modeToggle, mode);
		renderReadableIntoContainer(readable, parsedResponse, mode);

		if (!parsedResponse) setActiveResponseTab(wrapper, "raw");
		wrapper.classList.remove("hidden");
	}

	// --------------------------------------------------------------- validation

	function clearFormValidationState(form) {
		clearTimeout(formValidationTimers.get(form));
		formValidationTimers.delete(form);
		form.querySelectorAll(".is-invalid").forEach((field) => field.classList.remove("is-invalid"));
		const message = form.querySelector("[data-form-validation-message]");
		if (message) {
			message.classList.add("hidden");
			message.textContent = "";
		}
	}

	function showFormValidationError(form, message, invalidFields = []) {
		clearFormValidationState(form);
		invalidFields.forEach((field) => field instanceof HTMLElement && field.classList.add("is-invalid"));
		invalidFields[0]?.focus?.();
		const node = form.querySelector("[data-form-validation-message]");
		if (node) {
			node.textContent = message;
			node.classList.remove("hidden");
		}
		formValidationTimers.set(form, setTimeout(() => clearFormValidationState(form), 6000));
	}

	// ------------------------------------------------------------------ setup

	function setupDescriptionToggles() {
		document.querySelectorAll("[data-desc-wrapper]").forEach((wrapper) => {
			const content = wrapper.querySelector("[data-desc-content]");
			const button = wrapper.querySelector("[data-desc-toggle]");
			const fade = wrapper.querySelector("[data-desc-fade]");
			if (!content || !button) return;

			const lineHeight = parseFloat(getComputedStyle(content).lineHeight) || 24;
			const collapsedHeight = Math.round(lineHeight * 5);
			if (content.scrollHeight <= collapsedHeight + 8) return;

			const collapse = (collapsed) => {
				content.style.maxHeight = collapsed ? `${collapsedHeight}px` : "none";
				fade?.classList.toggle("hidden", !collapsed);
				button.dataset.expanded = String(!collapsed);
				button.textContent = collapsed ? "Show more" : "Show less";
			};
			collapse(true);
			button.classList.remove("hidden");
			button.addEventListener("click", () => collapse(button.dataset.expanded === "true"));
		});
	}

	function setupResponseExampleToggles() {
		document.querySelectorAll("[data-resp-example-toggle]").forEach((button) => {
			const body = button.closest("[data-resp-example-wrapper]")?.querySelector("[data-resp-example-body]");
			button.addEventListener("click", () => {
				const hidden = body?.classList.toggle("hidden");
				button.setAttribute("aria-expanded", String(!hidden));
			});
		});
	}

	function setupCopyButtons() {
		document.addEventListener("click", async (event) => {
			const button = event.target.closest("[data-copy-btn]");
			const wrapper = button?.closest("[data-response-wrapper]");
			if (!wrapper) return;
			const selector = button.dataset.copyTarget === "language" ? "[data-language-content]" : "[data-response-content]";
			const ok = await auth()?.copyText?.(wrapper.querySelector(selector)?.textContent || "");
			auth()?.flashLabel?.(button, ok ? "Copied" : "Copy failed");
		});
	}

	function setupLanguageTabs() {
		document.addEventListener("click", (event) => {
			const button = event.target.closest("[data-lang-tab]");
			const wrapper = button?.closest("[data-response-wrapper]");
			const snippets = wrapper?.querySelector("[data-language-content]")?.__snippets;
			if (snippets) setActiveLanguageSnippet(wrapper, button.dataset.langKey || "curl", snippets);
		});
	}

	function setupResponseTabs() {
		document.addEventListener("click", (event) => {
			const tab = event.target.closest("[data-response-tab]");
			const wrapper = tab?.closest("[data-response-wrapper]");
			if (wrapper) setActiveResponseTab(wrapper, tab.dataset.responseTab);
		});
	}

	function setupReadableModeToggles() {
		document.addEventListener("click", (event) => {
			const button = event.target.closest("[data-readable-mode-toggle]");
			const readable = button?.closest("[data-response-wrapper]")?.querySelector("[data-response-readable]");
			if (!readable) return;
			const nextMode = readable.dataset.mode === "header" ? "key-value" : "header";
			readable.dataset.mode = nextMode;
			setReadableModeButtonLabel(button, nextMode);
			renderReadableIntoContainer(readable, readable.__parsedResponse ?? null, nextMode);
		});
	}

	function setupEndpointFilter() {
		const input = document.querySelector("[data-endpoint-filter]");
		const list = document.querySelector("[data-endpoint-list]");
		if (!input || !list) return;
		const links = Array.from(list.querySelectorAll("[data-filter-text]"));
		const empty = list.querySelector("[data-endpoint-empty]");
		input.addEventListener("input", () => {
			const query = input.value.trim().toLowerCase();
			let visible = 0;
			links.forEach((link) => {
				const match = !query || link.dataset.filterText.includes(query);
				link.classList.toggle("hidden", !match);
				visible += match ? 1 : 0;
			});
			empty?.classList.toggle("hidden", visible > 0);
		});
	}

	// ----------------------------------------------------------------- submit

	async function submitOperation(form) {
		clearFormValidationState(form);

		const invalidFields = Array.from(form.querySelectorAll(":invalid"));
		if (invalidFields.length) {
			showFormValidationError(form, "Please fill all required fields and fix invalid values.", invalidFields);
			return;
		}

		const method = form.dataset.method || "GET";
		let apiPath = form.dataset.apiPath || "";

		for (const input of form.querySelectorAll('[data-param-in="path"]')) {
			const name = input.dataset.paramName;
			const values = getValuesFromInput(input);
			if (!name || !values.length) {
				showFormValidationError(form, `Please fill required path parameter: ${name || "path"}.`, [input]);
				return;
			}
			apiPath = apiPath.replace(`{${name}}`, encodeURIComponent(values[0]));
		}

		const url = new URL(apiPath, API_BASE);

		for (const input of form.querySelectorAll('[data-param-in="query"]')) {
			const name = input.dataset.paramName;
			if (!name) continue;
			const values = getValuesFromInput(input);
			const required = input.hasAttribute("required") || input.dataset.required === "true";
			if (required && !values.length) {
				showFormValidationError(form, `Please fill required query parameter: ${name}.`, [input]);
				return;
			}
			values.forEach((value) => url.searchParams.append(name, value));
		}

		const headers = { accept: "application/json" };

		if (form.dataset.requiresAuth === "true") {
			const session = auth()?.readAuth?.();
			if (!session) {
				showFormValidationError(form, "Please sign in first to use this endpoint.");
				setResponse(form, "JWT required", "This endpoint requires sign-in. Use Sign In in the navbar; the JWT is cached for 1 day.", emptySnippets());
				return;
			}
			headers.Authorization = `Bearer ${session.jwt}`;
		}

		let requestBody;
		const bodyField = form.querySelector("textarea[data-request-body='true']");
		const rawBody = bodyField?.value.trim();
		if (rawBody) {
			const parsedBody = parseJson(rawBody);
			if (parsedBody === null) {
				showFormValidationError(form, "Request body must be valid JSON.", [bodyField]);
				return;
			}
			requestBody = JSON.stringify(parsedBody);
			headers["content-type"] = "application/json";
		}

		const executeButton = form.querySelector("[data-execute]");
		executeButton?.setAttribute("disabled", "");
		const startedAt = performance.now();

		try {
			const snippets = buildLanguageSnippets(method, url.toString(), headers, requestBody);
			const response = await fetch(url.toString(), {
				method,
				headers,
				body: method === "GET" ? undefined : requestBody,
			});
			const rawText = await response.text();
			const parsed = parseJson(rawText);
			const elapsed = Math.round(performance.now() - startedAt);

			if (apiPath === "/api/user/auth/login" && parsed?.data?.jwt) {
				auth()?.writeAuth?.(parsed.data.jwt);
				void hydrateUserInfoIfMissing();
			}
			if (apiPath === "/api/user/info" && hasCoreUserInfo(parsed?.data)) {
				const session = auth()?.readAuth?.();
				if (session && !hasCoreUserInfo(auth().readUserInfo?.(session))) {
					auth().writeUserInfo?.(parsed.data, session.expiresAt);
				}
			}
			if (apiPath === "/api/user/auth/logout" && response.ok) {
				auth()?.clearAuth?.();
			}

			setResponse(
				form,
				`HTTP ${response.status} · ${elapsed} ms`,
				parsed ? JSON.stringify(parsed, null, 2) : rawText || "(empty response)",
				snippets,
				parsed
			);
		} catch (error) {
			const message = error instanceof Error ? error.message : "Request failed.";
			showFormValidationError(form, message);
			setResponse(form, "Request Error", message, emptySnippets());
		} finally {
			executeButton?.removeAttribute("disabled");
		}
	}

	auth()?.renderNavbarState?.();
	void hydrateUserInfoIfMissing();
	setupDescriptionToggles();
	setupResponseExampleToggles();
	setupCopyButtons();
	setupLanguageTabs();
	setupResponseTabs();
	setupReadableModeToggles();
	setupEndpointFilter();

	document.querySelectorAll(".api-operation-form").forEach((form) => {
		form.querySelectorAll("[data-form-field='true']").forEach((field) => {
			field.addEventListener("input", () => clearFormValidationState(form));
			field.addEventListener("change", () => clearFormValidationState(form));
		});
		form.addEventListener("submit", (event) => {
			event.preventDefault();
			void submitOperation(form);
		});
	});

	window.ArenaPlayground = { buildCurl, buildLanguageSnippets, createObjectTable, looksLikeImageUrl };
})();
