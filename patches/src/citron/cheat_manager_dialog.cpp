// SPDX-FileCopyrightText: Copyright 2026 citron Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#include <algorithm>
#include <cstddef>
#include <map>
#include <utility>

#include <QAbstractItemView>
#include <QCheckBox>
#include <QDesktopServices>
#include <QDir>
#include <QFont>
#include <QHBoxLayout>
#include <QHeaderView>
#include <QLabel>
#include <QLineEdit>
#include <QPushButton>
#include <QTreeWidget>
#include <QTreeWidgetItem>
#include <QUrl>
#include <QVBoxLayout>

#include "citron/cheat_manager_dialog.h"
#include "common/fs/fs_util.h"
#include "common/fs/path_util.h"
#include "common/settings.h"
#include "core/core.h"
#include "core/file_sys/control_metadata.h"
#include "core/hle/service/filesystem/filesystem.h"
#include "core/memory/cheat_engine.h"

namespace {

constexpr int kCheatIndexRole = Qt::UserRole;

QString TitleIdToHex(u64 title_id) {
    return QStringLiteral("%1").arg(title_id, 16, 16, QLatin1Char('0')).toUpper();
}

/// Cheat files are named after the build ID, so the file name alone is the friendliest label we
/// can show for a group. Falls back to the full source string when there is no path separator.
QString SourceDisplayName(const std::string& source) {
    const auto qsource = QString::fromStdString(source);
    const int separator = qsource.lastIndexOf(QLatin1Char('/'));
    return separator < 0 ? qsource : qsource.mid(separator + 1);
}

QString SourceModName(const std::string& source) {
    const auto qsource = QString::fromStdString(source);
    const int separator = qsource.lastIndexOf(QLatin1Char('/'));
    return separator < 0 ? QString{} : qsource.left(separator);
}

} // Anonymous namespace

CheatManagerDialog::CheatManagerDialog(Core::System& system_, u64 title_id_, QWidget* parent)
    : QDialog(parent), system{system_}, title_id{title_id_} {
    setWindowTitle(tr("Cheat Manager"));
    setWindowFlags(windowFlags() & ~Qt::WindowContextHelpButtonHint);
    resize(720, 520);

    header_label = new QLabel(this);
    QFont header_font = header_label->font();
    header_font.setBold(true);
    header_label->setFont(header_font);
    header_label->setTextInteractionFlags(Qt::TextSelectableByMouse);

    master_toggle = new QCheckBox(tr("Enable cheats"), this);
    master_toggle->setToolTip(
        tr("Master switch for the cheat engine. When off, no cheat runs even if it is ticked "
           "below."));
    master_toggle->setChecked(Settings::values.cheats_enabled.GetValue());

    filter_edit = new QLineEdit(this);
    filter_edit->setPlaceholderText(tr("Search cheats..."));
    filter_edit->setClearButtonEnabled(true);

    tree = new QTreeWidget(this);
    tree->setColumnCount(3);
    tree->setHeaderLabels({tr("Cheat"), tr("Source"), tr("Build ID")});
    tree->setAlternatingRowColors(true);
    tree->setRootIsDecorated(true);
    tree->setUniformRowHeights(true);
    tree->setSelectionMode(QAbstractItemView::SingleSelection);
    tree->setSelectionBehavior(QAbstractItemView::SelectRows);
    tree->setEditTriggers(QAbstractItemView::NoEditTriggers);
    tree->setVerticalScrollMode(QAbstractItemView::ScrollPerPixel);
    tree->header()->setStretchLastSection(false);
    tree->header()->setSectionResizeMode(0, QHeaderView::Stretch);
    tree->header()->setSectionResizeMode(1, QHeaderView::ResizeToContents);
    tree->header()->setSectionResizeMode(2, QHeaderView::ResizeToContents);

    summary_label = new QLabel(this);

    enable_all_button = new QPushButton(tr("Enable All"), this);
    disable_all_button = new QPushButton(tr("Disable All"), this);
    invert_button = new QPushButton(tr("Invert"), this);
    refresh_button = new QPushButton(tr("Refresh"), this);
    open_folder_button = new QPushButton(tr("Open Cheats Folder"), this);
    close_button = new QPushButton(tr("Close"), this);
    close_button->setDefault(true);

    auto* const top_row = new QHBoxLayout;
    top_row->addWidget(master_toggle);
    top_row->addStretch();
    top_row->addWidget(filter_edit, 1);

    auto* const button_row = new QHBoxLayout;
    button_row->addWidget(enable_all_button);
    button_row->addWidget(disable_all_button);
    button_row->addWidget(invert_button);
    button_row->addWidget(refresh_button);
    button_row->addWidget(open_folder_button);
    button_row->addStretch();
    button_row->addWidget(close_button);

    auto* const main_layout = new QVBoxLayout(this);
    main_layout->addWidget(header_label);
    main_layout->addLayout(top_row);
    main_layout->addWidget(tree, 1);
    main_layout->addWidget(summary_label);
    main_layout->addLayout(button_row);

    connect(tree, &QTreeWidget::itemChanged, this, &CheatManagerDialog::OnItemChanged);
    connect(master_toggle, &QCheckBox::toggled, this, &CheatManagerDialog::OnMasterToggled);
    connect(filter_edit, &QLineEdit::textChanged, this, [this](const QString&) { ApplyFilter(); });
    connect(enable_all_button, &QPushButton::clicked, this, [this] { SetAllCheats(true); });
    connect(disable_all_button, &QPushButton::clicked, this, [this] { SetAllCheats(false); });
    connect(invert_button, &QPushButton::clicked, this, &CheatManagerDialog::InvertSelection);
    connect(refresh_button, &QPushButton::clicked, this, &CheatManagerDialog::RefreshCheats);
    connect(open_folder_button, &QPushButton::clicked, this,
            &CheatManagerDialog::OnOpenCheatsFolder);
    connect(close_button, &QPushButton::clicked, this, &QDialog::accept);

    RefreshCheats();
}

