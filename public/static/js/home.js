/*
 * Home page: the live hero meta table and the "first request" exchange.
 * One fetch fills both, so the response shown is the one the table came from.
 * Win / Pick / Ban re-sort by calling the API again (cached per sort).
 * It asks for 10 rows and shows the top 5 heroes that were actually picked.
 */
(() => {
	const table = document.querySelector("[data-live-rank]");
	const body = table?.querySelector("[data-live-rank-body]");
	if (!table || !body) return;

	const base = `${window.location.origin}/api`;
	const sortButtons = Array.from(document.querySelectorAll("[data-rank-sort]"));
	const requestBox = document.querySelector("[data-exchange-request]");
	const responseBox = document.querySelector("[data-exchange-response]");
	const responseNote = document.querySelector("[data-exchange-note]");
	const cache = new Map();
	const percent = (value) => (typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "-");
	const columns = ["win_rate", "pick_rate", "ban_rate"];

	const urlFor = (field) => `${base}/heroes/rank?days=7&rank=all&sort_field=${field}&sort_order=desc&size=10&index=1`;

	function cell(text, className) {
		const td = document.createElement("td");
		if (className) td.className = className;
		td.textContent = text;
		return td;
	}

	function showMessage(text) {
		const row = document.createElement("tr");
		const td = cell(text, "faint");
		td.colSpan = 5;
		row.appendChild(td);
		body.replaceChildren(row);
	}

	function render(field, records) {
		const rows = records.map((record, index) => {
			const data = record.data || {};
			const hero = data.main_hero?.data || {};
			const row = document.createElement("tr");
			row.appendChild(cell(String(index + 1), "rank-no"));

			const heroCell = document.createElement("td");
			const wrap = document.createElement("span");
			wrap.className = "hero-cell";
			if (hero.head) {
				const img = document.createElement("img");
				img.src = hero.head;
				img.alt = "";
				img.loading = "lazy";
				wrap.appendChild(img);
			}
			wrap.appendChild(document.createTextNode(hero.name || `Hero ${data.main_heroid ?? ""}`));
			heroCell.appendChild(wrap);
			row.appendChild(heroCell);

			const values = [data.main_hero_win_rate, data.main_hero_appearance_rate, data.main_hero_ban_rate];
			values.forEach((value, column) => {
				const sorted = columns[column] === field;
				const classes = ["num", column === 0 ? "win" : "", sorted ? "is-sorted" : ""].filter(Boolean).join(" ");
				row.appendChild(cell(percent(value), classes));
			});
			return row;
		});
		body.replaceChildren(...rows);
	}

	function showExchange(field, payload) {
		if (requestBox) requestBox.textContent = `curl "${urlFor(field)}"`;
		if (!responseBox) return;
		const records = payload?.data?.records || [];
		// The full body is long; show the envelope and the first record.
		const excerpt = { ...payload, data: { ...payload.data, records: records.slice(0, 1) } };
		responseBox.textContent = JSON.stringify(excerpt, null, 2);
		if (responseNote) responseNote.textContent = records.length ? `record 1 of ${records.length} shown` : "no records";
	}

	function markSort(field) {
		sortButtons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.rankSort === field)));
		table.querySelectorAll("[data-rank-col]").forEach((th) => th.classList.toggle("is-sorted", th.dataset.rankCol === field));
	}

	async function load(field) {
		markSort(field);
		try {
			if (!cache.has(field)) {
				const response = await fetch(urlFor(field), { headers: { accept: "application/json" } });
				if (!response.ok) throw new Error(String(response.status));
				cache.set(field, await response.json());
			}
			const payload = cache.get(field);
			// Heroes nobody picked this week (unreleased or brand new) have empty
			// rates, so they are skipped rather than shown at 100% or 0%.
			const records = (payload?.data?.records || []).filter((record) => (record.data?.main_hero_appearance_rate || 0) > 0).slice(0, 5);
			if (!records.length) {
				showMessage("No ranking data came back. Try the request in the playground.");
				return;
			}
			render(field, records);
			showExchange(field, payload);
		} catch {
			cache.delete(field);
			showMessage("Could not reach the API just now. The request still works in the playground.");
			if (responseBox) responseBox.textContent = "The request failed. Try again in a moment.";
		}
	}

	sortButtons.forEach((button) => button.addEventListener("click", () => load(button.dataset.rankSort)));
	load("win_rate");
})();
