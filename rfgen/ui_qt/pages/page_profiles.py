"""Profile manager page - view, edit, import/export profiles."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QLabel,
    QMessageBox, QInputDialog, QFileDialog
)
from PySide6.QtCore import Qt, Signal
from pathlib import Path
import shutil

from ...utils.paths import profiles_dir
from ...utils.profile_io import load_json, save_json, validate_profile
from ...utils.migrate import migrate_legacy_profiles


class PageProfiles(QWidget):
    """Profile manager page.

    Features:
    - List all profiles from rfgen/profiles/
    - Load/Duplicate/Rename/Delete operations
    - Import/Export profiles
    - JSON preview
    - Migration of legacy profiles
    """

    profile_loaded = Signal(dict)  # Emit when profile is loaded

    def __init__(self, parent=None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)

        # Header
        header = QLabel("<b>Profile Manager</b>")
        header.setStyleSheet("font-size: 14pt;")
        root.addWidget(header)

        # Info label
        info = QLabel(f"Location: {profiles_dir()}")
        info.setStyleSheet("color: #666; font-size: 9pt;")
        root.addWidget(info)

        # Main layout: list + preview
        main_layout = QHBoxLayout()

        # Left: Profile list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        list_label = QLabel("<b>Profiles:</b>")
        left_layout.addWidget(list_label)

        self.profile_list = QListWidget()
        self.profile_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.profile_list.itemDoubleClicked.connect(self._load_profile)
        left_layout.addWidget(self.profile_list)

        # Buttons for list
        list_btn_layout = QHBoxLayout()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self._refresh_list)
        btn_migrate = QPushButton("Migrate Legacy")
        btn_migrate.clicked.connect(self._migrate_legacy)
        list_btn_layout.addWidget(btn_refresh)
        list_btn_layout.addWidget(btn_migrate)
        left_layout.addLayout(list_btn_layout)

        main_layout.addWidget(left_widget, 1)

        # Right: Preview + actions
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        preview_label = QLabel("<b>Preview:</b>")
        right_layout.addWidget(preview_label)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlaceholderText("Select a profile to preview...")
        right_layout.addWidget(self.preview_text)

        # Action buttons
        action_layout = QVBoxLayout()

        self.btn_load = QPushButton("Load Profile")
        self.btn_load.setEnabled(False)
        self.btn_load.clicked.connect(self._load_profile)
        action_layout.addWidget(self.btn_load)

        self.btn_duplicate = QPushButton("Duplicate...")
        self.btn_duplicate.setEnabled(False)
        self.btn_duplicate.clicked.connect(self._duplicate_profile)
        action_layout.addWidget(self.btn_duplicate)

        self.btn_rename = QPushButton("Rename...")
        self.btn_rename.setEnabled(False)
        self.btn_rename.clicked.connect(self._rename_profile)
        action_layout.addWidget(self.btn_rename)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._delete_profile)
        action_layout.addWidget(self.btn_delete)

        action_layout.addSpacing(10)

        btn_import = QPushButton("Import...")
        btn_import.clicked.connect(self._import_profile)
        action_layout.addWidget(btn_import)

        self.btn_export = QPushButton("Export...")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._export_profile)
        action_layout.addWidget(self.btn_export)

        action_layout.addStretch()

        right_layout.addLayout(action_layout)

        main_layout.addWidget(right_widget, 1)

        root.addLayout(main_layout)

        # Status
        self.status_label = QLabel("Ready")
        root.addWidget(self.status_label)

        # Initial refresh
        self._refresh_list()

    def _refresh_list(self):
        """Refresh profile list from directory."""
        self.profile_list.clear()
        self.preview_text.clear()

        pdir = profiles_dir()
        profiles = sorted(pdir.glob("*.json"))

        if not profiles:
            self.status_label.setText("No profiles found")
            return

        for profile_path in profiles:
            item = QListWidgetItem(profile_path.stem)
            item.setData(Qt.UserRole, str(profile_path))
            self.profile_list.addItem(item)

        self.status_label.setText(f"Found {len(profiles)} profile(s)")

    def _on_selection_changed(self):
        """Update preview when selection changes."""
        items = self.profile_list.selectedItems()
        if not items:
            self.preview_text.clear()
            self.btn_load.setEnabled(False)
            self.btn_duplicate.setEnabled(False)
            self.btn_rename.setEnabled(False)
            self.btn_delete.setEnabled(False)
            self.btn_export.setEnabled(False)
            return

        # Enable buttons
        self.btn_load.setEnabled(True)
        self.btn_duplicate.setEnabled(True)
        self.btn_rename.setEnabled(True)
        self.btn_delete.setEnabled(True)
        self.btn_export.setEnabled(True)

        # Load and preview
        path = Path(items[0].data(Qt.UserRole))
        data = load_json(path)
        if data:
            import json
            self.preview_text.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))
            ok, msg = validate_profile(data)
            if not ok:
                self.status_label.setText(f"⚠️ Validation: {msg}")
            else:
                self.status_label.setText(f"Valid profile: {path.name}")
        else:
            self.preview_text.setPlainText("Error loading profile")
            self.status_label.setText("Error loading profile")

    def _load_profile(self):
        """Load selected profile (emit signal)."""
        items = self.profile_list.selectedItems()
        if not items:
            return

        path = Path(items[0].data(Qt.UserRole))
        data = load_json(path)
        if not data:
            QMessageBox.critical(self, "Load Error", "Failed to load profile")
            return

        ok, msg = validate_profile(data)
        if not ok:
            QMessageBox.warning(self, "Validation Error", f"Profile validation failed:\n{msg}")
            return

        # Emit signal for other pages to catch
        self.profile_loaded.emit(data)
        self.status_label.setText(f"Loaded: {path.name}")
        QMessageBox.information(self, "Profile Loaded",
                               f"Profile '{path.stem}' loaded.\n\n"
                               f"Navigate to the appropriate page (Basic/AIS/etc.) to use it.")

    def _duplicate_profile(self):
        """Duplicate selected profile."""
        items = self.profile_list.selectedItems()
        if not items:
            return

        path = Path(items[0].data(Qt.UserRole))
        new_name, ok = QInputDialog.getText(
            self,
            "Duplicate Profile",
            "Enter new profile name:",
            text=f"{path.stem}_copy"
        )

        if not ok or not new_name:
            return

        if not new_name.endswith('.json'):
            new_name += '.json'

        new_path = profiles_dir() / new_name

        if new_path.exists():
            QMessageBox.warning(self, "Error", f"Profile '{new_name}' already exists")
            return

        try:
            shutil.copy(path, new_path)
            self._refresh_list()
            self.status_label.setText(f"Duplicated: {new_name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to duplicate:\n{e}")

    def _rename_profile(self):
        """Rename selected profile."""
        items = self.profile_list.selectedItems()
        if not items:
            return

        path = Path(items[0].data(Qt.UserRole))
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Profile",
            "Enter new name:",
            text=path.stem
        )

        if not ok or not new_name:
            return

        if not new_name.endswith('.json'):
            new_name += '.json'

        new_path = profiles_dir() / new_name

        if new_path.exists():
            QMessageBox.warning(self, "Error", f"Profile '{new_name}' already exists")
            return

        try:
            path.rename(new_path)
            self._refresh_list()
            self.status_label.setText(f"Renamed to: {new_name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to rename:\n{e}")

    def _delete_profile(self):
        """Delete selected profile."""
        items = self.profile_list.selectedItems()
        if not items:
            return

        path = Path(items[0].data(Qt.UserRole))

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete profile '{path.stem}'?\n\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                path.unlink()
                self._refresh_list()
                self.status_label.setText(f"Deleted: {path.stem}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete:\n{e}")

    def _import_profile(self):
        """Import profile from external location."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Profile",
            "",
            "Profiles (*.json)"
        )

        if not file_path:
            return

        source = Path(file_path)
        dest = profiles_dir() / source.name

        if dest.exists():
            reply = QMessageBox.question(
                self,
                "Overwrite?",
                f"Profile '{source.name}' already exists. Overwrite?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        try:
            shutil.copy(source, dest)
            self._refresh_list()
            self.status_label.setText(f"Imported: {source.name}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import:\n{e}")

    def _export_profile(self):
        """Export selected profile to external location."""
        items = self.profile_list.selectedItems()
        if not items:
            return

        path = Path(items[0].data(Qt.UserRole))

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Profile",
            str(Path.home() / path.name),
            "Profiles (*.json)"
        )

        if not file_path:
            return

        try:
            shutil.copy(path, file_path)
            self.status_label.setText(f"Exported to: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export:\n{e}")

    def _migrate_legacy(self):
        """Migrate profiles from legacy location."""
        result = migrate_legacy_profiles()

        if result["found"] == 0:
            QMessageBox.information(self, "Migration", "No legacy profiles found")
            return

        msg = f"Migration Results:\n\n"
        msg += f"Found: {result['found']}\n"
        msg += f"Migrated: {result['migrated']}\n"
        msg += f"Skipped: {result['skipped']}\n"

        if result['errors']:
            msg += f"\nErrors:\n"
            for err in result['errors'][:5]:  # Show first 5 errors
                msg += f"  • {err}\n"

        QMessageBox.information(self, "Migration Complete", msg)
        self._refresh_list()