CheatManagerDialog::~CheatManagerDialog() = default;

void CheatManagerDialog::RefreshCheats() {
    const FileSys::PatchManager pm{title_id, system.GetFileSystemController(),
                                   system.GetContentProvider()};
    cheats = pm.GetCheats();

    active_build_id.clear();
    if (const auto* cheat_engine = system.GetCheatEngine(); cheat_engine != nullptr) {
        active_build_id = FileSys::GetCheatBuildId(cheat_engine->GetBuildId());
    }

    const QString title_hex = TitleIdToHex(title_id);
    const QString resolved_name = ResolveTitleName();
    header_label->setText(tr("%1  (Title ID: %2)")
                              .arg(resolved_name.isEmpty() ? title_hex : resolved_name, title_hex));

    RebuildTree();
    ApplyFilter();
    UpdateSummary();
}

QString CheatManagerDialog::ResolveTitleName() const {
    const FileSys::PatchManager pm{title_id, system.GetFileSystemController(),
                                   system.GetContentProvider()};
    const auto control = pm.GetControlMetadata();
    if (control.first == nullptr) {
        return {};
    }
    return QString::fromStdString(control.first->GetApplicationName());
}

void CheatManagerDialog::RebuildTree() {
    updating = true;
    tree->clear();

    // Group by the file the cheats were parsed from so users can tell overlapping mods apart.
    std::map<std::string, QTreeWidgetItem*> groups;
    for (std::size_t i = 0; i < cheats.size(); ++i) {
        const auto& cheat = cheats[i];

        auto group_it = groups.find(cheat.source);
        if (group_it == groups.end()) {
            auto* const group = new QTreeWidgetItem(tree);
            const auto mod_name = SourceModName(cheat.source);
            group->setText(0, mod_name.isEmpty() ? SourceDisplayName(cheat.source) : mod_name);
            group->setText(1, SourceDisplayName(cheat.source));
            group->setText(2, QString::fromStdString(cheat.build_id));
            group->setFlags(group->flags() | Qt::ItemIsUserCheckable);
            group->setCheckState(0, Qt::Unchecked);
            group->setExpanded(true);
            QFont group_font = group->font(0);
            group_font.setBold(true);
            group->setFont(0, group_font);
            group_it = groups.emplace(cheat.source, group).first;
        }

        auto* const item = new QTreeWidgetItem(group_it->second);
        item->setText(0, QString::fromStdString(cheat.name));
        item->setText(1, SourceDisplayName(cheat.source));
        item->setText(2, QString::fromStdString(cheat.build_id));
        item->setData(0, kCheatIndexRole, static_cast<qulonglong>(i));
        item->setFlags(item->flags() | Qt::ItemIsUserCheckable);
        item->setCheckState(0, cheat.enabled ? Qt::Checked : Qt::Unchecked);

        // Cheats written for a different build of the game can never fire against the running
        // one, so show them but keep them out of reach.
        if (!active_build_id.empty() && cheat.build_id != active_build_id) {
            item->setDisabled(true);
            item->setToolTip(0, tr("This cheat targets another version of the game (build ID %1) "
                                   "and will not run.")
                                    .arg(QString::fromStdString(cheat.build_id)));
        }
    }

    for (const auto& group : groups) {
        UpdateGroupState(group.second);
    }

    if (cheats.empty()) {
        auto* const placeholder = new QTreeWidgetItem(tree);
        placeholder->setText(0, tr("No cheats found for this game."));
        placeholder->setFlags(Qt::ItemIsEnabled);
        placeholder->setFirstColumnSpanned(true);
    }

    tree->setEnabled(master_toggle->isChecked());
    updating = false;
}

