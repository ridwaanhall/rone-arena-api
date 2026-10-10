/*
 * Standings simulator: edit match results and re-rank the table.
 *
 * All ranking maths happens on the server (POST /api/esports/{league}/standings/simulate and
 * /api/esports/standings/calculate); this script sends the edits, then draws the answer. Calls go
 * through ArenaApi so they retry on the backup host when the main one fails.
 */
(() => {
	const root = document.getElementById("standings-tool");
	if (!root) return;

	const API_BASE = (root.dataset.apiBase || `${window.location.origin}/api`).replace(/\/+$/, "");
	const STORE_KEY = "arena_standings_v1";
	const RESULTS = [
		["", "Not played"],
		["2-0", "2-0"],
		["2-1", "2-1"],
		["1-2", "1-2"],
		["0-2", "0-2"],
	];
	const TIEBREAKS = {
		net_game_win: ["NET", "Separated from a team on the same points by game difference"],
		head_to_head: ["H2H", "Separated by the matches the tied teams played against each other"],
		unresolved: ["TIED", "Level on everything: the league plays a tiebreaker match"],
	};
	const STATUS = {
		clinched: ["Clinched", "tag--win"],
		alive: ["Alive", ""],
		eliminated: ["Eliminated", "tag--loss"],
	};
	const LEAGUE_NAMES = { id: "Indonesia", ph: "Philippines", custom: "Custom league" };

	const $ = (id) => document.getElementById(id);
	const els = {
		tabs: $("mode-tabs"),
		weekTabs: $("week-tabs"),
		matchList: $("match-list"),
		body: $("standings-body"),
		summary: $("table-summary"),
		legend: $("table-legend"),
		status: $("status"),
		eliminated: $("eliminated"),
		teamCount: $("team-count"),
		teamCountField: $("team-count-field"),
		teamNames: $("team-names"),
		teamNamesGrid: $("team-names-grid"),
		reset: $("reset-edits"),
	};

	const state = {
		mode: "id",
		week: null,
		// Edits per mode: key "week|team1|team2" -> { week, team1, team2, score1, score2 } (scores null = cleared).
		edits: { id: {}, ph: {}, custom: {} },
		eliminated: { id: null, ph: null, custom: null },
		custom: { count: 8, names: [] },
		data: null,
	};

	// ------------------------------------------------------------------ storage

	function load() {
		try {
			const saved = JSON.parse(localStorage.getItem(STORE_KEY) || "null");
			if (!saved || typeof saved !== "object") return;
			if (LEAGUE_NAMES[saved.mode]) state.mode = saved.mode;
			for (const key of Object.keys(state.edits)) {
				if (saved.edits?.[key] && typeof saved.edits[key] === "object") state.edits[key] = saved.edits[key];
				const cut = saved.eliminated?.[key];
				state.eliminated[key] = Number.isInteger(cut) ? cut : null;
			}
			const count = Number(saved.custom?.count);
			if (count >= 2 && count <= 20) state.custom.count = count;
			if (Array.isArray(saved.custom?.names)) state.custom.names = saved.custom.names.map(String);
		} catch {
			/* storage unavailable or corrupted: start fresh */
		}
	}

	function save() {
		try {
			localStorage.setItem(
				STORE_KEY,
				JSON.stringify({ mode: state.mode, edits: state.edits, eliminated: state.eliminated, custom: state.custom })
			);
		} catch {
			/* storage unavailable */
		}
	}

	// ---------------------------------------------------------------- requests

	function el(tag, className, text) {
		const node = document.createElement(tag);
		if (className) node.className = className;
		if (text !== undefined) node.textContent = text;
		return node;
	}

	function setStatus(text, variant) {
		els.status.textContent = text || "";
		if (variant) els.status.dataset.variant = variant;
		else delete els.status.dataset.variant;
	}

	function customNames() {
		const names = state.custom.names.slice(0, state.custom.count);
		while (names.length < state.custom.count) names.push(`Team ${String.fromCharCode(65 + names.length)}`);
		return names.map((name, index) => name.trim() || `Team ${String.fromCharCode(65 + index)}`);
	}

	function buildRequest() {
		const results = Object.values(state.edits[state.mode]).map((edit) => ({
			week: edit.week,
			team1: edit.team1,
			team2: edit.team2,
			score1: edit.score1,
			score2: edit.score2,
		}));
		const body = { results };
		const cut = state.eliminated[state.mode];
		if (cut !== null) body.eliminated = cut;
		if (state.mode === "custom") {
			body.teams = customNames();
			return { path: "/esports/standings/calculate", body };
		}
		return { path: `/esports/${state.mode}/standings/simulate`, body };
	}

	let inflight = 0;

	async function refresh() {
		const ticket = ++inflight;
		const { path, body } = buildRequest();
		setStatus("Updating the table...", "info");
		try {
			const init = { method: "POST", headers: { accept: "application/json", "content-type": "application/json" }, body: JSON.stringify(body) };
			const url = `${API_BASE}${path}`;
			const result = window.ArenaApi ? await window.ArenaApi.request(url, init) : { response: await fetch(url, init), fellBack: false, host: "" };
			const parsed = await result.response.json().catch(() => null);
			if (ticket !== inflight) return;
			if (!result.response.ok || !parsed?.standings) {
				setStatus(parsed?.message || `The server answered ${result.response.status}.`, "error");
				return;
			}
			state.data = parsed;
			render();
			setStatus(result.fellBack ? `Answered by the backup host ${result.host}.` : "", result.fellBack ? "warn" : null);
		} catch (error) {
			if (ticket !== inflight) return;
			setStatus("The server could not be reached. Check your connection and try again.", "error");
		}
	}

	let timer = null;
	function refreshSoon() {
		clearTimeout(timer);
		timer = setTimeout(refresh, 250);
	}

	// ----------------------------------------------------------------- rendering

	function teamLabel(team, className) {
		const side = el("span", className);
		if (team.logo) {
			const image = el("img");
			image.src = team.logo;
			image.alt = "";
			image.loading = "lazy";
			image.width = image.height = 24;
			side.appendChild(image);
		}
		side.appendChild(el("span", "", team.name));
		return side;
	}

	function renderTable() {
		const { standings, playoff_spots: spots, eliminated, matches_played: played, matches_remaining: left, edited_matches: edited } = state.data;
		const rows = standings.map((row) => {
			const tr = el("tr");
			if (row.rank === spots && eliminated > 0) tr.classList.add("cut");
			if (!row.in_playoffs_zone) tr.classList.add("is-out");
			tr.appendChild(el("td", "num rank-no", String(row.rank)));

			const name = el("td");
			const cell = teamLabel(row.team, "team-cell");
			cell.className = "team-cell";
			if (row.tiebreak && row.played > 0) {
				const [label, hint] = TIEBREAKS[row.tiebreak];
				const mark = el("span", "tb", label);
				mark.title = hint;
				cell.appendChild(mark);
			}
			name.appendChild(cell);
			tr.appendChild(name);

			tr.appendChild(el("td", "num", String(row.match_point)));
			tr.appendChild(el("td", "num", `${row.match_wl.win}-${row.match_wl.lose}`));
			tr.appendChild(el("td", "num", row.net_game_win > 0 ? `+${row.net_game_win}` : String(row.net_game_win)));
			tr.appendChild(el("td", "num", `${row.game_wl.win}-${row.game_wl.lose}`));
			tr.appendChild(el("td", "num", String(row.remaining)));

			const status = el("td");
			const [word, tone] = STATUS[row.status];
			status.appendChild(el("span", `tag ${tone}`.trim(), word));
			tr.appendChild(status);
			return tr;
		});
		els.body.replaceChildren(...rows);

		const count = (n, word) => `${n} ${word}${n === 1 ? "" : "es"}`;
		const parts = [`${LEAGUE_NAMES[state.mode]}: ${count(played, "match")} played, ${left} to play.`];
		if (edited) parts.push(`${edited} changed by you.`);
		els.summary.textContent = parts.join(" ");
		els.legend.textContent =
			eliminated > 0
				? `The heavy line is the playoff cut: the top ${spots} go through and the last ${eliminated} are out.`
				: "Nobody is cut: every team goes through.";
		if (document.activeElement !== els.eliminated) els.eliminated.value = String(eliminated);
	}

	function editKey(week, team1, team2) {
		return `${week}|${team1}|${team2}`;
	}

	function renderWeeks() {
		const { weeks } = state.data;
		if (state.week === null || !weeks.some((item) => item.week === state.week)) {
			const open = weeks.find((item) => item.matches.some((match) => match.score1 === null));
			state.week = (open || weeks[weeks.length - 1]).week;
		}
		const buttons = weeks.map((item) => {
			const button = el("button", `tab${item.week === state.week ? " is-active" : ""}`, `Week ${item.week}`);
			button.type = "button";
			button.setAttribute("role", "tab");
			button.setAttribute("aria-selected", String(item.week === state.week));
			button.dataset.week = String(item.week);
			return button;
		});
		els.weekTabs.replaceChildren(...buttons);
	}

	function renderMatches() {
		const week = state.data.weeks.find((item) => item.week === state.week);
		const rows = week.matches.map((match) => {
			const li = el("li", `match-row${match.state === "edited" ? " is-edited" : ""}`);
			li.appendChild(teamLabel(match.team1, "side"));

			const select = el("select", "select");
			select.dataset.week = String(week.week);
			select.dataset.team1 = match.team1.name;
			select.dataset.team2 = match.team2.name;
			select.setAttribute("aria-label", `Result of ${match.team1.name} against ${match.team2.name}, week ${week.week}`);
			const current = match.score1 === null ? "" : `${match.score1}-${match.score2}`;
			for (const [value, label] of RESULTS) {
				const option = el("option", "", label);
				option.value = value;
				option.selected = value === current;
				select.appendChild(option);
			}
			li.appendChild(select);
			li.appendChild(teamLabel(match.team2, "side"));
			return li;
		});
		els.matchList.replaceChildren(...rows);
	}

	function renderControls() {
		for (const tab of els.tabs.querySelectorAll(".tab")) {
			const active = tab.dataset.mode === state.mode;
			tab.classList.toggle("is-active", active);
			tab.setAttribute("aria-selected", String(active));
		}
		const custom = state.mode === "custom";
		els.teamCountField.hidden = !custom;
		els.teamNames.hidden = !custom;
		if (custom) {
			els.teamCount.value = String(state.custom.count);
			const names = customNames();
			const inputs = names.map((name, index) => {
				const input = el("input", "input");
				input.type = "text";
				input.value = name;
				input.maxLength = 40;
				input.dataset.index = String(index);
				input.setAttribute("aria-label", `Name of team ${index + 1}`);
				return input;
			});
			if (!els.teamNamesGrid.contains(document.activeElement)) els.teamNamesGrid.replaceChildren(...inputs);
		}
	}

	function render() {
		renderControls();
		renderTable();
		renderWeeks();
		renderMatches();
	}

	// ------------------------------------------------------------------- events

	els.tabs.addEventListener("click", (event) => {
		const tab = event.target.closest(".tab");
		if (!tab || tab.dataset.mode === state.mode) return;
		state.mode = tab.dataset.mode;
		state.week = null;
		state.data = null;
		save();
		renderControls();
		els.eliminated.value = state.eliminated[state.mode] === null ? "" : String(state.eliminated[state.mode]);
		void refresh();
	});

	els.weekTabs.addEventListener("click", (event) => {
		const tab = event.target.closest(".tab");
		if (!tab || !state.data) return;
		state.week = Number(tab.dataset.week);
		renderWeeks();
		renderMatches();
	});

	els.matchList.addEventListener("change", (event) => {
		const select = event.target.closest("select");
		if (!select) return;
		const week = Number(select.dataset.week);
		const [score1, score2] = select.value ? select.value.split("-").map(Number) : [null, null];
		const key = editKey(week, select.dataset.team1, select.dataset.team2);
		const shown = state.data.weeks.find((item) => item.week === week)?.matches.find((match) => match.team1.name === select.dataset.team1 && match.team2.name === select.dataset.team2);
		if (!select.value && shown?.state === "scheduled") {
			// "Not played" on a match with no result is not a change.
			delete state.edits[state.mode][key];
			return;
		}
		state.edits[state.mode][key] = {
			week,
			team1: select.dataset.team1,
			team2: select.dataset.team2,
			score1,
			score2,
		};
		save();
		void refresh();
	});

	els.eliminated.addEventListener("input", () => {
		const raw = els.eliminated.value.trim();
		const value = raw === "" ? null : Number(raw);
		state.eliminated[state.mode] = value !== null && Number.isInteger(value) && value >= 0 ? value : null;
		save();
		refreshSoon();
	});

	els.teamCount.addEventListener("input", () => {
		const value = Number(els.teamCount.value);
		if (!Number.isInteger(value) || value < 2 || value > 20) return;
		state.custom.count = value;
		state.custom.names = state.custom.names.slice(0, value);
		state.edits.custom = {};
		state.eliminated.custom = null;
		state.week = null;
		els.teamNamesGrid.replaceChildren();
		save();
		refreshSoon();
	});

	els.teamNamesGrid.addEventListener("input", (event) => {
		const input = event.target.closest("input");
		if (!input) return;
		const names = customNames();
		names[Number(input.dataset.index)] = input.value;
		state.custom.names = names;
		// New names mean a new schedule, so earlier edits no longer point at real matches.
		state.edits.custom = {};
		state.week = null;
		save();
		refreshSoon();
	});

	els.reset.addEventListener("click", () => {
		state.edits[state.mode] = {};
		state.eliminated[state.mode] = null;
		els.eliminated.value = "";
		save();
		void refresh();
	});

	load();
	renderControls();
	els.eliminated.value = state.eliminated[state.mode] === null ? "" : String(state.eliminated[state.mode]);
	void refresh();
})();
