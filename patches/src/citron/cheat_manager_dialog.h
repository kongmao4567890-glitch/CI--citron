// SPDX-FileCopyrightText: Copyright 2026 citron Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#pragma once

#include <cstddef>
#include <string>
#include <vector>

#include <QDialog>
#include <QString>

#include "common/common_types.h"
#include "core/file_sys/patch_manager.h"

namespace Core {
class System;
}

class QCheckBox;
class QLabel;
class QLineEdit;
class QPushButton;
class QTreeWidget;
class QTreeWidgetItem;

/**
 * Standalone cheat manager.
 *
 * Lists every cheat shipped by the mods installed for a title, grouped by the file it came from,
 * and lets the user pick individually which ones run. Toggling a cheat rewrites the persisted
 * disabled-cheat set and hot-reloads the running cheat engine, so cheats can be switched on and
 * off without restarting the game.
 */
class CheatManagerDialog : public QDialog {
    Q_OBJECT

public:
    explicit CheatManagerDialog(Core::System& system_, u64 title_id_, QWidget* parent = nullptr);
    ~CheatManagerDialog() override;

private:
    void RefreshCheats();
    QString ResolveTitleName() const;
    void RebuildTree();
    void OnItemChanged(QTreeWidgetItem* item, int column);
    void UpdateGroupState(QTreeWidgetItem* group);
    void SetAllCheats(bool enabled);
    void InvertSelection();
    void OnMasterToggled(bool enabled);
    void OnOpenCheatsFolder();
    void ApplyFilter();
    void UpdateSummary();
    void SetCheatEnabled(std::size_t index, bool enabled);
    void ReloadCheatEngine() const;

    Core::System& system;
    u64 title_id;

    std::vector<FileSys::CheatPatch> cheats;
    std::string active_build_id;

    QLabel* header_label{};
    QLabel* summary_label{};
    QCheckBox* master_toggle{};
    QLineEdit* filter_edit{};
    QTreeWidget* tree{};
    QPushButton* enable_all_button{};
    QPushButton* disable_all_button{};
    QPushButton* invert_button{};
    QPushButton* refresh_button{};
    QPushButton* open_folder_button{};
    QPushButton* close_button{};

    /// Guards OnItemChanged while the tree is being repopulated programmatically.
    bool updating{};
};