void CheatManagerDialog::UpdateGroupState(QTreeWidgetItem* group) {
    if (group == nullptr) {
        return;
    }

    int checked = 0;
    int total = 0;
    for (int i = 0; i < group->childCount(); ++i) {
        const auto* const child = group->child(i);
        if (!child->data(0, kCheatIndexRole).isValid()) {
            continue;
        }
        ++total;
        if (child->checkState(0) == Qt::Checked) {
            ++checked;
        }
    }

    if (total == 0) {
        return;
    }

    const bool was_updating = updating;
    updating = true;
    if (checked == 0) {
        group->setCheckState(0, Qt::Unchecked);
    } else if (checked == total) {
        group->setCheckState(0, Qt::Checked);
    } else {
        group->setCheckState(0, Qt::PartiallyChecked);
    }
    updating = was_updating;
}

void CheatManagerDialog::OnItemChanged(QTreeWidgetItem* item, int column) {
    if (updating || item == nullptr || column != 0) {
        return;
    }

    const bool checked = item->checkState(0) == Qt::Checked;
    const auto index_data = item->data(0, kCheatIndexRole);

    updating = true;
    if (index_data.isValid()) {
        SetCheatEnabled(static_cast<std::size_t>(index_data.toULongLong()), checked);
        updating = false;
        UpdateGroupState(item->parent());
    } else {
        // Group header: push the new state onto every cheat it owns.
        for (int i = 0; i < item->childCount(); ++i) {
            auto* const child = item->child(i);
            const auto child_index = child->data(0, kCheatIndexRole);
            if (!child_index.isValid() || child->isDisabled()) {
                continue;
            }
            child->setCheckState(0, checked ? Qt::Checked : Qt::Unchecked);
            SetCheatEnabled(static_cast<std::size_t>(child_index.toULongLong()), checked);
        }
        updating = false;
        UpdateGroupState(item);
    }

    UpdateSummary();
    ReloadCheatEngine();
}

void CheatManagerDialog::SetAllCheats(bool enabled) {
    updating = true;
    for (int i = 0; i < tree->topLevelItemCount(); ++i) {
        auto* const group = tree->topLevelItem(i);
        for (int j = 0; j < group->childCount(); ++j) {
            auto* const child = group->child(j);
            const auto child_index = child->data(0, kCheatIndexRole);
            if (!child_index.isValid() || child->isDisabled()) {
                continue;
            }
            child->setCheckState(0, enabled ? Qt::Checked : Qt::Unchecked);
            SetCheatEnabled(static_cast<std::size_t>(child_index.toULongLong()), enabled);
        }
    }
    updating = false;

    for (int i = 0; i < tree->topLevelItemCount(); ++i) {
        UpdateGroupState(tree->topLevelItem(i));
    }

    UpdateSummary();
    ReloadCheatEngine();
}

