/* Home page: fill the "highest win rates" table from the live API. */
(() => {
	const table = document.querySelector("[data-live-rank]");
	const body = table?.querySelector("[data-live-rank-body]");
	if (!table || !body) return;

	const base = table.dataset.apiBase || `${window.location.origin}/api`;
	const url = `${base}/heroes/rank?days=7&rank=all&sort_field=win_rate&sort_order=desc&size=5&index=1`;
	const percent = (value) => (typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "-");

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

	fetch(url, { headers: { accept: "application/json" } })
		.then((response) => (response.ok ? response.json() : Promise.reject(response.status)))
		.then((payload) => {
			const records = payload?.data?.records;
			if (!Array.isArray(records) || !records.length) {
				showMessage("No ranking data came back. Try the request in the playground.");
				return;
			}
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

				row.appendChild(cell(percent(data.main_hero_win_rate), "num win"));
				row.appendChild(cell(percent(data.main_hero_appearance_rate), "num"));
				row.appendChild(cell(percent(data.main_hero_ban_rate), "num"));
				return row;
			});
			body.replaceChildren(...rows);
		})
		.catch(() => showMessage("Could not reach the API just now. The request below still works in the playground."));
})();
