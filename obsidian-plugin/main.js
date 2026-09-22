const { Notice, Plugin, PluginSettingTab, Setting } = require("obsidian");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const DEFAULT_SETTINGS = {
	uvPath: "uv",
	projectPath: "",
};

const OUTPUT_LIMIT = 12_000;

module.exports = class NotesReviewerPlugin extends Plugin {
	async onload() {
		this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
		this.isRunning = false;

		this.addRibbonIcon("calendar-check", "Review personal note for today", () => {
			this.runReview(["personal", "today"], "personal note");
		});
		this.addRibbonIcon("briefcase", "Review the current work week", () => {
			const { week, year } = getISOWeek(new Date());
			this.runReview(["work", String(week), "--year", String(year)], `work week ${week}, ${year}`);
		});

		this.addCommand({
			id: "review-personal-today",
			name: "Review personal note for today",
			callback: () => this.runReview(["personal", "today"], "personal note"),
		});
		this.addCommand({
			id: "review-current-work-week",
			name: "Review the current work week",
			callback: () => {
				const { week, year } = getISOWeek(new Date());
				this.runReview(["work", String(week), "--year", String(year)], `work week ${week}, ${year}`);
			},
		});

		this.addSettingTab(new NotesReviewerSettingTab(this.app, this));
	}

	async saveSettings() {
		await this.saveData(this.settings);
	}

	runReview(reviewArgs, label) {
		if (this.isRunning) {
			new Notice("A notes review is already running.");
			return;
		}

		const uvPath = this.settings.uvPath.trim();
		const projectPath = this.settings.projectPath.trim();
		if (!uvPath) {
			new Notice("Set the uv executable in Notes Reviewer settings.", 8000);
			return;
		}
		if (!projectPath || !path.isAbsolute(projectPath)) {
			new Notice("Set an absolute project folder path in Notes Reviewer settings.", 8000);
			return;
		}
		try {
			if (!fs.statSync(projectPath).isDirectory()) {
				new Notice("The Notes Reviewer project path is not a folder.", 8000);
				return;
			}
			if (!fs.existsSync(path.join(projectPath, "pyproject.toml"))) {
				new Notice("Could not find pyproject.toml in the configured project folder.", 8000);
				return;
			}
		} catch (error) {
			new Notice(`Could not access the project folder: ${error.message}`, 8000);
			return;
		}

		this.isRunning = true;
		new Notice(`Starting review of ${label}…`);
		let stdout = "";
		let stderr = "";
		let launchError;
		let child;
		try {
			child = spawn(
				uvPath,
				["run", "--project", projectPath, "notes-review", ...reviewArgs],
				{ cwd: projectPath, shell: false, windowsHide: true },
			);
		} catch (error) {
			this.isRunning = false;
			new Notice(`Could not start uv: ${error.message}`, 10000);
			return;
		}

		child.stdout.on("data", (chunk) => {
			stdout = appendLimited(stdout, chunk.toString());
		});
		child.stderr.on("data", (chunk) => {
			stderr = appendLimited(stderr, chunk.toString());
		});
		child.on("error", (error) => {
			launchError = error;
		});
		child.on("close", (code) => {
			this.isRunning = false;
			if (code === 0) {
				new Notice(`Review complete: ${label}.`, 6000);
				return;
			}

			const details = (launchError?.message || stderr || stdout || "No error details were returned.").trim();
			new Notice(`Review failed${code === null ? "" : ` (exit ${code})`}: ${details.slice(-1200)}`, 12000);
		});
	}
};

class NotesReviewerSettingTab extends PluginSettingTab {
	constructor(app, plugin) {
		super(app, plugin);
		this.plugin = plugin;
	}

	display() {
		const { containerEl } = this;
		containerEl.empty();
		containerEl.createEl("h2", { text: "Notes Reviewer" });
		containerEl.createEl("p", {
			text: "Set the local uv executable and the folder containing this project's pyproject.toml and config.toml.",
		});

		new Setting(containerEl)
			.setName("uv executable")
			.setDesc("Use the absolute path if Obsidian cannot find uv from its environment.")
			.addText((text) => text
				.setPlaceholder("/usr/bin/uv")
				.setValue(this.plugin.settings.uvPath)
				.onChange(async (value) => {
					this.plugin.settings.uvPath = value.trim();
					await this.plugin.saveSettings();
				}));

		new Setting(containerEl)
			.setName("Project folder")
			.setDesc("Absolute path to the notes-reviewer folder in your local filesystem.")
			.addText((text) => text
				.setPlaceholder("/home/you/dev/notes-reviewer")
				.setValue(this.plugin.settings.projectPath)
				.onChange(async (value) => {
					this.plugin.settings.projectPath = value.trim();
					await this.plugin.saveSettings();
				}));
	}
}

function appendLimited(current, addition) {
	if (current.length >= OUTPUT_LIMIT) return current;
	return current + addition.slice(0, OUTPUT_LIMIT - current.length);
}

function getISOWeek(date) {
	const thursday = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
	const weekday = thursday.getUTCDay() || 7;
	thursday.setUTCDate(thursday.getUTCDate() + 4 - weekday);
	const year = thursday.getUTCFullYear();
	const firstDayOfYear = new Date(Date.UTC(year, 0, 1));
	const week = Math.ceil(((thursday - firstDayOfYear) / 86400000 + 1) / 7);
	return { week, year };
}