void CheatManagerDialog::InvertSelection() {
    updating = true;
    for (int i = 0; i < tree->topLevelItemCount(); ++i) {
        auto* const group = tree->topLevelItem(i);
        for (int j = 0; j < group->childCount(); ++j) {
            auto* const child = group->child(j);
            const auto child_index = child->data(0, kCheatIndexRole);
            if (!child_index.isValid() || child->isDisabled()) {
                continue;
            }
            const bool enabled = child->checkState(0) != Qt::Checked;
            child->setCheckState(0, enabled ? Qt::Checked : Qt::Unchecked);
            SetCheatEnabled(static_cast<std::size_t>(child_index.toULongLong()), enabled);
        }
    }
    updating = false;

    for (int i = 0; i < tree->topLevelItemCount(); ++i) {
        UpdateGroupState(tree->topLevelItem(i));
    }

    UpdateSummary();
    ReloadCheatEngine();
}

void CheatManagerDialog::OnMasterToggled(bool enabled) {
    Settings::values.cheats_enabled.SetValue(enabled);
    tree->setEnabled(enabled);
    UpdateSummary();
    ReloadCheatEngine();
}

void CheatManagerDialog::OnOpenCheatsFolder() {
    const auto cheats_dir = Common::FS::GetCitronPath(Common::FS::CitronPath::LoadDir);
    const QString path = QString::fromStdString(Common::FS::PathToUTF8String(cheats_dir)) +
                         QLatin1Char('/') + TitleIdToHex(title_id);
    QDir().mkpath(path);
    QDesktopServices::openUrl(QUrl::fromLocalFile(path));
}

void CheatManagerDialog::ApplyFilter() {
    const QString needle = filter_edit->text().trimmed();

    for (int i = 0; i < tree->topLevelItemCount(); ++i) {
        auto* const group = tree->topLevelItem(i);

        if (group->childCount() == 0) {
            // The "no cheats" placeholder has no children and should always stay visible.
            group->setHidden(false);
            continue;
        }

        int visible_children = 0;
        for (int j = 0; j < group->childCount(); ++j) {
            auto* const child = group->child(j);
            const bool matches =
                needle.isEmpty() || child->text(0).contains(needle, Qt::CaseInsensitive) ||
                child->text(1).contains(needle, Qt::CaseInsensitive);
            child->setHidden(!matches);
            visible_children += matches ? 1 : 0;
        }

        group->setHidden(visible_children == 0);
        if (!needle.isEmpty() && visible_children > 0) {
            group->setExpanded(true);
        }
    }
}

void CheatManagerDialog::UpdateSummary() {
    const auto enabled_count =
        std::count_if(cheats.begin(), cheats.end(),
                      [](const FileSys::CheatPatch& cheat) { return cheat.enabled; });

    if (!master_toggle->isChecked()) {
        summary_label->setText(tr("%1 cheats found, but the cheat engine is switched off.")
                                   .arg(static_cast<int>(cheats.size())));
        return;
    }

    summary_label->setText(tr("%1 of %2 cheats enabled.")
                               .arg(static_cast<int>(enabled_count))
                               .arg(static_cast<int>(cheats.size())));
}

void CheatManagerDialog::SetCheatEnabled(std::size_t index, bool enabled) {
    if (index >= cheats.size()) {
        return;
    }

    auto& cheat = cheats[index];
    cheat.enabled = enabled;

    const auto cheat_key = FileSys::GetCheatConfigKey(cheat.source, cheat.name);
    auto& disabled_cheats = Settings::values.disabled_cheats[cheat.build_id];
    if (enabled) {
        disabled_cheats.erase(cheat_key);
        // Configs written before source-specific keys existed stored the bare name; drop that
        // too so the cheat does not stay disabled through the legacy path.
        disabled_cheats.erase(cheat.name);
        if (disabled_cheats.empty()) {
            Settings::values.disabled_cheats.erase(cheat.build_id);
        }
    } else {
        disabled_cheats.insert(cheat_key);
    }
}

void CheatManagerDialog::ReloadCheatEngine() const {
    if (!system.IsPoweredOn()) {
        return;
    }

    auto* const cheat_engine = system.GetCheatEngine();
    if (cheat_engine == nullptr) {
        return;
    }

    const FileSys::PatchManager pm{title_id, system.GetFileSystemController(),
                                   system.GetContentProvider()};
    cheat_engine->Reload(pm.CreateCheatList(cheat_engine->GetBuildId()));
}
