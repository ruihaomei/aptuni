"use strict";

const { ItemView, Modal, Notice, Plugin, PluginSettingTab, Setting } = require("obsidian");
const { execFile } = require("child_process");

const CONTRACT = "aptuni.obsidian@1";
const VIEW_TYPE = "aptuni-owner-view";
const DEFAULT_SETTINGS = { executable: "aptuni" };
const SECTIONS = [
  ["profile", "Profile"],
  ["memories", "Memory"],
  ["evidence", "Evidence"],
  ["recent_changes", "Recent Changes"],
  ["pending_reviews", "Pending Reviews"],
];

class AptuniClient {
  constructor(executable) {
    this.executable = executable;
  }

  run(args) {
    return new Promise((resolve, reject) => {
      execFile(this.executable, args, { encoding: "utf8", maxBuffer: 2 * 1024 * 1024 }, (error, stdout, stderr) => {
        if (error) {
          reject(new Error((stderr || error.message || "Aptuni command failed").trim()));
          return;
        }
        try {
          const value = JSON.parse(stdout);
          if (!value || value.contract !== CONTRACT) {
            reject(new Error("Aptuni returned an incompatible Obsidian bridge contract."));
            return;
          }
          resolve(value);
        } catch (_error) {
          reject(new Error("Aptuni returned invalid JSON."));
        }
      });
    });
  }

  snapshot() {
    return this.run(["interface", "obsidian", "snapshot", "--json"]);
  }

  evidence(recordId) {
    return this.run(["interface", "obsidian", "evidence", recordId, "--json"]);
  }

  action(recordId, action, extra = []) {
    return this.run(["interface", "obsidian", "action", recordId, action, ...extra, "--json"]);
  }
}

class TextPromptModal extends Modal {
  constructor(app, title, initial, submit) {
    super(app);
    this.title = title;
    this.initial = initial;
    this.submit = submit;
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.createEl("h2", { text: this.title });
    const area = contentEl.createEl("textarea");
    area.value = this.initial;
    area.rows = 6;
    const button = contentEl.createEl("button", { text: "Save edit", cls: "mod-cta" });
    button.addEventListener("click", () => {
      const value = area.value.trim();
      if (!value) {
        new Notice("A replacement statement is required.");
        return;
      }
      this.close();
      this.submit(value);
    });
  }

  onClose() {
    this.contentEl.empty();
  }
}

class ForgetModal extends Modal {
  constructor(app, preview, confirm) {
    super(app);
    this.preview = preview;
    this.confirm = confirm;
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.createEl("h2", { text: "Forget Memory" });
    contentEl.createEl("p", { text: "This stops using the Memory but keeps canonical history." });
    contentEl.createEl("blockquote", { text: this.preview.statement });
    const button = contentEl.createEl("button", { text: "Forget", cls: "mod-warning" });
    button.addEventListener("click", () => {
      this.close();
      this.confirm(this.preview.digest);
    });
  }

  onClose() {
    this.contentEl.empty();
  }
}

class EvidenceModal extends Modal {
  constructor(app, value) {
    super(app);
    this.value = value;
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.createEl("h2", { text: "Show Evidence" });
    if (!this.value.supports.length) {
      contentEl.createEl("p", { text: "No linked canonical support is recorded.", cls: "aptuni-empty" });
      return;
    }
    if (this.value.supports_truncated) {
      contentEl.createEl("p", { text: "Additional linked support is not shown in this bounded view.", cls: "aptuni-meta" });
    }
    for (const item of this.value.supports) {
      const card = contentEl.createDiv({ cls: "aptuni-card" });
      card.createEl("div", { text: `${item.kind} · ${item.id}`, cls: "aptuni-card-title" });
      card.createEl("div", { text: item.text });
      card.createEl("div", {
        text: `${item.provider || "local"} · ${item.episode || "unknown episode"}`,
        cls: "aptuni-meta",
      });
    }
  }

  onClose() {
    this.contentEl.empty();
  }
}

class AptuniView extends ItemView {
  constructor(leaf, plugin) {
    super(leaf);
    this.plugin = plugin;
    this.snapshotValue = null;
  }

  getViewType() {
    return VIEW_TYPE;
  }

  getDisplayText() {
    return "Aptuni";
  }

  async onOpen() {
    await this.refresh();
  }

  async refresh() {
    try {
      this.snapshotValue = await this.plugin.client().snapshot();
      this.render();
    } catch (error) {
      new Notice(`Aptuni: ${error.message}`);
    }
  }

  render() {
    const root = this.containerEl.children[1];
    root.empty();
    root.addClass("aptuni-view");
    const toolbar = root.createDiv({ cls: "aptuni-toolbar" });
    toolbar.createEl("h1", { text: "Aptuni" });
    const refresh = toolbar.createEl("button", { text: "Refresh" });
    refresh.addEventListener("click", () => this.refresh());
    root.createEl("div", { text: `Vault commit ${this.snapshotValue.vault_seq}`, cls: "aptuni-meta" });
    for (const [key, label] of SECTIONS) {
      this.renderSection(root, label, this.snapshotValue[key], this.snapshotValue.truncated[key]);
    }
  }

  renderSection(root, label, items, truncated) {
    const section = root.createDiv({ cls: "aptuni-section" });
    section.createEl("h2", { text: label });
    if (truncated) {
      section.createEl("p", { text: "Additional records are not shown in this bounded view.", cls: "aptuni-meta" });
    }
    if (!items.length) {
      section.createEl("p", { text: "Nothing here yet.", cls: "aptuni-empty" });
      return;
    }
    for (const item of items) {
      this.renderItem(section, item);
    }
  }

  renderItem(section, item) {
    const card = section.createDiv({ cls: "aptuni-card" });
    card.createEl("div", { text: `${item.kind} · ${item.id}`, cls: "aptuni-card-title" });
    card.createEl("div", { text: item.text });
    card.createEl("div", {
      text: [item.module, item.review_state, item.change_kind, item.recorded_at].filter(Boolean).join(" · "),
      cls: "aptuni-meta",
    });
    const actions = card.createDiv({ cls: "aptuni-actions" });
    if (item.actions.includes("show_evidence")) {
      this.button(actions, "Show Evidence", () => this.showEvidence(item.id));
    }
    if (item.kind === "memory") {
      for (const action of ["Accept", "Edit", "Reject", "Pin", "Forget"]) {
        if (item.actions.includes(action.toLowerCase())) {
          this.button(actions, action, () => this.review(item, action.toLowerCase()));
        }
      }
    } else if (item.kind === "fact") {
      for (const action of ["Accept", "Reject"]) {
        if (item.actions.includes(action.toLowerCase())) {
          this.button(actions, action, () => this.review(item, action.toLowerCase()));
        }
      }
    }
  }

  button(parent, label, callback) {
    const button = parent.createEl("button", { text: label });
    button.addEventListener("click", callback);
  }

  async showEvidence(recordId) {
    try {
      new EvidenceModal(this.app, await this.plugin.client().evidence(recordId)).open();
    } catch (error) {
      new Notice(`Aptuni: ${error.message}`);
    }
  }

  async review(item, action) {
    if (action === "edit") {
      new TextPromptModal(this.app, "Edit Memory", item.text, (value) => {
        this.applyAction(item.id, action, ["--statement", value]);
      }).open();
      return;
    }
    if (action === "forget") {
      try {
        const preview = await this.plugin.client().action(item.id, action);
        new ForgetModal(this.app, preview, (digest) => {
          this.applyAction(item.id, action, ["--confirm-digest", digest]);
        }).open();
      } catch (error) {
        new Notice(`Aptuni: ${error.message}`);
      }
      return;
    }
    await this.applyAction(item.id, action);
  }

  async applyAction(recordId, action, extra = []) {
    try {
      await this.plugin.client().action(recordId, action, extra);
      new Notice(`Aptuni ${action} complete.`);
      await this.refresh();
    } catch (error) {
      new Notice(`Aptuni: ${error.message}`);
    }
  }
}

class AptuniSettingTab extends PluginSettingTab {
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display() {
    const { containerEl } = this;
    containerEl.empty();
    new Setting(containerEl)
      .setName("Aptuni executable")
      .setDesc("Absolute path or command name for the local Aptuni CLI. No Profile content is stored here.")
      .addText((text) => text
        .setPlaceholder("aptuni")
        .setValue(this.plugin.settings.executable)
        .onChange(async (value) => {
          this.plugin.settings.executable = value.trim() || "aptuni";
          await this.plugin.saveData(this.plugin.settings);
        }));
  }
}

module.exports = class AptuniPlugin extends Plugin {
  async onload() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
    this.registerView(VIEW_TYPE, (leaf) => new AptuniView(leaf, this));
    this.addRibbonIcon("contact", "Open Aptuni", () => this.activateView());
    this.addCommand({ id: "open-owner-view", name: "Open owner view", callback: () => this.activateView() });
    this.addCommand({ id: "refresh-owner-view", name: "Refresh owner view", callback: () => this.refreshView() });
    this.addSettingTab(new AptuniSettingTab(this.app, this));
  }

  client() {
    return new AptuniClient(this.settings.executable);
  }

  async activateView() {
    let leaf = this.app.workspace.getLeavesOfType(VIEW_TYPE)[0];
    if (!leaf) {
      leaf = this.app.workspace.getRightLeaf(false);
      await leaf.setViewState({ type: VIEW_TYPE, active: true });
    }
    this.app.workspace.revealLeaf(leaf);
  }

  async refreshView() {
    const leaf = this.app.workspace.getLeavesOfType(VIEW_TYPE)[0];
    if (leaf && leaf.view instanceof AptuniView) {
      await leaf.view.refresh();
    } else {
      await this.activateView();
    }
  }

  onunload() {
    this.app.workspace.detachLeavesOfType(VIEW_TYPE);
  }
};
